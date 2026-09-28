"""
evaluation_utils.py
===================
Text processing and metric computation utilities for the RAG Evaluation framework.
"""

from __future__ import annotations

import re
import string
from typing import Any, Dict, List, Optional, Set, Tuple


def normalize_text(text: str) -> str:
    """
    Standard normalization for text metrics:
    - Lowercase
    - Replace consecutive whitespaces with a single space
    - Remove punctuation (except percentage symbols and decimal points inside numbers)
    """
    if not text:
        return ""
    val = text.lower().strip()
    val = re.sub(r"\s+", " ", val)
    # Remove punctuation except digits/letters and % or .
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
    """Tokenize normalized text into space-separated words."""
    return normalize_text(text).split()


def compute_token_f1(generated: str, gold: str) -> Tuple[float, float, float]:
    """
    Compute token-level precision, recall, and F1 score.
    """
    gen_tokens = tokenize_normalized(generated)
    gold_tokens = tokenize_normalized(gold)
    
    if not gen_tokens and not gold_tokens:
        return 1.0, 1.0, 1.0
    if not gen_tokens or not gold_tokens:
        return 0.0, 0.0, 0.0
        
    # Count token frequencies
    gen_counts: Dict[str, int] = {}
    for t in gen_tokens:
        gen_counts[t] = gen_counts.get(t, 0) + 1
        
    gold_counts: Dict[str, int] = {}
    for t in gold_tokens:
        gold_counts[t] = gold_counts.get(t, 0) + 1
        
    overlap_tokens = 0
    for token, count in gen_counts.items():
        if token in gold_counts:
            overlap_tokens += min(count, gold_counts[token])
            
    precision = overlap_tokens / len(gen_tokens)
    recall = overlap_tokens / len(gold_tokens)
    
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2.0 * (precision * recall) / (precision + recall)
        
    return precision, recall, f1


def compute_keyword_recall(generated: str, gold_keywords: List[str]) -> float:
    """
    Compute the fraction of gold keywords/phrases present in the generated answer.
    Uses normalized substring matching.
    """
    if not gold_keywords:
        return 1.0
        
    gen_norm = normalize_text(generated)
    hits = 0
    for keyword in gold_keywords:
        kw_norm = normalize_text(keyword)
        if kw_norm in gen_norm:
            hits += 1
            
    return float(hits / len(gold_keywords))


def normalize_numeric_value(val_str: str) -> str:
    """
    Strip commas, currency symbols, and spaces from a numeric string representation.
    E.g. "Rs. 1,50,000" -> "150000", "10%" -> "10%"
    """
    val = val_str.lower().strip()
    val = re.sub(r"(?:rs\.?|inr|₹|[\s,])", "", val)
    return val


def compute_numeric_claim_recall(generated: str, gold_numeric_claims: List[str]) -> Optional[float]:
    """
    Compute percentage of gold numeric claims present in the generated answer.
    """
    if not gold_numeric_claims:
        return None
        
    gen_norm = normalize_numeric_value(generated)
    hits = 0
    for claim in gold_numeric_claims:
        claim_norm = normalize_numeric_value(claim)
        
        # Check if normalized value is in normalized generated string
        if claim_norm in gen_norm:
            hits += 1
            continue
            
        # Try finding raw values (e.g. matching "2%" in different formats)
        if "%" in claim_norm:
            pct_num = claim_norm.replace("%", "")
            if f"{pct_num}%" in gen_norm or f"{pct_num}percent" in gen_norm or f"{pct_num}percent" in gen_norm.replace(" ", ""):
                hits += 1
                
    return float(hits / len(gold_numeric_claims))


def compute_section_recall(generated: str, gold_sections: List[str]) -> Optional[float]:
    """
    Compute percentage of expected gold sections mentioned in the generated answer.
    E.g. "Section 80C" or "80C" or "section 80c".
    """
    if not gold_sections:
        return None
        
    gen_lower = generated.lower()
    hits = 0
    for sec in gold_sections:
        sec_clean = sec.lower().strip()
        # Look for the section number with word boundaries or as a citation
        pattern = r"\b" + re.escape(sec_clean) + r"\b"
        if re.search(pattern, gen_lower):
            hits += 1
            
    return float(hits / len(gold_sections))


STOP_WORDS: Set[str] = {
    "the", "in", "of", "to", "is", "a", "for", "and", "that", "under",
    "with", "by", "on", "or", "as", "at", "from", "this", "which", "it",
    "shall", "be", "an", "any", "are", "such", "means", "made", "has", "been"
}


def compute_overlaps(question: str, evidence: str) -> Tuple[float, float]:
    """
    Compute lexical overlaps between a question and its source evidence text:
    1. Token overlap: fraction of normalized query words (non-stopwords) that appear in normalized evidence.
    2. Phrase overlap: count of contiguous matching phrases of 4 or more normalized tokens.
    """
    q_norm = normalize_text(question)
    ev_norm = normalize_text(evidence)
    
    q_tokens = [t for t in q_norm.split() if t not in STOP_WORDS]
    ev_tokens = [t for t in ev_norm.split() if t not in STOP_WORDS]
    
    if not q_tokens:
        token_overlap = 0.0
    else:
        ev_set = set(ev_tokens)
        matched_tokens = sum(1 for t in q_tokens if t in ev_set)
        token_overlap = float(matched_tokens / len(q_tokens))
        
    # Phrase overlap: scan question for contiguous runs of 4+ tokens matching evidence
    q_all_tokens = q_norm.split()
    ev_all_tokens = ev_norm.split()
    phrase_count = 0
    
    # Simple sliding window of size 4
    if len(q_all_tokens) >= 4 and len(ev_all_tokens) >= 4:
        # Build set of all 4-grams in evidence for fast matching
        ev_4grams = set()
        for i in range(len(ev_all_tokens) - 3):
            ev_4grams.add(" ".join(ev_all_tokens[i:i+4]))
            
        for i in range(len(q_all_tokens) - 3):
            q_4gram = " ".join(q_all_tokens[i:i+4])
            if q_4gram in ev_4grams:
                phrase_count += 1
                
    return token_overlap, float(phrase_count)
