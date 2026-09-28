# TAXITIQ Evaluation Guide

This guide explains the structure, categories, and evaluation criteria of the IndiaLawRAG v2 benchmark.

## 1. Question Stratification

The benchmark consists of **60 questions** partitioned as follows:

### Corpus Status
- **SUPPORTED** (55 questions): The required legal evidence is fully present in the statutory text.
- **NOT_SUPPORTED** (5 questions): The query represents an out-of-corpus question. The model is expected to refuse to answer.

### Query Formulations
- **LEXICAL** (8 questions): Direct questions written using exact phrases and terms from the statute.
- **PARAPHRASED** (47 questions): Questions written using synonyms, alternate phrasings, and common vocabulary.
- **REASONING** (5 questions): Complex questions requiring information synthesis across multiple sections or mathematical computations.

---

## 2. Scoring Framework & Failures

Under the `INDIALAWRAG_SCORING_V2` policy, candidate responses are graded as follows:

1. **Content Coverage Threshold**:
   For supported questions, the model must achieve a content coverage score of **0.50** or higher (derived from token-level F1, keyword recall, and numerical checks) to be marked as successful.
2. **Hard Failures (Auto-Fail)**:
   A response is marked as a failure if it encounters any of the following:
   - **`EMPTY_RESPONSE`**: The model generated an empty text.
   - **`SUPPORTED_QUESTION_REFUSAL`**: The model refused to answer a supported question despite context being present.
   - **`CITATION_GROUNDING_FAILURE`**: The response cited a provision that does not exist or is unrelated to the context.
   - **`NUMERIC_GROUNDING_FAILURE`**: The model claimed a numerical value (tax rate, threshold) that is unsupported by the context.
   - **`CONTENT_COVERAGE_BELOW_THRESHOLD`**: The coverage score was below the primary threshold of 0.50.
