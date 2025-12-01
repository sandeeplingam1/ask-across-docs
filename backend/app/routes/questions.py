"""API routes for question answering"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db_session import get_session
from app.database import Engagement, QuestionAnswer
from app.models import (
    QuestionRequest,
    AnswerResponse,
    BatchQuestionRequest,
    BatchAnswerResponse,
    SourceChunk
)
from app.services.qa_service import QAService
import json
from datetime import datetime

router = APIRouter(prefix="/api/engagements/{engagement_id}", tags=["questions"])

qa_service = QAService()


@router.post("/ask", response_model=AnswerResponse)
async def ask_question(
    engagement_id: str,
    request: QuestionRequest,
    session: AsyncSession = Depends(get_session)
):
    """Ask a single question about engagement documents"""
    # Verify engagement exists
    engagement = await session.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    # Get answer from QA service
    result = await qa_service.answer_question(
        engagement_id=engagement_id,
        question=request.question,
        max_sources=request.max_sources
    )
    
    # Format sources
    sources = []
    if request.include_sources:
        for source in result["sources"]:
            sources.append(SourceChunk(
                document_id=source["document_id"],
                document_name=source.get("filename", ""),
                chunk_text=source["text"],
                similarity_score=source["similarity_score"],
                page_number=source.get("page_number"),
                page_numbers=source.get("page_numbers")
            ))
    
    answer_response = AnswerResponse(
        question=request.question,
        answer=result["answer"],
        sources=sources,
        confidence=result["confidence"]
    )
    
    # Save to database
    qa_record = QuestionAnswer(
        engagement_id=engagement_id,
        question=request.question,
        answer=result["answer"],
        sources=json.dumps([s.model_dump() for s in sources]),
        confidence=result["confidence"]
    )
    session.add(qa_record)
    await session.commit()
    
    return answer_response


@router.post("/batch-ask", response_model=BatchAnswerResponse)
async def ask_batch_questions(
    engagement_id: str,
    request: BatchQuestionRequest,
    session: AsyncSession = Depends(get_session)
):
    """Ask multiple questions at once"""
    # Verify engagement exists
    engagement = await session.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    # Get answers
    results = await qa_service.answer_batch(
        engagement_id=engagement_id,
        questions=request.questions,
        max_sources=5
    )
    
    # Format responses
    answers = []
    for result in results:
        sources = []
        if request.include_sources:
            for source in result["sources"]:
                sources.append(SourceChunk(
                    document_id=source["document_id"],
                    document_name=source.get("filename", ""),
                    chunk_text=source["text"],
                    similarity_score=source["similarity_score"],
                    page_number=source.get("page_number"),
                    page_numbers=source.get("page_numbers")
                ))
        
        answer = AnswerResponse(
            question=result["question"],
            answer=result["answer"],
            sources=sources,
            confidence=result["confidence"]
        )
        answers.append(answer)
        
        # Save to database
        qa_record = QuestionAnswer(
            engagement_id=engagement_id,
            question=result["question"],
            answer=result["answer"],
            sources=json.dumps([s.model_dump() for s in sources]),
            confidence=result["confidence"]
        )
        session.add(qa_record)
    
    await session.commit()
    
    return BatchAnswerResponse(
        total_questions=len(request.questions),
        answers=answers
    )


@router.post("/batch-ask-file", response_model=BatchAnswerResponse)
async def ask_batch_questions_from_file(
    engagement_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    """Upload a file with questions (one per line) and get answers - supports .txt, .docx"""
    # Verify engagement exists
    engagement = await session.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    # Extract text based on file type
    filename = file.filename.lower()
    content = await file.read()
    
    try:
        if filename.endswith('.docx'):
            # Handle Word documents
            import io
            from docx import Document as DocxDocument
            
            doc = DocxDocument(io.BytesIO(content))
            text = '\n'.join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
        elif filename.endswith('.doc'):
            # Legacy Word documents not supported - inform user
            raise HTTPException(
                status_code=400, 
                detail="Legacy .doc files are not supported. Please save as .docx or .txt"
            )
        else:
            # Handle text files (.txt)
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
    
    # Split by lines and filter empty
    questions = [q.strip() for q in text.split('\n') if q.strip()]
    
    if not questions:
        raise HTTPException(status_code=400, detail="No questions found in file")
    
    # Process batch
    batch_request = BatchQuestionRequest(questions=questions)
    return await ask_batch_questions(engagement_id, batch_request, session)


@router.get("/history", response_model=list[AnswerResponse])
async def get_qa_history(
    engagement_id: str,
    limit: int = 50,
    session: AsyncSession = Depends(get_session)
):
    """Get Q&A history for an engagement"""
    query = (
        select(QuestionAnswer)
        .where(QuestionAnswer.engagement_id == engagement_id)
        .order_by(QuestionAnswer.answered_at.desc())
        .limit(limit)
    )
    
    result = await session.execute(query)
    qa_records = result.scalars().all()
    
    responses = []
    for qa in qa_records:
        # Parse sources from JSON
        sources = []
        if qa.sources:
            try:
                source_data = json.loads(qa.sources)
                sources = [SourceChunk(**s) for s in source_data]
            except:
                pass
        
        responses.append(AnswerResponse(
            question=qa.question,
            answer=qa.answer,
            sources=sources,
            confidence=qa.confidence,
            answered_at=qa.answered_at
        ))
    
    return responses
