# TAXITIQ Git Final Sanity Report

**Final Status**: `READY_TO_COMMIT_AND_PUSH`

## 1. Path Sanity Scan Findings
| File | Line | Content | Status |
| --- | --- | --- | --- |
| `11_statistical_analysis.py` | 23 | `ARTIFACT_DIR = r"C:\Users\Mukul Ghai\AppData\Roaming\antigravity-ide\brain\fe5e9763-c290-4e74-9264-2ac6e58e4fa9"` | Leak |
| `11_statistical_analysis.py` | 25 | `ARTIFACT_DIR = r"C:\Users\Mukul Ghai\.gemini\antigravity-ide\brain\fe5e9763-c290-4e74-9264-2ac6e58e4fa9"` | Leak |
| `14_run_sanity_checks.py` | 6 | `WORKSPACE = r"c:\Users\Mukul Ghai\Desktop\tax"` | Leak |
| `14_run_sanity_checks.py` | 6 | `WORKSPACE = r"c:\Users\Mukul Ghai\Desktop\tax"` | Leak |
| `14_run_sanity_checks.py` | 6 | `WORKSPACE = r"c:\Users\Mukul Ghai\Desktop\tax"` | Leak |
| `14_run_sanity_checks.py` | 28 | `scan_patterns = [r"C:\Users", r"C:/Users", r"Mukul Ghai\Desktop", r"Desktop\tax", r"Desktop/tax"]` | Leak |
| `14_run_sanity_checks.py` | 28 | `scan_patterns = [r"C:\Users", r"C:/Users", r"Mukul Ghai\Desktop", r"Desktop\tax", r"Desktop/tax"]` | Leak |
| `14_run_sanity_checks.py` | 28 | `scan_patterns = [r"C:\Users", r"C:/Users", r"Mukul Ghai\Desktop", r"Desktop\tax", r"Desktop/tax"]` | Leak |
| `14_run_sanity_checks.py` | 28 | `scan_patterns = [r"C:\Users", r"C:/Users", r"Mukul Ghai\Desktop", r"Desktop\tax", r"Desktop/tax"]` | Leak |
| `14_run_sanity_checks.py` | 28 | `scan_patterns = [r"C:\Users", r"C:/Users", r"Mukul Ghai\Desktop", r"Desktop\tax", r"Desktop/tax"]` | Leak |
## 2. Source PDF Distribution
- File exists: `True`
- PDF Size: `3299341 bytes`
- SHA-256 Checksum: `d54a0ed6a91673d1a4fbcef9b5e472c3efe441139fae38f85a5a0c5b2cfc998b`
- Git Ignored (Status): `True`
- Data README created: `True`

## 3. PyTorch / CUDA Documentation Accuracy
- CUDA Optionality Documented: `True`
- Ollama Separation Documented: `True`

## 4. Git Staging Dry Run
- Total staged files: `135`
- Staged size estimate: `11.26 MB`
- Ignored local state files staged: `0`

## 5. README Beginner Simulation Questions
| Question | Simulation Score |
| --- | --- |
| What is TAXITIQ? | **CLEAR** |
| What legal corpus does it use? | **CLEAR** |
| What does RAG mean? | **CLEAR** |
| Why are vector and BM25 search both used? | **CLEAR** |
| What does the reranker do? | **CLEAR** |
| Why are two Qwen models compared? | **CLEAR** |
| What is frozen in the experiment? | **CLEAR** |
| What is the main result? | **CLEAR** |
| What does 28.33 percentage points mean? | **CLEAR** |
| What is McNemar's test used for here? | **CLEAR** |
| What does CORPUS_GROUNDED mean? | **CLEAR** |
| What does AUTO_GROUNDED mean? | **CLEAR** |
| Is this legal advice? | **CLEAR** |
| What software must I install? | **CLEAR** |
| Where do I place the source PDF? | **CLEAR** |
| How do I build the chunks? | **CLEAR** |
| How do I ingest ChromaDB? | **CLEAR** |
| How do I validate the benchmark? | **CLEAR** |
| How do I run evaluation? | **CLEAR** |
| How do I reproduce paper analysis? | **CLEAR** |

## 6. Frozen Integrity Check
- Hash errors: `0`
- Integrity status: `PAPER_RESULTS_VERIFIED`
