"""
CircuitSathi Configuration Module
Centralized, validated configuration for local-first electronics engineering assistant.
"""

from pathlib import Path
from pydantic import BaseModel, Field

# Base Directory paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma"
SAMPLE_DOCS_DIR = DATA_DIR / "sample_docs"
ASSETS_DIR = BASE_DIR / "assets"

# Ensure directories exist
for directory in (DATA_DIR, UPLOADS_DIR, CHROMA_DIR, SAMPLE_DOCS_DIR, ASSETS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


class AppSettings(BaseModel):
    """Runtime application settings."""
    app_name: str = "CircuitSathi"
    tagline: str = "Your Local AI Engineering Companion"
    version: str = "0.1.0"

    # Ollama Settings
    ollama_base_url: str = "http://localhost:11434"
    default_model: str = "gemma3:4b"
    fallback_model: str = "gemma3:1b"
    active_model: str = "gemma3:4b"
    model_temperature: float = 0.2  # Low temperature for technical precision

    # Embedding & Vector Store Settings
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_collection_name: str = "circuitsathi_datasheets"
    top_k_retrieval: int = 4
    score_threshold: float = 0.20  # Threshold for considering evidence relevant

    # Chunking Configuration
    chunk_size: int = 600
    chunk_overlap: int = 120

    # Safety limits
    max_upload_size_mb: int = 50
    allowed_extensions: list[str] = Field(default_factory=lambda: [".pdf", ".png", ".jpg", ".jpeg"])


# Global singleton settings instance
settings = AppSettings()
