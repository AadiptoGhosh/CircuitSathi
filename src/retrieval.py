"""
CircuitSathi Vector Retrieval Engine
Persistent local ChromaDB storage for datasheet embeddings, semantic search,
re-indexing, deduplication, and evidence thresholding.
"""

from pathlib import Path
from typing import Any
import logging
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings, CHROMA_DIR
from src.pdf_ingest import DocumentChunk
from src.embeddings import embed_texts, embed_query

logger = logging.getLogger(__name__)


class VectorStore:
    """Persistent local vector database interface using ChromaDB."""

    def __init__(self, persist_dir: Path | str | None = None):
        self.persist_dir = str(persist_dir or CHROMA_DIR)
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection_name = settings.chroma_collection_name
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_document_chunks(self, chunks: list[DocumentChunk], replace_existing: bool = True) -> int:
        """
        Store document chunks with local dense embeddings.
        If replace_existing is True, removes any prior chunks for this document first.
        """
        if not chunks:
            return 0

        doc_name = chunks[0].doc_name
        if replace_existing:
            self.delete_document(doc_name)

        ids = [c.chunk_id for c in chunks]
        texts = [c.content for c in chunks]
        metadatas = [
            {
                "source": c.doc_name,
                "page": c.page_number,
                "chunk_index": c.chunk_index,
                "is_ocr": c.is_ocr,
            }
            for c in chunks
        ]

        # Generate embeddings locally
        vectors = embed_texts(texts)

        # Batch upsert into Chroma
        batch_size = 64
        for i in range(0, len(ids), batch_size):
            self.collection.upsert(
                ids=ids[i:i + batch_size],
                documents=texts[i:i + batch_size],
                embeddings=vectors[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size]
            )

        return len(chunks)

    def query(
        self,
        query_text: str,
        top_k: int | None = None,
        score_threshold: float | None = None
    ) -> list[dict[str, Any]]:
        """
        Semantic vector retrieval for user engineering questions.
        Returns evidence-grounded chunks sorted by similarity score.
        """
        k = top_k or settings.top_k_retrieval
        thresh = score_threshold if score_threshold is not None else settings.score_threshold

        count = self.collection.count()
        if count == 0:
            return []

        # Avoid requesting more than existing items
        effective_k = min(k, count)
        query_vec = embed_query(query_text)

        results = self.collection.query(
            query_embeddings=[query_vec],
            n_results=effective_k,
            include=["documents", "metadatas", "distances"]
        )

        output: list[dict[str, Any]] = []
        if not results or not results.get("documents"):
            return output

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        ids = results["ids"][0]

        for chunk_id, doc, meta, dist in zip(ids, documents, metadatas, distances):
            # Cosine distance in Chroma: dist in [0, 2], similarity = 1 - dist
            similarity = max(0.0, 1.0 - float(dist))
            
            # Apply relevance threshold
            if similarity >= thresh:
                source_doc = meta.get("source", "Unknown Document")
                page_num = meta.get("page", 1)
                output.append({
                    "chunk_id": chunk_id,
                    "doc_name": source_doc,
                    "page_number": int(page_num),
                    "content": doc,
                    "score": round(similarity, 4),
                    "citation": f"[Doc: {source_doc}, Page: {page_num}]",
                    "is_ocr": bool(meta.get("is_ocr", False)),
                })

        return output

    def list_documents(self) -> list[dict[str, Any]]:
        """List distinct documents indexed in vector storage."""
        count = self.collection.count()
        if count == 0:
            return []

        data = self.collection.get(include=["metadatas"])
        metas = data.get("metadatas", [])
        
        doc_stats: dict[str, dict[str, Any]] = {}
        for m in metas:
            if not m:
                continue
            src = m.get("source", "Unknown")
            page = m.get("page", 1)
            if src not in doc_stats:
                doc_stats[src] = {"source": src, "chunks": 0, "pages": set()}
            doc_stats[src]["chunks"] += 1
            doc_stats[src]["pages"].add(page)

        summary = []
        for src, info in doc_stats.items():
            summary.append({
                "doc_name": src,
                "chunk_count": info["chunks"],
                "page_count": len(info["pages"]),
            })
        return summary

    def delete_document(self, doc_name: str) -> bool:
        """Delete all chunks belonging to a specific document."""
        try:
            self.collection.delete(where={"source": doc_name})
            return True
        except Exception as e:
            logger.warning(f"Error deleting document '{doc_name}': {e}")
            return False

    def clear_all(self) -> bool:
        """Clear the entire vector collection."""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            return True
        except Exception as e:
            logger.error(f"Error resetting vector collection: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """Return total chunks and indexed document count."""
        total_chunks = self.collection.count()
        docs = self.list_documents()
        return {
            "total_chunks": total_chunks,
            "document_count": len(docs),
            "documents": docs,
        }


def format_context_for_prompt(retrieved_passages: list[dict[str, Any]]) -> str:
    """Format retrieved chunks into a clean, cited string for LLM injection."""
    if not retrieved_passages:
        return "No relevant datasheet passages found."

    formatted = []
    for idx, p in enumerate(retrieved_passages, 1):
        formatted.append(
            f"--- PASSAGE {idx} {p['citation']} (Similarity: {p['score']:.2f}) ---\n"
            f"{p['content']}\n"
        )
    return "\n".join(formatted)


# Global singleton vector store instance
vector_store = VectorStore()
