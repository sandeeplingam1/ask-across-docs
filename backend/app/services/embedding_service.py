"""Azure OpenAI embedding service with Azure AD authentication"""
from openai import AzureOpenAI, RateLimitError
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from app.config import settings
import logging
import asyncio

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
        Generate embeddings for multiple texts with rate limit handling
        
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
            
            # Retry logic for rate limiting
            max_retries = 5
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    response = self.client.embeddings.create(
                        input=batch,
                        model=self.deployment
                    )
                    
                    embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(embeddings)
                    break  # Success
                    
                except RateLimitError as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Rate limit hit for batch {i//batch_size + 1}, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"Rate limit exceeded after {max_retries} attempts for batch {i//batch_size + 1}")
                        raise
                except Exception as e:
                    logger.error(f"Error generating embeddings for batch {i//batch_size + 1}: {str(e)}")
                    raise
            
            # Small delay between batches to avoid rate limits
            if i + batch_size < len(texts):
                await asyncio.sleep(0.5)
        
        return all_embeddings
