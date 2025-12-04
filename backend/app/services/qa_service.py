"""Question-answering service with Azure AD authentication"""
from openai import AzureOpenAI, RateLimitError
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from app.config import settings
from app.services.vector_store import get_vector_store
from app.services.embedding_service import EmbeddingService
import logging
import time
import asyncio

logger = logging.getLogger(__name__)


class QAService:
    """Answer questions using RAG with Azure OpenAI"""
    
    def __init__(self):
        # Use Azure AD authentication (Managed Identity)
        if settings.use_azure_ad_auth:
            logger.info("Using Azure AD authentication for QA service")
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default"
            )
            self.client = AzureOpenAI(
                azure_ad_token_provider=token_provider,
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
        
        # 2. Retrieve relevant chunks from vector store (get more for better context)
        search_results = await self.vector_store.search(
            engagement_id=engagement_id,
            query_embedding=question_embedding,
            top_k=max_sources * 2  # Get more results for better filtering
        )
        
        # Normalize the field names (vector store returns 'score', but we use 'similarity_score')
        for result in search_results:
            if 'score' in result and 'similarity_score' not in result:
                result['similarity_score'] = result['score']
        
        # Filter out results with low similarity scores
        # Use higher threshold (0.7) to ensure only relevant content is used
        filtered_results = [r for r in search_results if r.get('similarity_score', 0) > 0.7]
        
        # If no high-confidence results, try with medium threshold (0.55)
        if not filtered_results:
            filtered_results = [r for r in search_results if r.get('similarity_score', 0) > 0.55]
            if not filtered_results:
                # Last resort: check if question is too generic
                question_lower = question.lower().strip()
                generic_questions = ['hi', 'hello', 'hey', 'what', 'who are you', 'help']
                if question_lower in generic_questions or len(question_lower) < 5:
                    return {
                        "answer": "Please ask a specific question about the documents in this engagement.",
                        "sources": [],
                        "confidence": "low"
                    }
        
        # Take only top max_sources after filtering
        filtered_results = filtered_results[:max_sources]
        
        if not filtered_results:
            return {
                "answer": "I don't have enough information to answer this question. Please make sure documents have been uploaded to this engagement.",
                "sources": [],
                "confidence": "low"
            }
        
        # 3. Build context from retrieved chunks
        context_parts = []
        for i, result in enumerate(filtered_results):
            context_parts.append(f"[Source {i+1}]\n{result['text']}")
        
        context = "\n\n".join(context_parts)
        
        # Initialize confidence to low by default
        confidence = "low"
        
        # 4. Build improved prompt for GPT
        system_prompt = """You are an expert AI assistant helping auditors analyze engagement documents. 

Your responsibilities:
1. Answer questions based STRICTLY on the provided document excerpts
2. Use inline numbered citations [1], [2], etc. after relevant statements
3. Use professional audit terminology when appropriate
4. If sources don't contain enough information to answer fully, clearly state what's missing
5. Structure answers logically with clear explanations

Important citation guidelines:
- Use [1], [2], [3] format for inline citations (not "Source 1")
- Place citations at the end of relevant sentences or claims
- Be specific and precise - include numbers, dates, names when available
- If multiple sources contain relevant information, synthesize them coherently
- Never make assumptions or add information not in the sources"""
        
        user_prompt = f"""Please answer the following question based on the document excerpts provided below. 

Analyze the excerpts carefully and provide a comprehensive answer with numbered citations.

=== DOCUMENT EXCERPTS ===
{context}

=== QUESTION ===
{question}

=== INSTRUCTIONS ===
Provide a detailed answer that:
1. Directly addresses the question
2. Uses inline citations in [1], [2], [3] format
3. Places citations after each claim or statement from sources
4. Includes relevant details from the documents
5. Is clear and professionally structured

Example format:
"The company implemented new security measures in 2024 [1]. These include badge readers 
and enhanced monitoring systems [2]. No security breaches were reported [3]."

=== ANSWER ===
"""
        
        # 5. Call Azure OpenAI with retry logic for rate limiting
        max_retries = 5
        retry_delay = 1  # Start with 1 second
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.chat_deployment,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,  # Very low temperature for factual, focused responses
                    max_tokens=1500,  # Allow longer responses for detailed answers
                    top_p=0.9  # Focus on high-probability tokens
                )
                
                answer = response.choices[0].message.content
                break  # Success, exit retry loop
                
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Rate limit hit, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    logger.error(f"Rate limit exceeded after {max_retries} attempts")
                    return {
                        "answer": "The system is currently busy. Please try again in a few moments.",
                        "sources": filtered_results,
                        "confidence": "low"
                    }
            except Exception as e:
                logger.error(f"Error calling Azure OpenAI: {e}")
                return {
                    "answer": f"Error generating answer: {str(e)}",
                    "sources": filtered_results,
                    "confidence": "low"
                }
            
            # Determine confidence based on similarity scores and answer quality
            avg_score = sum(r["similarity_score"] for r in filtered_results) / len(filtered_results)
            max_score = max(r["similarity_score"] for r in filtered_results)
            
            # More accurate confidence calculation
            # High: Strong semantic match (avg > 0.8 and max > 0.85)
            # Medium: Good match (avg > 0.65 or max > 0.75)
            # Low: Weak match
            if avg_score >= 0.8 and max_score >= 0.85:
                confidence = "high"
            elif avg_score >= 0.65 or max_score >= 0.75:
                confidence = "medium"
            else:
                confidence = "low"
            
        return {
            "answer": answer,
            "sources": filtered_results,
            "confidence": confidence
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
