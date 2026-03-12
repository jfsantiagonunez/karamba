"""Embedding generation for vector search."""
from typing import List
from sentence_transformers import SentenceTransformer
from loguru import logger


class EmbeddingGenerator:
    """Generate embeddings for text chunks."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize embedding model.
        
        Args:
            model_name: Sentence transformer model name
                       Options: 'all-MiniLM-L6-v2' (fast, 384 dims)
                               'all-mpnet-base-v2' (better quality, 768 dims)
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding dimension: {self.dimension}")
    
    def encode(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for list of texts."""
        if not texts:
            return []
        
        logger.info(f"Generating embeddings for {len(texts)} texts")
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 10,
            convert_to_numpy=True
        )
        
        return embeddings.tolist()
    
    def encode_query(self, query: str) -> List[float]:
        """Generate embedding for a single query."""
        embedding = self.model.encode(query, convert_to_numpy=True)
        return embedding.tolist()