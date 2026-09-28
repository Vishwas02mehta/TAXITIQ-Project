# TAXITIQ Git Pre-Push Report

This report summarizes the status of the repository files, Git tracking configuration, security scans, and integrity checks prior to repository initialization.

---

## 1. Tracking Summary
- **Files to be Tracked**: All python execution scripts (01-13), helper utilities, markdown documentation drafts, CSV tables, PNG charts, and PowerShell helper scripts.
- **Files Ignored**:
  - `__pycache__/`
  - `.gemini/`
  - `chroma_db/` (Local vector database files)
  - `logs/` (Local trace log files)
  - `venv/` (Local virtual environment)
  - `data/Income-tax-Rules-2026_*.pdf` (Large rules PDF)
- **Large Files Detected**:
  - `data/Income-tax-Rules-2026_2026-06-22_03-37-12_06bfa6_en.pdf` (72.09 MB - Ignored).
  - `data/Income_Tax_Act_2025_as_amended_by_FA_Act_2026.pdf` (3.30 MB - Tracked).

---

## 2. Security & Integrity Checks
- **Secret Scan Status**: **PASSED** (0 potential credentials, tokens, or local path usernames detected in tracked files).
- **Frozen Artifact Integrity**: **PASSED** (All 10 authoritative experiment baseline files match their expected SHA-256 hashes exactly).
- **Documentation Audit Status**: **VERIFIED** (All commands, model names, p-values, and hashes in the documentation exactly match the source files).
- **Repository Size Estimate**: ~4.5 MB (excluding ignored files).

---

## 3. Git Action Plan & First Commit
We will initialize the repository and make the first commit using the following message:

### Proposed Commit Message:
```text
feat: initialize TAXITIQ legal RAG research repository

- add local legal RAG pipeline
- add hybrid retrieval and reranking
- add controlled multi-LLM evaluation framework
- add corpus-grounded benchmark and scoring V2
- add statistical analysis and integrity audits
- add reproducibility artifacts and project documentation
```

> [!WARNING]
> We have paused execution before running any Git command (`git init`, `git add`, or `git push`).
