# IndiaLawRAG v2 Paper Results Integrity Audit Report
**Audit Status**: `PAPER_RESULTS_VERIFIED`

## Inconsistency Analysis & Resolutions

### ISSUE 1: Category Distribution Mismatch
- **Root Cause**: `E. stale artifact`
- **Detail**: The category mismatch originates from a stale artifact (historical version of files or previous benchmark iteration). The current generated paper_table_category_analysis.csv in the workspace contains the correct category counts matching the dataset (Definition: 10, Section Lookup: 8, Eligibility: 8, Deduction: 8, Rate: 6, Deadline: 5, Penalty: 5, Cross Section: 5, Out Of Corpus: 5).
- **Mismatched Question IDs**: None (All Q01-Q60 questions are fully consistent in current files).

### ISSUE 2: Paired Outcome Q52/Q55 Conflict
- **Root Cause**: Manual list indexing typo in walkthrough.md report.
- **Resolution**: Q52 belongs to `ONLY_QWEN2.5_SUCCESS` (b) and Q55 belongs to `BOTH_FAILURE` (d). All counts and matrix alignments are correct in python statistical outputs.
- **Authoritative Groups**: BOTH_SUCCESS=24, ONLY_QWEN2.5_SUCCESS=2, ONLY_QWEN3_SUCCESS=19, BOTH_FAILURE=15.

## Self-Test Execution Summary
- **Total Tests**: 35
- **Passed**: 35
- **Failed**: 0
