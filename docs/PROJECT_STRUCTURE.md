# TAXITIQ Project Structure

This document outlines the top-level repository directories.

```text
TAXITIQ/
├── docs/                 # Detailed architectural and pipeline guides
├── data/                 # Raw legal PDFs (Income-Tax Act 2025)
├── scripts/              # PowerShell automation wrappers for executing Python files
├── manifests/            # Frozen experimental manifests and integrity parameters
├── paper/                # Generated research paper artifacts
│   ├── drafts/           # Markdown drafts of paper sections
│   ├── tables/           # CSV statistical tables used in paper
│   └── figures/          # PNG evaluation charts and plots
├── chroma_db/            # ChromaDB local vector database (gitignored)
└── logs/                 # Pipeline execution run logs (gitignored)
```

---

## Top-Level Directories

- **`docs/`**: Holds markdown technical documents describing overview, architecture, and reproducibility parameters.
- **`data/`**: Directory containing legal document sources. Heavy PDF rulebooks are gitignored.
- **`scripts/`**: Convenience PowerShell commands designed to wrap Python execution scripts and return correct exit status.
- **`manifests/`**: Manifest files holding checksum parameters to verify consistency during reproduction runs.
- **`paper/`**: All paper writing draft elements, formatted CSV tables, and visual chart plots.
- **`chroma_db/`**: Machine-specific directory holding the populated vector database collection. This is excluded from Git tracking.
- **`logs/`**: Holds log outputs from ingestion, reranking, and generation stages. Excluded from Git tracking.
