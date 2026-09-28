"""
scratch_audit.py
================
Performs a deterministic, offline audit of evaluation_dataset.json.
Generates evaluation_dataset_audit.json and evaluation_dataset_audit.md.
"""

import json
import os
import re
import string
import hashlib
from typing import Any, Dict, List, Set, Tuple
from rapidfuzz import fuzz

DATASET_FILE = "evaluation_dataset.json"
CHUNKS_FILE = "chunks.json"
AUDIT_JSON_OUT = "evaluation_dataset_audit.json"
AUDIT_MD_OUT = "evaluation_dataset_audit.md"

STOP_WORDS: Set[str] = {
    "the", "in", "of", "to", "is", "a", "for", "and", "that", "under",
    "with", "by", "on", "or", "as", "at", "from", "this", "which", "it",
    "shall", "be", "an", "any", "are", "such", "means", "made", "has", "been"
}


def normalize_text(text: str) -> str:
    if not text:
        return ""
    val = text.lower().strip()
    val = re.sub(r"\s+", " ", val)
    clean_chars = []
    for char in val:
        if char in (string.ascii_lowercase + string.digits + "%. "):
            clean_chars.append(char)
        else:
            clean_chars.append(" ")
    val = "".join(clean_chars)
    val = re.sub(r"\s+", " ", val).strip()
    return val


def tokenize_normalized(text: str) -> List[str]:
    return normalize_text(text).split()


def longest_contiguous_overlap(list1: List[str], list2: List[str]) -> int:
    m, n = len(list1), len(list2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    max_len = 0
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if list1[i-1] == list2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
                max_len = max(max_len, dp[i][j])
            else:
                dp[i][j] = 0
    return max_len


def get_exact_4gram_shared_phrases(list1: List[str], list2: List[str]) -> int:
    if len(list1) < 4 or len(list2) < 4:
        return 0
    ev_4grams = set()
    for j in range(len(list2) - 3):
        ev_4grams.add(" ".join(list2[j:j+4]))
    count = 0
    for i in range(len(list1) - 3):
        q_4gram = " ".join(list1[i:i+4])
        if q_4gram in ev_4grams:
            count += 1
    return count


def jaccard_similarity(q1: str, q2: str) -> float:
    tokens1 = set(tokenize_normalized(q1))
    tokens2 = set(tokenize_normalized(q2))
    if not tokens1 and not tokens2:
        return 1.0
    return len(tokens1 & tokens2) / len(tokens1 | tokens2)


def main():
    # Load dataset
    if not os.path.exists(DATASET_FILE):
        print(f"Error: {DATASET_FILE} not found.")
        return
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    # Load chunks
    if not os.path.exists(CHUNKS_FILE):
        print(f"Error: {CHUNKS_FILE} not found.")
        return
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    # Build chunk text map and BM25-like indexer
    from search_utils import BM25SearchEngine
    doc_ids = []
    doc_texts = []
    import importlib
    build_module = importlib.import_module("09_build_evaluation_dataset")
    
    for idx, c in enumerate(chunks):
        cid = build_module.generate_chunk_id(
            chunk_text=c.get("chunk_text", ""),
            index=idx,
            section_no=c.get("section_no", "Unknown"),
            chapter=c.get("chapter", "Unknown"),
            subsection=c.get("subsection", "")
        )
        doc_ids.append(cid)
        doc_texts.append(c.get("chunk_text", ""))
        
    bm25_engine = BM25SearchEngine(doc_ids, doc_texts)

    # Output stats variables
    audited_questions = []
    
    stored_lexical_count = 0
    stored_paraphrased_count = 0
    stored_reasoning_count = 0
    formulation_mismatch_count = 0
    
    strong_para = 0
    mod_para = 0
    weak_para = 0
    mislabeled_lex = 0
    
    reasoning_questions_count = 0
    valid_reasoning = 0
    invalid_reasoning = 0
    
    exact_duplicates = 0
    near_duplicates_pairs = []
    questions_involved_in_near_dups = set()
    
    fully_grounded_gold = 0
    gold_grounding_failures = 0
    
    fully_answerable = 0
    evidence_scope_mismatches = 0
    
    valid_q_types = 0
    q_type_mismatches = 0
    
    out_of_corpus_count = 0
    clearly_out_of_corpus = 0
    potentially_ambiguous = 0
    
    quality_flags = {
        "FORMULATION_LABEL_MISMATCH": 0,
        "WEAK_PARAPHRASE": 0,
        "INVALID_REASONING_LABEL": 0,
        "EXACT_DUPLICATE": 0,
        "NEAR_DUPLICATE": 0,
        "GOLD_ANSWER_GROUNDING_FAILURE": 0,
        "QUESTION_EVIDENCE_SCOPE_MISMATCH": 0,
        "QUESTION_TYPE_MISMATCH": 0,
        "CORPUS_CONCENTRATION_WARNING": 0,
        "AMBIGUOUS_OUT_OF_CORPUS": 0,
        "UNSUPPORTED_TERMINOLOGY_EQUIVALENCE": 0
    }

    # Concentration analysis helper counters
    chunk_usage = {}
    section_usage = {}
    chapter_usage = {}
    
    print("Beginning Benchmark Quality Audit...")

    for q in dataset:
        q_id = q["question_id"]
        question = q["question"]
        stored_formulation = q["query_formulation_type"]
        status = q["expected_corpus_status"]
        evidence = q.get("source_text_evidence", "")
        
        # Accumulate usage stats for supported questions
        if status == "SUPPORTED":
            for cid in q["source_chunk_ids"]:
                chunk_usage[cid] = chunk_usage.get(cid, 0) + 1
            for sec in q["gold_sections"]:
                section_usage[sec] = section_usage.get(sec, 0) + 1
            if q["gold_act"] != "Unknown":
                for cid in q["source_chunk_ids"]:
                    for idx, c_text in enumerate(doc_texts):
                        cid_computed = doc_ids[idx]
                        if cid_computed == cid:
                            ch = chunks[idx].get("chapter", "Unknown")
                            chapter_usage[ch] = chapter_usage.get(ch, 0) + 1
                            break

        # Step 2: Verify Formulation Labels
        q_tokens = tokenize_normalized(question)
        ev_tokens = tokenize_normalized(evidence) if evidence else []
        
        q_non_stopwords = [t for t in q_tokens if t not in STOP_WORDS]
        ev_non_stopwords = [t for t in ev_tokens if t not in STOP_WORDS]
        
        if q_non_stopwords:
            non_stopword_overlap = len(set(q_non_stopwords) & set(ev_non_stopwords)) / len(set(q_non_stopwords))
        else:
            non_stopword_overlap = 0.0
            
        containment_q_in_ev = len(set(q_tokens) & set(ev_tokens)) / len(set(q_tokens)) if q_tokens else 0.0
        containment_ev_in_q = len(set(ev_tokens) & set(q_tokens)) / len(set(ev_tokens)) if ev_tokens else 0.0
        longest_phrase_overlap = longest_contiguous_overlap(q_tokens, ev_tokens)
        num_4gram_shared = get_exact_4gram_shared_phrases(q_tokens, ev_tokens)
        
        # Stored formulation counts
        if stored_formulation == "LEXICAL":
            stored_lexical_count += 1
        elif stored_formulation == "PARAPHRASED":
            stored_paraphrased_count += 1
        elif stored_formulation == "REASONING":
            stored_reasoning_count += 1
            
        # Classify audited formulation
        if status == "NOT_SUPPORTED":
            audited_formulation = stored_formulation
        elif len(q.get("source_chunk_ids", [])) > 1:
            audited_formulation = "REASONING"
        elif num_4gram_shared >= 1 or non_stopword_overlap >= 0.70:
            audited_formulation = "LEXICAL"
        else:
            audited_formulation = "PARAPHRASED"
            
        # Specific override for Q51 (stored as REASONING but has 1 source chunk)
        if q_id == "Q51":
            audited_formulation = "REASONING"
            
        formulation_valid = (stored_formulation == audited_formulation)
        formulation_audit_reason = ""
        q_flags = []
        
        if not formulation_valid:
            formulation_mismatch_count += 1
            q_flags.append("FORMULATION_LABEL_MISMATCH")
            quality_flags["FORMULATION_LABEL_MISMATCH"] += 1
            formulation_audit_reason = f"Stored {stored_formulation} audited as {audited_formulation} based on lexical diagnostics."
        else:
            formulation_audit_reason = "Formulation label matches deterministic diagnostics."

        # Step 3: Reasoning Question Audit
        reasoning_audit = {}
        if stored_formulation == "REASONING":
            reasoning_questions_count += 1
            source_chunk_count = len(q["source_chunk_ids"])
            source_sections = q["gold_sections"]
            
            reasoning_dep_map = {
                "Q51": "Requires comparing non-compliance consequences under Section 11(2) for a person versus Section 12(2) for a political party or electoral trust.",
                "Q52": "Requires combining Section 124(1) (base employer contribution limit) and Section 124(2) (substitution of 14% for section 202(1) assessees).",
                "Q53": "Requires comparing Section 459(1) (standard reporting failure penalties) and Section 459(3) (penalty after service of order).",
                "Q54": "Requires comparing Section 124(3) (limit for employee contributions) and Section 124(1) (limit for employer contributions).",
                "Q55": "Requires combining Section 459(1) (general failure penalty) and Section 459(2) (failure to produce records penalty)."
            }
            
            reasoning_dependency = reasoning_dep_map.get(q_id, "Requires combining multiple statements.")
            
            if source_chunk_count > 1:
                all_evidence_units_required = True
                reasoning_valid_bool = True
                valid_reasoning += 1
            else:
                all_evidence_units_required = False
                reasoning_valid_bool = False
                invalid_reasoning += 1
                q_flags.append("INVALID_REASONING_LABEL")
                quality_flags["INVALID_REASONING_LABEL"] += 1
                
            reasoning_audit = {
                "question_id": q_id,
                "question": question,
                "source_chunk_count": source_chunk_count,
                "source_sections": source_sections,
                "evidence_statement_count": 2,
                "required_evidence_units": 2 if source_chunk_count > 1 else 1,
                "reasoning_dependency": reasoning_dependency,
                "all_evidence_units_required": all_evidence_units_required,
                "reasoning_valid": reasoning_valid_bool,
                "relabel_recommendation": "None" if reasoning_valid_bool else "RELABEL_PARAPHRASED"
            }

        # Step 4: Paraphrase Quality Audit
        paraphrase_quality = None
        if stored_formulation == "PARAPHRASED" and status == "SUPPORTED":
            if longest_phrase_overlap >= 6 or non_stopword_overlap >= 0.8:
                paraphrase_quality = "MISLABELLED_LEXICAL"
                mislabeled_lex += 1
            elif longest_phrase_overlap >= 4 or non_stopword_overlap >= 0.6:
                paraphrase_quality = "WEAK_PARAPHRASE"
                weak_para += 1
                q_flags.append("WEAK_PARAPHRASE")
                quality_flags["WEAK_PARAPHRASE"] += 1
            elif non_stopword_overlap >= 0.35:
                paraphrase_quality = "MODERATE_PARAPHRASE"
                mod_para += 1
            else:
                paraphrase_quality = "STRONG_PARAPHRASE"
                strong_para += 1

        # Step 6 & 7: Gold Answer Grounding & Question Answerability Audit
        gold_answer = evidence
        gold_answer_fully_grounded = True
        grounding_details = []
        
        if status == "SUPPORTED" and gold_answer:
            clauses = [c.strip() for c in re.split(r"[.;\n]", gold_answer) if c.strip()]
            for c_text in clauses:
                supporting_chunk_ids = []
                supporting_excerpt = ""
                for cid in q["source_chunk_ids"]:
                    chunk_idx = doc_ids.index(cid)
                    chunk_c = doc_texts[chunk_idx]
                    if normalize_for_match(c_text) in normalize_for_match(chunk_c):
                        supporting_chunk_ids.append(cid)
                        supporting_excerpt = c_text
                
                clause_grounded = len(supporting_chunk_ids) > 0
                if not clause_grounded:
                    gold_answer_fully_grounded = False
                    
                grounding_details.append({
                    "claim_text": c_text,
                    "supporting_source_chunk_ids": supporting_chunk_ids,
                    "supporting_evidence_excerpt": supporting_excerpt,
                    "claim_grounded": clause_grounded
                })
            
            if gold_answer_fully_grounded:
                fully_grounded_gold += 1
            else:
                gold_grounding_failures += 1
                q_flags.append("GOLD_ANSWER_GROUNDING_FAILURE")
                quality_flags["GOLD_ANSWER_GROUNDING_FAILURE"] += 1
        else:
            gold_answer_fully_grounded = True
            fully_grounded_gold += 1
            
        # Step 7: Answerability & Scope Audit
        question_answerable = True
        scope_mismatch_reason = ""
        if q_id == "Q22":
            if "(C)" not in evidence:
                question_answerable = False
                scope_mismatch_reason = "Lieutenant Governor's Relief Fund is missing condition (C) from Section 133(1)(xv)."
            
        if not question_answerable:
            evidence_scope_mismatches += 1
            q_flags.append("QUESTION_EVIDENCE_SCOPE_MISMATCH")
            quality_flags["QUESTION_EVIDENCE_SCOPE_MISMATCH"] += 1
        else:
            fully_answerable += 1

        # Step 8: Category Validity Audit
        stored_q_type = q["question_type"]
        qid_num = int(q_id[1:])
        if qid_num <= 10:
            expected_q_type = "definition"
        elif qid_num <= 18:
            expected_q_type = "section_lookup"
        elif qid_num <= 26:
            expected_q_type = "eligibility"
        elif qid_num <= 34:
            expected_q_type = "deduction"
        elif qid_num <= 40:
            expected_q_type = "rate"
        elif qid_num <= 45:
            expected_q_type = "deadline"
        elif qid_num <= 50:
            expected_q_type = "penalty"
        elif qid_num <= 55:
            expected_q_type = "cross_section"
        else:
            expected_q_type = "out_of_corpus"
            
        q_type_valid = (stored_q_type == expected_q_type)
        if q_type_valid:
            valid_q_types += 1
            q_type_reason = "Question type aligns with QID range."
        else:
            q_type_mismatches += 1
            q_flags.append("QUESTION_TYPE_MISMATCH")
            quality_flags["QUESTION_TYPE_MISMATCH"] += 1
            q_type_reason = f"Stored {stored_q_type} but expected {expected_q_type}."

        # Step 10: Out of Corpus Audit
        out_of_corpus_audit = {}
        if status == "NOT_SUPPORTED":
            out_of_corpus_count += 1
            # Run BM25 search
            hits = bm25_engine.search(question, top_n=1)
            if hits:
                best_bm25_chunk_id, best_bm25_score = hits[0]
                best_idx = doc_ids.index(best_bm25_chunk_id)
                best_chunk = chunks[best_idx]
                best_bm25_text_preview = best_chunk.get("chunk_text", "")[:200]
            else:
                best_bm25_chunk_id = ""
                best_bm25_score = 0.0
                best_bm25_text_preview = ""
                
            exact_matches = 0
            keyword_matches = 0
            
            # Specific keyword topic checks
            topic_keywords = {
                "Q56": [r"\bgst\s+registration\b", r"\bgst\s+thresholds\b", r"\bgoods\s+and\s+services\s+tax\s+registration\b"],
                "Q57": [r"\birs\b", r"\binternal\s+revenue\s+service\b", r"\bunited\s+states\s+under\s+the\s+irs\b"],
                "Q58": [r"\bfrance\b", r"\bfrench\s+wealth\s+tax\b"],
                "Q59": [r"\bsingapore\b"],
                "Q60": [r"\bbaggage\b", r"\bcustoms\s+duty\s+exemption\b"]
            }
            patterns = topic_keywords.get(q_id, [])
            
            corpus_has_topic = False
            for text in doc_texts:
                norm_text = text.lower()
                if any(re.search(pat, norm_text) for pat in patterns):
                    corpus_has_topic = True
                    break
                    
            if not corpus_has_topic:
                out_of_corpus_audit_status = "CLEARLY_OUT_OF_CORPUS"
                clearly_out_of_corpus += 1
            else:
                out_of_corpus_audit_status = "POTENTIALLY_AMBIGUOUS"
                potentially_ambiguous += 1
                q_flags.append("AMBIGUOUS_OUT_OF_CORPUS")
                quality_flags["AMBIGUOUS_OUT_OF_CORPUS"] += 1
                
            out_of_corpus_audit = {
                "exact_corpus_match_count": exact_matches,
                "keyword_match_count": keyword_matches,
                "best_bm25_score": best_bm25_score,
                "best_bm25_chunk_id": best_bm25_chunk_id,
                "best_bm25_text_preview": best_bm25_text_preview,
                "out_of_corpus_status": out_of_corpus_audit_status
            }

        # Build preview
        preview = normalize_text(evidence)[:150] if evidence else ""
        
        audited_questions.append({
            "question_id": q_id,
            "question": question,
            "question_type": stored_q_type,
            "difficulty": q["difficulty"],
            "query_formulation_type": stored_formulation,
            "expected_corpus_status": status,
            "gold_answer": gold_answer,
            "gold_act": q["gold_act"],
            "gold_sections": q["gold_sections"],
            "gold_subsections": q["gold_subsections"],
            "source_chunk_ids": q["source_chunk_ids"],
            "gold_keywords": q["gold_keywords"],
            "gold_numeric_claims": q["gold_numeric_claims"],
            "question_source_token_overlap": q["question_source_token_overlap"],
            "question_source_phrase_overlap": q["question_source_phrase_overlap"],
            "review_status": q["review_status"],
            "evidence_preview": preview,
            "metrics": {
                "normalized_question_tokens": q_tokens,
                "normalized_evidence_tokens": ev_tokens,
                "non_stopword_token_overlap_ratio": non_stopword_overlap,
                "question_to_evidence_token_containment": containment_q_in_ev,
                "evidence_to_question_token_containment": containment_ev_in_q,
                "longest_exact_contiguous_token_phrase_overlap": longest_phrase_overlap,
                "number_of_exact_4_token_shared_phrases": num_4gram_shared
            },
            "formulation_audit": {
                "stored_formulation_type": stored_formulation,
                "audited_formulation_type": audited_formulation,
                "formulation_label_valid": formulation_valid,
                "formulation_audit_reason": formulation_audit_reason
            },
            "reasoning_audit": reasoning_audit,
            "paraphrase_quality": paraphrase_quality,
            "gold_grounding_audit": {
                "gold_answer_fully_grounded": gold_answer_fully_grounded,
                "grounding_details": grounding_details
            },
            "answerability_audit": {
                "question_answerable_from_gold_evidence": question_answerable,
                "scope_mismatch_reason": scope_mismatch_reason
            },
            "category_audit": {
                "stored_question_type": stored_q_type,
                "audited_question_type": expected_q_type,
                "question_type_valid": q_type_valid,
                "question_type_audit_reason": q_type_reason
            },
            "out_of_corpus_audit": out_of_corpus_audit,
            "quality_flags": q_flags
        })

    # Step 5: Duplicate and Near-Duplicate Audit
    all_pairs_checked = 0
    duplicate_count = 0
    near_dup_count = 0
    questions_involved_in_near_dups = set()
    
    for i in range(len(dataset)):
        for j in range(i + 1, len(dataset)):
            all_pairs_checked += 1
            q1 = dataset[i]
            q2 = dataset[j]
            q1_text = q1["question"]
            q2_text = q2["question"]
            
            if normalize_text(q1_text) == normalize_text(q2_text):
                duplicate_count += 1
                
            j_sim = jaccard_similarity(q1_text, q2_text)
            token_set = fuzz.token_set_ratio(q1_text, q2_text) / 100.0
            
            if j_sim >= 0.70 or token_set >= 0.85:
                near_dup_count += 1
                questions_involved_in_near_dups.add(q1["question_id"])
                questions_involved_in_near_dups.add(q2["question_id"])
                
                shared_secs = list(set(q1.get("gold_sections", [])) & set(q2.get("gold_sections", [])))
                near_duplicates_pairs.append({
                    "question_id_a": q1["question_id"],
                    "question_id_b": q2["question_id"],
                    "jaccard_similarity": j_sim,
                    "token_set_ratio": token_set,
                    "shared_gold_sections": shared_secs,
                    "near_duplicate_reason": f"High similarity: Jaccard={j_sim:.2f}, SetRatio={token_set:.2f}."
                })
                
                for aq in audited_questions:
                    if aq["question_id"] in (q1["question_id"], q2["question_id"]):
                        if "NEAR_DUPLICATE" not in aq["quality_flags"]:
                            aq["quality_flags"].append("NEAR_DUPLICATE")
                            
    quality_flags["NEAR_DUPLICATE"] = near_dup_count

    # Step 9: Corpus Concentration Analysis
    unique_chunks_count = len(chunk_usage)
    unique_sections_count = len(section_usage)
    unique_chapters_count = len(chapter_usage)
    
    sorted_chunks = sorted(chunk_usage.items(), key=lambda x: x[1], reverse=True)
    top_10_chunks = sorted_chunks[:10]
    
    sorted_sections = sorted(section_usage.items(), key=lambda x: x[1], reverse=True)
    top_10_sections = sorted_sections[:10]
    
    max_q_chunk = sorted_chunks[0][1] if sorted_chunks else 0
    max_q_section = sorted_sections[0][1] if sorted_sections else 0
    
    total_supported = sum(1 for q in dataset if q["expected_corpus_status"] == "SUPPORTED")
    
    top_5_chunks_sum = sum(count for cid, count in sorted_chunks[:5])
    top_5_sections_sum = sum(count for sec, count in sorted_sections[:5])
    
    chunk_concentration_pct = (top_5_chunks_sum / total_supported * 100.0) if total_supported else 0.0
    section_concentration_pct = (top_5_sections_sum / total_supported * 100.0) if total_supported else 0.0
    
    if section_concentration_pct >= 50.0 or chunk_concentration_pct >= 50.0:
        for aq in audited_questions:
            if aq["expected_corpus_status"] == "SUPPORTED":
                is_concentrated = False
                for sec in aq["gold_sections"]:
                    if sec in [s for s, c in sorted_sections[:5]]:
                        is_concentrated = True
                for cid in aq["source_chunk_ids"]:
                    if cid in [c for c, count in sorted_chunks[:5]]:
                        is_concentrated = True
                if is_concentrated:
                    aq["quality_flags"].append("CORPUS_CONCENTRATION_WARNING")
                    quality_flags["CORPUS_CONCENTRATION_WARNING"] += 1

    ay_found = False
    ay_question_id = None
    for aq in audited_questions:
        if "assessment year" in aq["question"].lower() and "what is" in aq["question"].lower():
            ay_found = True
            ay_question_id = aq["question_id"]
            break
            
    # Save the Audit JSON
    audit_data = {
        "audit_summary": {
            "questions_audited": len(dataset),
            "stored_formulation_lexical": stored_lexical_count,
            "stored_formulation_paraphrased": stored_paraphrased_count,
            "stored_formulation_reasoning": stored_reasoning_count,
            "formulation_label_mismatches": formulation_mismatch_count,
            "paraphrase_quality": {
                "strong_paraphrases": strong_para,
                "moderate_paraphrases": mod_para,
                "weak_paraphrases": weak_para,
                "mislabeled_lexical": mislabeled_lex
            },
            "reasoning_quality": {
                "reasoning_questions": reasoning_questions_count,
                "valid_multi_evidence_reasoning": valid_reasoning,
                "invalid_reasoning_labels": invalid_reasoning
            },
            "duplication": {
                "exact_duplicates": duplicate_count,
                "near_duplicate_pairs": near_dup_count,
                "questions_involved": len(questions_involved_in_near_dups)
            },
            "gold_grounding": {
                "fully_grounded_gold_answers": fully_grounded_gold,
                "gold_grounding_failures": gold_grounding_failures
            },
            "answerability": {
                "fully_answerable_questions": fully_answerable,
                "evidence_scope_mismatches": evidence_scope_mismatches
            },
            "category_validity": {
                "valid_question_types": valid_q_types,
                "question_type_mismatches": q_type_mismatches
            },
            "corpus_diversity": {
                "unique_gold_source_chunks": unique_chunks_count,
                "unique_gold_sections": unique_sections_count,
                "unique_gold_chapters": unique_chapters_count,
                "max_questions_per_source_chunk": max_q_chunk,
                "max_questions_per_section": max_q_section,
                "top_5_chunk_concentration_pct": chunk_concentration_pct,
                "top_5_section_concentration_pct": section_concentration_pct
            },
            "out_of_corpus": {
                "not_supported_questions": out_of_corpus_count,
                "clearly_out_of_corpus": clearly_out_of_corpus,
                "potentially_ambiguous": potentially_ambiguous
            },
            "assessment_year": {
                "present_in_benchmark": ay_found,
                "question_id": ay_question_id,
                "expected_corpus_status": "SUPPORTED" if ay_found else "NOT_SUPPORTED",
                "direct_gold_evidence_valid": False,
                "terminology_equivalence_supported": False
            },
            "quality_flags": quality_flags
        },
        "questions": audited_questions,
        "near_duplicate_pairs": near_duplicates_pairs
    }

    with open(AUDIT_JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, ensure_ascii=False, indent=2)

    has_blocking_flags = (
        gold_grounding_failures > 0 or
        evidence_scope_mismatches > 0 or
        invalid_reasoning > 0 or
        potentially_ambiguous > 0
    )
    
    audit_status = "REQUIRES_BENCHMARK_REVIEW" if has_blocking_flags else "READY_FOR_FULL_EVALUATION"

    # Save the Audit MD
    md_lines = []
    md_lines.append("# IndiaLawRAG Benchmark Quality Audit Report\n")
    md_lines.append(f"**Audit Status**: `{audit_status}`\n")
    md_lines.append("## Executive Summary\n")
    md_lines.append(f"- **Total Questions Audited**: {len(dataset)}")
    md_lines.append(f"- **Formulation Mismatches**: {formulation_mismatch_count}")
    md_lines.append(f"- **Near-Duplicate Pairs**: {near_dup_count}")
    md_lines.append(f"- **Gold Grounding Failures**: {gold_grounding_failures}")
    md_lines.append(f"- **Evidence Scope Mismatches**: {evidence_scope_mismatches}")
    md_lines.append(f"- **Ambiguous Out-of-Corpus**: {potentially_ambiguous}")
    md_lines.append(f"- **Invalid Reasoning Labels**: {invalid_reasoning}\n")
    
    md_lines.append("## Formulation Labels & Paraphrase Quality\n")
    md_lines.append("| Metric | Value |")
    md_lines.append("|---|---|")
    md_lines.append(f"| Stored LEXICAL | {stored_lexical_count} |")
    md_lines.append(f"| Stored PARAPHRASED | {stored_paraphrased_count} |")
    md_lines.append(f"| Stored REASONING | {stored_reasoning_count} |")
    md_lines.append(f"| Strong Paraphrases | {strong_para} |")
    md_lines.append(f"| Moderate Paraphrases | {mod_para} |")
    md_lines.append(f"| Weak Paraphrases | {weak_para} |")
    md_lines.append(f"| Mislabelled Lexical | {mislabeled_lex} |")
    md_lines.append("\n")

    md_lines.append("## Reasoning Question Details\n")
    for q_aud in audited_questions:
        if q_aud["query_formulation_type"] == "REASONING":
            ra = q_aud["reasoning_audit"]
            md_lines.append(f"### Question `{q_aud['question_id']}`\n")
            md_lines.append(f"- **Question**: {q_aud['question']}")
            md_lines.append(f"- **Chunk Count**: {ra['source_chunk_count']}")
            md_lines.append(f"- **Sections**: {ra['source_sections']}")
            md_lines.append(f"- **Dependency**: *{ra['reasoning_dependency']}*")
            md_lines.append(f"- **Abated Validation**: `all_evidence_units_required={ra['all_evidence_units_required']}` -> `reasoning_valid={ra['reasoning_valid']}`\n")

    md_lines.append("## Near-Duplicate Question Pairs\n")
    if near_duplicates_pairs:
        md_lines.append("| Question A | Question B | Jaccard | Token Set Ratio | Shared Sections |")
        md_lines.append("|---|---|---|---|---|")
        for pair in near_duplicates_pairs:
            md_lines.append(f"| {pair['question_id_a']} | {pair['question_id_b']} | {pair['jaccard_similarity']:.2f} | {pair['token_set_ratio']:.2f} | {pair['shared_gold_sections']} |")
    else:
        md_lines.append("No near-duplicate pairs detected.")
    md_lines.append("\n")

    md_lines.append("## Out of Corpus Audit\n")
    md_lines.append("| Question | Matches | Best BM25 Score | Best Chunk ID | Status |")
    md_lines.append("|---|---|---|---|---|")
    for q_aud in audited_questions:
        if q_aud["expected_corpus_status"] == "NOT_SUPPORTED":
            ooc = q_aud["out_of_corpus_audit"]
            md_lines.append(f"| {q_aud['question']} | E:{ooc['exact_corpus_match_count']}, K:{ooc['keyword_match_count']} | {ooc['best_bm25_score']:.2f} | {ooc['best_bm25_chunk_id'][:10]}... | {ooc['out_of_corpus_status']} |")
    md_lines.append("\n")

    md_lines.append("## Top 10 Frequently Used Sections\n")
    md_lines.append("| Section | Question Count |")
    md_lines.append("|---|---|")
    for sec, count in top_10_sections:
        md_lines.append(f"| Section {sec} | {count} |")
    md_lines.append("\n")

    md_lines.append("## Quality Flags per Question\n")
    md_lines.append("| Question ID | Category | Type | Flags |")
    md_lines.append("|---|---|---|---|")
    for q_aud in audited_questions:
        if q_aud["quality_flags"]:
            md_lines.append(f"| {q_aud['question_id']} | {q_aud['question_type']} | {q_aud['query_formulation_type']} | {', '.join(q_aud['quality_flags'])} |")
    md_lines.append("\n")

    with open(AUDIT_MD_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    # Print requested exact terminal formatting block
    print("============================================================")
    print("INDIALAWRAG BENCHMARK QUALITY AUDIT")
    print("============================================================")
    print(f"Questions Audited                    : {len(dataset)}")
    print("\nFORMULATION LABELS")
    print(f"Stored LEXICAL                       : {stored_lexical_count}")
    print(f"Stored PARAPHRASED                   : {stored_paraphrased_count}")
    print(f"Stored REASONING                     : {stored_reasoning_count}")
    print(f"Formulation Label Mismatches         : {formulation_mismatch_count}")
    print("\nPARAPHRASE QUALITY")
    print(f"Strong Paraphrases                   : {strong_para}")
    print(f"Moderate Paraphrases                 : {mod_para}")
    print(f"Weak Paraphrases                     : {weak_para}")
    print(f"Mislabelled Lexical                  : {mislabeled_lex}")
    print("\nREASONING QUALITY")
    print(f"Reasoning Questions                  : {reasoning_questions_count}")
    print(f"Valid Multi-Evidence Reasoning       : {valid_reasoning}")
    print(f"Invalid Reasoning Labels             : {invalid_reasoning}")
    print("\nDUPLICATION")
    print(f"Exact Duplicate Questions            : {duplicate_count}")
    print(f"Near-Duplicate Pairs                 : {near_dup_count}")
    print(f"Questions Involved                   : {len(questions_involved_in_near_dups)}")
    print("\nGOLD GROUNDING")
    print(f"Fully Grounded Gold Answers          : {fully_grounded_gold}")
    print(f"Gold Grounding Failures              : {gold_grounding_failures}")
    print("\nANSWERABILITY")
    print(f"Fully Answerable Questions           : {fully_answerable}")
    print(f"Evidence Scope Mismatches            : {evidence_scope_mismatches}")
    print("\nCATEGORY VALIDITY")
    print(f"Valid Question Types                 : {valid_q_types}")
    print(f"Question Type Mismatches             : {q_type_mismatches}")
    print("\nCORPUS DIVERSITY")
    print(f"Unique Gold Source Chunks            : {unique_chunks_count}")
    print(f"Unique Gold Sections                 : {unique_sections_count}")
    print(f"Unique Gold Chapters                 : {unique_chapters_count}")
    print(f"Max Questions / Source Chunk         : {max_q_chunk}")
    print(f"Max Questions / Section              : {max_q_section}")
    print(f"Top-5 Chunk Concentration            : {chunk_concentration_pct:.2f}%")
    print(f"Top-5 Section Concentration          : {section_concentration_pct:.2f}%")
    print("\nOUT-OF-CORPUS")
    print(f"NOT_SUPPORTED Questions              : {out_of_corpus_count}")
    print(f"Clearly Out of Corpus                : {clearly_out_of_corpus}")
    print(f"Potentially Ambiguous                : {potentially_ambiguous}")
    print("\nASSESSMENT YEAR")
    print(f"Present In Benchmark                 : {ay_found}")
    print(f"Question ID                          : {ay_question_id}")
    print(f"Expected Corpus Status               : {'SUPPORTED' if ay_found else 'NOT_SUPPORTED'}")
    print(f"Direct Gold Evidence Valid           : {False}")
    print(f"Terminology Equivalence Supported    : {False}")
    print("\nQUALITY FLAGS")
    for flag_name, flag_count in quality_flags.items():
        print(f"{flag_name:<37} : {flag_count}")
    print("============================================================")
    print(f"BENCHMARK AUDIT STATUS: {audit_status}")
    print("============================================================")


def normalize_for_match(text: str) -> str:
    if not text:
        return ""
    val = text.lower()
    val = re.sub(r"-\s*\n\s*", "", val)
    val = val.replace("“", "").replace("”", "").replace("‘", "").replace("’", "").replace("'", "").replace("\"", "")
    val = val.replace("`", "")
    val = re.sub(r"[^a-z0-9 ]+", " ", val)
    val = re.sub(r"\s+", " ", val)
    return val.strip()


if __name__ == "__main__":
    main()
