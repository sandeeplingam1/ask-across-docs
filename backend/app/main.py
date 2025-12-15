"""FastAPI application entry point"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.db_session import init_db
from app.routes import engagements, documents, questions, document_files, question_templates
import logging
import time

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    try:
        print("[STARTUP] Starting Audit App API v1.1.0", flush=True)
        logger.info("Starting Audit App API v1.1.0")
        print(f"[STARTUP] Environment: {settings.environment}", flush=True)
        logger.info(f"Environment: {settings.environment}")
        print("[STARTUP] Initializing database...", flush=True)
        await init_db()  # Now async
        print("[STARTUP] Database initialized", flush=True)
        logger.info("Database initialized")
        print(f"[STARTUP] Vector store: {settings.vector_db_type}", flush=True)
        logger.info(f"Vector store: {settings.vector_db_type}")
        print(f"[STARTUP] CORS origins: {', '.join(settings.cors_origins_list[:3])}...", flush=True)
        logger.info(f"CORS origins: {', '.join(settings.cors_origins_list[:3])}...")
        if settings.enable_telemetry:
            print("[STARTUP] Application Insights enabled", flush=True)
            logger.info("Application Insights enabled")
        
        # Background processing is handled by separate worker process
        # See backend/worker.py for document processing
        print("[STARTUP] Background processing: Separate worker process", flush=True)
        logger.info("Background processing handled by separate worker process")
        
        print("[STARTUP] API ready to accept requests", flush=True)
        logger.info("API ready to accept requests")
    except Exception as e:
        print(f"[STARTUP ERROR] {str(e)}", flush=True)
        logger.error(f"Startup failed: {str(e)}", exc_info=True)
        raise  # Re-raise to prevent app from starting in broken state
    
    yield
    # Shutdown
    print("[SHUTDOWN] Shutting down Audit App API...", flush=True)
    logger.info("Shutting down Audit App API...")


app = FastAPI(
    title="Audit App - Document Q&A API",
    description="RAG-based document question answering for audit engagements",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else "/docs",
    redoc_url="/redoc" if settings.is_development else "/redoc"
)

# CORS configuration - Explicitly allow frontend and development origins
allowed_origins = [
    "https://blue-island-0b509160f.3.azurestaticapps.net",
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
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
app.include_router(question_templates.router)


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
    from app.db_session import get_session, AsyncSessionLocal
    from sqlalchemy import text, select, func
    from app.database import Document
    
    health_status = {
        "status": "healthy",
        "version": "1.1.0",
        "environment": settings.environment,
        "vector_db": settings.vector_db_type,
        "services": {}
    }
    
    # Check database connectivity and get processing stats
    try:
        async with AsyncSessionLocal() as session:
            # Get document processing stats
            stats_query = select(
                Document.status,
                func.count(Document.id).label('count')
            ).group_by(Document.status)
            
            result = await session.execute(stats_query)
            stats = {row.status: row.count for row in result}
            
            health_status["services"]["database"] = "healthy"
            health_status["document_processing"] = {
                "queued": stats.get("queued", 0),
                "processing": stats.get("processing", 0),
                "completed": stats.get("completed", 0),
                "failed": stats.get("failed", 0)
            }
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
