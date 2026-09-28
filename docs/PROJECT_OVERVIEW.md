# TAXITIQ Project Overview

TAXITIQ is a fully local, corpus-grounded Retrieval-Augmented Generation (RAG) system developed for questioning and reasoning over the **Income-tax Act, 2025** of India. 

The system leverages state-of-the-art local embedding models, dense vector indexing, BM25 keyword matching, hybrid reciprocal rank fusion, sequence classification rerankers, and local Large Language Models (LLMs) running via Ollama. 

## Benchmark & Review Status
- **Benchmark Status**: `CORPUS_GROUNDED`
- **Review Status**: `AUTO_GROUNDED`

*Note: TAXITIQ is a research prototype. It does not provide professional legal advice, nor has it undergone validation by legal experts or human practitioners.*

## The Core Concept
Traditional search engines look for words, but they do not understand the underlying context or meaning of legal questions. On the other hand, raw Large Language Models (LLMs) can answer questions fluently, but they are prone to "hallucinations" (generating plausible-sounding but completely fabricated facts) and cannot cite specific statutory provisions.

TAXITIQ solves this by combining the two approaches using a **Retrieval-Augmented Generation (RAG)** pipeline:
1. **Retrieve**: When a user asks a question, the system searches the Income-tax Act, 2025, and retrieves the most relevant statutory chunks.
2. **Rerank**: It uses a local reranker model to sort and select the most precise evidence chunks.
3. **Assemble**: It builds a structured context window containing the retrieved evidence.
4. **Generate**: It passes the question along with the evidence to a local LLM, which generates a grounded response containing precise section citations.
