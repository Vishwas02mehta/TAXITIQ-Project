# TAXITIQ Architecture

This document details each technical component of the TAXITIQ pipeline and explains the rationale behind its selection.

## 1. Corpus Parsing & Chunking
- **Component**: `pdfplumber` & Custom Regex Chunker.
- **Why**: `pdfplumber` provides page-by-page text layout preservation. The chunker splits the text into section-level and sub-section level chunks.
- **Size**: Mapped to 4,123 deterministic chunks of India's Income-tax Act, 2025. Each chunk is assigned a unique SHA-256 identifier.

## 2. Embedding & Vector Database
- **Component**: `BAAI/bge-large-en-v1.5` embeddings stored in a persistent ChromaDB database.
- **Why**: `bge-large-en-v1.5` is a leading open-weights embedding model optimized for English semantic retrieval. ChromaDB is a lightweight, fully local vector database.

## 3. Keyword Search
- **Component**: BM25 (using `rank_bm25`).
- **Why**: Legal texts heavily rely on exact terms, codes, and section numbers. Vector search alone can miss exact numerical section matches. BM25 guarantees keyword-level retrieval accuracy.

## 4. Hybrid Fusion (RRF)
- **Component**: Reciprocal Rank Fusion (RRF).
- **Why**: Merges ranking lists from BM25 and vector search using standard reciprocal rank scores, pulling the top 30 candidate chunks.

## 5. Reranker
- **Component**: `BAAI/bge-reranker-v2-m3` cross-encoder.
- **Why**: Evaluates candidate chunks query-interactively. Cross-encoders provide significantly better precision than bi-encoders (embeddings) by computing joint queries/contexts representation.

## 6. Context Assembler
- **Component**: Custom token-aware buffer builder.
- **Why**: Automatically selects the top 8 reranked chunks, filters duplicate items, and truncates within token limits to avoid overflow.

## 7. Inference Engine
- **Component**: Local Ollama runtime.
- **Why**: Enables zero-cost, private, and deterministic generation of local open-weights models (`qwen2.5:7b-instruct` and `qwen3:8b`).
