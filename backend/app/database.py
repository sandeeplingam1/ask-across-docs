from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()


def generate_uuid():
    """Generate UUID string for primary keys"""
    return str(uuid.uuid4())


class Engagement(Base):
    """Engagement/Folder that contains documents"""
    __tablename__ = "engagements"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    client_name = Column(String(200), nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())


class Document(Base):
    """Document uploaded to an engagement"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    engagement_id = Column(String, ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(1000), nullable=True)  # Local or Azure Blob path
    chunk_count = Column(Integer, default=0)
    status = Column(String(50), default="queued")  # queued, processing, completed, failed
    progress = Column(Integer, default=0)  # 0-100 percentage
    error_message = Column(Text, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())


class QuestionAnswer(Base):
    """Q&A history for engagements"""
    __tablename__ = "question_answers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    engagement_id = Column(String, ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)  # JSON string of source chunks
    confidence = Column(String(20), default="high")
    answered_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
