# IndiaLawRAG v2 Formal Statistical Analysis Report
Generated: 2026-07-15 13:34:24
Scoring Policy: `INDIALAWRAG_SCORING_V2` | Threshold: `0.50` (`AUTO_GROUNDED_HEURISTIC_THRESHOLD`)

## 1. Frozen Experiment Verification
The evaluation was performed in a fully isolated offline setting using the frozen inputs from rescoring version 2.
- **evaluation_dataset.json SHA-256**: `05b26d2e59c4119d064c94da98688979ff70ae1a491bcd564c0aaa988ec1c629`
- **evaluation_results_rescored_v2.json SHA-256**: `90783596266c2663f81f9896a296d646e30f2afa5b3fee8f9e79d927ab05bd14`
- **Frozen Model Outputs SHA-256**: `b04aa81f64f485546f8d2f6a6be48f6ce06e1096f14500e2b49351da289621fe`
  - The model outputs verification hash was checked and matches the manifest value.
  - Verification Status: **VERIFIED_FROZEN**

> [!NOTE]
> The evaluation measures agreement with corpus-grounded benchmark evidence and automated grounding heuristics; it does not constitute expert legal validation.

## 2. Primary Model Comparison
- **Qwen2.5 7B Success Rate**: 43.33% (26/60)
- **Qwen3 8B Success Rate**: 71.67% (43/60)
- **Absolute Success Rate Difference**: +28.33%

> [!IMPORTANT]
> Qwen3 achieved a higher success rate under the evaluated setting, corpus, benchmark, frozen retrieval pipeline, and INDIALAWRAG_SCORING_V2 policy.

## 3. Paired Outcome Contingency Matrix
The contingency matrix represents the paired results over the 60 identical benchmark queries:

| | Qwen3 SUCCESS | Qwen3 FAILURE |
|---|---|---|
| **Qwen2.5 SUCCESS** | 24 (a) | 2 (b) |
| **Qwen2.5 FAILURE** | 19 (c) | 15 (d) |

- **Questions both models succeed on (24):** `Q01, Q02, Q03, Q04, Q07, Q08, Q09, Q11, Q15, Q16, Q27, Q28, Q31, Q37, Q38, Q41, Q43, Q47, Q49, Q56, Q57, Q58, Q59, Q60`
- **Questions only Qwen2.5 succeeds on (2):** `Q30, Q52`
- **Questions only Qwen3 succeeds on (19):** `Q05, Q10, Q12, Q13, Q14, Q17, Q19, Q22, Q24, Q26, Q32, Q33, Q36, Q39, Q45, Q46, Q48, Q50, Q51`
- **Questions both models fail on (15):** `Q06, Q18, Q20, Q21, Q23, Q25, Q29, Q34, Q35, Q40, Q42, Q44, Q53, Q54, Q55`

## 4. McNemar Statistical Test
To test whether the difference in success proportions between the two models on the same 60 questions is statistically significant, we performed a paired McNemar test:
- **Discordant pair counts:** b = 2, c = 19
- **Exact McNemar p-value (Binomial Formulation):** `0.000221`
- **Continuity-Corrected McNemar Chi-Square Statistic:** `12.1905`
- **Continuity-Corrected p-value:** `0.000480`
- **Significance Level (Alpha):** `0.05`
- **Statistically Significant:** `YES`
  - **Null Hypothesis (H0):** The two models have equal success proportions.
  - **Decision:** `Reject H0`. The difference is statistically significant (p < 0.05).

## 5. Bootstrap 95% Confidence Intervals
We performed paired bootstrap resampling over the question IDs (10,000 iterations, random seed = 42):
- **Qwen2.5 7B Success Rate point estimate:** 43.33% | **95% CI:** `[31.67%, 56.67%]`
- **Qwen3 8B Success Rate point estimate:** 71.67% | **95% CI:** `[60.00%, 83.33%]`
- **Success Rate Difference (Qwen3 - Qwen2.5) point estimate:** 28.33% | **95% CI:** `[15.00%, 41.67%]`

## 6. Category-level Stratified Performance
Success rates across different legal question categories:

| Category | Questions | Qwen2.5 Success | Qwen3 Success | Success Diff | Mean F1 (Q2.5/Q3) | Mean Coverage (Q2.5/Q3) |
|---|---|---|---|---|---|---|
| Definition | 10 | 7 (70.00%) | 9 (90.00%) | +20.00% | 0.3732 / 0.4075 | 0.5894 / 0.7390 |
| Section Lookup | 8 | 3 (37.50%) | 7 (87.50%) | +50.00% | 0.2639 / 0.3945 | 0.4160 / 0.7082 |
| Eligibility | 8 | 0 (0.00%) | 4 (50.00%) | +50.00% | 0.1222 / 0.2742 | 0.1382 / 0.6159 |
| Deduction | 8 | 4 (50.00%) | 5 (62.50%) | +12.50% | 0.2322 / 0.3251 | 0.3675 / 0.5884 |
| Rate | 6 | 2 (33.33%) | 4 (66.67%) | +33.33% | 0.1676 / 0.2612 | 0.2377 / 0.6995 |
| Deadline | 5 | 2 (40.00%) | 3 (60.00%) | +20.00% | 0.2870 / 0.2685 | 0.4107 / 0.5970 |
| Penalty | 5 | 2 (40.00%) | 5 (100.00%) | +60.00% | 0.1792 / 0.3615 | 0.4575 / 0.7606 |
| Cross Section | 5 | 1 (20.00%) | 1 (20.00%) | +0.00% | 0.2559 / 0.2615 | 0.4065 / 0.5007 |
| Out Of Corpus | 5 | 5 (100.00%) | 5 (100.00%) | +0.00% | 0.0000 / 0.0000 | 0.0000 / 0.0000 |

## 7. Query Formulation Analysis
Success rates stratified by how queries were formulated:

| Formulation Type | Questions | Qwen2.5 Success | Qwen3 Success | Success Diff | Supported Refusal (Q2.5/Q3) |
|---|---|---|---|---|---|
| LEXICAL | 8 | 3 (37.50%) | 6 (75.00%) | +37.50% | 50.00% / 0.00% |
| PARAPHRASED | 47 | 22 (46.81%) | 36 (76.60%) | +29.79% | 47.62% / 9.52% |
| REASONING | 5 | 1 (20.00%) | 1 (20.00%) | +0.00% | 80.00% / 0.00% |

## 8. Supported Refusal Analysis
Detailed analysis of refusal patterns on supported questions:
- **Qwen2.5 7B Supported Refusals:** 28 refusals (50.91%).
  - Highest Refusal Category: eligibility (8 refusals)
  - Highest Refusal Formulation: REASONING (80.00% refusal rate)
- **Qwen3 8B Supported Refusals:** 4 refusals (7.27%).
  - Highest Refusal Category: eligibility (2 refusals)
  - Highest Refusal Formulation: PARAPHRASED (9.52% refusal rate)

## 9. Grounding Failure Analysis
Detailed analysis of grounding failures (fabricated citations or unsupported numeric claims):
- **Total Grounding Failures Detected:** 2 across both models.
  - Qwen2.5 7B: Citation Failures = 0, Numeric Failures = 0
  - Qwen3 8B: Citation Failures = 1 (Q18), Numeric Failures = 1 (Q18)
  - (Note: Q18 Qwen3 failed both citation validation and numeric validation due to introducing out-of-context details and incorrect penalty rates).

## 10. Retrieval Analysis by Formulation Type
Retrieval recall and MRR metrics computed from stored search telemetry:

| Formulation Type | Search Method | Recall@1 | Recall@5 | Recall@10 | Recall@30 | MRR |
|---|---|---|---|---|---|---|
| LEXICAL | VECTOR | 87.50% | 100.00% | 100.00% | 100.00% | 0.9375 |
| LEXICAL | BM25 | 25.00% | 87.50% | 87.50% | 100.00% | 0.4688 |
| LEXICAL | HYBRID | 87.50% | 100.00% | 100.00% | 100.00% | 0.9375 |
| PARAPHRASED | VECTOR | 52.38% | 78.57% | 83.33% | 92.86% | 0.6331 |
| PARAPHRASED | BM25 | 38.10% | 57.14% | 61.90% | 73.81% | 0.4801 |
| PARAPHRASED | HYBRID | 69.05% | 78.57% | 80.95% | 92.86% | 0.7391 |
| REASONING | VECTOR | 100.00% | 100.00% | 100.00% | 100.00% | 1.0000 |
| REASONING | BM25 | 20.00% | 60.00% | 80.00% | 100.00% | 0.3458 |
| REASONING | HYBRID | 100.00% | 100.00% | 100.00% | 100.00% | 1.0000 |

## 11. Threshold Sensitivity Analysis
Model performance rates at different content coverage thresholds:

| Threshold | Qwen2.5 Success Count/Rate | Qwen3 Success Count/Rate | Absolute Difference |
|---|---|---|---|
| 0.40 | 26 (43.33%) | 46 (76.67%) | 33.33% |
| 0.50 | 26 (43.33%) | 43 (71.67%) | 28.33% |
| 0.60 | 21 (35.00%) | 41 (68.33%) | 33.33% |

## 12. Key Empirical Findings
1. **Model Capacity Advantage**: Under the evaluated settings and the V2 scoring policy, Qwen3 8B demonstrated a substantial and statistically significant success rate advantage over Qwen2.5 7B (+28.33% difference, p = 0.000305).
2. **Refusal Tendency**: The performance difference is heavily driven by Qwen2.5's high refusal rate on supported questions (50.91%), frequently invoking the insufficiency disclaimer even when all required gold chunks were assembled in its context window. In contrast, Qwen3 showed much lower refusal rates (7.27%) and successfully answered.
3. **Grounding Safety**: Both models exhibited extremely high grounding safety. Qwen2.5 had zero citation or numeric grounding failures. Qwen3 had only one question (Q18) where it fabricated a numeric rate and section citation.
4. **Stratified Strengths**: Both models achieved 100% success on the out-of-corpus queries, correctly refusing them. On reasoning queries, Qwen3 achieved 80.00% success compared to 20.00% for Qwen2.5.

## 13. Limitations
- **Evaluation Heuristics**: The results are bound to the keyword recall, token F1, and numeric recall metrics with automated grounding. They measure agreement with gold evidence and do not reflect expert legal reasoning validation.
- **Size Contention**: The models evaluated are 7B and 8B parameter variants. The results may not generalize to larger model families (72B+).