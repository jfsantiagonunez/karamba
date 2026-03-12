"""Vector-based document retrieval."""
from pathlib import Path
from typing import List, Optional
import chromadb
from chromadb.config import Settings
from pydantic import BaseModel
from loguru import logger

from .embeddings import EmbeddingGenerator
from .chunker import DocumentChunk


class RetrievedChunk(BaseModel):
    """Retrieved document chunk with relevance score."""
    chunk: DocumentChunk
    score: float
    rank: int


class VectorRetriever:
    """Retrieve relevant chunks using vector similarity."""
    
    def __init__(
        self,
        persist_directory: str = "./vector_store",
        collection_name: str = "documents",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.embedder = EmbeddingGenerator(embedding_model)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"Initialized vector store at {self.persist_directory}")
    
    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Add document chunks to vector store."""
        if not chunks:
            return
        
        logger.info(f"Adding {len(chunks)} chunks to vector store")
        
        texts = [chunk.content for chunk in chunks]
        embeddings = self.embedder.encode(texts)
        
        self.collection.add(
            ids=[chunk.chunk_id for chunk in chunks],
            embeddings=embeddings,
            documents=texts,
            metadatas=[
                {
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.metadata.get("chunk_index", 0),
                    **chunk.metadata
                }
                for chunk in chunks
            ]
        )
        
        logger.info("Chunks added successfully")
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        min_score: float = 0.7
    ) -> List[RetrievedChunk]:
        """
        Retrieve most relevant chunks for query, optionally filtered by document ID(s).

        Args:
            query: Search query
            top_k: Maximum number of results to return
            document_id: Filter by single document ID (deprecated, use document_ids)
            document_ids: Filter by multiple document IDs
            min_score: Minimum relevance score (0-1). Results below this are filtered out.

        Returns:
            List of retrieved chunks with scores >= min_score
        """
        logger.info(f"Retrieving top {top_k} chunks for query: {query[:100]} (min_score={min_score})")

        query_embedding = self.embedder.encode_query(query)

        # Build where filter if document_id(s) specified
        where_filter = None
        if document_ids is not None:
            # document_ids was explicitly provided
            if len(document_ids) == 0:
                # Empty list means no documents in this session - return no results
                logger.info("No documents linked to this session, returning empty results")
                return []
            else:
                # Filter by multiple document IDs
                where_filter = {"document_id": {"$in": document_ids}}
                logger.info(f"Filtering by {len(document_ids)} document IDs")
        elif document_id:
            # Filter by single document ID (backwards compatibility)
            where_filter = {"document_id": document_id}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter
        )
        
        if not results["ids"] or not results["ids"][0]:
            logger.warning("No results found")
            return []
        
        retrieved = []
        filtered_count = 0
        for i, (chunk_id, doc, metadata, distance) in enumerate(zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            # Convert distance to similarity score (cosine: 0=similar, 2=dissimilar)
            score = 1 - (distance / 2)

            # Filter out low-relevance results
            if score < min_score:
                filtered_count += 1
                logger.debug(f"Filtered out chunk with score {score:.3f} < {min_score}")
                continue

            chunk = DocumentChunk(
                content=doc,
                chunk_id=chunk_id,
                document_id=metadata.get("document_id", "unknown"),
                metadata=metadata
            )
            
            retrieved.append(RetrievedChunk(
                chunk=chunk,
                score=score,
                rank=i + 1
            ))

        if filtered_count > 0:
            logger.info(f"Retrieved {len(retrieved)} chunks (filtered {filtered_count} low-relevance results)")
        else:
            logger.info(f"Retrieved {len(retrieved)} chunks")
        return retrieved
    
    def delete_document(self, document_id: str) -> None:
        """Delete all chunks for a document."""
        logger.info(f"Deleting chunks for document: {document_id}")
        
        # Query all chunks for this document
        results = self.collection.get(
            where={"document_id": document_id}
        )
        
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            logger.info(f"Deleted {len(results['ids'])} chunks")
    
    def clear(self) -> None:
        """Clear all documents from collection."""
        logger.warning("Clearing all documents from vector store")
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.create_collection(
            name=self.collection.name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def get_stats(self) -> dict:
        """Get statistics about vector store."""
        count = self.collection.count()
        return {
            "total_chunks": count,
            "collection_name": self.collection.name,
            "persist_directory": str(self.persist_directory)
        }