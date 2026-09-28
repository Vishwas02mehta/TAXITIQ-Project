# Paper Contributions

We outline the core contributions of this work:

1. **Controlled Generator-Isolation Framework**

"We present a controlled evaluation methodology in which hybrid retrieval, reranking, context assembly, and canonical prompting are frozen per query, enabling paired comparison of local LLM generators under identical RAG inputs."

2. **Corpus-Grounded Legal RAG Benchmark**

"We construct and audit a 60-question benchmark grounded in 4,123 deterministic chunks of the Income-tax Act 2025, covering lexical, paraphrased, multi-evidence reasoning, and explicitly out-of-corpus queries."

3. **Paired Empirical Comparison of Local Generators**

"We compare Qwen2.5 7B Instruct and Qwen3 8B under the frozen IndiaLawRAG v2 pipeline and observe success rates of 43.33% and 71.67%, respectively. The 28.33 percentage-point paired difference is supported by an exact McNemar test (p = 0.000221) and a 10,000-resample paired bootstrap confidence interval."

4. **Supported-Question Refusal Analysis**

"We quantify a substantial generator-specific refusal discrepancy under identical RAG inputs. Qwen2.5 refused 50.91% of supported questions, compared with 7.27% for Qwen3, identifying refusal behavior as a major observed correlate of downstream success differences in the evaluated configuration."

5. **Stage-Level Failure and Grounding Analysis**

"We distinguish retrieval, reranking, context assembly, refusal, content-coverage, citation-grounding, and numeric-grounding failures, enabling component-level attribution rather than relying exclusively on aggregate end-to-end accuracy."
