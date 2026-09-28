# IndiaLawRAG v2 Evaluation Report (Scoring V2)
Generated: 2026-07-15 13:24:18
Scoring Policy: `INDIALAWRAG_SCORING_V2` | Threshold: `0.50` (`AUTO_GROUNDED_HEURISTIC_THRESHOLD`)

## Executive Summary
- **Total Questions Evaluated**: 60
- **Ollama Models**: Qwen2.5 7B Instruct (`qwen2.5:7b-instruct`), Qwen3 8B (`qwen3:8b`)
- **Grounded Output verification**: 100% outputs rescored offline.

## Retrieval Component Performance
| Component | Recall@1 | Recall@5 | Recall@10 | Recall@30 | MRR |
|---|---|---|---|---|---|
| VECTOR | 61.82% | 83.64% | 87.27% | 94.55% | 0.7107 |
| BM25 | 34.55% | 61.82% | 67.27% | 80.00% | 0.4663 |
| HYBRID | 74.55% | 83.64% | 85.45% | 94.55% | 0.7917 |


## Reranker & Context Assembly Performance
- **Reranker Recall@8 (ANY)**: 92.73%
- **Reranker Recall@8 (ALL)**: 92.73%
- **Mean Rank Delta**: 2.15
- **Median Rank Delta**: 0.00
- **Gold chunks pushed up**: 15
- **Gold chunks unchanged**: 37
- **Gold chunks pushed down**: 8
- **Gold chunks dropped outside Top 8**: 1
- **Context ANY Gold Recall**: 92.73%
- **Context ALL Gold Recall**: 92.73%

## Model Generation Quality Metrics (Scoring V2)
| Model | Token F1 | Keyword Recall | Numeric Recall | Cit. Precision | Cit. Validity | Refusal Rate (Supported) | OOC Refusal Rate | Success Count / Rate |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5 7B | 24.17% | 39.55% | 51.28% | 100.00% | 94.55% | 58.18% | 100.00% | 26/60 (43.33%) |
| Qwen3 8B | 32.82% | 68.85% | 87.61% | 98.78% | 85.45% | 12.73% | 100.00% | 43/60 (71.67%) |


## Failure Stage Attribution (Scoring V2)
| Model | SUCCESS | CORPUS_EVIDENCE_INVALID | RETRIEVAL_FAILURE | RERANKER_FAILURE | CONTEXT_ASSEMBLY_FAILURE | GENERATOR_FAILURE |
|---|---|---|---|---|---|---|
| Qwen2.5 7B | 21 | 0 | 3 | 1 | 0 | 30 |
| Qwen3 8B | 38 | 0 | 3 | 1 | 0 | 13 |


## Detailed Generator Failure Breakdown
| Model | EMPTY_RESPONSE | SUPPORTED_REFUSAL | CITATION_FAILURE | NUMERIC_FAILURE | COVERAGE_BELOW_THRESHOLD |
|---|---|---|---|---|---|
| Qwen2.5 7B | 0 | 28 | 0 | 0 | 2 |
| Qwen3 8B | 4 | 4 | 1 | 1 | 3 |


## Threshold Sensitivity Analysis
| Threshold | Qwen2.5 Success Rate | Qwen3 Success Rate |
|---|---|---|
| 0.40 | 43.33% (26/60) | 76.67% (46/60) |
| 0.50 | 43.33% (26/60) | 71.67% (43/60) |
| 0.60 | 35.00% (21/60) | 68.33% (41/60) |


## Multi-Evidence Reasoning Questions (Q51-Q55)
### `Q51`: Compare the tax consequences under Section 11(2) and Section 12(2) when the conditions for income exclusions are not satisfied by a person versus a political party or electoral trust.
- **Required Gold Chunks**: `185ba1800d312e61cf35409db3cf99da, c06b6aa209d396b1fa69d98480b39125`
- **Assembled Gold Chunks Present**: `2/2`
- **Qwen2.5 Failure Stage / Reasons**: `GENERATOR_FAILURE` / `['SUPPORTED_QUESTION_REFUSAL']`
- **Qwen3 Failure Stage / Reasons**: `SUCCESS` / `[]`
- **Qwen2.5 Answer excerpt**: *"The provided legal context is insufficient to answer this question reliably.

The context does not explicitly differentiate between the tax consequenc..."*
- **Qwen3 Answer excerpt**: *"Under Section 11(2), if the conditions for income exclusions (referenced in Schedules II–VII) are not satisfied by a **person**, such income is charge..."*

### `Q52`: How does Section 124(2) modify the contribution limit of 10% mentioned in Section 124(1) for assessees taxed under Section 202(1)?
- **Required Gold Chunks**: `718bde1193393d5173651b6890e4590f, b15b07c754f037c59090a81be0e2f52e`
- **Assembled Gold Chunks Present**: `2/2`
- **Qwen2.5 Failure Stage / Reasons**: `SUCCESS` / `[]`
- **Qwen3 Failure Stage / Reasons**: `GENERATOR_FAILURE` / `['CITATION_GROUNDING_FAILURE']`
- **Qwen2.5 Answer excerpt**: *"[Income-tax Act 2025, Section: 124, Subsection: 2] modifies the contribution limit of 10% mentioned in [Income-tax Act 2025, Section: 124, Subsection:..."*
- **Qwen3 Answer excerpt**: *"Section 124(2) modifies the 10% contribution limit in Section 124(1) by substituting "10%" with "14%" for assessees whose total income is chargeable t..."*

### `Q53`: Compare the daily penalties for a reporting entity's initial default under Section 459(1) versus a continuing default after order service under Section 459(3).
- **Required Gold Chunks**: `5254d9b66ab0b8289bbddc0f3a1cabba, b244bfd45103de33595cc5762f821c28`
- **Assembled Gold Chunks Present**: `2/2`
- **Qwen2.5 Failure Stage / Reasons**: `GENERATOR_FAILURE` / `['SUPPORTED_QUESTION_REFUSAL']`
- **Qwen3 Failure Stage / Reasons**: `GENERATOR_FAILURE` / `['CONTENT_COVERAGE_BELOW_THRESHOLD']`
- **Qwen2.5 Answer excerpt**: *"The provided legal context is insufficient to answer this question reliably.

The context does not explicitly differentiate between penalties for init..."*
- **Qwen3 Answer excerpt**: *"The daily penalties for a reporting entity's initial default under **Section 459(1)** and continuing default under **Section 459(3)** are as follows: ..."*

### `Q54`: Compare the deduction limit for employee pension contributions under Section 124(3) versus employer pension contribution under Section 124(1).
- **Required Gold Chunks**: `718bde1193393d5173651b6890e4590f, 7f842679efe1b9785762f70a6b6d86d1`
- **Assembled Gold Chunks Present**: `2/2`
- **Qwen2.5 Failure Stage / Reasons**: `GENERATOR_FAILURE` / `['SUPPORTED_QUESTION_REFUSAL']`
- **Qwen3 Failure Stage / Reasons**: `GENERATOR_FAILURE` / `['EMPTY_RESPONSE']`
- **Qwen2.5 Answer excerpt**: *"The deduction limit for employee pension contributions under [Act: Income-tax Act 2025, Section: 124, Subsection: 3] is `50,000.

For employer pension..."*
- **Qwen3 Answer excerpt**: *"..."*

### `Q55`: Explain standard daily penalties under Section 459(1) for reporting entity default and Section 459(2) for failing to produce records.
- **Required Gold Chunks**: `5254d9b66ab0b8289bbddc0f3a1cabba, 49233bb39dd96a6be9c11ab2b03cc944`
- **Assembled Gold Chunks Present**: `2/2`
- **Qwen2.5 Failure Stage / Reasons**: `GENERATOR_FAILURE` / `['SUPPORTED_QUESTION_REFUSAL']`
- **Qwen3 Failure Stage / Reasons**: `GENERATOR_FAILURE` / `['CONTENT_COVERAGE_BELOW_THRESHOLD']`
- **Qwen2.5 Answer excerpt**: *"The provided legal context is insufficient to answer this question reliably.

The context does not explicitly address penalties for reporting entity d..."*
- **Qwen3 Answer excerpt**: *"Under Section 459 of the Income-tax Act 2025:  

1. **Section 459(1)** applies to a reporting entity failing to furnish the required report under sect..."*
