# Paper Methodology

## Corpus Preparation and Chunking
The evaluation corpus is constructed from the statutory text of the Income-tax Act 2025. The raw text was parsed and divided into 4,123 deterministic chunks. Each chunk is assigned a unique, immutable SHA-256 identifier based on the chunk text, index, section number, chapter, and subsection metadata. 

## Storage and Embeddings
All chunks are indexed in a persistent ChromaDB collection. Semantic embeddings were generated using the `BAAI/bge-large-en-v1.5` model. Keyword retrieval was configured using a BM25 index built directly on the chunk text.

## Hybrid Retrieval
To maximize retrieval recall, we implemented a Reciprocal Rank Fusion (RRF) hybrid search engine that queries the ChromaDB vector database and the BM25 index. The results are merged using standard RRF rank aggregation, retrieving a depth of 30 candidate chunks.

## Reranking and Context Assembly
The top 30 candidate chunks are reranked using the `BAAI/bge-reranker-v2-m3` model. The context assembler constructs the prompt's context window using the top 8 reranked chunks. This configuration achieved a reranker recall@8 (ANY and ALL) of 92.73% and a context gold recall of 92.73% for supported questions, ensuring that required evidence was present inside the prompt context before inference.

## Benchmark Design
The IndiaLawRAG v2 benchmark consists of 60 corpus-grounded questions. The queries are stratified into 55 SUPPORTED questions (where gold evidence is present in the corpus) and 5 NOT_SUPPORTED questions (which represent out-of-corpus queries). Query formulations are distributed across three distinct structural types:
- **LEXICAL** (8 queries): Direct match queries using exact statutory terms.
- **PARAPHRASED** (47 queries): Conceptually identical queries formulated using alternative phrasing.
- **REASONING** (5 queries): Complex queries requiring cross-section synthesis or mathematical calculations.

## Scoring Policy (Scoring V2)
We evaluate generator responses using the `INDIALAWRAG_SCORING_V2` offline scoring policy. The policy computes a versioned content coverage score based on token-level F1 score, keyword recall, and numeric claim recall. A success is declared if:
1. The question is NOT_SUPPORTED and the model correctly refuses (refusal rate = 100%).
2. The question is SUPPORTED and the content coverage score meets or exceeds a primary threshold of 0.50, and the response is free of hard failures (empty answers, supported-question refusals, fabricated citations, or unsupported numeric claims).
