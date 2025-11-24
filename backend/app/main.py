"""FastAPI application entry point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.db_session import init_db
from app.routes import engagements, documents, questions, document_files


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    await init_db()
    print("✅ Database initialized")
    print(f"✅ Vector store: {settings.vector_db_type}")
    yield
    # Shutdown
    print("👋 Shutting down...")


app = FastAPI(
    title="Audit App - Document Q&A API",
    description="RAG-based document question answering for audit engagements",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(engagements.router)
app.include_router(documents.router)
app.include_router(questions.router)
app.include_router(document_files.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Audit App API",
        "version": "1.0.0",
        "status": "running",
        "vector_db": settings.vector_db_type
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
