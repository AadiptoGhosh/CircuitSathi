"""
Tests for PDF Ingestion, Page Extraction, and Chunking.
"""

from pathlib import Path
import pytest
from config import SAMPLE_DOCS_DIR
from src.pdf_ingest import process_pdf, validate_pdf_file, split_text_into_chunks


def test_validate_pdf_file(tmp_path):
    """Test validation of file existence, extension, and empty files."""
    # Non-existent
    ok, msg = validate_pdf_file(tmp_path / "ghost.pdf")
    assert not ok
    assert "does not exist" in msg

    # Bad extension
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("Hello")
    ok, msg = validate_pdf_file(txt_file)
    assert not ok
    assert "Unsupported file extension" in msg

    # Empty file
    empty_pdf = tmp_path / "empty.pdf"
    empty_pdf.touch()
    ok, msg = validate_pdf_file(empty_pdf)
    assert not ok
    assert "empty" in msg


def test_split_text_into_chunks():
    """Test sliding window chunking with word boundary handling."""
    text = "Short text under 600 chars."
    chunks = split_text_into_chunks(text, chunk_size=600, chunk_overlap=120)
    assert len(chunks) == 1
    assert chunks[0] == text

    # Long text
    long_text = " ".join([f"Word{i}" for i in range(300)])
    chunks = split_text_into_chunks(long_text, chunk_size=200, chunk_overlap=50)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 250  # Boundary margin


def test_process_tb6612fng_pdf():
    """Verify that sample TB6612FNG datasheet parses with exact 3 pages and chunk metadata."""
    sample_path = SAMPLE_DOCS_DIR / "TB6612FNG_Datasheet.pdf"
    assert sample_path.exists(), "Sample PDF must exist"

    result = process_pdf(sample_path)
    assert result.doc_name == "TB6612FNG_Datasheet.pdf"
    assert result.page_count == 3
    assert result.total_chunks >= 3
    
    # Check page numbers are 1-indexed
    pages = {c.page_number for c in result.chunks}
    assert 1 in pages
    assert 2 in pages
    assert 3 in pages
    assert 0 not in pages, "Page numbers must be 1-indexed"

    # Check content of page 2 includes STBY or PWMA
    p2_chunks = [c for c in result.chunks if c.page_number == 2]
    combined_p2 = " ".join(c.content for c in p2_chunks)
    assert "STBY" in combined_p2
    assert "PWMA" in combined_p2
    assert "4.5 V to 13.5 V" in combined_p2


def test_corrupted_pdf_handling(tmp_path):
    """Ensure corrupted PDFs fail gracefully without unhandled exceptions."""
    corrupted = tmp_path / "corrupt.pdf"
    corrupted.write_bytes(b"%PDF-1.4 garbage binary data not a real pdf header EOF")
    
    with pytest.raises(ValueError) as excinfo:
        process_pdf(corrupted)
    assert "corrupted" in str(excinfo.value).lower() or "failed to open" in str(excinfo.value).lower()
