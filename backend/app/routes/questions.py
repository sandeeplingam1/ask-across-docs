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
    
    # Intelligently parse questions from any format
    questions = _parse_questions_from_text(text)
    
    if not questions:
        raise HTTPException(status_code=400, detail="No questions found in file")
    
    # Process batch
    batch_request = BatchQuestionRequest(questions=questions)
    return await ask_batch_questions(engagement_id, batch_request, session)


def _parse_questions_from_text(text: str) -> list[str]:
    """
    Parse audit questions from text with hierarchy awareness.
    
    Supports any formatting style:
    - Bullets: •, -, *, o •
    - Numbering: 1., 1), 1-, I., A.
    - Indentation-based hierarchy
    - Multi-line parent questions with sub-points
    
    Logic:
    - Parent questions: Full questions (ends with ? or :, starts with question words, or is long)
    - Sub-points: Indented, short fragments, or bullets under a parent
    - Returns structured questions with sub-points included in the text
    """
    import re
    
    lines = text.split('\n')
    questions = []
    current_question = None
    current_subpoints = []
    
    # Question indicators
    question_starters = r'^(does|has|is|are|was|were|do|did|have|can|could|should|would|will|' \
                       r'provide|describe|explain|list|identify|document|what|when|where|who|why|how)'
    
    for line in lines:
        if not line.strip():
            continue
            
        original_line = line
        stripped = line.strip()
        leading_spaces = len(line) - len(line.lstrip())
        
        # Remove common bullet/number prefixes for analysis
        cleaned = re.sub(r'^[-*•o]\s*', '', stripped)
        cleaned = re.sub(r'^\d+[.):\-]\s*', '', cleaned)
        cleaned = re.sub(r'^[A-Z][.)]\s*', '', cleaned)
        cleaned = re.sub(r'^[ivxIVX]+[.)]\s*', '', cleaned)
        cleaned = stripped  # Keep original for bullet detection
        
        # Detect if this is a parent question
        is_parent_question = False
        
        # Check 1: Ends with ? or : (strong indicator)
        if stripped.endswith('?') or stripped.endswith(':'):
            is_parent_question = True
        
        # Check 2: Starts with question words and is substantial
        elif re.match(question_starters, stripped, re.IGNORECASE) and len(cleaned) > 20:
            is_parent_question = True
        
        # Check 3: Long enough to be a complete question (>40 chars) and not heavily indented
        elif len(cleaned) > 40 and leading_spaces < 8:
            is_parent_question = True
        
        # Check 4: Contains question-like structure
        elif '?' in stripped:
            is_parent_question = True
        
        # Detect if this is a sub-point
        is_subpoint = False
        
        # Sub-point indicators:
        # - Heavily indented (4+ spaces or 2+ tabs)
        if leading_spaces >= 4:
            is_subpoint = True
        
        # - Very short (< 40 chars) and starts with bullet/letter
        elif len(cleaned) < 40 and re.match(r'^[o•\-\*]', stripped):
            is_subpoint = True
        
        # - Fragment-like (no question structure, short)
        elif len(cleaned) < 30 and not stripped.endswith(('?', ':', '.', ';')):
            is_subpoint = True
        
        # Decision logic
        if is_parent_question and not is_subpoint:
            # Save previous question if exists
            if current_question:
                question_text = current_question
                if current_subpoints:
                    question_text += '\n' + '\n'.join([f"    - {sp}" for sp in current_subpoints])
                questions.append(question_text)
            
            # Start new question
            current_question = stripped
            current_subpoints = []
        
        elif current_question and is_subpoint:
            # This is a sub-point of the current question
            # Clean up the sub-point text
            subpoint = re.sub(r'^[-*•o]\s*', '', stripped)
            subpoint = re.sub(r'^\d+[.):\-]\s*', '', subpoint)
            subpoint = re.sub(r'^[A-Z][.)]\s*', '', subpoint)
            subpoint = subpoint.strip()
            if subpoint:
                current_subpoints.append(subpoint)
        
        elif current_question:
            # Ambiguous line - if short, treat as subpoint; if long, new question
            if len(cleaned) < 50:
                subpoint = re.sub(r'^[-*•o]\s*', '', stripped).strip()
                if subpoint:
                    current_subpoints.append(subpoint)
            else:
                # Save previous and start new
                question_text = current_question
                if current_subpoints:
                    question_text += '\n' + '\n'.join([f"    - {sp}" for sp in current_subpoints])
                questions.append(question_text)
                current_question = stripped
                current_subpoints = []
        else:
            # First line or standalone - treat as potential question
            if len(cleaned) > 20:
                current_question = stripped
                current_subpoints = []
    
    # Don't forget the last question
    if current_question:
        question_text = current_question
        if current_subpoints:
            question_text += '\n' + '\n'.join([f"    - {sp}" for sp in current_subpoints])
        questions.append(question_text)
    
    # Final cleanup
    cleaned_questions = []
    for q in questions:
        q = q.strip()
        # Remove questions that are too short to be meaningful
        if len(q) > 10:
            cleaned_questions.append(q)
    
    return cleaned_questions


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
