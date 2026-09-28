# Paper Limitations

We document the primary limitations of the current study:

1. **Benchmark Scale**: The evaluation benchmark is limited to 60 questions. While statistically sufficient under McNemar's test, larger datasets would provide finer grain category analyses.
2. **Corpus Focus**: The study focuses exclusively on a single statutory legal text: India's Income-tax Act 2025. Results may vary on other statutes, case law, or multi-jurisdictional corpora.
3. **Automated Grounding**: The benchmark status is `CORPUS_GROUNDED` and the review status is `AUTO_GROUNDED`. We explicitly distinguish corpus-grounded evaluation from expert human legal validation. This study does not represent a professional legal-expert audit or expert human legal validation.
4. **Local Generators Only**: Evaluation is limited to two local open-weights generators (Qwen2.5 7B and Qwen3 8B). Cloud-hosted proprietary LLMs were not evaluated.
5. **Heuristic Scoring**: Success is bound to the `INDIALAWRAG_SCORING_V2` metric at a primary threshold of 0.50. High threshold sensitivity might alter exact numbers, though general patterns persist.
6. **Reasoning Subsets**: The reasoning category was limited to 5 questions, making statistical claims regarding complex statutory reasoning tentative.
