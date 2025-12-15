"""Background processor for queued documents - processes automatically in batches"""
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select
from app.database import Document
from app.db_session import AsyncSessionLocal
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import get_vector_store
from app.config import settings
import aiofiles
from io import BytesIO

logger = logging.getLogger(__name__)

doc_processor = DocumentProcessor(
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap
)
embedding_service = EmbeddingService()
vector_store = get_vector_store()


async def process_queued_documents_batch():
    """Process queued documents in batches automatically"""
    logger.info("Background processor starting")
    
    # Wait 10 seconds before starting to let app fully initialize
    await asyncio.sleep(10)
    
    # Reset stuck documents on startup
    try:
        async with AsyncSessionLocal() as session:
            from datetime import datetime, timedelta
            ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
            
            stuck_query = select(Document).where(
                Document.status == "processing",
                (Document.processing_started_at < ten_minutes_ago) | 
                (Document.processing_started_at.is_(None))
            )
            
            result = await session.execute(stuck_query)
            stuck_docs = result.scalars().all()
            
            if stuck_docs:
                logger.info(f"Resetting {len(stuck_docs)} stuck documents")
                for doc in stuck_docs:
                    doc.status = "queued"
                    doc.progress = 0
                    doc.error_message = None
                    doc.processing_started_at = None
                await session.commit()
    except Exception as e:
        logger.error(f"Error resetting stuck documents: {e}")
        # Continue anyway
    
    logger.info("Background processor main loop started")
    
    while True:
        try:
            async with AsyncSessionLocal() as session:
                # Process ONE document at a time for stability
                query = select(Document).where(
                    Document.status == "queued"
                ).limit(1)
                
                result = await session.execute(query)
                queued_docs = result.scalars().all()
                
                if not queued_docs:
                    # No documents to process, wait and check again
                    await asyncio.sleep(10)
                    continue
                
                logger.info(f"Processing {len(queued_docs)} document(s)")
                
                for document in queued_docs:
                    # Process each document with full error isolation
                    try:
                        logger.info(f"Processing document {document.id}: {document.filename}")
                        document.status = "processing"
                        document.progress = 10
                        document.processing_started_at = datetime.utcnow()
                        await session.commit()
                        
                        # Download file from blob storage with timeout
                        from app.services.file_storage import get_file_storage
                        file_storage = get_file_storage()
                        
                        try:
                            file_content = await asyncio.wait_for(
                                file_storage.get_file(document.file_path),
                                timeout=60.0  # 60 second timeout for download
                            )
                        except asyncio.TimeoutError:
                            raise ValueError("File download timeout - file may be too large or storage is slow")
                        
                        # Extract text
                        document.progress = 25
                        await session.commit()
                        
                        try:
                            extraction_result = await asyncio.wait_for(
                                asyncio.to_thread(
                                    doc_processor.extract_with_metadata,
                                    BytesIO(file_content),
                                    document.filename
                                ),
                                timeout=120.0  # 2 minute timeout for extraction
                            )
                        except asyncio.TimeoutError:
                            raise ValueError("Text extraction timeout - document may be too complex or corrupted")
                        
                        text = extraction_result['text']
                        pages_info = extraction_result['pages']
                        
                        if not text.strip():
                            raise ValueError("No text extracted from document - file may be empty or corrupted")
                        
                        # Chunk text
                        document.progress = 50
                        await session.commit()
                        
                        chunks = doc_processor.chunk_text(
                            text,
                            metadata={
                                "document_id": document.id,
                                "filename": document.filename,
                                "engagement_id": document.engagement_id
                            },
                            pages_info=pages_info
                        )
                        
                        logger.info(f"Document {document.id}: Created {len(chunks)} chunks")
                        
                        # Generate embeddings
                        document.progress = 70
                        await session.commit()
                        
                        chunk_texts = [chunk["text"] for chunk in chunks]
                        
                        try:
                            embeddings = await asyncio.wait_for(
                                embedding_service.embed_batch(chunk_texts),
                                timeout=180.0  # 3 minute timeout for embeddings
                            )
                        except asyncio.TimeoutError:
                            raise ValueError(f"Embedding generation timeout - {len(chunks)} chunks may be too many")
                        
                        # Store in vector database
                        document.progress = 90
                        await session.commit()
                        
                        try:
                            await asyncio.wait_for(
                                vector_store.add_documents(
                                    engagement_id=document.engagement_id,
                                    document_id=document.id,
                                    chunks=chunks,
                                    embeddings=embeddings
                                ),
                                timeout=60.0  # 1 minute timeout for vector store
                            )
                        except asyncio.TimeoutError:
                            raise ValueError("Vector store indexing timeout")
                        
                        # Update document status
                        document.status = "completed"
                        document.chunk_count = len(chunks)
                        document.progress = 100
                        document.error_message = None
                        document.processing_completed_at = datetime.utcnow()  # SET COMPLETION TIME
                        await session.commit()
                        
                        logger.info(f"✅ Successfully processed document {document.id} ({document.filename}) - {len(chunks)} chunks")
                        
                    except Exception as e:
                        # Mark document as failed but keep processing others
                        error_msg = str(e)[:500]
                        logger.error(f"Failed to process document {document.id}: {error_msg}")
                        try:
                            document.status = "failed"
                            document.error_message = error_msg
                            document.progress = 0
                            await session.commit()
                        except:
                            pass  # Even if we can't update, continue processing
                
                # Brief pause between documents
                await asyncio.sleep(2)
                
        except Exception as e:
            # Catch any loop-level errors and continue
            logger.error(f"Background processor error: {str(e)}")
            await asyncio.sleep(10)


_background_task = None

def _task_done_callback(task):
    """Callback when background task completes (it shouldn't!)"""
    try:
        task.result()  # This will raise if task failed
        logger.warning("Background processor task completed unexpectedly")
    except Exception as e:
        logger.error(f"Background processor task failed: {str(e)}", exc_info=True)

def start_background_processor():
    """Start the background processor task"""
    global _background_task
    try:
        loop = asyncio.get_running_loop()
        _background_task = loop.create_task(process_queued_documents_batch())
        _background_task.add_done_callback(_task_done_callback)
        logger.info("Background document processor task created")
    except Exception as e:
        logger.error(f"Failed to start background processor: {str(e)}", exc_info=True)
