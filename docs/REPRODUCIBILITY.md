# TAXITIQ Reproducibility Guide

This guide registers the technical constants and cryptographic hashes to guarantee full reproducibility of the TAXITIQ v2 study.

## 1. Cryptographic Hashes

- **Frozen Dataset (`evaluation_dataset.json`)**:
  - SHA-256: `05b26d2e59c4119d064c94da98688979ff70ae1a491bcd564c0aaa988ec1c629`
- **Frozen Model Outputs (`evaluation_results_rescored_v2.json`)**:
  - SHA-256: `90783596266c2663f81f9896a296d646e30f2afa5b3fee8f9e79d927ab05bd14`
- **Frozen Model Output Texts**:
  - SHA-256: `b04aa81f64f485546f8d2f6a6be48f6ce06e1096f14500e2b49351da289621fe` (Computed from QID + model key + exact response text).

## 2. Experimental Parameters

- **Models**: `qwen2.5:7b-instruct` and `qwen3:8b` via local Ollama runtime.
- **Inference Config**: Temperature = 0.0, Top-p = 0.9, Seed = 42, Max Tokens = 512.
- **Embeddings Model**: `BAAI/bge-large-en-v1.5`
- **Reranker Model**: `BAAI/bge-reranker-v2-m3` (top 8 candidate chunks assembled).
- **Primary Database**: ChromaDB collection `it_act_2025` containing 4,123 chunks.
- **Scoring Policy**: `INDIALAWRAG_SCORING_V2` with content coverage threshold = 0.50.
- **Bootstrap Parameters**: seed = 42, iterations = 10,000.
