# TAXITIQ Experiment History

This document details the chronological evolution and engineering history of the TAXITIQ project.

## Chronological Project Stages

1. **PDF Parser & Chunker (`01_parse_pdf.py` & `02_chunker.py`)**: Mapped statutory PDFs to 4,123 chunks.
2. **ChromaDB Ingestion (`03_ingest.py`)**: Generated local dense embeddings using `bge-large-en-v1.5`.
3. **Retrieval, Reranking & Context Assembly (`04_search.py` - `06_context_builder.py`)**: Developed RRF hybrid search and cross-encoder reranking to ensure correct evidence was present in context windows.
4. **Local Generation & Multi-LLM Execution (`07_answer_engine.py` & `08_multi_llm_generator.py`)**: Ran inference on 60 benchmark questions comparing Qwen2.5 7B and Qwen3 8B.
5. **Initial Evaluation & Bug Discovery**:
   During initial scoring, a bug was identified in question Q51 where a division-by-zero error occurred during keyword match counting, throwing off the evaluation metrics.
6. **Offline Rescoring (`INDIALAWRAG_SCORING_V2`)**:
   We updated the scoring logic to version 2 (`INDIALAWRAG_SCORING_V2`) to resolve the division-by-zero bug, calculate strict citation/numeric grounding failures, and rescored the **existing frozen model outputs** offline without repeating LLM inference.
7. **Statistical Analysis (`11_statistical_analysis.py`)**:
   Conducted McNemar paired test and a 10,000-iteration paired bootstrap to determine the significance of Qwen3's performance gain.
8. **Integrity Audits & Artifact Generation (`12_results_integrity_audit.py` & `13_generate_paper_artifacts.py`)**:
   Built verification scripts to run self-tests on results and generated publication drafts, followed by a scientific wording repair pass to correct terminology ("percentage points") and remove unsupported causal mechanism claims.
