"""
CircuitSathi 20-Question Retrieval & Citation Evaluation Benchmark
Evaluates semantic vector retrieval, citation accuracy, and evidence grounding against authentic datasheets.
"""

from pathlib import Path
import json
import pytest
from config import SAMPLE_DOCS_DIR, DATA_DIR
from src.pdf_ingest import process_pdf
from src.retrieval import VectorStore


@pytest.fixture(scope="module")
def populated_vector_store(tmp_path_factory):
    """Vector store populated with the two sample datasheets."""
    tmp_dir = tmp_path_factory.mktemp("eval_chroma")
    store = VectorStore(persist_dir=tmp_dir)

    for pdf_name in ["TB6612FNG_Datasheet.pdf", "LM7805_Datasheet.pdf"]:
        pdf_path = SAMPLE_DOCS_DIR / pdf_name
        ingest = process_pdf(pdf_path)
        store.add_document_chunks(ingest.chunks)

    return store


def test_run_20_question_evaluation_benchmark(populated_vector_store):
    """
    Run the 20-question datasheet benchmark.
    Tests:
    1. Retrieval hit rate (top-2 retrieval contains expected keywords)
    2. Citation accuracy (retrieved chunk page matches expected datasheet page)
    """
    bench_file = DATA_DIR / "evaluation_benchmark.json"
    assert bench_file.exists(), "Benchmark JSON file must exist"

    with open(bench_file, "r", encoding="utf-8") as f:
        benchmarks = json.load(f)

    assert len(benchmarks) >= 20, "Evaluation benchmark must contain at least 20 questions"

    retrieval_hits = 0
    citation_page_matches = 0
    evaluation_records = []

    for item in benchmarks:
        q_id = item["id"]
        q_text = item["question"]
        doc_name = item["doc_name"]
        expected_page = item["expected_page"]
        keywords = item["expected_answer_keywords"]

        # Retrieve top 4 (matches default top_k_retrieval setting)
        results = populated_vector_store.query(q_text, top_k=4, score_threshold=0.15)
        
        hit = False
        page_matched = False
        retrieved_citation = "None"
        retrieved_page = None

        if results:
            for r in results:
                if r["doc_name"] == doc_name:
                    if any(kw.lower() in r["content"].lower() for kw in keywords):
                        hit = True
                    if r["page_number"] == expected_page and not page_matched:
                        page_matched = True
                        retrieved_page = r["page_number"]
                        retrieved_citation = r["citation"]

            if not page_matched and results:
                retrieved_page = results[0]["page_number"]
                retrieved_citation = results[0]["citation"]

        if hit:
            retrieval_hits += 1
        if page_matched:
            citation_page_matches += 1

        evaluation_records.append({
            "id": q_id,
            "question": q_text,
            "expected_doc": doc_name,
            "expected_page": expected_page,
            "retrieved_page": retrieved_page,
            "retrieval_hit": hit,
            "citation_page_matched": page_matched,
            "citation": retrieved_citation,
        })

    hit_rate = (retrieval_hits / len(benchmarks)) * 100
    page_acc = (citation_page_matches / len(benchmarks)) * 100

    print(f"\n================ BENCHMARK EVALUATION RESULTS ================")
    print(f"Total Questions Evaluated: {len(benchmarks)}")
    print(f"Retrieval Hit Rate:        {hit_rate:.1f}% ({retrieval_hits}/{len(benchmarks)})")
    print(f"Exact Page Citation Match: {page_acc:.1f}% ({citation_page_matches}/{len(benchmarks)})")
    print("==============================================================")

    # We require at least 85% retrieval accuracy on this benchmark
    assert hit_rate >= 85.0, f"Retrieval hit rate was {hit_rate:.1f}%, expected >= 85%"
    assert page_acc >= 75.0, f"Citation page match was {page_acc:.1f}%, expected >= 75%"
