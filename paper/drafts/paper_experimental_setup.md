# Paper Experimental Setup

## Frozen Components
We execute the empirical study inside a frozen pipeline environment to isolate generator variance. The following configurations are held completely constant:
- **Retrieval Engine**: ChromaDB persistent collection containing 4,123 chunks. Embedding model `bge-large-en-v1.5`.
- **Reranker Model**: `BAAI/bge-reranker-v2-m3`.
- **Context Builder**: Fixed context window of top 8 reranked chunks.
- **System Prompt**: Identical prompt template requesting statutory grounding and prohibiting hallucinations.

## Generator Models
We evaluate two local open-weights generators deployed locally via Ollama:
1. **Qwen2.5 7B Instruct** (`qwen2.5:7b-instruct`)
2. **Qwen3 8B** (`qwen3:8b`)

## Hyperparameters and Inference
The models were run under deterministic generation configurations:
- Temperature = 0.0
- Top-p = 0.9
- Max token output = 512
- Seed = 42

All model outputs are stored as frozen JSON objects in `evaluation_results_rescored_v2.json`.
