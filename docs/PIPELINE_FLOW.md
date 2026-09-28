# TAXITIQ Pipeline Flow

This document outlines the sequential execution flow of the 13 canonical project scripts.

---

### `01_parse_pdf.py`
- **Input**: `data/Income_Tax_Act_2025_as_amended_by_FA_Act_2026.pdf`
- **Process**: Reads layout page-by-page, extracts raw text, detects chapter/section headers via regex.
- **Output**: `parsed_output.json`
- **Why**: Converts binary PDF document layout into structural JSON representation.
- **Next Script**: `02_chunker.py`

---

### `02_chunker.py`
- **Input**: `parsed_output.json`
- **Process**: Splits statutory text into section-level and sub-section level chunks (4,123 chunks total).
- **Output**: `chunks.json`
- **Why**: Generates the granular document units necessary for high-precision context retrieval.
- **Next Script**: `03_ingest.py`

---

### `03_ingest.py`
- **Input**: `chunks.json`
- **Process**: Generates dense semantic vectors using local `bge-large-en-v1.5` embeddings, validates metadata, and indexes them in a persistent ChromaDB database.
- **Output**: Persistent collection directories inside `chroma_db/`.
- **Why**: Prepares the vector database for local semantic search.
- **Next Script**: `04_search.py`

---

### `04_search.py`
- **Input**: `evaluation_dataset.json` (or user search queries)
- **Process**: Runs RRF hybrid search (BM25 + ChromaDB vector retrieval) at a depth of 30 candidate chunks.
- **Output**: `search_results.json`
- **Why**: Fetches candidate evidence documents.
- **Next Script**: `05_reranker.py`

---

### `05_reranker.py`
- **Input**: `search_results.json`
- **Process**: Reranks the top 30 candidates using `bge-reranker-v2-m3` cross-encoder.
- **Output**: `reranked_results.json`
- **Why**: Re-sorts retrieved documents, bringing the most relevant chunks to the very top.
- **Next Script**: `06_context_builder.py`

---

### `06_context_builder.py`
- **Input**: `reranked_results.json`
- **Process**: Assembles prompt contexts using the top 8 reranked chunks.
- **Output**: `assembled_context.json`
- **Why**: Builds structured evidence context windows.
- **Next Script**: `07_answer_engine.py`

---

### `07_answer_engine.py`
- **Input**: User queries + `assembled_context.json`
- **Process**: Combines context with prompt instructions, runs generation via local Ollama models.
- **Output**: Grounded answer text with precise section citations.
- **Why**: Serves as the primary answer generator of the RAG pipeline.
- **Next Script**: `08_multi_llm_generator.py`

---

### `08_multi_llm_generator.py`
- **Input**: `assembled_context.json` + `evaluation_dataset.json`
- **Process**: Runs batch inference on Qwen2.5 7B and Qwen3 8B.
- **Output**: `evaluation_results.json`
- **Why**: Conducts the controlled experimental run on the evaluation benchmark.
- **Next Script**: `09_build_evaluation_dataset.py` (Wait, evaluation dataset builder was historically run to construct/verify the benchmark dataset `evaluation_dataset.json`).

---

### `09_build_evaluation_dataset.py`
- **Input**: Raw benchmark specifications and candidate questions.
- **Process**: Compiles, validates, and hashes the benchmark questions.
- **Output**: Canonical benchmark `evaluation_dataset.json` (60 questions).
- **Why**: Establishes the frozen evaluation dataset.
- **Next Script**: `10_evaluate_rag.py`

---

### `10_evaluate_rag.py`
- **Input**: `evaluation_dataset.json` + `evaluation_results.json`
- **Process**: Runs the scoring framework (`INDIALAWRAG_SCORING_V2`), evaluating responses for coverage and hard failures.
- **Output**: `evaluation_results_rescored_v2.json`, `evaluation_summary_rescored_v2.json`
- **Why**: Executes the offline evaluation rescoring engine.
- **Next Script**: `11_statistical_analysis.py`

---

### `11_statistical_analysis.py`
- **Input**: Rescored results files.
- **Process**: Recomputes exact McNemar p-value, Chi-Square, and runs 10,000 paired bootstrap iterations.
- **Output**: `statistical_analysis_manifest.json`, paper CSV tables, and PNG charts.
- **Why**: Performs statistical analysis on the experimental run.
- **Next Script**: `12_results_integrity_audit.py`

---

### `12_results_integrity_audit.py`
- **Input**: Markdown reports, PNG charts, and CSV tables.
- **Process**: Executes 35 self-tests verifying that tables and figures correspond to results.
- **Output**: `results_integrity_audit.json`
- **Why**: Performs results integrity audit.
- **Next Script**: `13_generate_paper_artifacts.py`

---

### `13_generate_paper_artifacts.py`
- **Input**: Audit outcomes and numbers/claims registries.
- **Process**: Validates lexical claim limits and renders 12 Markdown paper drafts.
- **Output**: Generated publication draft drafts and registries.
- **Why**: Compiles final research outputs.
