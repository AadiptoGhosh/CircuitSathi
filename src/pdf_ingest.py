"""
CircuitSathi PDF Ingestion Engine
Extracts text page-by-page with 1-indexed numbers, OCR fallback for scanned pages,
chunking with metadata, and robust validation against corrupted/encrypted PDFs.
"""

from pathlib import Path
from typing import Any
import hashlib
import pymupdf as fitz
from pydantic import BaseModel, Field
from config import settings
from src.ocr import is_ocr_available, extract_text_from_image


class DocumentChunk(BaseModel):
    """Represents an embedded passage chunk with provenance."""
    chunk_id: str
    doc_name: str
    page_number: int  # 1-indexed
    chunk_index: int
    content: str
    is_ocr: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResult(BaseModel):
    """Result of processing a technical PDF document."""
    doc_name: str
    file_path: str
    page_count: int
    total_chunks: int
    ocr_pages_count: int
    chunks: list[DocumentChunk]
    warnings: list[str] = Field(default_factory=list)
    has_complex_tables_or_drawings: bool = False


def validate_pdf_file(file_path: Path | str) -> tuple[bool, str]:
    """Validate file existence, extension, and size."""
    path = Path(file_path)
    if not path.exists():
        return False, f"File does not exist: {path.name}"
    if path.suffix.lower() not in settings.allowed_extensions:
        return False, f"Unsupported file extension '{path.suffix}'. Allowed: {settings.allowed_extensions}"
    
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > settings.max_upload_size_mb:
        return False, f"File size ({size_mb:.1f} MB) exceeds maximum allowed {settings.max_upload_size_mb} MB."
    
    if path.stat().st_size == 0:
        return False, "File is completely empty (0 bytes)."
    
    return True, "Valid"


def split_text_into_chunks(
    text: str,
    chunk_size: int = 600,
    chunk_overlap: int = 120
) -> list[str]:
    """
    Split text into overlapping sliding-window chunks with clean boundary handling.
    """
    cleaned_text = " ".join(text.split())
    if not cleaned_text:
        return []
    
    if len(cleaned_text) <= chunk_size:
        return [cleaned_text]
    
    chunks = []
    start = 0
    text_len = len(cleaned_text)
    
    while start < text_len:
        end = start + chunk_size
        if end >= text_len:
            chunk = cleaned_text[start:]
            chunks.append(chunk)
            break
        
        # Try to break at a sentence or word boundary within the last 50 chars of window
        last_space = cleaned_text.rfind(" ", start + (chunk_size // 2), end)
        if last_space != -1 and last_space > start:
            chunk = cleaned_text[start:last_space]
            start = max(last_space + 1 - chunk_overlap, start + 1)
        else:
            chunk = cleaned_text[start:end]
            start = end - chunk_overlap
            
        chunks.append(chunk)
        
    return chunks


def process_pdf(
    file_path: Path | str,
    doc_name: str | None = None,
    chunk_size: int = settings.chunk_size,
    chunk_overlap: int = settings.chunk_overlap
) -> IngestResult:
    """
    Extracts text page-by-page from PDF, applies OCR to image-only pages if needed,
    and returns chunked text with source page citations.
    """
    path = Path(file_path)
    is_valid, reason = validate_pdf_file(path)
    if not is_valid:
        raise ValueError(reason)

    name = doc_name or path.name
    warnings: list[str] = []
    chunks: list[DocumentChunk] = []
    ocr_pages_count = 0
    has_complex_drawings = False

    try:
        doc = fitz.open(str(path))
    except Exception as e:
        raise ValueError(f"Failed to open PDF (file may be corrupted or encrypted): {str(e)}")

    if doc.is_encrypted:
        doc.close()
        raise ValueError("PDF is password-protected or encrypted. Please decrypt before uploading.")

    page_count = len(doc)
    if page_count == 0:
        doc.close()
        raise ValueError("PDF contains 0 pages.")

    try:
        for page_idx in range(page_count):
            page_num = page_idx + 1  # 1-indexed
            page = doc[page_idx]
            
            # Check for vector drawings or complex tables
            drawings = page.get_drawings()
            if len(drawings) > 20:
                has_complex_drawings = True

            text = page.get_text("text").strip()
            is_ocr = False

            # If page text is minimal (< 50 chars), check if page has images / is scanned
            if len(text) < 50:
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                
                if is_ocr_available():
                    ocr_text, ocr_ok = extract_text_from_image(img_bytes)
                    if ocr_ok and len(ocr_text) > len(text):
                        text = ocr_text
                        is_ocr = True
                        ocr_pages_count += 1
                else:
                    if len(text) == 0:
                        warnings.append(
                            f"Page {page_num} appears to be a scanned image, but Tesseract OCR is not installed."
                        )

            if not text:
                continue

            page_chunks = split_text_into_chunks(text, chunk_size, chunk_overlap)
            for c_idx, chunk_text in enumerate(page_chunks):
                # Deterministic chunk ID hash
                h = hashlib.sha256(f"{name}_{page_num}_{c_idx}_{chunk_text[:30]}".encode()).hexdigest()[:12]
                chunk_id = f"{name}_p{page_num}_c{c_idx}_{h}"
                
                chunk_obj = DocumentChunk(
                    chunk_id=chunk_id,
                    doc_name=name,
                    page_number=page_num,
                    chunk_index=c_idx,
                    content=chunk_text,
                    is_ocr=is_ocr,
                    metadata={
                        "source": name,
                        "page": page_num,
                        "chunk_index": c_idx,
                        "is_ocr": is_ocr,
                    }
                )
                chunks.append(chunk_obj)

    finally:
        doc.close()

    if has_complex_drawings:
        warnings.append(
            "Document contains complex technical schematics/drawings. Note that vector pinout diagrams and graphic tables may require manual visual inspection."
        )

    return IngestResult(
        doc_name=name,
        file_path=str(path),
        page_count=page_count,
        total_chunks=len(chunks),
        ocr_pages_count=ocr_pages_count,
        chunks=chunks,
        warnings=warnings,
        has_complex_tables_or_drawings=has_complex_drawings
    )
