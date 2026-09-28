# Paper Outline

1. **Introduction**
   - Background on legal RAG systems.
   - Core research question: Effect of generator selection on frozen pipelines.
   - Summary of key empirical results (+28.33 percentage points success rate gain for Qwen3).
2. **Methodology**
   - Corpus preprocessing and ChromaDB persistent collection (4,123 chunks).
   - RRF hybrid retrieval and `bge-reranker-v2-m3` reranking.
   - IndiaLawRAG v2 corpus-grounded benchmark (60 questions).
   - `INDIALAWRAG_SCORING_V2` metric and 0.50 threshold criteria.
3. **Experimental Setup**
   - Open-weights local generators (`qwen2.5:7b-instruct` and `qwen3:8b`).
   - Hyperparameters: Temperature = 0.0, max tokens = 512, seed = 42.
4. **Results**
   - Point estimates: Qwen2.5 success = 43.33%, Qwen3 success = 71.67%.
   - Paired McNemar significance (p = 0.000221) and bootstrap 95% CI (15.00 to 41.67 percentage points).
   - Stratified formulation outcomes (Lexical, Paraphrased, Reasoning).
   - Supported refusal and grounding reliability analysis.
5. **Discussion**
   - Sensitivity under identical contexts.
   - Refusal behavior hypotheses.
6. **Limitations**
   - Out-of-corpus vs. supported scale constraints.
   - Focus on India Income-tax Act 2025.
   - Distinction between `AUTO_GROUNDED` status and expert human legal validation.
7. **Threats to Validity**
   - Construct, Internal, External, and Statistical Conclusion validity.
8. **Conclusion & Reproducibility**
   - Summary of insights and data reproducibility statements.
