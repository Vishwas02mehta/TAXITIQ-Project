# TAXITIQ Project Roadmap

## 1. COMPLETED
- Custom regex-based PDF parser and layout preservation.
- Deterministic section-level chunker (4,123 chunks).
- Hybrid search (vector + BM25) and RRF fusion retrieval.
- Cross-encoder reranking integration (`bge-reranker-v2-m3`).
- Local multi-LLM benchmark evaluation runner (`08_multi_llm_generator.py`).
- Automatic rescoring engine (`INDIALAWRAG_SCORING_V2`) resolving scoring bugs.
- McNemar test and paired bootstrap statistical suite.
- 50-test results integrity audit and scientific wording repair.

## 2. CURRENT
- Repository organization and preparation for open-source publication.
- Technical documentation, architectural specs, and user guides setup.

## 3. NEXT
- Incorporate external related work literature references.
- Conduct human legal-expert validation and preference studies on candidate answers.
- Implement structured schema outputs (e.g. JSON mode or Instructor) to enforce strict grounding format layout.

## 4. LONG-TERM
- Expand evaluation benchmark to other tax Acts and case law databases.
- Compare local open-weights generators with cloud-hosted proprietary LLMs (e.g. GPT-4o or Claude 3.5 Sonnet).
