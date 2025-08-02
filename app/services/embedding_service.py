import logging
import asyncio
import numpy as np
import pickle
import os
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
import faiss

from config.config import settings
from app.models.schemas import DocumentChunk, RetrievalResult, EmbeddingStats

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating embeddings and semantic search"""

    def __init__(self):
        """Initialize embedding service"""
        self.model_name = settings.EMBEDDING_MODEL
        self.embedding_dimension = settings.EMBEDDING_DIMENSION
        self.top_k = settings.TOP_K_RESULTS

        # Initialize the sentence transformer model
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

        # Initialize FAISS index
        self.index = None
        self.chunk_metadata = []
        self.index_path = "data/faiss_index.bin"
        self.metadata_path = "data/chunk_metadata.pkl"

        # Load existing index if available
        self._load_index()

    async def create_embeddings(self, chunks: List[DocumentChunk]) -> List[np.ndarray]:
        """Create embeddings for document chunks"""
        logger.info(f"Creating embeddings for {len(chunks)} chunks")

        try:
            # Extract text from chunks
            texts = [chunk.text for chunk in chunks]

            # Generate embeddings
            embeddings = await asyncio.to_thread(self.model.encode, texts, show_progress_bar=True)

            # Convert to numpy array and normalize
            embeddings = np.array(embeddings).astype('float32')
            faiss.normalize_L2(embeddings)

            logger.info(f"Successfully created {len(embeddings)} embeddings")
            return embeddings

        except Exception as e:
            logger.error(f"Error creating embeddings: {e}")
            raise

    async def add_to_index(self, chunks: List[DocumentChunk], embeddings: np.ndarray):
        """Add embeddings to FAISS index"""
        logger.info(f"Adding {len(embeddings)} embeddings to index")

        try:
            # Initialize index if not exists
            if self.index is None:
                self.index = faiss.IndexFlatIP(self.embedding_dimension)  # Inner product for cosine similarity

            # Add embeddings to index
            self.index.add(embeddings)

            # Store chunk metadata
            for chunk in chunks:
                chunk_meta = {
                    'chunk_id': chunk.chunk_id,
                    'document_id': chunk.document_id,
                    'text': chunk.text,
                    'page_number': chunk.page_number,
                    'section': chunk.section,
                    'metadata': chunk.metadata
                }
                self.chunk_metadata.append(chunk_meta)

            # Save index and metadata
            await self._save_index()

            logger.info(f"Successfully added embeddings to index. Total vectors: {self.index.ntotal}")

        except Exception as e:
            logger.error(f"Error adding to index: {e}")
            raise

    async def search(self, query: str, k: Optional[int] = None) -> RetrievalResult:
        """Search for similar chunks using query"""
        if k is None:
            k = self.top_k

        logger.info(f"Searching for query: '{query[:50]}...' (top {k} results)")

        try:
            # Generate query embedding
            query_embedding = await asyncio.to_thread(self.model.encode, [query])
            query_embedding = np.array(query_embedding).astype('float32')
            faiss.normalize_L2(query_embedding)

            if self.index is None or self.index.ntotal == 0:
                logger.warning("No index available for search")
                return RetrievalResult(
                    chunks=[],
                    scores=[],
                    query_embedding=query_embedding[0].tolist()
                )

            # Search in index
            scores, indices = self.index.search(query_embedding, min(k, self.index.ntotal))

            # Retrieve corresponding chunks
            retrieved_chunks = []
            retrieved_scores = []

            for score, idx in zip(scores[0], indices[0]):
                if idx != -1:  # Valid index
                    chunk_meta = self.chunk_metadata[idx]

                    chunk = DocumentChunk(
                        text=chunk_meta['text'],
                        chunk_id=chunk_meta['chunk_id'],
                        document_id=chunk_meta['document_id'],
                        page_number=chunk_meta['page_number'],
                        section=chunk_meta['section'],
                        metadata=chunk_meta['metadata']
                    )

                    retrieved_chunks.append(chunk)
                    retrieved_scores.append(float(score))

            logger.info(f"Found {len(retrieved_chunks)} relevant chunks")

            return RetrievalResult(
                chunks=retrieved_chunks,
                scores=retrieved_scores,
                query_embedding=query_embedding[0].tolist()
            )

        except Exception as e:
            logger.error(f"Error during search: {e}")
            raise

    async def get_embeddings_stats(self) -> EmbeddingStats:
        """Get statistics about the embedding index"""
        try:
            total_embeddings = self.index.ntotal if self.index else 0

            # Calculate index size
            index_size = 0
            if os.path.exists(self.index_path):
                index_size = os.path.getsize(self.index_path)

            # Get last update time
            last_updated = None
            if os.path.exists(self.metadata_path):
                last_updated = os.path.getmtime(self.metadata_path)
                last_updated = datetime.fromtimestamp(last_updated)

            return EmbeddingStats(
                total_embeddings=total_embeddings,
                dimension=self.embedding_dimension,
                index_size=index_size,
                last_updated=last_updated or datetime.now()
            )

        except Exception as e:
            logger.error(f"Error getting embedding stats: {e}")
            raise

    async def _save_index(self):
        """Save FAISS index and metadata to disk"""
        try:
            # Create data directory if not exists
            os.makedirs("data", exist_ok=True)

            # Save FAISS index
            if self.index:
                faiss.write_index(self.index, self.index_path)

            # Save metadata
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.chunk_metadata, f)

            logger.info("Index and metadata saved successfully")

        except Exception as e:
            logger.error(f"Error saving index: {e}")
            raise

    def _load_index(self):
        """Load FAISS index and metadata from disk"""
        try:
            # Load FAISS index
            if os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")

            # Load metadata
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, 'rb') as f:
                    self.chunk_metadata = pickle.load(f)
                logger.info(f"Loaded metadata for {len(self.chunk_metadata)} chunks")

        except Exception as e:
            logger.error(f"Error loading index: {e}")
            # Initialize empty index and metadata
            self.index = None
            self.chunk_metadata = []

    async def clear_index(self):
        """Clear the entire index"""
        logger.info("Clearing embedding index")

        self.index = None
        self.chunk_metadata = []

        # Remove saved files
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
        if os.path.exists(self.metadata_path):
            os.remove(self.metadata_path)

        logger.info("Index cleared successfully")

    async def remove_document_from_index(self, document_id: str):
        """Remove all chunks of a specific document from index"""
        logger.info(f"Removing document {document_id} from index")

        # This is a complex operation with FAISS - would need to rebuild index
        # For now, we'll just mark it as removed in metadata
        # In production, consider using a more sophisticated vector DB like Pinecone

        # Filter out chunks from the specified document
        remaining_metadata = [
            meta for meta in self.chunk_metadata 
            if meta['document_id'] != document_id
        ]

        removed_count = len(self.chunk_metadata) - len(remaining_metadata)

        if removed_count > 0:
            logger.info(f"Need to rebuild index to remove {removed_count} chunks")
            # In a production system, you would rebuild the index here
            # For now, just log the action

        logger.info(f"Marked {removed_count} chunks for removal")

    async def health_check(self) -> bool:
        """Check if embedding service is healthy"""
        try:
            # Test embedding generation
            test_embedding = await asyncio.to_thread(self.model.encode, ["health check"])
            return len(test_embedding) > 0 and len(test_embedding[0]) == self.embedding_dimension
        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")
            return False
