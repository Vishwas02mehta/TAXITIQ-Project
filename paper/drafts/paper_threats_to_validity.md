# Paper Threats to Validity

## Construct Validity
Construct validity concerns whether our metrics accurately measure grounding and success. We address this by using a versioned scoring formula (`INDIALAWRAG_SCORING_V2`) that combines token F1, keyword recall, and numeric recall, with strict hard failure penalties for unsupported citation or numeric hallucinations. However, automated metrics may not fully capture the syntactic nuances of legal drafting.

## Internal Validity
Internal validity involves confounding factors that could explain performance differences. We control for this by holding the context window, prompt templates, retrieval depth, and hyperparameters completely constant. Quantization differences or inference temperature settings in local Ollama runtimes could introduce minor variations.

## External Validity
External validity concerns the generalizability of results. The study is restricted to the Income-tax Act 2025. Tax statutes contain unique lexical densities and numeric dependencies (e.g. rate tables and deadlines) that might make generators behave differently than on case law or constitutional text.

## Statistical Conclusion Validity
We address statistical conclusion validity by reporting two-sided McNemar exact test p-values (p = 0.000221) for paired success rates, alongside continuity-corrected chi-square values. Furthermore, we run a 10,000-iteration paired bootstrap to report the 95% confidence interval for the success-rate difference as 15.00 to 41.67 percentage points, mitigating issues related to small sample size.
