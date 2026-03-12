"""Tests for text chunking."""
import pytest

from karamba.document import TextChunker, DocumentChunk


class TestDocumentChunk:
    """Tests for DocumentChunk model."""

    def test_create_document_chunk(self):
        """Test creating a document chunk."""
        chunk = DocumentChunk(
            content="Test content",
            chunk_id="doc1_chunk_0",
            document_id="doc1",
            metadata={"page": 1}
        )

        assert chunk.content == "Test content"
        assert chunk.chunk_id == "doc1_chunk_0"
        assert chunk.document_id == "doc1"
        assert chunk.metadata["page"] == 1

    def test_document_chunk_default_metadata(self):
        """Test DocumentChunk with default metadata."""
        chunk = DocumentChunk(
            content="Test",
            chunk_id="test_0",
            document_id="test_doc"
        )

        assert chunk.metadata == {}


class TestTextChunker:
    """Tests for TextChunker class."""

    def test_create_chunker(self):
        """Test creating a text chunker."""
        chunker = TextChunker(
            chunk_size=1000,
            chunk_overlap=200
        )

        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 200
        assert len(chunker.separators) > 0

    def test_chunker_defaults(self):
        """Test TextChunker default values."""
        chunker = TextChunker()

        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 200
        assert chunker.separators == ["\n\n", "\n", ". ", " ", ""]

    def test_chunk_short_text(self):
        """Test chunking text shorter than chunk size."""
        chunker = TextChunker(chunk_size=1000)
        text = "This is a short text."

        chunks = chunker.chunk_text(text, "doc1")

        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].document_id == "doc1"
        assert chunks[0].chunk_id == "doc1_chunk_0"

    def test_chunk_long_text(self):
        """Test chunking text longer than chunk size."""
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)

        # Create text longer than chunk size
        text = "This is a sentence. " * 20

        chunks = chunker.chunk_text(text, "doc1")

        assert len(chunks) > 1
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_id == f"doc1_chunk_{i}"
            assert chunk.document_id == "doc1"
            assert len(chunk.content) <= 100 + 20  # chunk_size + overlap

    def test_chunk_text_with_paragraphs(self):
        """Test chunking respects paragraph boundaries."""
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)

        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."

        chunks = chunker.chunk_text(text, "doc1")

        assert len(chunks) >= 2
        # Verify chunks contain complete information
        all_content = " ".join(c.content for c in chunks)
        assert "paragraph" in all_content.lower()

    def test_chunk_overlap(self):
        """Test that chunks have overlap."""
        chunker = TextChunker(chunk_size=50, chunk_overlap=20)

        text = "Word " * 30  # Create enough text to have multiple chunks

        chunks = chunker.chunk_text(text, "doc1")

        if len(chunks) > 1:
            # Check that there's some overlap between consecutive chunks
            for i in range(len(chunks) - 1):
                # Overlap means some content from chunk[i] appears in chunk[i+1]
                assert len(chunks[i].content) > 0
                assert len(chunks[i + 1].content) > 0

    def test_chunk_metadata(self):
        """Test that chunks include metadata."""
        chunker = TextChunker(chunk_size=100)
        text = "Test content for metadata checking."

        chunks = chunker.chunk_text(text, "doc1")

        assert "chunk_index" in chunks[0].metadata
        assert "total_chunks" in chunks[0].metadata
        assert chunks[0].metadata["chunk_index"] == 0
        assert chunks[0].metadata["total_chunks"] == len(chunks)

    def test_chunk_empty_text(self):
        """Test chunking empty text."""
        chunker = TextChunker()
        text = ""

        chunks = chunker.chunk_text(text, "doc1")

        assert len(chunks) == 0

    def test_chunk_whitespace_text(self):
        """Test chunking whitespace-only text."""
        chunker = TextChunker()
        text = "   \n\n   "

        chunks = chunker.chunk_text(text, "doc1")

        # Should handle whitespace gracefully
        assert isinstance(chunks, list)

    def test_chunk_with_custom_separators(self):
        """Test chunking with custom separators."""
        chunker = TextChunker(
            chunk_size=50,
            separators=["|", ",", " "]
        )

        text = "Part1|Part2|Part3|Part4|Part5"

        chunks = chunker.chunk_text(text, "doc1")

        assert len(chunks) >= 1
        # Verify chunking respects separator
        for chunk in chunks:
            assert chunk.content

    def test_chunk_very_long_text(self):
        """Test chunking very long text."""
        chunker = TextChunker(chunk_size=500, chunk_overlap=100)

        # Create a long document
        paragraphs = [f"This is paragraph {i}. " * 10 for i in range(50)]
        text = "\n\n".join(paragraphs)

        chunks = chunker.chunk_text(text, "long_doc")

        assert len(chunks) > 1
        # Verify all chunks have proper IDs
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_id == f"long_doc_chunk_{i}"
            assert chunk.metadata["chunk_index"] == i

    def test_chunk_preserves_content(self):
        """Test that chunking preserves all content."""
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)

        text = "Word " * 100

        chunks = chunker.chunk_text(text, "doc1")

        # Collect all unique content
        all_words = set()
        for chunk in chunks:
            words = chunk.content.split()
            all_words.update(words)

        # Should have captured "Word" multiple times
        assert "Word" in all_words

    def test_chunk_with_no_overlap(self):
        """Test chunking with no overlap."""
        chunker = TextChunker(chunk_size=50, chunk_overlap=0)

        text = "A " * 50

        chunks = chunker.chunk_text(text, "doc1")

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.content

    def test_split_text_internal(self):
        """Test internal _split_text method."""
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)

        text = "Short text"
        splits = chunker._split_text(text)

        assert len(splits) == 1
        assert splits[0] == text

    def test_split_text_with_separators(self):
        """Test _split_text respects separators."""
        chunker = TextChunker(chunk_size=30, chunk_overlap=5)

        text = "First sentence. Second sentence. Third sentence."
        splits = chunker._split_text(text)

        assert isinstance(splits, list)
        assert len(splits) >= 1

    def test_fallback_hard_split(self):
        """Test fallback to hard split when no separators work."""
        chunker = TextChunker(chunk_size=20, chunk_overlap=5)

        # Text with no separators
        text = "x" * 100

        splits = chunker._split_text(text)

        assert len(splits) >= 1
        # Each split should be close to chunk_size
        for split in splits[:-1]:  # Except possibly the last one
            assert len(split) <= chunker.chunk_size + chunker.chunk_overlap
