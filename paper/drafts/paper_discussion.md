# Paper Discussion

## Generator Sensitivity under Frozen Contexts
The empirical findings demonstrate that when context and prompts are held constant, generator choice was associated with a substantial and statistically significant difference in legal QA performance (28.33 percentage points, p = 0.000221). This highlights that retrieval optimization is only part of the pipeline; generator behavior under fixed contexts heavily dictates overall success.

## Supported Refusal Behavior
The refusal analysis indicates that the observed difference was heavily driven by Qwen2.5's conservative refusal behavior (50.91% refusal rate vs. 7.27% for Qwen3). Qwen2.5 frequently invoked refusal statements (e.g., "the context does not contain sufficient information") even when all gold chunks were fully present. In contrast, Qwen3 demonstrated greater capability in evidence utilization, successfully answering 19 queries where Qwen2.5 refused. The discrepancy may reflect differences in instruction following, evidence utilization, uncertainty handling, or refusal behavior; however, the present experiment does not isolate the underlying model mechanism.

## Grounding Reliability vs. Answer Coverage
While Qwen3 achieved higher success, it exhibited a minor grounding trade-off, experiencing 1 citation and 1 numeric grounding failure (both associated with Question `Q18`). Conversely, Qwen2.5 had zero grounding failures. Qwen2.5's high refusal rate is associated with a highly conservative response behavior that prioritizes avoiding false claims over maximizing answer coverage. However, because Qwen3's grounding issues are restricted to a single question (Q18), these results do not establish a universal grounding trade-off mechanism, but rather highlight the contrast between answer coverage and grounding reliability under the evaluated configuration.

## Retrieval Recall
The retrieval data shows that RRF Hybrid retrieval achieved a Recall@1 of 74.55% and Recall@30 of 94.55%, providing a solid foundation for both models. The reranker successfully preserved these chunks, pushing recall to 92.73%. This confirms that the observed discrepancies were generator-side effects rather than retrieval failures.
