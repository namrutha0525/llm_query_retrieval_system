from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

class DocumentRequest(BaseModel):
    """Request model for document processing"""
    documents: str = Field(..., description="URL to the document (PDF)")
    questions: List[str] = Field(..., description="List of questions to answer")

class QueryRequest(BaseModel):
    """Request model for individual query processing"""
    query: str = Field(..., description="Natural language query")
    document_id: Optional[str] = Field(None, description="Document identifier")

class StructuredQuery(BaseModel):
    """Structured query extracted from natural language"""
    entities: List[str] = Field(default_factory=list, description="Extracted entities")
    action: str = Field(..., description="Action type (e.g., coverage inquiry)")
    context: str = Field(..., description="Query context")
    intent: str = Field(..., description="Parsed intent")

class DocumentChunk(BaseModel):
    """Document chunk with metadata"""
    text: str = Field(..., description="Chunk text content")
    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Parent document identifier")
    page_number: Optional[int] = Field(None, description="Page number")
    section: Optional[str] = Field(None, description="Document section")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ClauseMatch(BaseModel):
    """Matched clause with similarity score"""
    text: str = Field(..., description="Clause text")
    section: str = Field(..., description="Document section")
    page: Optional[int] = Field(None, description="Page number")
    similarity_score: float = Field(..., description="Semantic similarity score")
    chunk_id: str = Field(..., description="Source chunk identifier")

class RetrievalResult(BaseModel):
    """Result from embedding search"""
    chunks: List[DocumentChunk] = Field(..., description="Retrieved document chunks")
    scores: List[float] = Field(..., description="Similarity scores")
    query_embedding: List[float] = Field(..., description="Query embedding vector")

class RationaleItem(BaseModel):
    """Individual rationale item for explainability"""
    section: str = Field(..., description="Document section")
    excerpt: str = Field(..., description="Relevant text excerpt")
    source: str = Field(..., description="Source document")
    page: Optional[int] = Field(None, description="Page number")
    confidence: float = Field(..., description="Confidence score")

class QueryResponse(BaseModel):
    """Individual query response"""
    query: str = Field(..., description="Original query")
    result: str = Field(..., description="Generated answer")
    rationale: List[RationaleItem] = Field(default_factory=list, description="Supporting evidence")
    confidence: float = Field(..., description="Overall confidence score")
    processing_time: float = Field(..., description="Processing time in seconds")

class DocumentResponse(BaseModel):
    """Response model for document processing"""
    answers: List[str] = Field(..., description="List of answers corresponding to questions")
    detailed_responses: Optional[List[QueryResponse]] = Field(None, description="Detailed responses with rationale")
    document_id: str = Field(..., description="Processed document identifier")
    processing_time: float = Field(..., description="Total processing time")

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    error_code: Optional[str] = Field(None, description="Error code")

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="API version")
    components: Dict[str, str] = Field(..., description="Component status")

class DocumentMetadata(BaseModel):
    """Document metadata"""
    document_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    upload_time: datetime = Field(..., description="Upload timestamp")
    processed: bool = Field(default=False, description="Processing status")
    chunk_count: int = Field(default=0, description="Number of chunks created")

class EmbeddingStats(BaseModel):
    """Embedding statistics"""
    total_embeddings: int = Field(..., description="Total number of embeddings")
    dimension: int = Field(..., description="Embedding dimension")
    index_size: int = Field(..., description="Index size")
    last_updated: datetime = Field(..., description="Last update time")
