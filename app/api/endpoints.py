from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
import logging
from datetime import datetime

from app.models.schemas import (
    DocumentRequest, DocumentResponse, QueryRequest, QueryResponse,
    HealthResponse, ErrorResponse
)
from app.services.query_service import QueryProcessingService  
from app.core.auth import get_current_token

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize query processing service
query_service = QueryProcessingService()

@router.post("/hackrx/run", response_model=DocumentResponse)
async def run_document_processing(
    request: DocumentRequest,
    token: str = Depends(get_current_token)
) -> DocumentResponse:
    """
    Main endpoint for processing documents and answering questions

    This endpoint matches the specification provided:
    - Takes a document URL and list of questions
    - Returns structured answers
    """
    logger.info(f"Received document processing request with {len(request.questions)} questions")

    try:
        # Validate document URL
        if not request.documents:
            raise HTTPException(
                status_code=400,
                detail="Document URL is required"
            )

        # Validate questions
        if not request.questions or len(request.questions) == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one question is required"
            )

        # Process the request
        response = await query_service.process_document_request(request)

        logger.info(f"Successfully processed document request in {response.processing_time:.2f}s")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/query", response_model=QueryResponse)
async def process_single_query(
    request: QueryRequest,
    token: str = Depends(get_current_token)
) -> QueryResponse:
    """
    Process a single query against the indexed documents
    """
    logger.info(f"Received single query: {request.query[:50]}...")

    try:
        response = await query_service.process_query_request(request)

        logger.info(f"Successfully processed query in {response.processing_time:.2f}s")

        return response

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint - no authentication required
    """
    try:
        # Check service health
        components = await query_service.health_check()

        overall_status = "healthy" if components.get("overall") == "healthy" else "unhealthy"

        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now(),
            version="1.0.0",
            components=components
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            version="1.0.0",
            components={"error": str(e)}
        )

@router.get("/stats")
async def get_service_statistics(
    token: str = Depends(get_current_token)
) -> Dict[str, Any]:
    """
    Get service statistics and metrics
    """
    try:
        stats = await query_service.get_service_stats()
        return stats

    except Exception as e:
        logger.error(f"Error getting service stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving statistics: {str(e)}"
        )

@router.delete("/index/clear")
async def clear_index(
    token: str = Depends(get_current_token)
) -> Dict[str, str]:
    """
    Clear the embedding index (useful for testing)
    """
    try:
        await query_service.clear_index()

        logger.info("Index cleared successfully")

        return {"message": "Index cleared successfully"}

    except Exception as e:
        logger.error(f"Error clearing index: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing index: {str(e)}"
        )

@router.delete("/documents/{document_id}")
async def remove_document(
    document_id: str,
    token: str = Depends(get_current_token)
) -> Dict[str, str]:
    """
    Remove a specific document from the index
    """
    try:
        await query_service.remove_document(document_id)

        logger.info(f"Document {document_id} removal initiated")

        return {"message": f"Document {document_id} removal initiated"}

    except Exception as e:
        logger.error(f"Error removing document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error removing document: {str(e)}"
        )

# Error handlers
@router.exception_handler(404)
async def not_found_handler(request, exc):
    return ErrorResponse(
        error="Endpoint not found",
        detail="The requested endpoint does not exist",
        error_code="NOT_FOUND"
    )

@router.exception_handler(422)
async def validation_error_handler(request, exc):
    return ErrorResponse(
        error="Validation error",
        detail="Request validation failed",
        error_code="VALIDATION_ERROR"
    )
