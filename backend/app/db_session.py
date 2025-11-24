from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database import Base
from app.config import settings
import os


# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """Initialize database tables"""
    # Create data directories if they don't exist
    os.makedirs("./data", exist_ok=True)
    if settings.vector_db_type == "chromadb":
        os.makedirs(settings.chromadb_path, exist_ok=True)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Dependency for getting database session"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
