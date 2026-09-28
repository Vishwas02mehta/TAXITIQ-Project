# TAXITIQ Repository Migration Plan

To preserve the reproducibility of the frozen legal RAG pipeline, **all production pipeline scripts and helper utility modules are preserved at the repository root**.

Relocating production python files (e.g. `01_parse_pdf.py` through `13_generate_paper_artifacts.py` or helper utilities like `search_utils.py`) would introduce risk to relative imports and runtime path resolution.

## Proposed Moves:

| Old Path | Proposed New Path | Risk | Recommendation |
| --- | --- | --- | --- |
| `paper_*.md` | `paper/drafts/paper_*.md` | Low | Move repaired drafts to `paper/drafts` subdirectory |
| `paper_table_*.csv` | `paper/tables/paper_table_*.csv` | Low | Move paper CSV tables to `paper/tables` |
| `*.png` | `paper/figures/*.png` | Low | Move evaluation charts to `paper/figures` |
| `chroma_db/` | `chroma_db/` | Low | Retain in root and gitignore |
| `logs/` | `logs/` | Low | Retain in root and gitignore |
