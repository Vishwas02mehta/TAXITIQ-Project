# Paper Results

## Primary Success Rates
Under the `INDIALAWRAG_SCORING_V2` policy at a primary threshold of 0.50:
- **Qwen2.5 7B Instruct** achieved a success rate of **43.33%** (26/60 questions).
- **Qwen3 8B** achieved a success rate of **71.67%** (43/60 questions).
- **Absolute Difference**: **28.33 percentage points** (absolute success rate change).

## Paired Outcome Matrix
The joint outcomes for the same 60 questions evaluated on both models are:

| | Qwen3 SUCCESS | Qwen3 FAILURE |
|---|---|---|
| **Qwen2.5 SUCCESS** | 24 | 2 |
| **Qwen2.5 FAILURE** | 19 | 15 |

- Both models succeed on 24 questions.
- Only Qwen2.5 succeeds on 2 questions (`Q30`, `Q52`).
- Only Qwen3 succeeds on 19 questions.
- Both models fail on 15 questions.

## McNemar Test Results
Using the discordant pair counts ($b = 2$ and $c = 19$):
- **Exact two-sided binomial p-value**: **0.000221**
- **Continuity-corrected Chi-Square**: **12.1905**
- **Continuity-corrected p-value**: **0.000480**
- **Significance Status**: Statistically significant at the $\alpha = 0.05$ level.

## Paired Bootstrap Confidence Intervals
Based on 10,000 bootstrap resamples (seed = 42):
- **Qwen2.5 7B success rate 95% CI**: **[31.67%, 56.67%]**
- **Qwen3 8B success rate 95% CI**: **[60.00%, 83.33%]**
- **Success rate difference (Qwen3 - Qwen2.5) 95% CI**: **15.00 to 41.67 percentage points**

## Supported Question Refusal Analysis
Supported-question refusals accounted for the largest category of generator failures:
- **Qwen2.5 7B** refused **50.91%** (28/55 questions) where evidence was present in context.
- **Qwen3 8B** refused **7.27%** (4/55 questions) under identical context constraints.

## Grounding Reliability Analysis
Under version 2 criteria:
- **Qwen2.5 7B** experienced **0** citation and **0** numeric grounding failures.
- **Qwen3 8B** experienced **1** citation and **1** numeric grounding failure.
- **Observed Contrast**: The single grounding failure occurred in Question `Q18` for Qwen3 8B, where the model fabricated a statutory citation (`Section 459(1)`) and hallucinated penalty values. Because this is the only detected grounding failure case for Qwen3, it represents a limited empirical observation from which a broad efficacy trade-off theory cannot be generalized.

## Retrieval Performance
The retrieval recalls over the 55 supported questions are:
- **Vector**: Recall@1 = 61.82%, Recall@5 = 83.64%, Recall@10 = 87.27%, Recall@30 = 94.55%, MRR = 0.7107
- **BM25**: Recall@1 = 34.55%, Recall@5 = 61.82%, Recall@10 = 67.27%, Recall@30 = 80.00%, MRR = 0.4663
- **Hybrid**: Recall@1 = 74.55%, Recall@5 = 83.64%, Recall@10 = 85.45%, Recall@30 = 94.55%, MRR = 0.7917
