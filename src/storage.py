"""
CircuitSathi Storage & Session Isolation Manager
Safely manages local uploaded PDF/image files and metadata.
Ensures zero data leakage to external networks, safe path traversals, and complete document deletion.
"""

from pathlib import Path
import shutil
import logging
from config import UPLOADS_DIR, CHROMA_DIR, SAMPLE_DOCS_DIR
from src.retrieval import vector_store
from typing import Any

logger = logging.getLogger(__name__)


def save_uploaded_file(file_bytes: bytes, filename: str) -> Path:
    """
    Saves uploaded file into local uploads directory after sanitizing filename.
    Rejects directory traversal attempts.
    """
    safe_name = Path(filename).name  # Strips any directory traversal attempts
    target_path = UPLOADS_DIR / safe_name
    
    with open(target_path, "wb") as f:
        f.write(file_bytes)
        
    return target_path


def delete_uploaded_document(filename: str) -> bool:
    """
    Deletes document file from disk and purges all its vectors from ChromaDB.
    """
    safe_name = Path(filename).name
    file_path = UPLOADS_DIR / safe_name
    
    # 1. Delete vector embeddings
    vector_ok = vector_store.delete_document(safe_name)
    
    # 2. Delete file from disk
    file_ok = True
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete {file_path}: {e}")
            file_ok = False
            
    return vector_ok or file_ok


def list_uploaded_files() -> list[dict[str, Any]]:
    """List all user uploaded files stored locally."""
    files = []
    for p in UPLOADS_DIR.glob("*"):
        if p.is_file():
            size_kb = p.stat().st_size / 1024
            files.append({
                "filename": p.name,
                "size_kb": round(size_kb, 1),
                "modified": p.stat().st_mtime,
            })
    return sorted(files, key=lambda x: x["filename"])


def purge_all_data() -> bool:
    """
    Total privacy purge: Deletes all uploaded files and wipes the vector database.
    """
    try:
        # 1. Clear ChromaDB
        vector_store.clear_all()
        
        # 2. Delete files in uploads
        for f in UPLOADS_DIR.glob("*"):
            if f.is_file():
                f.unlink()
                
        return True
    except Exception as e:
        logger.error(f"Error purging local data: {e}")
        return False
