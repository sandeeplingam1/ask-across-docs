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
    
    # Azure OpenAI - Using Azure AD Authentication (Managed Identity)
    azure_openai_endpoint: str
    azure_openai_api_key: str | None = None  # Not used with Azure AD auth
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_openai_embedding_deployment: str
    azure_openai_chat_deployment: str
    
    # Use Azure AD authentication in production (Managed Identity)
    use_azure_ad_auth: bool = True  # Changed to True by default
    
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
    
    # Application
    backend_cors_origins: str = "http://localhost:5173,http://localhost:3000"
    max_upload_size_mb: int = 100
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # Background Processing
    enable_background_processing: bool = True
    max_concurrent_document_processing: int = 10
    
    # Azure Service Bus (for event-driven processing)
    service_bus_enabled: bool = False  # Enable to use Service Bus instead of polling
    service_bus_connection_string: str | None = None  # For local development
    service_bus_namespace: str | None = None  # For Azure deployment with managed identity (e.g., "mybus.servicebus.windows.net")
    service_bus_queue_name: str = "document-processing"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/audit_app.db"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # Monitoring
    applicationinsights_connection_string: str | None = None
    enable_telemetry: bool = False
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string and ensure frontend URL is present"""
        origins = [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]
        # Always add production/staging frontend URL if not in development
        if not self.is_development:
            static_web_url = "https://blue-island-0b509160f.3.azurestaticapps.net"
            if static_web_url not in origins:
                origins.append(static_web_url)
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
