import logging
import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from config.config import settings
from app.models.schemas import (
    DocumentRequest, DocumentResponse, QueryRequest, QueryResponse,
    DocumentChunk, ClauseMatch, RationaleItem
)
from app.services.gemini_service import GeminiLLMService
from app.services.document_service import DocumentProcessingService
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class QueryProcessingService:
    """Main service that orchestrates the entire query processing workflow"""

    def __init__(self):
        """Initialize all services"""
        self.gemini_service = GeminiLLMService()
        self.document_service = DocumentProcessingService()
        self.embedding_service = EmbeddingService()

    async def process_document_request(self, request: DocumentRequest) -> DocumentResponse:
        """Process document and answer multiple questions"""
        start_time = time.time()

        logger.info(f"Processing document request with {len(request.questions)} questions")

        try:
            # Step 1: Process the document
            document_id = await self._process_document(request.documents)

            # Step 2: Process all questions
            answers = []
            detailed_responses = []

            for question in request.questions:
                logger.info(f"Processing question: {question[:50]}...")

                # Process individual query
                query_response = await self._process_single_query(question, document_id)

                answers.append(query_response.result)
                detailed_responses.append(query_response)

            processing_time = time.time() - start_time

            logger.info(f"Completed document request processing in {processing_time:.2f}s")

            return DocumentResponse(
                answers=answers,
                detailed_responses=detailed_responses,
                document_id=document_id,
                processing_time=processing_time
            )

        except Exception as e:
            logger.error(f"Error processing document request: {e}")
            raise

    async def _process_document(self, document_url: str) -> str:
        """Process document: download, extract, chunk, and index"""

        # Check if document is already processed (simple cache based on URL)
        document_id = self.document_service._generate_document_id(document_url)

        # For now, always reprocess. In production, you'd check if already indexed
        logger.info(f"Processing document: {document_url}")

        # Step 1: Download and extract text
        chunks, metadata = await self.document_service.process_document_from_url(document_url)

        # Step 2: Generate embeddings
        embeddings = await self.embedding_service.create_embeddings(chunks)

        # Step 3: Add to search index
        await self.embedding_service.add_to_index(chunks, embeddings)

        logger.info(f"Document {document_id} processed successfully with {len(chunks)} chunks")

        return document_id

    async def _process_single_query(self, query: str, document_id: Optional[str] = None) -> QueryResponse:
        """Process a single query through the complete pipeline"""
        start_time = time.time()

        try:
            # Step 1: Extract structured query information
            logger.debug("Extracting structured query")
            structured_query = await self.gemini_service.extract_structured_query(query)

            # Step 2: Semantic search for relevant chunks
            logger.debug("Performing semantic search")
            retrieval_result = await self.embedding_service.search(query)

            # Step 3: Clause matching - filter and rank results
            logger.debug("Matching clauses")
            matched_clauses = await self._match_clauses(query, retrieval_result)

            # Step 4: Generate answer using LLM
            logger.debug("Generating answer")
            retrieved_texts = [chunk.text for chunk in retrieval_result.chunks]
            chunk_metadata = [
                {
                    'section': chunk.section,
                    'page_number': chunk.page_number,
                    'document_id': chunk.document_id,
                    'chunk_id': chunk.chunk_id
                }
                for chunk in retrieval_result.chunks
            ]

            response = await self.gemini_service.generate_answer(
                query, retrieved_texts, chunk_metadata
            )

            # Update processing time
            response.processing_time = time.time() - start_time

            logger.info(f"Query processed in {response.processing_time:.2f}s with confidence {response.confidence:.2f}")

            return response

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return QueryResponse(
                query=query,
                result=f"Error processing query: {str(e)}",
                rationale=[],
                confidence=0.0,
                processing_time=time.time() - start_time
            )

    async def _match_clauses(self, query: str, retrieval_result) -> List[ClauseMatch]:
        """Match and rank clauses based on semantic similarity and relevance"""

        matched_clauses = []

        for i, (chunk, score) in enumerate(zip(retrieval_result.chunks, retrieval_result.scores)):
            # Apply confidence threshold
            if score >= settings.CONFIDENCE_THRESHOLD:
                clause_match = ClauseMatch(
                    text=chunk.text,
                    section=chunk.section or "Unknown Section",
                    page=chunk.page_number,
                    similarity_score=score,
                    chunk_id=chunk.chunk_id
                )
                matched_clauses.append(clause_match)

        # Sort by similarity score
        matched_clauses.sort(key=lambda x: x.similarity_score, reverse=True)

        logger.debug(f"Matched {len(matched_clauses)} clauses above threshold")

        return matched_clauses

    async def process_query_request(self, request: QueryRequest) -> QueryResponse:
        """Process a single query request"""
        logger.info(f"Processing individual query: {request.query[:50]}...")

        return await self._process_single_query(request.query, request.document_id)

    async def health_check(self) -> Dict[str, str]:
        """Check health of all services"""
        health_status = {}

        try:
            # Check Gemini service
            gemini_healthy = await self.gemini_service.health_check()
            health_status['gemini'] = 'healthy' if gemini_healthy else 'unhealthy'

            # Check embedding service
            embedding_healthy = await self.embedding_service.health_check()
            health_status['embeddings'] = 'healthy' if embedding_healthy else 'unhealthy'

            # Check document service (simple validation)
            health_status['document_processing'] = 'healthy'  # Always healthy if no exceptions

            # Overall status
            all_healthy = all(status == 'healthy' for status in health_status.values())
            health_status['overall'] = 'healthy' if all_healthy else 'degraded'

        except Exception as e:
            logger.error(f"Health check error: {e}")
            health_status['overall'] = 'unhealthy'
            health_status['error'] = str(e)

        return health_status

    async def get_service_stats(self) -> Dict[str, Any]:
        """Get statistics from all services"""
        try:
            stats = {}

            # Embedding stats
            embedding_stats = await self.embedding_service.get_embeddings_stats()
            stats['embeddings'] = embedding_stats.dict()

            # Add more service stats as needed
            stats['timestamp'] = datetime.now().isoformat()

            return stats

        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}

    async def clear_index(self):
        """Clear the embedding index (useful for testing/reset)"""
        logger.info("Clearing embedding index")
        await self.embedding_service.clear_index()

    async def remove_document(self, document_id: str):
        """Remove a specific document from the index"""
        logger.info(f"Removing document {document_id}")
        await self.embedding_service.remove_document_from_index(document_id)
