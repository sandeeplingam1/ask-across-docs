from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    
    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_api_key: str | None = None  # Optional - uses Azure AD if not provided
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_openai_embedding_deployment: str
    azure_openai_chat_deployment: str
    
    # Use Azure AD authentication in production (Managed Identity)
    use_azure_ad_auth: bool = False
    
    # Vector Database
    vector_db_type: Literal["chromadb", "azure_search"] = "chromadb"
    
    # ChromaDB
    chromadb_path: str = "./data/chromadb"
    
    # Azure AI Search (optional)
    azure_search_endpoint: str | None = None
    azure_search_api_key: str | None = None
    azure_search_index_name: str = "documents"
    
    # Azure Blob Storage (optional)
    azure_storage_connection_string: str | None = None
    azure_storage_container_name: str = "audit-documents"
    
    # Azure Storage Queue for background processing
    azure_queue_connection_string: str | None = None
    azure_queue_name: str = "document-processing"
    
    # Redis (for Celery/background tasks)
    redis_url: str | None = None
    
    # Application
    backend_cors_origins: str = "http://localhost:5173,http://localhost:3000"
    max_upload_size_mb: int = 100
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # Background Processing
    enable_background_processing: bool = True
    max_concurrent_document_processing: int = 10
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/audit_app.db"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # Monitoring
    applicationinsights_connection_string: str | None = None
    enable_telemetry: bool = False
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        origins = [origin.strip() for origin in self.backend_cors_origins.split(",")]
        # Add production frontend URL if in staging/production
        if not self.is_development:
            origins.extend([
                "https://auditapp-frontend.graydune-dadabae1.eastus.azurecontainerapps.io",
                "https://*.azurecontainerapps.io"
            ])
        return origins
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"


# Global settings instance
settings = Settings()
