"""Azure OpenAI embedding service with Azure AD authentication"""
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate embeddings using Azure OpenAI"""
    
    def __init__(self):
        """Initialize Azure OpenAI client"""
        # Use Azure AD authentication (Managed Identity)
        if settings.use_azure_ad_auth:
            logger.info("Using Azure AD authentication for OpenAI")
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default"
            )
            self.client = AzureOpenAI(
                azure_ad_token_provider=token_provider,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint
            )
        self.deployment = settings.azure_openai_embedding_deployment
    
    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        # Truncate if too long (max 8191 tokens for ada-002)
        text = text[:8000]  # Conservative limit
        
        response = self.client.embeddings.create(
            input=text,
            model=self.deployment
        )
        
        return response.data[0].embedding
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        # Batch size limit for Azure OpenAI
        batch_size = 16
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            # Truncate each text
            batch = [text[:8000] for text in batch]
            
            response = self.client.embeddings.create(
                input=batch,
                model=self.deployment
            )
            
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)
        
        return all_embeddings
