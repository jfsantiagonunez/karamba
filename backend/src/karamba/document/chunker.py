"""Text chunking for document processing."""
from typing import List
from pydantic import BaseModel


class DocumentChunk(BaseModel):
    """Single chunk of document."""
    content: str
    chunk_id: str
    document_id: str
    metadata: dict = {}


class TextChunker:
    """Chunk text into smaller pieces for embedding."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
    
    def chunk_text(self, text: str, document_id: str) -> List[DocumentChunk]:
        """Chunk text using recursive character splitting."""
        chunks = self._split_text(text)
        
        return [
            DocumentChunk(
                content=chunk,
                chunk_id=f"{document_id}_chunk_{i}",
                document_id=document_id,
                metadata={"chunk_index": i, "total_chunks": len(chunks)}
            )
            for i, chunk in enumerate(chunks)
        ]
    
    def _split_text(self, text: str) -> List[str]:
        """Recursively split text by separators."""
        if len(text) <= self.chunk_size:
            return [text] if text else []
        
        # Try each separator
        for separator in self.separators:
            if separator in text:
                splits = text.split(separator)
                chunks = []
                current_chunk = ""
                
                for split in splits:
                    # Add separator back
                    piece = split + separator if separator else split
                    
                    if len(current_chunk) + len(piece) <= self.chunk_size:
                        current_chunk += piece
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = piece
                
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Add overlap between chunks
                overlapped_chunks = []
                for i, chunk in enumerate(chunks):
                    if i > 0 and self.chunk_overlap > 0:
                        # Add overlap from previous chunk
                        prev_chunk = chunks[i - 1]
                        overlap = prev_chunk[-self.chunk_overlap:]
                        chunk = overlap + chunk
                    overlapped_chunks.append(chunk)
                
                return [c for c in overlapped_chunks if c]
        
        # Fallback: hard split by chunk_size
        return [
            text[i:i + self.chunk_size]
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap)
        ]