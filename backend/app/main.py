"""FastAPI application entry point"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.db_session import init_db
from app.routes import engagements, documents, questions, document_files
import logging
import time

logger = logging.getLogger(__name__)


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
    
    # Start background processor for queued documents
    from app.background_processor import start_background_processor
    start_background_processor()
    print("✅ Background document processor started")
    
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
    expose_headers=["*"],  # Allow frontend to read all response headers
)


# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.is_development else "An unexpected error occurred"
        }
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = time.time()
    logger.info(f"Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Response: {request.method} {request.url.path} - {response.status_code} ({process_time:.2f}s)")
        return response
    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url.path} - {str(e)}", exc_info=True)
        raise

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
            # Simple connection check - just opening session validates the connection
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
