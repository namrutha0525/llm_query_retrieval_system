import logging
import uvicorn
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from config.config import settings
from app.api.endpoints import router
from app.core.middleware import LoggingMiddleware, RateLimitingMiddleware, setup_cors_middleware

# Configure logging: logs to console and to file 'app.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting LLM Query-Retrieval System")
    logger.info(f"API Version: {settings.API_V1_STR}")
    logger.info(f"Gemini Model: {settings.GEMINI_MODEL}")
    logger.info(f"Embedding Model: {settings.EMBEDDING_MODEL}")

    # Placeholder for startup tasks,
    # e.g., initialize models or connections

    yield

    logger.info("Shutting down LLM Query-Retrieval System")

# Create FastAPI app instance with lifespan context
app = FastAPI(
    title="LLM-Powered Intelligent Query–Retrieval System",
    description="""
    An intelligent document processing and query-retrieval system powered by Google Gemini LLM.

    **Features:**
    - Process PDF documents from URLs
    - Semantic search with FAISS embeddings
    - Natural language query processing
    - Explainable AI with source citations
    - Real-world applications in insurance, legal, HR, and compliance domains

    **Workflow:**
    1. **Document Input**: Upload PDFs via Blob URLs
    2. **LLM Parser**: Extract structured queries using Google Gemini
    3. **Embedding Search**: FAISS-powered semantic retrieval
    4. **Clause Matching**: Semantic similarity matching
    5. **Logic Evaluation**: AI-powered decision processing
    6. **JSON Output**: Structured responses with rationale
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware allowing all origins (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add custom middlewares for logging and rate limiting
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitingMiddleware, max_requests=100, window_seconds=60)

# Include API router with versioned prefix from config
app.include_router(router, prefix=settings.API_V1_STR)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic service info"""
    return {
        "message": "LLM-Powered Intelligent Query–Retrieval System",
        "version": "1.0.0",
        "status": "active",
        "docs": "/docs",
        "api_version": settings.API_V1_STR
    }

# Global exception handler to capture unhandled errors with logging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred",
            "path": str(request.url.path)
        }
    )

# Health check endpoint for load balancers or monitoring tools
@app.get("/ping")
async def ping():
    return {"status": "pong", "timestamp": "2025-08-01T14:00:00Z"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,  # Use False in production
        log_level="info"
    )
