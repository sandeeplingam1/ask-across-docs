"""Background task processing for document uploads"""
import asyncio
from typing import Optional
from io import BytesIO
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import Document
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import get_vector_store
from app.services.file_storage import get_file_storage
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class BackgroundDocumentProcessor:
    """Process documents in the background"""
    
    def __init__(self):
        self.doc_processor = DocumentProcessor(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        self.embedding_service = EmbeddingService()
        self.vector_store = get_vector_store()
        self.file_storage = get_file_storage()
    
    async def process_document(
        self,
        document_id: str,
        engagement_id: str,
        file_content: bytes,
        filename: str,
        session: AsyncSession
    ) -> dict:
        """
        Process a single document asynchronously
        
        Args:
            document_id: Document ID
            engagement_id: Engagement ID
            file_content: File binary content
            filename: Original filename
            session: Database session
            
        Returns:
            Processing result dict
        """
        try:
            # Update status to processing
            document = await session.get(Document, document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            document.status = "processing"
            document.progress = 10
            await session.commit()
            
            logger.info(f"Starting to process document {document_id}: {filename}")
            
            # Extract text with metadata
            extraction_result = self.doc_processor.extract_with_metadata(
                BytesIO(file_content), 
                filename
            )
            text = extraction_result['text']
            pages_info = extraction_result['pages']
            
            document.progress = 30
            await session.commit()
            
            logger.info(f"Extracted {len(text)} characters from {filename}")
            
            # Chunk text with page tracking
            chunks = self.doc_processor.chunk_text(
                text,
                metadata={
                    "document_id": document_id,
                    "filename": filename,
                    "engagement_id": engagement_id
                },
                pages_info=pages_info
            )
            
            if not chunks:
                raise ValueError("No text extracted from document")
            
            document.progress = 50
            await session.commit()
            
            logger.info(f"Created {len(chunks)} chunks from {filename}")
            
            # Generate embeddings in batches
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = await self.embedding_service.embed_batch(chunk_texts)
            
            document.progress = 70
            await session.commit()
            
            logger.info(f"Generated embeddings for {len(chunks)} chunks")
            
            # Store in vector database
            await self.vector_store.add_documents(
                engagement_id=engagement_id,
                document_id=document_id,
                chunks=chunks,
                embeddings=embeddings
            )
            
            document.progress = 90
            await session.commit()
            
            logger.info(f"Stored vectors for {filename}")
            
            # Update document status
            document.status = "completed"
            document.chunk_count = len(chunks)
            document.progress = 100
            document.error_message = None
            
            await session.commit()
            
            logger.info(f"Successfully processed document {document_id}: {filename}")
            
            return {
                "status": "success",
                "document_id": document_id,
                "chunk_count": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}", exc_info=True)
            
            # Update document with error
            document = await session.get(Document, document_id)
            if document:
                document.status = "failed"
                document.error_message = str(e)
                document.progress = 0
                await session.commit()
            
            return {
                "status": "error",
                "document_id": document_id,
                "error": str(e)
            }


async def process_document_task(
    document_id: str,
    engagement_id: str,
    file_path: str,
    filename: str
):
    """
    Background task to process a document
    This can be called by Celery, Azure Functions, or asyncio
    """
    from app.db_session import AsyncSessionLocal
    
    processor = BackgroundDocumentProcessor()
    file_storage = get_file_storage()
    
    async with AsyncSessionLocal() as session:
        try:
            # Read file from storage
            file_content = await file_storage.get_file(file_path)
            
            # Process document
            result = await processor.process_document(
                document_id=document_id,
                engagement_id=engagement_id,
                file_content=file_content,
                filename=filename,
                session=session
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Task failed for document {document_id}: {str(e)}")
            raise
