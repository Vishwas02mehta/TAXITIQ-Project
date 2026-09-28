"""
search_utils.py
===============
Core utility algorithms for the hybrid retrieval engine.

Provides:
1. Reusable Query Preprocessor: Expands legal/tax abbreviations using RapidFuzz.
2. BM25 Indexer Wrapper: Handles tokenization, punctuation removal, and index building.
3. Reciprocal Rank Fusion (RRF): Merges vector search results and BM25 results.
4. Metadata Booster: Dynamically boosts document ranks based on query term matches.
5. Search Metrics Tracker: Computes performance and retrieval metrics.
"""

from __future__ import annotations

import re
import string
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple
from rank_bm25 import BM25Okapi
from rapidfuzz import process, utils

# Configuration: Common tax/legal abbreviation mapping
ABBREVIATIONS: Dict[str, str] = {
    "hra": "house rent allowance",
    "tds": "tax deducted at source",
    "gst": "goods and services tax",
    "itc": "input tax credit",
    "ay": "assessment year",
    "fy": "financial year",
    "pan": "permanent account number",
    "deduction": "deduction exemption rebate",
}


def preprocess_query(query: str, threshold: float = 85.0) -> str:
    """
    Normalize and preprocess the input search query.
    
    1. Converts to lowercase and normalizes whitespace.
    2. Uses RapidFuzz to expand abbreviations, ensuring legal concepts are preserved
       even with minor spelling variations.
    """
    if not query:
        return ""
    
    q_lower = query.lower().strip()
    # Normalize duplicate whitespaces
    q_normalized = re.sub(r"\s+", " ", q_lower)
    
    # Tokenize query to check individual words for abbreviations
    words = re.findall(r"\b\w+\b", q_normalized)
    expansions: List[str] = []
    
    for word in words:
        # Check direct abbreviation match
        if word in ABBREVIATIONS:
            expansions.append(ABBREVIATIONS[word])
            continue
            
        # Use RapidFuzz for fuzzy abbreviation match (helps with typos or plural forms)
        # Avoid checking very short words of length <= 1
        if len(word) > 1:
            best_match = process.extractOne(
                word,
                ABBREVIATIONS.keys(),
                score_cutoff=threshold
            )
            if best_match:
                matched_key = best_match[0]
                expansions.append(ABBREVIATIONS[matched_key])
                
    # Combine original query and unique expansions to preserve both contexts
    unique_expansions = []
    seen = set()
    for exp in expansions:
        if exp not in seen:
            seen.add(exp)
            # Only expand if it's not already in the query string
            if exp not in q_normalized:
                unique_expansions.append(exp)
                
    if unique_expansions:
        return f"{query} {' '.join(unique_expansions)}"
    return query


def tokenize_document(text: str) -> List[str]:
    """
    Tokenize, lowercase, and remove punctuation from text.
    Suitable for building BM25 indexes.
    """
    if not text:
        return []
    text_lower = text.lower()
    # Remove punctuation
    text_clean = text_lower.translate(str.maketrans("", "", string.punctuation))
    return text_clean.split()


class BM25SearchEngine:
    """
    Wrapper for rank-bm25 indexing and querying.
    Designed to support easy scaling and caching for multiple collections.
    """

    def __init__(self, doc_ids: List[str], documents: List[str]) -> None:
        self.doc_ids = doc_ids
        self.documents = documents
        self.tokenized_corpus = [tokenize_document(doc) for doc in documents]
        self._bm25 = BM25Okapi(self.tokenized_corpus)

    def search(self, query: str, top_n: int = 50) -> List[Tuple[str, float]]:
        """
        Execute BM25 keyword search.
        Returns a list of tuples containing (doc_id, score).
        """
        tokenized_query = tokenize_document(query)
        if not tokenized_query:
            return []
            
        scores = self._bm25.get_scores(tokenized_query)
        
        # Zip doc_ids and scores, filter zero-score documents (to save processing), and sort
        hits = [(doc_id, float(score)) for doc_id, score in zip(self.doc_ids, scores) if score > 0.0]
        hits.sort(key=lambda x: x[1], reverse=True)
        return hits[:top_n]


def compute_rrf(
    vector_results: List[str],
    bm25_results: List[str],
    k: int = 60
) -> Dict[str, Tuple[float, int, int]]:
    """
    Compute Reciprocal Rank Fusion (RRF) for merged search results.
    
    Arguments:
        vector_results: Ordered list of document IDs from vector search.
        bm25_results: Ordered list of document IDs from BM25 search.
        k: RRF constant parameter (default 60).
        
    Returns:
        Dict mapping doc_id -> (rrf_score, vector_rank, bm25_rank)
        Unmatched rank is represented as -1.
    """
    rrf_scores: Dict[str, Tuple[float, int, int]] = {}
    
    # Track document rankings
    vector_ranks = {doc_id: i + 1 for i, doc_id in enumerate(vector_results)}
    bm25_ranks = {doc_id: i + 1 for i, doc_id in enumerate(bm25_results)}
    
    all_doc_ids = set(vector_results) | set(bm25_results)
    
    for doc_id in all_doc_ids:
        v_rank = vector_ranks.get(doc_id, -1)
        b_rank = bm25_ranks.get(doc_id, -1)
        
        v_score = 1.0 / (k + v_rank) if v_rank != -1 else 0.0
        b_score = 1.0 / (k + b_rank) if b_rank != -1 else 0.0
        
        score = v_score + b_score
        rrf_scores[doc_id] = (score, v_rank, b_rank)
        
    return rrf_scores


def apply_metadata_boosting(
    rrf_score: float,
    metadata: Dict[str, Any],
    query: str
) -> float:
    """
    Boost RRF score dynamically if metadata elements (section, chapter, act, subsection)
    are explicitly or closely mentioned in the search query.
    """
    if not metadata:
        return rrf_score
        
    q_lower = query.lower()
    boost_multiplier = 1.0
    
    # 1. Section Number Matching (Strong Boost)
    # e.g., "Section 80C" or "80C"
    sec_no = str(metadata.get("section_no", "")).lower().strip()
    if sec_no and sec_no != "unknown":
        # Check if the section number exists as a word in the query
        pattern = r"\b" + re.escape(sec_no) + r"\b"
        if re.search(pattern, q_lower):
            boost_multiplier += 1.0
            
    # 2. Chapter Matching (Moderate Boost)
    # e.g., "Chapter I"
    chapter = str(metadata.get("chapter", "")).lower().strip()
    if chapter and chapter != "unknown":
        pattern = r"\bchapter\s+" + re.escape(chapter) + r"\b"
        if re.search(pattern, q_lower):
            boost_multiplier += 0.3
            
    # 3. Subsection Matching (Mild Boost)
    # e.g., "Sub-section (1)", "subsection (1)", or just "(1)"
    subsection = str(metadata.get("subsection", "")).lower().strip()
    if subsection:
        sub_patterns = [
            f"({subsection})",
            f"sub-section ({subsection})",
            f"subsection ({subsection})",
            f"subsection {subsection}"
        ]
        if any(pat in q_lower for pat in sub_patterns):
            boost_multiplier += 0.2
            
    # 4. Act Matching (Small Context Boost)
    act = str(metadata.get("act", "")).lower().strip()
    if act:
        # Check matching words: "income", "tax", "act", "2025"
        act_words = re.findall(r"\b\w+\b", act)
        matches = sum(1 for w in act_words if w in q_lower)
        if matches > 0:
            boost_multiplier += 0.05 * matches
            
    return rrf_score * boost_multiplier


@dataclass
class QueryMetrics:
    """Dataclass to record telemetry and latency breakdown for a single search query."""
    query: str
    preprocessed_query: str
    vector_latency_sec: float = 0.0
    bm25_latency_sec: float = 0.0
    fusion_latency_sec: float = 0.0
    total_latency_sec: float = 0.0
    vector_hits_count: int = 0
    bm25_hits_count: int = 0
    fused_hits_count: int = 0
