"""Background processor for queued documents - processes automatically in batches"""
import asyncio
import logging
from sqlalchemy import select
from app.database import Document
from app.db_session import async_session_maker
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
    """Process queued documents in small batches automatically"""
    while True:
        try:
            async with async_session_maker() as session:
                # Get up to 3 queued documents at a time
                query = select(Document).where(
                    Document.status == "queued"
                ).limit(3)
                
                result = await session.execute(query)
                queued_docs = result.scalars().all()
                
                if not queued_docs:
                    # No documents to process, wait and check again
                    await asyncio.sleep(10)
                    continue
                
                logger.info(f"Processing batch of {len(queued_docs)} queued documents")
                
                for document in queued_docs:
                    try:
                        document.status = "processing"
                        await session.commit()
                        
                        # Read file content
                        async with aiofiles.open(document.file_path, 'rb') as f:
                            file_content = await f.read()
                        
                        # Extract text
                        extraction_result = doc_processor.extract_with_metadata(
                            BytesIO(file_content), 
                            document.filename
                        )
                        text = extraction_result['text']
                        pages_info = extraction_result['pages']
                        
                        if not text.strip():
                            raise ValueError("No text extracted from document")
                        
                        # Chunk text
                        chunks = doc_processor.chunk_text(
                            text,
                            metadata={
                                "document_id": document.id,
                                "filename": document.filename,
                                "engagement_id": document.engagement_id
                            },
                            pages_info=pages_info
                        )
                        
                        # Generate embeddings
                        chunk_texts = [chunk["text"] for chunk in chunks]
                        embeddings = await embedding_service.embed_batch(chunk_texts)
                        
                        # Store in vector database
                        await vector_store.add_documents(
                            engagement_id=document.engagement_id,
                            document_id=document.id,
                            chunks=chunks,
                            embeddings=embeddings
                        )
                        
                        # Update document status
                        document.status = "completed"
                        document.chunk_count = len(chunks)
                        document.progress = 100
                        await session.commit()
                        
                        logger.info(f"Successfully processed document {document.id} ({document.filename})")
                        
                    except Exception as e:
                        logger.error(f"Failed to process document {document.id}: {str(e)}", exc_info=True)
                        document.status = "failed"
                        document.error_message = str(e)
                        await session.commit()
                
                # Small delay between batches
                await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"Error in background processor: {str(e)}", exc_info=True)
            await asyncio.sleep(10)


def start_background_processor():
    """Start the background processor task"""
    asyncio.create_task(process_queued_documents_batch())
    logger.info("Background document processor started")
