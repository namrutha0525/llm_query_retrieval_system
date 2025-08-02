import logging
import asyncio
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from config.config import settings
from app.models.schemas import StructuredQuery, QueryResponse, RationaleItem

logger = logging.getLogger(__name__)

class GeminiLLMService:
    """Service for Google Gemini LLM interactions"""

    def __init__(self):
        """Initialize Gemini service with API key"""
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    async def extract_structured_query(self, query: str) -> StructuredQuery:
        """Extract structured information from natural language query"""

        prompt = f"""
        Analyze the following query and extract structured information:
        Query: "{query}"

        Extract the following information and return as JSON:
        {{
            "entities": ["list of entities mentioned (policy numbers, names, etc.)"],
            "action": "primary action/question type (e.g., 'coverage inquiry', 'claim processing', 'waiting period')",
            "context": "main subject/context (e.g., 'maternity benefits', 'pre-existing conditions')",
            "intent": "specific intent (e.g., 'check coverage', 'find waiting period', 'verify benefits')"
        }}

        Return only the JSON object, no additional text.
        """

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)

            # Parse the JSON response
            import json
            structured_data = json.loads(response.text.strip())

            return StructuredQuery(**structured_data)

        except Exception as e:
            logger.error(f"Error extracting structured query: {e}")
            # Return default structure if parsing fails
            return StructuredQuery(
                entities=[],
                action="general_inquiry",
                context=query[:100],
                intent="answer_question"
            )

    async def generate_answer(self, query: str, retrieved_chunks: List[str], 
                            chunk_metadata: List[Dict[str, Any]]) -> QueryResponse:
        """Generate answer using retrieved document chunks"""

        # Prepare context from retrieved chunks
        context_parts = []
        for i, (chunk, metadata) in enumerate(zip(retrieved_chunks, chunk_metadata)):
            section = metadata.get('section', 'Unknown Section')
            page = metadata.get('page_number', 'Unknown')
            context_parts.append(f"[Source {i+1}] Section: {section}, Page: {page}\n{chunk}")

        context = "\n\n".join(context_parts)

        prompt = f"""
        Based on the following document excerpts, answer the user's question with accuracy and detail.

        Question: {query}

        Document Context:
        {context}

        Instructions:
        1. Provide a comprehensive answer based only on the provided document excerpts
        2. If the information is not available in the context, clearly state that
        3. Reference specific sections and pages when possible
        4. Be precise with numbers, dates, and conditions
        5. Keep the answer concise but complete

        Answer:
        """

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            answer = response.text.strip()

            # Generate rationale
            rationale = await self._generate_rationale(query, answer, retrieved_chunks, chunk_metadata)

            # Calculate confidence based on content quality and retrieval scores
            confidence = self._calculate_confidence(answer, retrieved_chunks)

            return QueryResponse(
                query=query,
                result=answer,
                rationale=rationale,
                confidence=confidence,
                processing_time=0.0  # Will be set by calling function
            )

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return QueryResponse(
                query=query,
                result=f"Error generating answer: {str(e)}",
                rationale=[],
                confidence=0.0,
                processing_time=0.0
            )

    async def _generate_rationale(self, query: str, answer: str, 
                                retrieved_chunks: List[str], 
                                chunk_metadata: List[Dict[str, Any]]) -> List[RationaleItem]:
        """Generate rationale for the answer"""

        rationale_items = []

        for chunk, metadata in zip(retrieved_chunks, chunk_metadata):
            # Check if this chunk contributed to the answer
            if self._chunk_contributes_to_answer(chunk, answer):
                rationale_item = RationaleItem(
                    section=metadata.get('section', 'Unknown Section'),
                    excerpt=chunk[:300] + "..." if len(chunk) > 300 else chunk,
                    source=metadata.get('document_id', 'Unknown Document'),
                    page=metadata.get('page_number'),
                    confidence=0.8  # Could be refined with more sophisticated scoring
                )
                rationale_items.append(rationale_item)

        return rationale_items

    def _chunk_contributes_to_answer(self, chunk: str, answer: str) -> bool:
        """Simple heuristic to check if chunk contributed to answer"""
        # Look for common words/phrases between chunk and answer
        chunk_words = set(chunk.lower().split())
        answer_words = set(answer.lower().split())

        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
        chunk_words -= stop_words
        answer_words -= stop_words

        # Check overlap
        overlap = len(chunk_words.intersection(answer_words))
        return overlap >= 3  # Threshold for contribution

    def _calculate_confidence(self, answer: str, retrieved_chunks: List[str]) -> float:
        """Calculate confidence score for the answer"""
        base_confidence = 0.7

        # Boost confidence if answer contains specific details
        if any(keyword in answer.lower() for keyword in ['percent', '%', 'days', 'months', 'years', 'amount']):
            base_confidence += 0.1

        # Boost confidence if multiple chunks support the answer
        if len(retrieved_chunks) >= 3:
            base_confidence += 0.1

        # Reduce confidence if answer is too short or generic
        if len(answer) < 50:
            base_confidence -= 0.2

        return min(max(base_confidence, 0.0), 1.0)

    async def health_check(self) -> bool:
        """Check if Gemini service is healthy"""
        try:
            test_response = await asyncio.to_thread(
                self.model.generate_content, 
                "Hello, this is a health check. Please respond with 'OK'."
            )
            return "ok" in test_response.text.lower()
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False
