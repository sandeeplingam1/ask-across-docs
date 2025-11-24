"""File storage service - Local or Azure Blob Storage"""
from abc import ABC, abstractmethod
from pathlib import Path
import os
from typing import BinaryIO
from app.config import settings


class FileStorage(ABC):
    """Abstract base class for file storage"""
    
    @abstractmethod
    async def save_file(self, file_content: bytes, engagement_id: str, filename: str) -> str:
        """Save file and return file path/URL"""
        pass
    
    @abstractmethod
    async def get_file(self, file_path: str) -> bytes:
        """Retrieve file content"""
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete file"""
        pass


class LocalFileStorage(FileStorage):
    """Local filesystem storage for development"""
    
    def __init__(self, base_path: str = "./data/uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def save_file(self, file_content: bytes, engagement_id: str, filename: str) -> str:
        """Save file to local filesystem"""
        engagement_dir = self.base_path / engagement_id
        engagement_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = engagement_dir / filename
        
        # Write file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return str(file_path)
    
    async def get_file(self, file_path: str) -> bytes:
        """Read file from local filesystem"""
        with open(file_path, 'rb') as f:
            return f.read()
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from local filesystem"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False


class AzureBlobStorage(FileStorage):
    """Azure Blob Storage for production"""
    
    def __init__(self):
        from azure.storage.blob.aio import BlobServiceClient
        
        if not settings.azure_storage_connection_string:
            raise ValueError("Azure Storage connection string not configured")
        
        self.blob_service_client = BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string
        )
        self.container_name = settings.azure_storage_container_name
        self._ensure_container_exists()
    
    def _ensure_container_exists(self):
        """Ensure container exists (sync version for init)"""
        import asyncio
        from azure.storage.blob import BlobServiceClient
        
        # Use sync client for initialization
        sync_client = BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string
        )
        try:
            sync_client.create_container(self.container_name)
        except Exception:
            # Container already exists
            pass
    
    async def save_file(self, file_content: bytes, engagement_id: str, filename: str) -> str:
        """Save file to Azure Blob Storage"""
        blob_name = f"{engagement_id}/{filename}"
        
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        
        await blob_client.upload_blob(file_content, overwrite=True)
        
        # Return blob URL
        return blob_name
    
    async def get_file(self, blob_name: str) -> bytes:
        """Download file from Azure Blob Storage"""
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        
        downloader = await blob_client.download_blob()
        return await downloader.readall()
    
    async def delete_file(self, blob_name: str) -> bool:
        """Delete file from Azure Blob Storage"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            await blob_client.delete_blob()
            return True
        except Exception:
            return False


def get_file_storage() -> FileStorage:
    """Factory function to get file storage implementation"""
    if settings.azure_storage_connection_string:
        # Use Azure Blob Storage if configured
        return AzureBlobStorage()
    else:
        # Use local filesystem otherwise
        return LocalFileStorage()
