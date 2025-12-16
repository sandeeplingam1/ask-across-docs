"""
Vector store abstraction layer - supports BOTH ChromaDB and Azure AI Search
Switch by changing VECTOR_DB_TYPE in .env - NO CODE CHANGES NEEDED
"""
from abc import ABC, abstractmethod
from typing import Protocol, Optional, TYPE_CHECKING
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
)
from app.config import settings

# Conditional import for ChromaDB - only import if needed
if TYPE_CHECKING or settings.vector_db_type == "chromadb":
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
    except ImportError:
        if settings.vector_db_type == "chromadb":
            raise ImportError("chromadb is required when VECTOR_DB_TYPE=chromadb")
        chromadb = None
        ChromaSettings = None


class VectorStore(ABC):
    """Abstract base class for vector database operations"""
    
    @abstractmethod
    async def create_collection(self, engagement_id: str):
        """Create a new collection/index for an engagement"""
        pass
    
    @abstractmethod
    async def add_documents(
        self,
        engagement_id: str,
        document_id: str,
        chunks: list[dict],
        embeddings: list[list[float]]
    ):
        """Add document chunks with embeddings to the store"""
        pass
    
    @abstractmethod
    async def search(
        self,
        engagement_id: str,
        query_embedding: list[float],
        top_k: int = 5
    ) -> list[dict]:
        """Search for similar chunks"""
        pass
    
    @abstractmethod
    async def delete_document(self, engagement_id: str, document_id: str):
        """Delete all chunks for a document"""
        pass
    
    @abstractmethod
    async def delete_collection(self, engagement_id: str):
        """Delete entire engagement collection"""
        pass


class ChromaDBStore(VectorStore):
    """ChromaDB implementation (local vector database)"""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.chromadb_path,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
    
    def _get_collection_name(self, engagement_id: str) -> str:
        """Generate collection name for engagement"""
        # ChromaDB has strict naming requirements
        return f"engagement_{engagement_id.replace('-', '_')}"
    
    async def create_collection(self, engagement_id: str):
        """Create a new collection for an engagement"""
        collection_name = self._get_collection_name(engagement_id)
        try:
            self.client.get_or_create_collection(
                name=collection_name,
                metadata={"engagement_id": engagement_id}
            )
        except Exception as e:
            print(f"Error creating collection: {e}")
            raise
    
    async def add_documents(
        self,
        engagement_id: str,
        document_id: str,
        chunks: list[dict],
        embeddings: list[list[float]]
    ):
        """Add document chunks to ChromaDB"""
        collection_name = self._get_collection_name(engagement_id)
        collection = self.client.get_collection(collection_name)
        
        # Prepare data for ChromaDB
        ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
        documents = [chunk["text"] for chunk in chunks]
        metadatas = []
        
        for chunk in chunks:
            metadata = {
                "document_id": document_id,
                "chunk_index": chunk["chunk_index"],
                "engagement_id": engagement_id
            }
            # Add page number if available
            if "page_number" in chunk:
                metadata["page_number"] = chunk["page_number"]
            if "filename" in chunk:
                metadata["filename"] = chunk["filename"]
            metadatas.append(metadata)
        
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
    
    async def search(
        self,
        engagement_id: str,
        query_embedding: list[float],
        top_k: int = 5
    ) -> list[dict]:
        """Search for similar chunks in ChromaDB"""
        collection_name = self._get_collection_name(engagement_id)
        
        try:
            collection = self.client.get_collection(collection_name)
        except Exception:
            # Collection doesn't exist yet
            return []
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        search_results = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                result = {
                    "id": results["ids"][0][i],
                    "document_id": results["metadatas"][0][i]["document_id"],
                    "chunk_index": results["metadatas"][0][i]["chunk_index"],
                    "text": results["documents"][0][i],
                    "similarity_score": 1 - results["distances"][0][i]  # Convert distance to similarity
                }
                # Add page number if available
                if "page_number" in results["metadatas"][0][i]:
                    result["page_number"] = results["metadatas"][0][i]["page_number"]
                if "filename" in results["metadatas"][0][i]:
                    result["filename"] = results["metadatas"][0][i]["filename"]
                search_results.append(result)
        
        return search_results
    
    async def delete_document(self, engagement_id: str, document_id: str):
        """Delete all chunks for a document"""
        collection_name = self._get_collection_name(engagement_id)
        
        try:
            collection = self.client.get_collection(collection_name)
            # Delete all chunks with this document_id
            collection.delete(
                where={"document_id": document_id}
            )
        except Exception as e:
            print(f"Error deleting document: {e}")
    
    async def delete_collection(self, engagement_id: str):
        """Delete entire engagement collection"""
        collection_name = self._get_collection_name(engagement_id)
        try:
            self.client.delete_collection(collection_name)
        except Exception as e:
            print(f"Error deleting collection: {e}")


class AzureAISearchStore(VectorStore):
    """Azure AI Search implementation (cloud vector database)"""
    
    def __init__(self):
        if not settings.azure_search_endpoint or not settings.azure_search_api_key:
            raise ValueError("Azure AI Search credentials not configured")
        
        credential = AzureKeyCredential(settings.azure_search_api_key)
        self.index_client = SearchIndexClient(
            endpoint=settings.azure_search_endpoint,
            credential=credential
        )
        self.index_name = settings.azure_search_index_name
        self._ensure_index_exists()
    
    def _ensure_index_exists(self):
        """Create the search index if it doesn't exist"""
        try:
            self.index_client.get_index(self.index_name)
        except Exception:
            # Create index with vector search configuration
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SimpleField(name="engagement_id", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="filename", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="chunk_index", type=SearchFieldDataType.Int32),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=3072,  # text-embedding-3-large size
                    vector_search_profile_name="default-profile"
                )
            ]
            
            vector_search = VectorSearch(
                profiles=[VectorSearchProfile(name="default-profile", algorithm_configuration_name="default-algo")],
                algorithms=[HnswAlgorithmConfiguration(name="default-algo")]
            )
            
            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search
            )
            
            self.index_client.create_index(index)
    
    def _get_search_client(self) -> SearchClient:
        """Get search client for the index"""
        return SearchClient(
            endpoint=settings.azure_search_endpoint,
            index_name=self.index_name,
            credential=AzureKeyCredential(settings.azure_search_api_key)
        )
    
    async def create_collection(self, engagement_id: str):
        """No-op for Azure AI Search (uses single index with filters)"""
        pass
    
    async def add_documents(
        self,
        engagement_id: str,
        document_id: str,
        chunks: list[dict],
        embeddings: list[list[float]]
    ):
        """Add documents to Azure AI Search"""
        search_client = self._get_search_client()
        
        documents = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            documents.append({
                "id": f"{document_id}_chunk_{i}",
                "engagement_id": engagement_id,
                "document_id": document_id,
                "filename": chunk.get("filename", ""),
                "chunk_index": chunk["chunk_index"],
                "content": chunk["text"],
                "embedding": embedding
            })
        
        search_client.upload_documents(documents)
    
    async def search(
        self,
        engagement_id: str,
        query_embedding: list[float],
        top_k: int = 5
    ) -> list[dict]:
        """Search using vector similarity in Azure AI Search"""
        search_client = self._get_search_client()
        
        results = search_client.search(
            search_text=None,
            vector_queries=[{
                "kind": "vector",
                "vector": query_embedding,
                "fields": "embedding",
                "k": top_k
            }],
            filter=f"engagement_id eq '{engagement_id}'"
        )
        
        search_results = []
        for result in results:
            search_results.append({
                "id": result["id"],
                "document_id": result["document_id"],
                "chunk_index": result["chunk_index"],
                "text": result.get("content", result.get("text", "")),
                "score": result["@search.score"]
            })
        
        return search_results
    
    async def delete_document(self, engagement_id: str, document_id: str):
        """Delete all chunks for a document with logging and error handling"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            search_client = self._get_search_client()
            
            # Find all chunks for this document
            results = list(search_client.search(
                search_text="*",
                filter=f"document_id eq '{document_id}' and engagement_id eq '{engagement_id}'",
                select=["id"],
                top=1000
            ))
            
            ids_to_delete = [{"id": r["id"]} for r in results]
            if ids_to_delete:
                search_client.delete_documents(ids_to_delete)
                logger.info(f"AI Search: Deleted {len(ids_to_delete)} chunks for document {document_id}")
            else:
                logger.warning(f"AI Search: No chunks found for document {document_id}")
                
        except Exception as e:
            logger.error(f"AI Search: Failed to delete document {document_id}: {str(e)}")
            raise
    
    async def delete_collection(self, engagement_id: str):
        """Delete all documents for an engagement with pagination support"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            search_client = self._get_search_client()
            deleted_total = 0
            batch_count = 0
            
            # Keep deleting until no more results found (handles pagination)
            while True:
                results = list(search_client.search(
                    search_text="*",
                    filter=f"engagement_id eq '{engagement_id}'",
                    select=["id"],
                    top=1000  # Process in batches of 1000
                ))
                
                if not results:
                    break
                
                ids_to_delete = [{"id": r["id"]} for r in results]
                search_client.delete_documents(ids_to_delete)
                
                batch_count += 1
                deleted_total += len(ids_to_delete)
                logger.info(f"AI Search: Deleted batch {batch_count} ({len(ids_to_delete)} chunks) for engagement {engagement_id}")
                
                # If we got less than 1000, we're done
                if len(results) < 1000:
                    break
            
            if deleted_total > 0:
                logger.info(f"AI Search: Successfully deleted {deleted_total} total chunks for engagement {engagement_id}")
            else:
                logger.warning(f"AI Search: No chunks found for engagement {engagement_id}")
                
        except Exception as e:
            logger.error(f"AI Search: Failed to delete chunks for engagement {engagement_id}: {str(e)}")
            raise  # Re-raise so caller knows it failed


# Factory function to get the correct vector store
def get_vector_store() -> VectorStore:
    """
    Get vector store instance based on configuration
    
    Returns:
        VectorStore implementation (ChromaDB or Azure AI Search)
    """
    if settings.vector_db_type == "chromadb":
        return ChromaDBStore()
    elif settings.vector_db_type == "azure_search":
        return AzureAISearchStore()
    else:
        raise ValueError(f"Unknown vector DB type: {settings.vector_db_type}")
