# TAXITIQ Getting Started Guide

This guide provides copy-paste Windows PowerShell commands to set up the environment, run the pipeline, and reproduce the evaluation.

## Hardware Notes & CUDA Requirements
- **CPU Execution**: TAXITIQ can run entirely on CPU. A compatible GPU may improve embedding, reranking, or local model performance, but GPU/CUDA is not required for the evaluated pipeline.
- **GPU Recommendation**: A GPU with $\ge 12$ GB VRAM is recommended for Qwen3 8B inference, along with 16 GB system RAM.
- **Dependency Separation**:
  - **PyTorch**: Used by the Python ML components (embedding and reranking), installed from `requirements.txt`.
  - **Ollama**: Manages the local Qwen LLM generators as a separate background service. It must be installed independently.

## 1. Prerequisites & Environment Setup

### Create a Python Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 2. Local LLM Runtime Setup (Ollama)

1. Download and install [Ollama for Windows](https://ollama.com/download/windows).
2. Start the Ollama application.
3. Download the evaluated generator models in PowerShell:
```powershell
ollama pull qwen2.5:7b-instruct
ollama pull qwen3:8b
```

---

## 3. Running the Pipeline (Step-by-Step)

### Step 1: Parse the PDF
```powershell
python 01_parse_pdf.py
```

### Step 2: Create Corpus Chunks
```powershell
python 02_chunker.py
```

### Step 3: Ingest into ChromaDB
```powershell
python 03_ingest.py
```

### Step 4: Run Hybrid Search & Retrieval
```powershell
python 04_search.py
```

### Step 5: Execute Reranking
```powershell
python 05_reranker.py
```

### Step 6: Assemble Prompt Context
```powershell
python 06_context_builder.py
```

### Step 7: Query the Answer Engine
```powershell
python 07_answer_engine.py
```
