"""
Question Template Library routes
Allows users to upload, manage, and reuse question templates across engagements
"""
import logging
import os
import json
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc

from app.db_session import get_session
from app.database import QuestionTemplate
from app.services.file_storage import FileStorage
from app.routes.questions import _parse_questions_from_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/question-templates", tags=["question_templates"])


@router.get("/", response_model=List[Dict[str, Any]])
async def list_question_templates(session: AsyncSession = Depends(get_session)):
    """Get all question templates, sorted by most recent first"""
    try:
        query = select(QuestionTemplate).order_by(desc(QuestionTemplate.created_at))
        result = await session.execute(query)
        templates = result.scalars().all()
        
        template_list = []
        for template in templates:
            template_list.append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "filename": template.filename,
                "file_type": template.file_type,
                "file_size": template.file_size,
                "question_count": template.question_count,
                "created_at": template.created_at.isoformat() if template.created_at else None,
                "updated_at": template.updated_at.isoformat() if template.updated_at else None
            })
        
        logger.info(f"Retrieved {len(template_list)} question templates")
        return template_list
        
    except Exception as e:
        logger.error(f"Error listing question templates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")


@router.get("/{template_id}", response_model=Dict[str, Any])
async def get_question_template(template_id: str, session: AsyncSession = Depends(get_session)):
    """Get a specific question template with parsed questions"""
    try:
        query = select(QuestionTemplate).filter(QuestionTemplate.id == template_id)
        result = await session.execute(query)
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(status_code=404, detail="Question template not found")
        
        # Parse questions JSON
        questions = []
        if template.questions_json:
            try:
                questions = json.loads(template.questions_json)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse questions JSON for template {template_id}")
        
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "filename": template.filename,
            "file_type": template.file_type,
            "file_size": template.file_size,
            "question_count": template.question_count,
            "questions": questions,
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving question template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve template: {str(e)}")


@router.post("/", response_model=Dict[str, Any])
async def upload_question_template(
    name: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    """Upload a new question template"""
    try:
        # Validate file type
        file_ext = os.path.splitext(file.filename)[1].lower()
        allowed_types = ['.txt', '.docx', '.doc']
        if file_ext not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_types)}"
            )
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Store file in blob storage
        file_storage = FileStorage()
        file_path = f"question-templates/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        blob_url = await file_storage.upload_file(
            file_content=file_content,
            filename=file.filename,
            file_path=file_path
        )
        
        logger.info(f"Uploaded question template file to blob: {blob_url}")
        
        # Parse questions from the file
        questions = []
        try:
            # Extract text based on file type
            if file_ext == '.docx':
                import io
                from docx import Document as DocxDocument
                doc = DocxDocument(io.BytesIO(file_content))
                text = '\n'.join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
            else:
                # Handle text files
                try:
                    text = file_content.decode('utf-8')
                except UnicodeDecodeError:
                    text = file_content.decode('latin-1')
            
            # Parse questions using the existing parser
            questions = _parse_questions_from_text(text)
            logger.info(f"Parsed {len(questions)} questions from template file")
        except Exception as parse_error:
            logger.warning(f"Failed to parse questions from template: {str(parse_error)}")
            # Continue anyway - we still save the template
        
        # Create template record
        template = QuestionTemplate(
            name=name,
            description=description,
            filename=file.filename,
            file_path=file_path,
            file_type=file_ext,
            file_size=file_size,
            question_count=len(questions),
            questions_json=json.dumps(questions) if questions else None
        )
        
        session.add(template)
        await session.commit()
        await session.refresh(template)
        
        logger.info(f"Created question template: {template.id} - {name}")
        
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "filename": template.filename,
            "file_type": template.file_type,
            "file_size": template.file_size,
            "question_count": template.question_count,
            "questions": questions,
            "created_at": template.created_at.isoformat() if template.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading question template: {str(e)}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to upload template: {str(e)}")


@router.delete("/{template_id}")
async def delete_question_template(template_id: str, session: AsyncSession = Depends(get_session)):
    """Delete a question template and its associated file"""
    try:
        query = select(QuestionTemplate).filter(QuestionTemplate.id == template_id)
        result = await session.execute(query)
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(status_code=404, detail="Question template not found")
        
        # Delete file from blob storage
        try:
            file_storage = FileStorage()
            await file_storage.delete_file(template.file_path)
            logger.info(f"Deleted template file from blob: {template.file_path}")
        except Exception as file_error:
            logger.warning(f"Failed to delete template file from blob: {str(file_error)}")
            # Continue with DB deletion anyway
        
        # Delete from database
        await session.delete(template)
        await session.commit()
        
        logger.info(f"Deleted question template: {template_id}")
        
        return {
            "success": True,
            "message": f"Question template '{template.name}' deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting question template {template_id}: {str(e)}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {str(e)}")


@router.post("/{template_id}/apply/{engagement_id}")
async def apply_template_to_engagement(
    template_id: str,
    engagement_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Apply a question template to an engagement by creating copies of the questions"""
    try:
        from app.database import Engagement, QuestionAnswer
        
        # Verify template exists
        template_query = select(QuestionTemplate).filter(QuestionTemplate.id == template_id)
        template_result = await session.execute(template_query)
        template = template_result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(status_code=404, detail="Question template not found")
        
        # Verify engagement exists
        engagement_query = select(Engagement).filter(Engagement.id == engagement_id)
        engagement_result = await session.execute(engagement_query)
        engagement = engagement_result.scalar_one_or_none()
        
        if not engagement:
            raise HTTPException(status_code=404, detail="Engagement not found")
        
        # Parse questions from template
        questions = []
        if template.questions_json:
            try:
                questions = json.loads(template.questions_json)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Failed to parse template questions")
        
        if not questions:
            raise HTTPException(status_code=400, detail="Template has no questions to apply")
        
        # Create placeholder Q&A records for each question
        created_count = 0
        for question in questions:
            qa = QuestionAnswer(
                engagement_id=engagement_id,
                question=question,
                answer="",  # Empty answer - to be filled by user
                confidence="pending"
            )
            session.add(qa)
            created_count += 1
        
        await session.commit()
        
        logger.info(f"Applied template {template_id} to engagement {engagement_id}: {created_count} questions")
        
        return {
            "success": True,
            "message": f"Applied {created_count} questions from template '{template.name}' to engagement",
            "questions_added": created_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying template {template_id} to engagement {engagement_id}: {str(e)}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to apply template: {str(e)}")
