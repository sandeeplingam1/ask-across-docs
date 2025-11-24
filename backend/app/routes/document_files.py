"""API route to serve document files"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import Document
from app.db_session import get_session
from fastapi import Depends
import os

router = APIRouter(prefix="/api/documents", tags=["document-files"])


@router.get("/{document_id}/file")
async def get_document_file(
    document_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Serve the original document file for viewing"""
    document = await session.get(Document, document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not document.file_path or not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="Document file not found on disk")
    
    # Determine media type
    media_type = document.file_type or "application/octet-stream"
    
    return FileResponse(
        path=document.file_path,
        filename=document.filename,
        media_type=media_type
    )
