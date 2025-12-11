from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database import Base
from app.config import settings
import os


# Create async engine with aioodbc for SQL Server
# aioodbc supports async operations with ODBC drivers
# Standard S0 tier: 30 concurrent connections max, 10 DTU
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
    pool_size=5,         # Standard tier can handle more connections
    max_overflow=10,     # Allow up to 15 total connections
    pool_timeout=30,     # Wait max 30s for connection
    future=True
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
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
    async with AsyncSessionLocal() as session:
        yield session
