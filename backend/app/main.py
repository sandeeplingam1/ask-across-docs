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
    print("🚀 Starting Audit App API v1.1.0")
    print(f"📍 Environment: {settings.environment}")
    await init_db()  # Now async
    print("✅ Database initialized")
    print(f"✅ Vector store: {settings.vector_db_type}")
    print(f"✅ CORS origins: {', '.join(settings.cors_origins_list[:3])}...")
    if settings.enable_telemetry:
        print("✅ Application Insights enabled")
    print("✅ API ready to accept requests")
    yield
    # Shutdown
    print("👋 Shutting down Audit App API...")


app = FastAPI(
    title="Audit App - Document Q&A API",
    description="RAG-based document question answering for audit engagements",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else "/docs",
    redoc_url="/redoc" if settings.is_development else "/redoc"
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
        "version": "1.1.0",
        "status": "running",
        "environment": settings.environment,
        "vector_db": settings.vector_db_type,
        "documentation": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Container Apps"""
    from app.db_session import get_session
    from sqlalchemy import text
    
    health_status = {
        "status": "healthy",
        "version": "1.1.0",
        "environment": settings.environment,
        "vector_db": settings.vector_db_type,
        "services": {}
    }
    
    # Check database connectivity
    try:
        async for session in get_session():
            result = await session.execute(text("SELECT 1"))
            result.fetchone()  # Consume the result
            health_status["services"]["database"] = "healthy"
            break
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
    
    # Check Azure services connectivity
    if settings.azure_storage_connection_string:
        health_status["services"]["blob_storage"] = "configured"
    
    if settings.azure_search_endpoint:
        health_status["services"]["ai_search"] = "configured"
    
    return health_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
