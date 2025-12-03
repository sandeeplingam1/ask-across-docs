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
            # Handle Word documents - preserve indentation hierarchy
            import io
            from docx import Document as DocxDocument
            
            doc = DocxDocument(io.BytesIO(content))
            lines = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    indent_level = 0
                    
                    # Always try to detect indentation - don't restrict by style
                    if hasattr(paragraph, '_element') and hasattr(paragraph._element, 'pPr'):
                        pPr = paragraph._element.pPr
                        if pPr is not None:
                            # Method 1: Check numbering level (most reliable for bullets)
                            if hasattr(pPr, 'numPr') and pPr.numPr is not None:
                                ilvl = pPr.numPr.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ilvl')
                                if ilvl is not None and hasattr(ilvl, 'val'):
                                    # Level 0 = top-level, Level 1+ = nested
                                    level = int(ilvl.val)
                                    indent_level = level * 4  # 4 spaces per level
                            
                            # Method 2: Check left indentation (fallback)
                            if indent_level == 0 and hasattr(pPr, 'ind') and pPr.ind is not None:
                                if hasattr(pPr.ind, 'left') and pPr.ind.left is not None:
                                    indent_twips = int(pPr.ind.left)
                                    # Convert to spaces (roughly 720 twips = 4 spaces)
                                    indent_level = (indent_twips // 720) * 4
                    
                    # Add indentation to text
                    indented_text = ' ' * indent_level + paragraph.text
                    lines.append(indented_text)
            
            text = '\n'.join(lines)
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
    Parse audit questions from text with EXACT human auditor understanding.
    
    CRITICAL RULES:
    1. Ignore document titles/headings (lines without ? or : that don't contain question words)
    2. Multiple ? in same paragraph = ONE question (continuation, not separate items)
    3. Parent question ending with : + sub-bullets = ONE combined question
    4. Sub-bullets NEVER become standalone questions
    5. Short labels (< 5 words, no question structure) are IGNORED
    
    Supported formats:
    - Bullets: •, -, *, o, ◦
    - Numbering: 1., 1), 1:, 1-, I., A.), a.
    - Indentation-based hierarchy
    """
    import re
    
    lines = text.split('\n')
    questions = []
    current_question = None
    current_subpoints = []
    
    # Question word patterns (case-insensitive)
    question_words = r'\b(does|has|is|are|was|were|do|did|have|can|could|should|would|will|' \
                     r'provide|describe|explain|list|identify|document|what|when|where|who|why|how)\b'
    
    # Bullet patterns (comprehensive) - handle bullets with space OR tab OR multiple bullets
    bullet_pattern = r'^[-*•o◦○▪▫✓✔➢➣➤►▶]+[\s\t]+'
    
    # Number patterns: 1. 1) 1: 1- I. A.) a. etc.
    number_pattern = r'^(\d+[.):\-]|[A-Z][.):]|[a-z][.):]|[ivxIVX]+[.):])\s+'
    
    for line in lines:
        if not line.strip():
            continue
        
        stripped = line.strip()
        leading_spaces = len(line) - len(line.lstrip())
        
        # Clean line by removing numbering/bullets for content analysis
        cleaned = re.sub(number_pattern, '', stripped)
        cleaned = re.sub(bullet_pattern, '', cleaned)
        cleaned = cleaned.strip()
        
        # Word count for filtering
        word_count = len(cleaned.split())
        
        # ═══════════════════════════════════════════════════════════
        # RULE 1: IGNORE titles, headings, and short labels
        # ═══════════════════════════════════════════════════════════
        # A line is a title/heading if:
        # - No ? or : at the end
        # - Doesn't start with question words
        # - Too short (< 5 words)
        # - No question structure
        # BUT: Don't apply title filtering if we have an active parent and line could be a sub-point
        
        has_question_mark = '?' in stripped
        ends_with_colon = stripped.endswith(':')
        ends_with_question = stripped.endswith('?')
        starts_with_question_word = re.search(question_words, cleaned, re.IGNORECASE) is not None
        
        # Check if this could be a sub-point (nested bullet or heavy indent)
        could_be_subpoint = bool(re.match(r'^[o◦▪▫]+[\s\t]+', stripped)) or leading_spaces >= 8
        
        # Ignore if it's clearly a title/label AND not a potential sub-point
        is_title = (
            not has_question_mark 
            and not ends_with_colon 
            and not starts_with_question_word
            and word_count < 5
            and not (current_question and could_be_subpoint)  # Don't ignore potential sub-points!
        )
        
        # Also ignore very short fragments without structure (unless potential sub-point)
        if word_count < 3 and not ends_with_question and not ends_with_colon and not could_be_subpoint:
            is_title = True
        
        if is_title:
            # Skip this line entirely - it's a heading/title
            continue
        
        # ═══════════════════════════════════════════════════════════
        # RULE 2: Detect if this is a SUB-POINT (bullet under parent)
        # ═══════════════════════════════════════════════════════════
        # A line is a sub-point if:
        # - Indented 4+ spaces (secondary indentation)
        # - Starts with nested bullet marker (o, ◦, ▪) NOT top-level (•, -)
        # - Short fragment (< 40 chars) without own question structure
        # - We already have a parent question active
        
        is_subpoint = False
        
        if current_question:  # Only consider subpoints if we have an active parent
            # Check for NESTED bullets (o, ◦) vs TOP-LEVEL bullets (•, -, *)
            # o and ◦ are typically sub-bullets in Word
            is_nested_bullet = bool(re.match(r'^[o◦▪▫]+[\s\t]+', stripped))
            is_top_bullet = bool(re.match(r'^[•\-*]+[\s\t]+', stripped))
            
            # Check if parent ended with colon (expecting sub-list)
            parent_expects_sublist = current_question.rstrip().endswith(':')
            
            # Check 1: Heavily indented (8+ spaces = definitely a sub-point)
            if leading_spaces >= 8:
                is_subpoint = True
            
            # Check 2: Nested bullet (o, ◦)
            elif is_nested_bullet:
                is_subpoint = True
            
            # Check 3: Moderate indent (4+ spaces) 
            # If parent ends with :, ANY indented line is a sub-point
            # Otherwise, only short fragments
            elif leading_spaces >= 4:
                if parent_expects_sublist:
                    is_subpoint = True  # Parent expects list, all indented lines are sub-points
                elif len(cleaned) < 40 and not ends_with_question:
                    is_subpoint = True  # Short fragment
            
            # Check 4: Short fragment without question structure (even without indent)
            elif len(cleaned) < 30 and not ends_with_question and not starts_with_question_word:
                is_subpoint = True
        
        # ═══════════════════════════════════════════════════════════
        # RULE 3: Detect if this is a PARENT QUESTION
        # ═══════════════════════════════════════════════════════════
        # A line is a parent question if:
        # - Ends with ? or :
        # - Starts with question words and substantial (> 20 chars)
        # - NOT heavily indented (< 8 spaces)
        # - NOT identified as a subpoint
        
        is_parent = False
        
        if not is_subpoint:
            # Strong indicators
            if ends_with_question or ends_with_colon:
                is_parent = True
            
            # Question word starter with substance
            elif starts_with_question_word and len(cleaned) > 20 and leading_spaces < 8:
                is_parent = True
            
            # Contains ? somewhere (could be multiple questions in one line)
            elif has_question_mark and len(cleaned) > 15:
                is_parent = True
        
        # ═══════════════════════════════════════════════════════════
        # DECISION LOGIC
        # ═══════════════════════════════════════════════════════════
        
        if is_parent:
            # Check if this should EXTEND the current question (continuation)
            # This handles: "Has X been updated? Does it identify Y?"
            # Multiple ? in same numbered item = ONE question
            
            # Determine if this is a continuation or new question
            # It's a continuation if:
            # - No new numbering/bullet prefix
            # - Same indentation level as current question
            # - Current question exists
            
            has_own_numbering = re.match(number_pattern, stripped)
            
            if current_question and not has_own_numbering and leading_spaces >= 4:
                # This is a CONTINUATION of the current question
                # Add it to the current question text
                current_question += ' ' + stripped
            else:
                # This is a NEW parent question
                # Save previous question if exists
                if current_question:
                    question_text = current_question
                    if current_subpoints:
                        question_text += '\n' + '\n'.join([f"    - {sp}" for sp in current_subpoints])
                    questions.append(question_text)
                
                # Start new question - clean it by removing bullets/numbering
                new_question = stripped
                # Remove leading bullets and numbers
                prev_q = ""
                while prev_q != new_question:
                    prev_q = new_question
                    new_question = re.sub(number_pattern, '', new_question)
                    new_question = re.sub(bullet_pattern, '', new_question)
                    new_question = new_question.strip()
                
                current_question = new_question
                current_subpoints = []
        
        elif is_subpoint and current_question:
            # This is a sub-point belonging to the current parent question
            # Clean up the sub-point text (remove bullets/numbering)
            subpoint = stripped
            
            # Remove all leading bullets and numbers (handle nested: o • text)
            # Keep removing until no more bullets/numbers at start
            prev_subpoint = ""
            while prev_subpoint != subpoint:
                prev_subpoint = subpoint
                subpoint = re.sub(number_pattern, '', subpoint)
                subpoint = re.sub(bullet_pattern, '', subpoint)
                subpoint = subpoint.strip()
            
            if subpoint and len(subpoint) > 2:  # Ignore trivial fragments
                current_subpoints.append(subpoint)
    
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


@router.delete("/history")
async def clear_qa_history(
    engagement_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Clear all Q&A history for an engagement"""
    # Verify engagement exists
    engagement = await session.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    
    # Delete all Q&A records for this engagement
    query = select(QuestionAnswer).where(QuestionAnswer.engagement_id == engagement_id)
    result = await session.execute(query)
    qa_records = result.scalars().all()
    
    count = len(qa_records)
    for qa in qa_records:
        await session.delete(qa)
    
    await session.commit()
    
    return {"message": f"Cleared {count} Q&A records", "deleted_count": count}
