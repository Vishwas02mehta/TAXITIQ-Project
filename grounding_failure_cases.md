# IndiaLawRAG v2 Grounding Failure Cases Report
Generated: 2026-07-15 13:34:22

This report logs every grounding failure detected under Scoring V2 (fabricated citations or unsupported numeric claims).

Total Cases Detected: 2

### `Q18` (QWEN3)
- **Question**: What are the rules regarding daily penalty under Section 459(1) of the Act?
- **Category / Formulation**: `section_lookup` / `PARAPHRASED`
- **Content Coverage Score**: `0.6311`
- **Failure Reasons**: `['NUMERIC_GROUNDING_FAILURE']`
- **Unsupported Citation Count**: `0`
- **Unsupported Numeric Claim Count**: `1`
- **Model Response Response**:
  > *"The rules regarding the daily penalty under Section 459(1) of the Income-tax Act 2025 are as follows:  
- If a reporting entity fails to furnish the required report under section 511, the prescribed authority may impose a penalty of **₹5,000 for every day** during which the failure continues, **if the period of failure does not exceed one month**.  
- If the failure continues **beyond the period of one month**, the penalty increases to **₹15,000 for every day**.  

These provisions are specified in [Act: Income-tax Act 2025, Section: 459, Subsection: 1].  

Additionally, Subsection (3) of Section 459 imposes a penalty of **₹50,"*

----------------------------------------

### `Q52` (QWEN3)
- **Question**: How does Section 124(2) modify the contribution limit of 10% mentioned in Section 124(1) for assessees taxed under Section 202(1)?
- **Category / Formulation**: `cross_section` / `REASONING`
- **Content Coverage Score**: `0.7477`
- **Failure Reasons**: `['CITATION_GROUNDING_FAILURE']`
- **Unsupported Citation Count**: `1`
- **Unsupported Numeric Claim Count**: `0`
- **Model Response Response**:
  > *"Section 124(2) modifies the 10% contribution limit in Section 124(1) by substituting "10%" with "14%" for assessees whose total income is chargeable to tax under Section 202(1). This adjustment applies specifically to clause (b) of Section 124(1), which originally capped deductions at 10% for contributions by employers other than Central/State Governments. 

**Supporting legal references:**  
[Act: Income-tax Act 2025, Section: 124, Subsection: 2]"*

----------------------------------------
