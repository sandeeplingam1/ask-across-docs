from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# ==================== Engagement Models ====================

class EngagementCreate(BaseModel):
    """Request model for creating a new engagement"""
    name: str = Field(..., min_length=1, max_length=200, description="Engagement name")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description")
    client_name: Optional[str] = Field(None, max_length=200, description="Client name")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class EngagementResponse(BaseModel):
    """Response model for engagement data"""
    id: str
    name: str
    description: Optional[str] = None
    client_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    document_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ==================== Document Models ====================

class DocumentResponse(BaseModel):
    """Response model for document metadata"""
    id: str
    engagement_id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int = 0
    status: str = "processing"  # processing, completed, failed
    uploaded_at: datetime
    
    model_config = {"from_attributes": True}


# ==================== Question/Answer Models ====================

class QuestionRequest(BaseModel):
    """Request model for asking a single question"""
    question: str = Field(..., min_length=1, max_length=2000)
    include_sources: bool = Field(True, description="Include source document citations")
    max_sources: int = Field(5, ge=1, le=10, description="Maximum number of source chunks to retrieve")


class SourceChunk(BaseModel):
    """Source document chunk used to answer question"""
    document_id: str
    document_name: str
    chunk_text: str
    similarity_score: float
    page_number: Optional[int] = None
    page_numbers: Optional[list[int]] = None  # If chunk spans multiple pages


class AnswerResponse(BaseModel):
    """Response model for question answers"""
    question: str
    answer: str
    sources: list[SourceChunk] = []
    confidence: str = "high"  # high, medium, low
    answered_at: datetime = Field(default_factory=datetime.utcnow)


class BatchQuestionRequest(BaseModel):
    """Request model for batch questions from uploaded file"""
    questions: list[str] = Field(..., min_items=1)
    include_sources: bool = True


class BatchAnswerResponse(BaseModel):
    """Response model for batch question answers"""
    total_questions: int
    answers: list[AnswerResponse]
    processed_at: datetime = Field(default_factory=datetime.utcnow)


# ==================== Upload Response Models ====================

class UploadStatus(BaseModel):
    """Status of document upload and processing"""
    filename: str
    status: str  # success, processing, failed
    message: Optional[str] = None
    document_id: Optional[str] = None


class MultiUploadResponse(BaseModel):
    """Response for multiple document uploads"""
    total_files: int
    successful: int
    failed: int
    results: list[UploadStatus]
