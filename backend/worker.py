#!/usr/bin/env python3
"""
Standalone background worker process for document processing.
This runs separately from the API to avoid resource contention.

Usage:
    python worker.py
    
Environment variables:
    WORKER_BATCH_SIZE: Number of documents to process in parallel (default: 1)
    WORKER_POLL_INTERVAL: Seconds between checking for new documents (default: 10)
    WORKER_ENABLE: Set to 'false' to disable worker (default: true)
"""
import asyncio
import logging
import sys
import signal
from datetime import datetime, timedelta
from sqlalchemy import select

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [WORKER] %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Import app modules
from app.database import Document
from app.db_session import AsyncSessionLocal, init_db
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import get_vector_store
from app.services.file_storage import get_file_storage
from app.config import settings
from io import BytesIO


class DocumentWorker:
    """Standalone worker for processing queued documents"""
    
    def __init__(self):
        self.running = True
        self.batch_size = 1  # Process 1 document at a time (sequential processing for stability)
        self.poll_interval = 10  # Check every 10 seconds
        self.stuck_document_threshold = 600  # 10 minutes
        
        # Initialize services
        self.doc_processor = DocumentProcessor(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        self.embedding_service = EmbeddingService()
        self.vector_store = get_vector_store()
        self.file_storage = get_file_storage()
        
        # Initialize Service Bus (if enabled)
        from app.services.service_bus import get_service_bus
        self.service_bus = get_service_bus()
        
        if self.service_bus:
            logger.info(f"Worker initialized with SERVICE BUS (instant processing) - batch_size={self.batch_size}")
        else:
            logger.info(f"Worker initialized with POLLING (fallback) - batch_size={self.batch_size}, poll_interval={self.poll_interval}s")
    
    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    async def janitor_clean_stuck_leases(self):
        """FIX 2: Janitor that cleans stuck leases every minute"""
        try:
            async with AsyncSessionLocal() as session:
                from datetime import datetime, timedelta
                now = datetime.utcnow()
                ten_minutes_ago = now - timedelta(minutes=10)
                
                # Find stuck documents
                query = select(Document).where(
                    Document.status == "processing"
                )
                result = await session.execute(query)
                processing_docs = result.scalars().all()
                
                reset_count = 0
                for doc in processing_docs:
                    should_reset = False
                    reason = ""
                    
                    # Rule 1: Lease expired
                    if doc.lease_expires_at and doc.lease_expires_at < now:
                        should_reset = True
                        reason = f"lease expired at {doc.lease_expires_at}"
                    # Rule 2: Processing too long (>10 minutes)
                    elif doc.processing_started_at and doc.processing_started_at < ten_minutes_ago:
                        should_reset = True
                        reason = f"processing started {doc.processing_started_at}, >10 min ago"
                    
                    if should_reset:
                        logger.warning(f"🧹 Janitor: Resetting stuck doc {doc.filename} ({reason})")
                        doc.status = "queued"
                        doc.lease_expires_at = None
                        doc.message_enqueued_at = None  # Allow re-triggering
                        doc.processing_attempts = min(doc.processing_attempts + 1, doc.max_retries)
                        reset_count += 1
                
                if reset_count > 0:
                    await session.commit()
                    logger.info(f"🧹 Janitor: Reset {reset_count} stuck documents")
                    
        except Exception as e:
            logger.error(f"Janitor error: {e}", exc_info=True)
    
    async def recover_expired_leases(self):
        """Find and release expired leases for automatic retry"""
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import text
                
                # Call stored procedure to find expired leases
                result = await session.execute(text("EXEC find_expired_leases"))
                expired_docs = result.fetchall()
                
                if expired_docs:
                    logger.warning(f"Found {len(expired_docs)} expired leases, releasing for retry")
                    for doc_row in expired_docs:
                        doc_id = doc_row[0]
                        filename = doc_row[1]
                        attempts = doc_row[2]
                        max_retries = doc_row[3]
                        logger.info(f"Releasing expired lease: {filename} (attempt {attempts}/{max_retries})")
                        
                        # Release lease (will auto-queue for retry)
                        await self.release_lease(session, doc_id, success=False, error_message="Lease expired - worker may have crashed")
                    
                    logger.info(f"Released {len(expired_docs)} expired leases")
        except Exception as e:
            logger.error(f"Error recovering expired leases: {e}", exc_info=True)
    
    async def reset_stuck_documents(self):
        """Legacy method - now handled by lease expiration recovery"""
        # This method is replaced by recover_expired_leases()
        # Keep it for backward compatibility but log a warning
        logger.info("reset_stuck_documents() called - now handled by recover_expired_leases() with lease management")
        await self.recover_expired_leases()
    
    async def acquire_lease(self, session, document_id: str) -> bool:
        """Acquire lease for document using stored procedure"""
        try:
            from sqlalchemy import text
            # Use RETURN value from stored procedure
            result = await session.execute(
                text("""
                    DECLARE @acquired BIT;
                    EXEC acquire_document_lease :doc_id, 5, @acquired OUTPUT;
                    SELECT @acquired as acquired;
                """),
                {"doc_id": document_id}
            )
            row = result.fetchone()
            acquired = bool(row[0]) if row else False
            await session.commit()  # Commit the lease acquisition
            return acquired
        except Exception as e:
            logger.error(f"Failed to acquire lease for {document_id}: {e}")
            return False
    
    async def release_lease(self, session, document_id: str, success: bool, error_message: str = None):
        """Release lease for document using stored procedure"""
        try:
            from sqlalchemy import text
            await session.execute(
                text("EXEC release_document_lease @p_document_id = :doc_id, @p_success = :success, @p_error_message = :error"),
                {
                    "doc_id": document_id,
                    "success": 1 if success else 0,
                    "error": error_message[:1000] if error_message else None
                }
            )
            
            # FIX 1: Clear the "message in queue" flag when worker finishes
            doc = await session.get(Document, document_id)
            if doc:
                doc.message_enqueued_at = None
                logger.debug(f"Cleared message_enqueued_at flag for {document_id}")
            
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to release lease for {document_id}: {e}")
    
    async def process_document(self, document, session):
        """Process a single document with full error isolation and lease management"""
        doc_id = document.id
        filename = document.filename
        lease_acquired = False
        
        logger.info(f"🔴 ENTERED process_document() for {filename} (doc_id={doc_id})")
        
        try:
            import time
            start_time = time.time()
            
            logger.info(f"🟡 DOC {doc_id}: About to acquire lease...")
            
            # CRITICAL: Acquire lease with TIMEOUT
            try:
                lease_acquired = await asyncio.wait_for(
                    self.acquire_lease(session, doc_id),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.error(f"❌ LEASE ACQUISITION TIMED OUT (10s) for {filename} - DB HANG - ABANDONING for retry")
                return False  # Abandon and retry
            
            if not lease_acquired:
                logger.warning(f"⚠️ Lease NOT acquired for {filename} - another worker holds it OR max retries hit. ABANDONING message for retry.")
                # ABANDON MESSAGE: Lease contention is NOT success - retry later
                # If another worker has the lease, they'll finish it
                # If max retries hit, stored procedure will mark it failed
                # Either way, we should NOT complete the message
                return False  # Abandon and retry
            
            logger.info(f"🟡 DOC {doc_id}: LEASE ACQUIRED (%.1fs)", time.time() - start_time)
            
            # Refresh document to get updated values
            await session.refresh(document)
            logger.info(f"Starting document {doc_id} (attempt {document.processing_attempts}/{document.max_retries}): {filename}")
            
            # Update progress
            document.progress = 10
            await session.commit()
            
            # Download file
            phase_start = time.time()
            logger.info(f"🟡 DOC {doc_id}: DOWNLOADING file from storage")
            file_content = await asyncio.wait_for(
                self.file_storage.get_file(document.file_path),
                timeout=60.0
            )
            logger.info(f"🟡 DOC {doc_id}: DOWNLOAD DONE (%.1fs, %d bytes)", time.time() - phase_start, len(file_content))
            
            # Extract text
            document.progress = 25
            await session.commit()
            
            phase_start = time.time()
            logger.info(f"🟡 DOC {doc_id}: TEXT EXTRACTION START (file_type={document.file_type})")
            
            # PRODUCTION FIX: Longer timeout for AI Document Intelligence
            # AI extraction can take 2-5 minutes for complex documents
            extraction_timeout = 600  # 10 minutes max
            
            try:
                extraction_result = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.doc_processor.extract_with_metadata,
                        BytesIO(file_content),
                        filename
                    ),
                    timeout=extraction_timeout
                )
                elapsed = time.time() - phase_start
                logger.info(f"✅ DOC {doc_id}: TEXT EXTRACTION DONE ({elapsed:.1f}s)")
                
            except asyncio.TimeoutError:
                elapsed = time.time() - phase_start
                raise ValueError(f"Text extraction timed out after {elapsed:.1f}s (max: {extraction_timeout}s). Document may be too complex or DI service is slow.")
            except Exception as e:
                elapsed = time.time() - phase_start
                logger.error(f"❌ DOC {doc_id}: TEXT EXTRACTION FAILED after {elapsed:.1f}s: {type(e).__name__}: {str(e)}")
                raise
            
            text = extraction_result['text']
            pages_info = extraction_result['pages']
            
            if not text.strip():
                raise ValueError("No text extracted from document")
            
            logger.info(f"🟡 DOC {doc_id}: EXTRACTED %d chars", len(text))
            
            phase_start = time.time()
            logger.info(f"🟡 DOC {doc_id}: CHUNKING START")
            chunks = self.doc_processor.chunk_text(
                text,
                metadata={
                    "document_id": document.id,
                    "filename": document.filename,
                    "engagement_id": document.engagement_id
                },
                pages_info=pages_info
            )
            logger.info(f"🟡 DOC {doc_id}: CHUNKING DONE (%.1fs, %d chunks)", time.time() - phase_start, len(chunks))
            
            logger.info(f"Created {len(chunks)} chunks for {filename}")
            
            # Generate embeddings
            document.progress = 70
            await session.commit()
            
            phase_start = time.time()
            logger.info(f"🟡 DOC {doc_id}: EMBEDDINGS START ({len(chunks)} chunks)")
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = await asyncio.wait_for(
                self.embedding_service.embed_batch(chunk_texts),
                timeout=180.0
            )
            logger.info(f"🟡 DOC {doc_id}: EMBEDDINGS DONE (%.1fs)", time.time() - phase_start)
            
            # Store in vector database
            
            phase_start = time.time()
            logger.info(f"🟡 DOC {doc_id}: VECTOR STORE START")
            await asyncio.wait_for(
                self.vector_store.add_documents(
                    engagement_id=document.engagement_id,
                    document_id=document.id,
                    chunks=chunks,
                    embeddings=embeddings
                ),
                timeout=60.0
            )
            logger.info(f"🟡 DOC {doc_id}: VECTOR STORE DONE (%.1fs)", time.time() - phase_start)
            
            # Update chunk count
            document.chunk_count = len(chunks)
            document.progress = 100
            await session.commit()
            
            # Release lease with SUCCESS
            await self.release_lease(session, doc_id, success=True)
            
            # Refresh to see final status
            await session.refresh(document)
            total_time = time.time() - start_time
            logger.info(f"🟢 DOC {doc_id}: COMPLETED {filename} - {len(chunks)} chunks - %.1fs total", total_time)
            logger.info(f"✅ Completed {filename} - {len(chunks)} chunks indexed - Status: {document.status}")
            return True
            
        except asyncio.TimeoutError as e:
            error_msg = f"Timeout during processing: {str(e)}"
            logger.error(f"❌ {filename}: {error_msg}")
            
            # Release lease with FAILURE (will retry if attempts < max_retries)
            if lease_acquired:
                await self.release_lease(session, doc_id, success=False, error_message=error_msg)
            else:
                document.status = "failed"
                document.error_message = error_msg[:500]
                await session.commit()
            return False
            
        except Exception as e:
            error_msg = str(e)[:500]
            logger.error(f"❌ {filename}: {error_msg}", exc_info=True)
            
            # Release lease with FAILURE
            if lease_acquired:
                await self.release_lease(session, doc_id, success=False, error_message=error_msg)
            else:
                try:
                    document.status = "failed"
                    document.error_message = error_msg
                    await session.commit()
                except:
                    logger.error(f"Failed to update error status for {doc_id}")
            return False
    
    async def process_batch(self):
        """Process a batch of queued documents"""
        try:
            async with AsyncSessionLocal() as session:
                # Get queued documents
                query = select(Document).where(
                    Document.status == "queued"
                ).order_by(Document.updated_at).limit(self.batch_size)
                
                result = await session.execute(query)
                queued_docs = result.scalars().all()
                
                if not queued_docs:
                    return 0
                
                logger.info(f"Processing {len(queued_docs)} queued document(s)")
                
                # Process each document
                processed = 0
                for document in queued_docs:
                    try:
                        success = await self.process_document(document, session)
                        if success:
                            processed += 1
                    except Exception as e:
                        logger.error(f"Failed to process document {document.id}: {e}", exc_info=True)
                    finally:
                        # Force garbage collection after each document to free memory
                        import gc
                        gc.collect()
                    
                    # Small delay between documents
                    await asyncio.sleep(2)
                
                return processed
                
        except Exception as e:
            logger.error(f"Error in batch processing: {e}", exc_info=True)
            return 0
    
    async def auto_renew_lock(self, message, receiver, document_id: str):
        """Background task to automatically renew message lock during long processing"""
        try:
            while True:
                await asyncio.sleep(120)  # Renew every 2 minutes (lock is 5 min)
                try:
                    # Run sync renewal in thread executor
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, receiver.renew_message_lock, message)
                    logger.info(f"🔄 Renewed lock for document {document_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Lock renewal failed for {document_id}: {str(e)}")
                    break
        except asyncio.CancelledError:
            logger.debug(f"Lock renewal stopped for {document_id}")
    
    async def process_from_service_bus(self):
        """Process documents from Service Bus queue (event-driven)"""
        try:
            # Receive up to 4 messages (parallel processing)
            logger.info("🔍 Attempting to receive messages from Service Bus...")
            messages = self.service_bus.receive_messages(max_wait_time=30, max_message_count=4)
            
            if not messages:
                logger.info("📭 No messages received from Service Bus")
                return 0
            
            logger.info(f"📥 Received {len(messages)} message(s) from Service Bus")
            logger.info(f"📦 Message details: {[msg.get('document_id', 'unknown') for msg in messages]}")
            
            processed = 0
            failed = 0
            receivers_to_close = set()
            
            async with AsyncSessionLocal() as session:
                for msg_data in messages:
                    document_id = None
                    renewal_task = None
                    try:
                        document_id = msg_data["document_id"]
                        receiver = msg_data.get("receiver")
                        message = msg_data.get("message")
                        
                        if receiver:
                            receivers_to_close.add(receiver)
                        
                        logger.info(f"🔄 Processing document {document_id} from Service Bus")
                        
                        # Get document from database
                        result = await session.execute(
                            select(Document).where(Document.id == document_id)
                        )
                        document = result.scalar_one_or_none()
                        
                        if not document:
                            logger.warning(f"⚠️ Document {document_id} not found in database")
                            if receiver and message:
                                self.service_bus.complete_message(message, receiver)
                            continue
                        
                        if document.status != "queued":
                            logger.warning(f"⚠️ Document {document_id} already {document.status}, skipping")
                            if receiver and message:
                                self.service_bus.complete_message(message, receiver)
                            continue
                        
                        # Start automatic lock renewal in background
                        if receiver and message:
                            renewal_task = asyncio.create_task(
                                self.auto_renew_lock(message, receiver, document_id)
                            )
                            logger.info(f"🔐 Started lock renewal for {document_id}")
                        
                        # Process the document
                        logger.info(f"🚀 Starting process_document for {document.filename}...")
                        success = await self.process_document(document, session)
                        logger.info(f"{'✅' if success == True else '❌' if success == False else '⏭️'} process_document returned success={success} for {document.filename}")
                        
                        # Stop lock renewal
                        if renewal_task:
                            renewal_task.cancel()
                            try:
                                await renewal_task
                            except asyncio.CancelledError:
                                pass
                        
                        if success is True:
                            processed += 1
                            # Complete message (remove from queue)
                            if receiver and message:
                                self.service_bus.complete_message(message, receiver)
                                logger.info(f"✅ SUCCESS: Completed processing and removed message for {document.filename}")
                        else:
                            # ANY failure (False) → abandon for retry
                            failed += 1
                            if receiver and message:
                                self.service_bus.abandon_message(message, receiver)
                                logger.warning(f"❌ ABANDONED: Failed processing, message will retry: {document.filename}")
                            
                    except Exception as e:
                        # Stop lock renewal on error
                        if renewal_task:
                            renewal_task.cancel()
                            try:
                                await renewal_task
                            except asyncio.CancelledError:
                                pass
                        
                        failed += 1
                        logger.error(f"❌ Error processing message for document {document_id}: {e}", exc_info=True)
                        # Abandon message for retry
                        if "receiver" in msg_data and "message" in msg_data:
                            try:
                                self.service_bus.abandon_message(msg_data["message"], msg_data["receiver"])
                            except:
                                pass
            
            # Close all receivers
            for receiver in receivers_to_close:
                try:
                    receiver.close()
                except:
                    pass
            
            logger.info(f"📊 Batch complete: {processed} successful, {failed} failed")
            return processed
            
        except Exception as e:
            logger.error(f"❌ CRITICAL: Error in Service Bus processing: {e}", exc_info=True)
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return 0
    
    async def janitor_loop(self):
        """FIX 2: Janitor background task that runs every 1 minute to clean stuck leases"""
        logger.info("🧹 Janitor loop started (runs every 60 seconds)")
        
        while self.running:
            try:
                await asyncio.sleep(60)  # 1 minute
                if self.running:
                    await self.janitor_clean_stuck_leases()
            except Exception as e:
                logger.error(f"Janitor loop error: {e}", exc_info=True)
    
    async def lease_recovery_loop(self):
        """Background task to recover expired leases every 5 minutes"""
        logger.info("Lease recovery loop started (runs every 5 minutes)")
        
        while self.running:
            try:
                await asyncio.sleep(300)  # 5 minutes
                if self.running:
                    await self.recover_expired_leases()
            except Exception as e:
                logger.error(f"Error in lease recovery loop: {e}", exc_info=True)
    
    async def run(self):
        """Main worker loop with Service Bus support"""
        logger.info("🚀 Document Worker Starting...")
        
        # Initialize database
        try:
            await init_db()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            return
        
        # Recover expired leases on startup
        await self.recover_expired_leases()
        
        # Start background tasks
        recovery_task = asyncio.create_task(self.lease_recovery_loop())
        janitor_task = asyncio.create_task(self.janitor_loop())  # FIX 2: Janitor every 1 minute
        
        if self.service_bus:
            logger.info("📋 Worker ready - listening for Service Bus messages (instant processing)...")
            logger.info("🔒 Lease management enabled (5-minute expiration, auto-retry up to 3 attempts)")
        else:
            logger.info("📋 Worker ready - polling database (fallback mode)...")
        
        idle_count = 0
        
        try:
            while self.running:
                try:
                    # Use Service Bus if available, otherwise fall back to polling
                    if self.service_bus:
                        processed = await self.process_from_service_bus()
                    else:
                        processed = await self.process_batch()
                    
                    if processed > 0:
                        idle_count = 0
                        logger.info(f"Batch complete - processed {processed} document(s)")
                    else:
                        idle_count += 1
                        if idle_count % 6 == 1:  # Log every minute
                            logger.debug("No documents/messages in queue, waiting...")
                    
                    # Shorter wait with Service Bus (it has its own timeout)
                    wait_time = 5 if self.service_bus else self.poll_interval
                    await asyncio.sleep(wait_time)
                    
                except Exception as e:
                    logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
                    await asyncio.sleep(self.poll_interval)
        finally:
            # Cancel recovery task on shutdown
            recovery_task.cancel()
            try:
                await recovery_task
            except asyncio.CancelledError:
                pass
        
        logger.info("👋 Worker shutdown complete")


async def main():
    """Entry point"""
    worker = DocumentWorker()
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, worker.handle_shutdown)
    signal.signal(signal.SIGTERM, worker.handle_shutdown)
    
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
        sys.exit(0)
