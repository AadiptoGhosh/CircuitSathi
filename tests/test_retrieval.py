"""
Tests for Vector Store and Semantic Retrieval.
"""

from pathlib import Path
import pytest
from src.pdf_ingest import process_pdf
from src.retrieval import VectorStore, format_context_for_prompt
from config import SAMPLE_DOCS_DIR


@pytest.fixture(scope="module")
def test_vector_store(tmp_path_factory):
    """Temporary persistent Chroma vector store fixture."""
    tmp_dir = tmp_path_factory.mktemp("chroma_test")
    store = VectorStore(persist_dir=tmp_dir)
    return store


def test_indexing_and_query(test_vector_store):
    """Test indexing sample datasheet chunks and performing semantic query."""
    pdf_path = SAMPLE_DOCS_DIR / "TB6612FNG_Datasheet.pdf"
    assert pdf_path.exists(), "Sample datasheet must exist"

    ingest_res = process_pdf(pdf_path)
    added_count = test_vector_store.add_document_chunks(ingest_res.chunks)
    assert added_count == len(ingest_res.chunks)

    # Query for STBY pin function
    results = test_vector_store.query("What is the function of the STBY standby pin?", top_k=2)
    assert len(results) > 0

    top_match = results[0]
    assert "STBY" in top_match["content"]
    assert top_match["page_number"] in [1, 2, 3]
    assert "TB6612FNG_Datasheet.pdf" in top_match["doc_name"]
    assert top_match["score"] > 0.20
    assert "[Doc: TB6612FNG_Datasheet.pdf, Page:" in top_match["citation"]

    # Test format_context_for_prompt
    formatted = format_context_for_prompt(results)
    assert "PASSAGE 1" in formatted
    assert "STBY" in formatted


def test_document_listing_and_deletion(test_vector_store):
    """Verify document deduplication, listing, and deletion."""
    docs = test_vector_store.list_documents()
    assert any(d["doc_name"] == "TB6612FNG_Datasheet.pdf" for d in docs)

    # Delete document
    ok = test_vector_store.delete_document("TB6612FNG_Datasheet.pdf")
    assert ok is True

    # Confirm deletion
    docs_after = test_vector_store.list_documents()
    assert not any(d["doc_name"] == "TB6612FNG_Datasheet.pdf" for d in docs_after)
