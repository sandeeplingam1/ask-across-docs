"""Question-answering service using RAG (Retrieval-Augmented Generation)"""
from openai import AzureOpenAI
from app.config import settings
from app.services.vector_store import get_vector_store
from app.services.embedding_service import EmbeddingService


class QAService:
    """Handle question answering using RAG pattern"""
    
    def __init__(self):
        """Initialize Azure OpenAI client and services"""
        self.client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint
        )
        self.chat_deployment = settings.azure_openai_chat_deployment
        self.embedding_service = EmbeddingService()
        self.vector_store = get_vector_store()
    
    async def answer_question(
        self,
        engagement_id: str,
        question: str,
        max_sources: int = 5
    ) -> dict:
        """
        Answer a question using RAG
        
        Args:
            engagement_id: Engagement ID to search in
            question: User's question
            max_sources: Maximum number of source chunks to retrieve
            
        Returns:
            Dict with answer, sources, and confidence
        """
        # 1. Generate embedding for the question
        question_embedding = await self.embedding_service.embed_text(question)
        
        # 2. Retrieve relevant chunks from vector store
        search_results = await self.vector_store.search(
            engagement_id=engagement_id,
            query_embedding=question_embedding,
            top_k=max_sources
        )
        
        if not search_results:
            return {
                "answer": "I don't have enough information to answer this question. Please make sure documents have been uploaded to this engagement.",
                "sources": [],
                "confidence": "low"
            }
        
        # 3. Build context from retrieved chunks
        context_parts = []
        for i, result in enumerate(search_results):
            context_parts.append(f"[Source {i+1}]\n{result['text']}")
        
        context = "\n\n".join(context_parts)
        
        # 4. Build prompt for GPT
        system_prompt = """You are an AI assistant helping auditors analyze documents. 
Your role is to answer questions based ONLY on the provided document excerpts.

Rules:
1. Only use information from the provided sources
2. If the sources don't contain relevant information, say so
3. Cite source numbers when referencing specific information (e.g., "According to Source 2...")
4. Be precise and professional
5. If you're uncertain, acknowledge it"""
        
        user_prompt = f"""Based on the following document excerpts, please answer the question.

DOCUMENT EXCERPTS:
{context}

QUESTION: {question}

ANSWER:"""
        
        # 5. Call Azure OpenAI
        try:
            response = self.client.chat.completions.create(
                model=self.chat_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temperature for more factual responses
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            
            # Determine confidence based on similarity scores
            avg_score = sum(r["similarity_score"] for r in search_results) / len(search_results)
            if avg_score > 0.8:
                confidence = "high"
            elif avg_score > 0.6:
                confidence = "medium"
            else:
                confidence = "low"
            
            return {
                "answer": answer,
                "sources": search_results,
                "confidence": confidence
            }
            
        except Exception as e:
            print(f"Error calling Azure OpenAI: {e}")
            return {
                "answer": f"Error generating answer: {str(e)}",
                "sources": search_results,
                "confidence": "low"
            }
    
    async def answer_batch(
        self,
        engagement_id: str,
        questions: list[str],
        max_sources: int = 5
    ) -> list[dict]:
        """
        Answer multiple questions
        
        Args:
            engagement_id: Engagement ID to search in
            questions: List of questions
            max_sources: Maximum sources per question
            
        Returns:
            List of answer dicts
        """
        results = []
        
        for question in questions:
            answer_data = await self.answer_question(
                engagement_id=engagement_id,
                question=question,
                max_sources=max_sources
            )
            results.append({
                "question": question,
                **answer_data
            })
        
        return results
