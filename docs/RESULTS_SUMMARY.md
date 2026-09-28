# TAXITIQ Experimental Results Summary

This document registers the frozen, authoritative evaluation results of the IndiaLawRAG v2 study.

## 1. Overall Model Efficacy

- **Qwen2.5 7B Instruct**:
  - Success Rate: **43.33%** (26/60 questions successfully answered)
  - 95% Confidence Interval: **31.67% to 56.67%**
- **Qwen3 8B**:
  - Success Rate: **71.67%** (43/60 questions successfully answered)
  - 95% Confidence Interval: **60.00% to 83.33%**
- **Absolute Difference**: **28.33 percentage points** (Qwen3 - Qwen2.5)
  - 95% Confidence Interval: **15.00 to 41.67 percentage points**

## 2. Paired Outcome Matrix

The joint success outcomes across the same 60 questions are:

| | Qwen3 SUCCESS | Qwen3 FAILURE |
|---|---|---|
| **Qwen2.5 SUCCESS** | 24 | 2 |
| **Qwen2.5 FAILURE** | 19 | 15 |

- **Both Success ($a$)**: 24 questions
- **Only Qwen2.5 Success ($b$)**: 2 questions (`Q30`, `Q52`)
- **Only Qwen3 Success ($c$)**: 19 questions
- **Both Failure ($d$)**: 15 questions

## 3. McNemar Statistical Significance
- **Exact two-sided binomial p-value**: **0.000221**
- **Continuity-corrected Chi-Square**: **12.1905**
- **Continuity-corrected p-value**: **0.000480**
- **Significance Status**: The performance difference is statistically significant.

## 4. Supported Refusal Rates
- **Qwen2.5 7B Instruct**: Refused **50.91%** (28/55 supported questions) despite context being present.
- **Qwen3 8B**: Refused **7.27%** (4/55 supported questions) under identical context.

## 5. Grounding Reliability (Supported Questions)
- **Qwen2.5 7B**: Citation failures = 0 | Numeric failures = 0
- **Qwen3 8B**: Citation failures = 1 | Numeric failures = 1 (both failures occurred in question Q18).
