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
        
        logger.info(f"Worker initialized - batch_size={self.batch_size}, poll_interval={self.poll_interval}s")
    
    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    async def reset_stuck_documents(self):
        """Reset documents stuck in processing state"""
        try:
            async with AsyncSessionLocal() as session:
                threshold = datetime.utcnow() - timedelta(seconds=self.stuck_document_threshold)
                
                query = select(Document).where(
                    Document.status == "processing",
                    ((Document.processing_started_at < threshold) | 
                     (Document.processing_started_at.is_(None)))
                )
                
                result = await session.execute(query)
                stuck_docs = result.scalars().all()
                
                if stuck_docs:
                    logger.warning(f"Found {len(stuck_docs)} stuck documents, resetting to queued")
                    for doc in stuck_docs:
                        doc.status = "queued"
                        doc.progress = 0
                        doc.error_message = None
                        doc.processing_started_at = None
                    await session.commit()
                    logger.info(f"Reset {len(stuck_docs)} stuck documents")
                else:
                    logger.info("No stuck documents found")
        except Exception as e:
            logger.error(f"Error resetting stuck documents: {e}", exc_info=True)
    
    async def process_document(self, document, session):
        """Process a single document with full error isolation"""
        doc_id = document.id
        filename = document.filename
        
        try:
            logger.info(f"Starting document {doc_id}: {filename}")
            
            # Mark as processing
            document.status = "processing"
            document.progress = 10
            document.processing_started_at = datetime.utcnow()
            await session.commit()
            
            # Download file
            logger.debug(f"Downloading {filename} from storage")
            file_content = await asyncio.wait_for(
                self.file_storage.get_file(document.file_path),
                timeout=60.0
            )
            
            # Extract text
            document.progress = 25
            await session.commit()
            logger.debug(f"Extracting text from {filename}")
            
            extraction_result = await asyncio.wait_for(
                asyncio.to_thread(
                    self.doc_processor.extract_with_metadata,
                    BytesIO(file_content),
                    filename
                ),
                timeout=120.0
            )
            
            text = extraction_result['text']
            pages_info = extraction_result['pages']
            
            if not text.strip():
                raise ValueError("No text extracted from document")
            
            # Chunk text
            document.progress = 50
            await session.commit()
            logger.debug(f"Chunking {filename}")
            
            chunks = self.doc_processor.chunk_text(
                text,
                metadata={
                    "document_id": document.id,
                    "filename": document.filename,
                    "engagement_id": document.engagement_id
                },
                pages_info=pages_info
            )
            
            logger.info(f"Created {len(chunks)} chunks for {filename}")
            
            # Generate embeddings
            document.progress = 70
            await session.commit()
            logger.debug(f"Generating embeddings for {len(chunks)} chunks")
            
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = await asyncio.wait_for(
                self.embedding_service.embed_batch(chunk_texts),
                timeout=180.0
            )
            
            # Store in vector database
            document.progress = 90
            await session.commit()
            logger.debug(f"Indexing {filename} in vector store")
            
            await asyncio.wait_for(
                self.vector_store.add_documents(
                    engagement_id=document.engagement_id,
                    document_id=document.id,
                    chunks=chunks,
                    embeddings=embeddings
                ),
                timeout=60.0
            )
            
            # Mark as completed
            document.status = "completed"
            document.chunk_count = len(chunks)
            document.progress = 100
            document.error_message = None
            document.processing_completed_at = datetime.utcnow()
            await session.commit()
            
            logger.info(f"✅ Completed {filename} - {len(chunks)} chunks indexed")
            return True
            
        except asyncio.TimeoutError as e:
            error_msg = f"Timeout during processing: {str(e)}"
            logger.error(f"❌ {filename}: {error_msg}")
            document.status = "failed"
            document.error_message = error_msg[:500]
            document.progress = 0
            await session.commit()
            return False
            
        except Exception as e:
            error_msg = str(e)[:500]
            logger.error(f"❌ {filename}: {error_msg}", exc_info=True)
            try:
                document.status = "failed"
                document.error_message = error_msg
                document.progress = 0
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
    
    async def run(self):
        """Main worker loop"""
        logger.info("🚀 Document Worker Starting...")
        
        # Initialize database
        try:
            await init_db()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            return
        
        # Reset stuck documents on startup
        await self.reset_stuck_documents()
        
        logger.info("📋 Worker ready - waiting for documents...")
        idle_count = 0
        
        while self.running:
            try:
                processed = await self.process_batch()
                
                if processed > 0:
                    idle_count = 0
                    logger.info(f"Batch complete - processed {processed} document(s)")
                else:
                    idle_count += 1
                    if idle_count % 6 == 1:  # Log every minute
                        logger.debug("No documents in queue, waiting...")
                
                # Wait before next poll
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
        
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
