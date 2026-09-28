"""
reranker_utils.py
=================
Core utility algorithms for the local reranking system using BAAI/bge-reranker-v2-m3.

Provides:
1. Reusable LocalReranker class: Exposed for direct calls by python modules.
2. Model and tokenizer caching to prevent redundant disk loads.
3. Batch inference and sigmoid scoring.
4. Explainability logic for Reranked hits.
5. Telemetry metrics helper.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import psutil
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# Configuration Constants
DEFAULT_MODEL_NAME: str = "BAAI/bge-reranker-v2-m3"
LOG_DIR: str = "logs"
LOG_FILE: str = os.path.join(LOG_DIR, "reranker.log")

# Setup local reranker logging
def setup_reranker_logging() -> logging.Logger:
    """Configure search session logger with ASCII formats."""
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger("reranker")
    logger.setLevel(logging.DEBUG)
    
    if logger.handlers:
        logger.handlers.clear()

    # File Handler
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


logger = setup_reranker_logging()


@dataclass
class RerankerQualityMetrics:
    """Stores scoring statistics and latency telemetry for reranker operations."""
    average_score: float = 0.0
    median_score: float = 0.0
    lowest_score: float = 0.0
    highest_score: float = 0.0
    average_runtime: float = 0.0
    peak_ram_mb: float = 0.0
    peak_gpu_mb: float = 0.0
    candidates_count: int = 0
    returned_count: int = 0


class LocalReranker:
    """
    Local Reranking module using BAAI/bge-reranker-v2-m3.
    Implements model caching, batch processing, and score normalisation.
    """
    _tokenizer_cache: Dict[str, AutoTokenizer] = {}
    _model_cache: Dict[str, AutoModelForSequenceClassification] = {}
    _load_count: Dict[str, int] = {}  # Tracks how many times model loading code was entered

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, device: Optional[str] = None) -> None:
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = None
        self.model = None
        self._load_model_cached()

    def _load_model_cached(self) -> None:
        """Load tokenizer and model from cache or disk only once."""
        model_key = self.model_name
        
        # Track initial load entry point for testing purposes
        if model_key not in LocalReranker._load_count:
            LocalReranker._load_count[model_key] = 0
        
        if model_key in LocalReranker._tokenizer_cache and model_key in LocalReranker._model_cache:
            logger.debug(f"Using cached model and tokenizer for {self.model_name}")
            self.tokenizer = LocalReranker._tokenizer_cache[model_key]
            self.model = LocalReranker._model_cache[model_key]
            return

        LocalReranker._load_count[model_key] += 1
        logger.info(f"Loading local reranker model: {self.model_name} (Device: {self.device})")
        t0 = time.time()
        
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        model.to(self.device)
        model.eval()

        logger.info(f"Reranker model loaded in {time.time() - t0:.2f}s.")

        # Cache reference
        LocalReranker._tokenizer_cache[model_key] = tokenizer
        LocalReranker._model_cache[model_key] = model
        self.tokenizer = tokenizer
        self.model = model

    @classmethod
    def get_load_count(cls, model_name: str = DEFAULT_MODEL_NAME) -> int:
        """Return the number of times this model has been loaded from disk."""
        return cls._load_count.get(model_name, 0)

    def compute_scores_batched(
        self,
        query: str,
        passages: List[str],
        batch_size: int = 32
    ) -> List[float]:
        """
        Run batch inference on query-passage pairs and convert logs to [0, 1] using sigmoid.
        """
        if not passages:
            return []
            
        pairs = [[query, passage] for passage in passages]
        all_scores: List[float] = []

        # Run inference in batches
        for i in range(0, len(pairs), batch_size):
            batch_pairs = pairs[i : i + batch_size]
            
            with torch.no_grad():
                inputs = self.tokenizer(
                    batch_pairs,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt"
                )
                # Move tensors to device
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                outputs = self.model(**inputs)
                logits = outputs.logits.view(-1).float()
                
                # Convert raw classification logits to [0, 1] probability range using Sigmoid
                probs = torch.sigmoid(logits).tolist()
                
                # Handle single-item batch squeeze edge case
                if isinstance(probs, float):
                    probs = [probs]
                all_scores.extend(probs)
                
        return all_scores

    def generate_explanation(self, query: str, passage: str, metadata: Dict[str, Any]) -> str:
        """
        Provide a simple textual explanation of why the document is relevant.
        """
        relevance_reasons: List[str] = []
        q_words = set(re.findall(r"\b\w{3,}\b", query.lower()))
        p_words = set(re.findall(r"\b\w{3,}\b", passage.lower()))
        
        overlapping_words = q_words & p_words
        if overlapping_words:
            # Sort for determinism
            sorted_words = sorted(list(overlapping_words))
            relevance_reasons.append(
                f"Contains key search terms: {', '.join(sorted_words[:4])}"
            )
            
        # Metadata checks
        sec = str(metadata.get("section_no", "")).lower().strip()
        if sec and sec != "unknown" and sec in query.lower():
            relevance_reasons.append(f"Explicitly matches Section {metadata.get('section_no')}")
            
        ch = str(metadata.get("chapter", "")).lower().strip()
        if ch and ch != "unknown" and ch in query.lower():
            relevance_reasons.append(f"Matches Chapter {metadata.get('chapter')}")

        if not relevance_reasons:
            relevance_reasons.append("High semantic contextual correspondence.")
            
        return " | ".join(relevance_reasons)

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_n: int = 8,
        batch_size: int = 32
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], RerankerQualityMetrics]:
        """
        Rerank a list of retrieved documents for a given query.
        
        Arguments:
            query: The legal user question.
            candidates: List of hits (e.g. from hybrid search).
            top_n: Number of results to filter (default 8).
            
        Returns:
            Tuple containing:
            - top_n_reranked: Top N scored and sorted hits.
            - full_reranked: Full list of candidates with reranked scores and order preserved.
            - quality_metrics: Metrics tracking dataclass.
        """
        t0 = time.time()
        
        if not candidates:
            return [], [], RerankerQualityMetrics()

        passages = [c["chunk_text"] for c in candidates]
        scores = self.compute_scores_batched(query, passages, batch_size=batch_size)
        
        # Build list of candidates with new scores
        full_reranked_list: List[Dict[str, Any]] = []
        for score, cand in zip(scores, candidates):
            # Preserve original context, insert score, generate explanation
            reranked_item = dict(cand)
            
            # Ensure the item has an ID (fallback to hashing chunk_text if missing)
            if "id" not in reranked_item:
                metadata = cand.get("metadata", {})
                doc_id = metadata.get("id")
                if not doc_id:
                    import hashlib
                    doc_id = hashlib.sha256(cand["chunk_text"].encode("utf-8")).hexdigest()[:32]
                reranked_item["id"] = doc_id
                
            reranked_item["reranker_score"] = float(score)
            reranked_item["explanation"] = self.generate_explanation(
                query, cand["chunk_text"], cand.get("metadata", {})
            )
            full_reranked_list.append(reranked_item)

        # Sort the full list descending by reranker_score
        full_reranked_list.sort(key=lambda x: x["reranker_score"], reverse=True)
        
        # Truncate top_n
        top_n_reranked = full_reranked_list[:top_n]
        
        # Calculate quality metrics
        latency = time.time() - t0
        all_scores = [item["reranker_score"] for item in full_reranked_list]
        
        median_score = float(np.median(all_scores)) if all_scores else 0.0
        avg_score = float(np.mean(all_scores)) if all_scores else 0.0
        lowest = float(min(all_scores)) if all_scores else 0.0
        highest = float(max(all_scores)) if all_scores else 0.0

        process = psutil.Process(os.getpid())
        ram_mb = process.memory_info().rss / (1024 * 1024)
        gpu_mb = 0.0
        if torch.cuda.is_available():
            gpu_mb = torch.cuda.max_memory_allocated() / (1024 * 1024)
            
        metrics = RerankerQualityMetrics(
            average_score=avg_score,
            median_score=median_score,
            lowest_score=lowest,
            highest_score=highest,
            average_runtime=latency,
            peak_ram_mb=ram_mb,
            peak_gpu_mb=gpu_mb,
            candidates_count=len(candidates),
            returned_count=len(top_n_reranked)
        )
        
        # Log event to reranker.log
        logger.debug(
            f"Query: '{query}' | Model: {self.model_name} | Runtime: {latency:.4f}s | "
            f"Device: {self.device} | Score avg: {avg_score:.4f} | Reranked scores: {all_scores[:8]}"
        )
        
        return top_n_reranked, full_reranked_list, metrics
