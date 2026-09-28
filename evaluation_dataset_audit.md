# IndiaLawRAG Benchmark Quality Audit Report

**Audit Status**: `READY_FOR_FULL_EVALUATION`

## Executive Summary

- **Total Questions Audited**: 60
- **Formulation Mismatches**: 0
- **Near-Duplicate Pairs**: 1
- **Gold Grounding Failures**: 0
- **Evidence Scope Mismatches**: 0
- **Ambiguous Out-of-Corpus**: 0
- **Invalid Reasoning Labels**: 0

## Formulation Labels & Paraphrase Quality

| Metric | Value |
|---|---|
| Stored LEXICAL | 8 |
| Stored PARAPHRASED | 47 |
| Stored REASONING | 5 |
| Strong Paraphrases | 33 |
| Moderate Paraphrases | 9 |
| Weak Paraphrases | 0 |
| Mislabelled Lexical | 0 |


## Reasoning Question Details

### Question `Q51`

- **Question**: Compare the tax consequences under Section 11(2) and Section 12(2) when the conditions for income exclusions are not satisfied by a person versus a political party or electoral trust.
- **Chunk Count**: 2
- **Sections**: ['11', '12']
- **Dependency**: *Requires comparing non-compliance consequences under Section 11(2) for a person versus Section 12(2) for a political party or electoral trust.*
- **Abated Validation**: `all_evidence_units_required=True` -> `reasoning_valid=True`

### Question `Q52`

- **Question**: How does Section 124(2) modify the contribution limit of 10% mentioned in Section 124(1) for assessees taxed under Section 202(1)?
- **Chunk Count**: 2
- **Sections**: ['124']
- **Dependency**: *Requires combining Section 124(1) (base employer contribution limit) and Section 124(2) (substitution of 14% for section 202(1) assessees).*
- **Abated Validation**: `all_evidence_units_required=True` -> `reasoning_valid=True`

### Question `Q53`

- **Question**: Compare the daily penalties for a reporting entity's initial default under Section 459(1) versus a continuing default after order service under Section 459(3).
- **Chunk Count**: 2
- **Sections**: ['459']
- **Dependency**: *Requires comparing Section 459(1) (standard reporting failure penalties) and Section 459(3) (penalty after service of order).*
- **Abated Validation**: `all_evidence_units_required=True` -> `reasoning_valid=True`

### Question `Q54`

- **Question**: Compare the deduction limit for employee pension contributions under Section 124(3) versus employer pension contribution under Section 124(1).
- **Chunk Count**: 2
- **Sections**: ['124']
- **Dependency**: *Requires comparing Section 124(3) (limit for employee contributions) and Section 124(1) (limit for employer contributions).*
- **Abated Validation**: `all_evidence_units_required=True` -> `reasoning_valid=True`

### Question `Q55`

- **Question**: Explain standard daily penalties under Section 459(1) for reporting entity default and Section 459(2) for failing to produce records.
- **Chunk Count**: 2
- **Sections**: ['459']
- **Dependency**: *Requires combining Section 459(1) (general failure penalty) and Section 459(2) (failure to produce records penalty).*
- **Abated Validation**: `all_evidence_units_required=True` -> `reasoning_valid=True`

## Near-Duplicate Question Pairs

| Question A | Question B | Jaccard | Token Set Ratio | Shared Sections |
|---|---|---|---|---|
| Q35 | Q40 | 0.67 | 0.89 | ['202'] |


## Out of Corpus Audit

| Question | Matches | Best BM25 Score | Best Chunk ID | Status |
|---|---|---|---|---|
| What are the registration requirements and thresholds for GST in India? | E:0, K:0 | 22.51 | 5fc0515072... | CLEARLY_OUT_OF_CORPUS |
| What is the penalty for late filing of income tax returns in the United States under the IRS code? | E:0, K:0 | 28.24 | be09911dce... | CLEARLY_OUT_OF_CORPUS |
| How is wealth tax calculated for residential properties in France? | E:0, K:0 | 14.80 | b615f826c3... | CLEARLY_OUT_OF_CORPUS |
| What is the corporate tax rate in Singapore for tech startups? | E:0, K:0 | 16.27 | bb5ef0890e... | CLEARLY_OUT_OF_CORPUS |
| What are the rules for customs duty exemption on personal baggage for passengers arriving in India? | E:0, K:0 | 22.34 | dfb0dad205... | CLEARLY_OUT_OF_CORPUS |


## Top 10 Frequently Used Sections

| Section | Question Count |
|---|---|
| Section 459 | 10 |
| Section 3 | 9 |
| Section 2 | 9 |
| Section 124 | 6 |
| Section 133 | 5 |
| Section 123 | 3 |
| Section 7 | 3 |
| Section 122 | 2 |
| Section 6 | 2 |
| Section 202 | 2 |


## Quality Flags per Question

| Question ID | Category | Type | Flags |
|---|---|---|---|
| Q01 | definition | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q02 | definition | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q03 | definition | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q04 | definition | LEXICAL | CORPUS_CONCENTRATION_WARNING |
| Q05 | definition | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q06 | definition | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q07 | definition | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q08 | definition | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q09 | definition | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q10 | definition | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q11 | section_lookup | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q12 | section_lookup | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q16 | section_lookup | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q17 | section_lookup | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q18 | section_lookup | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q21 | eligibility | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q22 | eligibility | LEXICAL | CORPUS_CONCENTRATION_WARNING |
| Q23 | eligibility | LEXICAL | CORPUS_CONCENTRATION_WARNING |
| Q24 | eligibility | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q25 | eligibility | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q27 | deduction | LEXICAL | CORPUS_CONCENTRATION_WARNING |
| Q28 | deduction | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q32 | deduction | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q33 | deduction | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q34 | deduction | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q35 | rate | PARAPHRASED | NEAR_DUPLICATE |
| Q38 | rate | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q39 | rate | LEXICAL | CORPUS_CONCENTRATION_WARNING |
| Q40 | rate | PARAPHRASED | NEAR_DUPLICATE |
| Q42 | deadline | LEXICAL | CORPUS_CONCENTRATION_WARNING |
| Q43 | deadline | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q45 | deadline | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q46 | penalty | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q47 | penalty | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q48 | penalty | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q49 | penalty | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q50 | penalty | PARAPHRASED | CORPUS_CONCENTRATION_WARNING |
| Q52 | cross_section | REASONING | CORPUS_CONCENTRATION_WARNING |
| Q53 | cross_section | REASONING | CORPUS_CONCENTRATION_WARNING |
| Q54 | cross_section | REASONING | CORPUS_CONCENTRATION_WARNING |
| Q55 | cross_section | REASONING | CORPUS_CONCENTRATION_WARNING |

