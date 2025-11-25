from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.database import Base
from app.config import settings
import os


# Create sync engine (pyodbc is not async)
engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600    # Recycle connections after 1 hour
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def init_db():
    """Initialize database tables"""
    # Create data directories if they don't exist
    os.makedirs("./data", exist_ok=True)
    if settings.vector_db_type == "chromadb":
        os.makedirs(settings.chromadb_path, exist_ok=True)
    
    # Create tables
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
