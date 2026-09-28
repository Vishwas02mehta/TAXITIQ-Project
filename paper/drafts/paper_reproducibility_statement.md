# Paper Reproducibility Statement

To ensure reproducibility, we register the following technical metadata:

- **Frozen Results Hash**: `b04aa81f64f485546f8d2f6a6be48f6ce06e1096f14500e2b49351da289621fe`
- **Dataset Hash**: `05b26d2e59c4119d064c94da98688979ff70ae1a491bcd564c0aaa988ec1c629`
- **Models Evaluated**: `qwen2.5:7b-instruct`, `qwen3:8b` via local Ollama runtime.
- **Inference Configuration**: temperature = 0.0, top_p = 0.9, seed = 42, max_tokens = 512.
- **Embeddings Model**: `BAAI/bge-large-en-v1.5`
- **Reranker Model**: `BAAI/bge-reranker-v2-m3` (top 8 candidate chunks assembled).
- **Primary Collection**: `it_act_2025` containing 4,123 chunks.
- **Scoring Policy**: `INDIALAWRAG_SCORING_V2` with content coverage threshold = 0.50.
- **Paired Bootstrap Seed & Iterations**: seed = 42, iterations = 10,000.
- **Audit Verification Status**: `PAPER_RESULTS_VERIFIED` under offline results integrity audit.
