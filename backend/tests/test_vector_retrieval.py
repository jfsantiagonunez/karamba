"""Tests for vector retrieval."""
import pytest
from unittest.mock import Mock, patch, MagicMock

from karamba.document import VectorRetriever, RetrievedChunk, DocumentChunk


class TestVectorRetriever:
    """Tests for VectorRetriever class."""

    @pytest.fixture
    def mock_chroma_client(self):
        """Create a mock ChromaDB client."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        return mock_client, mock_collection

    def test_create_retriever(self, temp_test_dir):
        """Test creating a vector retriever."""
        with patch('karamba.document.retriever.chromadb.PersistentClient'):
            retriever = VectorRetriever(
                persist_directory=str(temp_test_dir / "vector_store")
            )

            assert retriever is not None

    def test_add_chunks(self, temp_test_dir, sample_document_chunks, mock_chroma_client):
        """Test adding chunks to vector store."""
        mock_client, mock_collection = mock_chroma_client

        with patch('karamba.document.retriever.chromadb.PersistentClient', return_value=mock_client):
            with patch('karamba.document.retriever.EmbeddingGenerator'):
                retriever = VectorRetriever(persist_directory=str(temp_test_dir))

                retriever.add_chunks(sample_document_chunks)

                # Verify collection.add was called
                mock_collection.add.assert_called_once()

    def test_retrieve_chunks(self, temp_test_dir, mock_chroma_client):
        """Test retrieving chunks by query."""
        mock_client, mock_collection = mock_chroma_client

        # Mock query results
        mock_collection.query.return_value = {
            'ids': [['chunk1', 'chunk2']],
            'documents': [['First chunk content', 'Second chunk content']],
            'distances': [[0.1, 0.2]],
            'metadatas': [[
                {'document_id': 'doc1', 'chunk_index': 0},
                {'document_id': 'doc1', 'chunk_index': 1}
            ]]
        }

        with patch('karamba.document.retriever.chromadb.PersistentClient', return_value=mock_client):
            with patch('karamba.document.retriever.EmbeddingGenerator') as mock_emb:
                mock_emb.return_value.generate.return_value = [0.1, 0.2, 0.3]

                retriever = VectorRetriever(persist_directory=str(temp_test_dir))
                results = retriever.retrieve("test query", top_k=2)

                assert len(results) <= 2
                mock_collection.query.assert_called_once()

    def test_retrieve_with_filter(self, temp_test_dir, mock_chroma_client):
        """Test retrieving chunks with document filter."""
        mock_client, mock_collection = mock_chroma_client
        mock_collection.query.return_value = {
            'ids': [['chunk1']],
            'documents': [['Content']],
            'distances': [[0.1]],
            'metadatas': [[{'document_id': 'doc1'}]]
        }

        with patch('karamba.document.retriever.chromadb.PersistentClient', return_value=mock_client):
            with patch('karamba.document.retriever.EmbeddingGenerator') as mock_emb:
                mock_emb.return_value.generate.return_value = [0.1, 0.2]

                retriever = VectorRetriever(persist_directory=str(temp_test_dir))
                results = retriever.retrieve("query", document_ids=["doc1"])

                # Verify filter was passed
                call_kwargs = mock_collection.query.call_args[1]
                assert 'where' in call_kwargs

    def test_delete_document(self, temp_test_dir, mock_chroma_client):
        """Test deleting a document from vector store."""
        mock_client, mock_collection = mock_chroma_client

        with patch('karamba.document.retriever.chromadb.PersistentClient', return_value=mock_client):
            retriever = VectorRetriever(persist_directory=str(temp_test_dir))
            retriever.delete_document("doc1")

            mock_collection.delete.assert_called_once()

    def test_get_stats(self, temp_test_dir, mock_chroma_client):
        """Test getting vector store statistics."""
        mock_client, mock_collection = mock_chroma_client
        mock_collection.count.return_value = 150

        with patch('karamba.document.retriever.chromadb.PersistentClient', return_value=mock_client):
            retriever = VectorRetriever(persist_directory=str(temp_test_dir))
            stats = retriever.get_stats()

            assert "total_chunks" in stats or isinstance(stats, dict)

    def test_empty_query(self, temp_test_dir, mock_chroma_client):
        """Test retrieving with empty query."""
        mock_client, mock_collection = mock_chroma_client

        with patch('karamba.document.retriever.chromadb.PersistentClient', return_value=mock_client):
            with patch('karamba.document.retriever.EmbeddingGenerator') as mock_emb:
                mock_emb.return_value.generate.return_value = [0.1]

                retriever = VectorRetriever(persist_directory=str(temp_test_dir))

                # Should handle empty query gracefully
                mock_collection.query.return_value = {
                    'ids': [[]],
                    'documents': [[]],
                    'distances': [[]],
                    'metadatas': [[]]
                }

                results = retriever.retrieve("")
                assert isinstance(results, list)


class TestRetrievedChunk:
    """Tests for RetrievedChunk model."""

    def test_create_retrieved_chunk(self):
        """Test creating a retrieved chunk."""
        chunk = DocumentChunk(
            content="Test content",
            chunk_id="test_chunk_0",
            document_id="test_doc",
            metadata={}
        )

        retrieved = RetrievedChunk(
            chunk=chunk,
            score=0.95
        )

        assert retrieved.chunk.content == "Test content"
        assert retrieved.score == 0.95

    def test_retrieved_chunk_ordering(self):
        """Test that retrieved chunks can be sorted by score."""
        chunk1 = DocumentChunk(
            content="Content 1",
            chunk_id="chunk1",
            document_id="doc1"
        )

        chunk2 = DocumentChunk(
            content="Content 2",
            chunk_id="chunk2",
            document_id="doc1"
        )

        retrieved1 = RetrievedChunk(chunk=chunk1, score=0.85)
        retrieved2 = RetrievedChunk(chunk=chunk2, score=0.95)

        chunks = [retrieved1, retrieved2]
        sorted_chunks = sorted(chunks, key=lambda x: x.score, reverse=True)

        assert sorted_chunks[0].score == 0.95
        assert sorted_chunks[1].score == 0.85
