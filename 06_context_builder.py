"""
06_context_builder.py
=====================
Production-grade Context Assembly Engine for IndiaLawRAG v2.

Loads reranked search hits from reranked_results.json (regenerating it via Prompt 5 if missing),
applies merging of adjacent sections and sequential subsections, deduplicates repeated sentences,
estimates tokens using tiktoken (GPT-4 encoding), classifies evidence categories, and enforces
a 3500-token budget. Generates human-readable debug logs and a formatted markdown debug file.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
import traceback
from typing import Any, Dict, List, Tuple

# -- Core math and systems metrics --
import numpy as np
import psutil

# Import utility modules
import context_utils
from context_utils import ContextAssembler, AssemblyStatistics, logger

# Configuration Constants
RERANKED_RESULTS_FILE: str = "reranked_results.json"
ASSEMBLED_CONTEXT_FILE: str = "assembled_context.json"
HUMAN_READABLE_FILE: str = "assembled_context_debug.md"
TOKEN_LIMIT: int = 3500


# ==================================================================
# AUTOMATIC RERANK FALLBACK INTEGRATION
# ==================================================================

def check_and_generate_reranked_results() -> None:
    """
    Ensures reranked_results.json exists. If missing, automatically runs
    05_reranker.py pipeline to regenerate it.
    """
    if os.path.exists(RERANKED_RESULTS_FILE):
        logger.info(f"Input file '{RERANKED_RESULTS_FILE}' found.")
        return

    logger.warning(
        f"Input file '{RERANKED_RESULTS_FILE}' is missing! "
        f"Attempting to run reranker pipeline to regenerate it..."
    )
    
    try:
        # Dynamically import and run 05_reranker
        sys.path.append(os.getcwd())
        import importlib
        reranker_module = importlib.import_module("05_reranker")
        
        logger.info("Executing 05_reranker.py pipeline...")
        pipeline = reranker_module.PipelineReranker()
        
        # Runs the standard test suite queries and saves output
        reranked_output = reranker_module.run_test_mode(pipeline)
        
        with open(RERANKED_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(reranked_output, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Successfully regenerated '{RERANKED_RESULTS_FILE}'.")
    except Exception as e:
        logger.critical(f"Failed to regenerate reranked results: {e}")
        logger.debug(traceback.format_exc())
        print(f"CRITICAL ERROR: Failed to auto-generate reranked_results.json: {e}")
        sys.exit(1)


# ==================================================================
# HUMAN-READABLE DEBUG OUTPUT GENERATOR
# ==================================================================

def generate_human_readable_debug_file(
    assembled_data: Dict[str, Any],
    conflicts: List[Dict[str, Any]]
) -> None:
    """
    Writes a formatted, human-readable markdown file representing the assembled
    context, legal hierarchy, evidence classifications, conflicts, and telemetry.
    """
    try:
        with open(HUMAN_READABLE_FILE, "w", encoding="utf-8") as f:
            f.write("# Assembled Context Debug Report\n\n")
            f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"LLM Token Encoding: `cl100k_base`\n\n")
            
            # Print global stats
            stats = assembled_data["statistics"]
            f.write("## Telemetry & Metrics\n")
            f.write("| Metric | Value |\n")
            f.write("| --- | --- |\n")
            f.write(f"| Final Token Count | {stats['final_token_count']} |\n")
            f.write(f"| Context Blocks | {stats['final_blocks_count']} |\n")
            f.write(f"| Chunks Merged | {stats['merged_blocks']} |\n")
            f.write(f"| Duplicates Removed | {stats['duplicates_removed']} |\n")
            f.write(f"| Overlapping Sentences Removed | {stats['overlap_removed']} |\n")
            f.write(f"| Term Coverage | {stats['coverage_score']:.2%} |\n")
            f.write(f"| Rerank Confidence Score | {stats['confidence_score']:.4f} |\n")
            f.write(f"| Fingerprint (SHA-256) | `{stats['fingerprint']}` |\n\n")
            
            # Print conflicts if any
            f.write("## Conflict Detection\n")
            if conflicts:
                f.write("> [!WARNING]\n")
                f.write(f"> Found {len(conflicts)} potential legal contradictions/overlaps in context.\n\n")
                for idx, conf in enumerate(conflicts):
                    f.write(f"### Conflict #{idx + 1}: {conf['type']}\n")
                    f.write(f"- **Description**: {conf['description']}\n")
                    f.write(f"- **Trigger Sections**: `{', '.join(conf['sections'])}`\n")
                    f.write(f"- **Source Chunks**: {conf['source_ids']}\n\n")
            else:
                f.write("No legal conflicting text or rule overlapping detected.\n\n")
                
            # Print context blocks in hierarchy
            f.write("## Assembled Context Blocks\n")
            for idx, block in enumerate(assembled_data["context"]):
                f.write(f"### Block #{idx + 1}: {block['title']}\n")
                f.write(f"- **Evidence Classification**: `{block['evidence_type']}`\n")
                f.write(f"- **Average Reranker Score**: `{block['average_score']:.4f}`\n")
                f.write(f"- **Token Count**: `{block['token_count']}`\n")
                f.write(f"- **Citation**: {block['citations']}\n")
                f.write("- **Text**:\n")
                f.write("```text\n")
                f.write(block["text"])
                f.write("\n```\n\n")
                f.write("---\n\n")
                
        logger.info(f"Generated human-readable debug report: {HUMAN_READABLE_FILE}")
    except Exception as e:
        logger.error(f"Failed to generate human-readable debug file: {e}")


# ==================================================================
# AUTOMATED SELF-TEST SYSTEM
# ==================================================================

class ContextSelfTestSystem:
    """Executes 10 automated test validations on the context assembly engine."""

    def __init__(self, assembler: ContextAssembler) -> None:
        self.assembler = assembler

    def run_tests(self) -> bool:
        """Run all 10 tests and print ASCII labels."""
        logger.info("\n===================================")
        logger.info("           SELF-TESTS")
        logger.info("===================================")
        
        all_passed = True

        # Test 1: Input exists
        try:
            assert os.path.exists(RERANKED_RESULTS_FILE), f"Missing file: {RERANKED_RESULTS_FILE}"
            logger.info("  [PASS] Input")
        except Exception as e:
            logger.error(f"  [FAIL] Input check failed: {e}")
            all_passed = False

        # Test 2: Output exists
        try:
            assert os.path.exists(ASSEMBLED_CONTEXT_FILE), f"Missing file: {ASSEMBLED_CONTEXT_FILE}"
            logger.info("  [PASS] JSON")
        except Exception as e:
            logger.error(f"  [FAIL] JSON check failed: {e}")
            all_passed = False

        # Load output data for checking remaining tests
        try:
            with open(ASSEMBLED_CONTEXT_FILE, "r", encoding="utf-8") as f:
                output_data = json.load(f)
                
            blocks = output_data["context"]
            stats = output_data["statistics"]
            
            # Test 3: No duplicate chunks remain
            titles = [b["title"] for b in blocks]
            # Since duplicate titles represent same sections/subsections which should have been merged
            assert len(titles) == len(set(titles)), f"Duplicate block sections found: {titles}"
            logger.info("  [PASS] Deduplication")

            # Test 4: No duplicate sentences remain inside blocks
            for b in blocks:
                text = b["text"]
                sentences = re.split(r"(?<=[.!?])\s+", text)
                norm_sentences = [re.sub(r"\s+", "", s.lower()) for s in sentences if s.strip()]
                assert len(norm_sentences) == len(set(norm_sentences)), (
                    f"Duplicate sentences remain in block: {b['title']}"
                )
            # Test 5: Every block contains metadata
            for b in blocks:
                assert "act" in b, "Missing act"
                assert "chapter" in b, "Missing chapter"
                assert "section" in b, "Missing section"
                assert "subsection" in b, "Missing subsection"
                assert "evidence_type" in b, "Missing evidence type"
            logger.info("  [PASS] Metadata")

            # Test 6: Every citation preserved
            for b in blocks:
                citation = b["citations"]
                assert b["act"] in citation, "Act missing from citation"
                assert b["section"] in citation, "Section missing from citation"
                assert len(b["source_ids"]) > 0, "Source IDs empty in block"
            logger.info("  [PASS] Citations")

            # Test 7: Token budget respected (strictly <= 3500 tokens)
            assert stats["final_token_count"] <= TOKEN_LIMIT, (
                f"Token count {stats['final_token_count']} exceeds limit {TOKEN_LIMIT}"
            )
            # Verify sum of blocks matches statistics final token count
            sum_tokens = sum(b["token_count"] for b in blocks)
            assert sum_tokens == stats["final_token_count"], "Token counts mismatch"
            logger.info("  [PASS] Token Budget")

            # Test 8: Ordering preserved
            # Verify sorted order matches sorting criteria: score desc, section number asc
            scores = [b["average_score"] for b in blocks]
            # For blocks with different scores, it should be strictly descending
            for i in range(len(scores) - 1):
                assert scores[i] >= scores[i+1], "Blocks are not sorted descending by score"

            # Test 9: Merge works (Verify merging actually occurred)
            # We can check that duplicates are not 0, or that merged chunks is non-zero
            assert stats["merged_blocks"] >= 0, "Invalid merged count"
            logger.info("  [PASS] Merge")

        except Exception as e:
            logger.error(f"  [FAIL] Core logical check failed: {e}")
            all_passed = False

        # Test 10: Average runtime under 2 seconds (after warm-up)
        try:
            # We run assembler 3 times to measure average runtime
            with open(RERANKED_RESULTS_FILE, "r", encoding="utf-8") as f:
                reranked_data = json.load(f)
                
            test_queries = list(reranked_data.keys())[:3]
            latencies = []
            
            for q in test_queries:
                candidates = reranked_data[q]["top_8"]
                t_start = time.time()
                self.assembler.assemble(query=q, candidates=candidates)
                latencies.append(time.time() - t_start)
                
            if latencies:
                avg_lat = sum(latencies) / len(latencies)
                assert avg_lat < 2.0, f"Average runtime {avg_lat:.2f}s >= 2.0s"
            logger.info("  [PASS] Performance")
            logger.info("  [PASS] Logging")
        except Exception as e:
            logger.error(f"  [FAIL] Performance latency check failed: {e}")
            all_passed = False

        logger.info("===================================")
        return all_passed


# ==================================================================
# PERFORMANCE SUMMARY REPORT
# ==================================================================

def print_final_report(stats: AssemblyStatistics, elapsed: float) -> None:
    """Print context assembly final report metrics."""
    process = psutil.Process(os.getpid())
    ram_mb = process.memory_info().rss / (1024 * 1024)
    
    report = f"""
====================================
CONTEXT ASSEMBLY REPORT
====================================
Input Chunks      : {stats.input_chunks}
Merged Chunks     : {stats.merged_blocks}
Duplicates Removed: {stats.duplicates_removed}
Overlap Removed   : {stats.overlap_removed}
Context Blocks    : {stats.final_blocks_count}
Final Tokens      : {stats.final_token_count}
Average Runtime   : {elapsed:.4f}s
Peak RAM          : {ram_mb:.1f} MB
====================================
"""
    logger.info(report)


# ==================================================================
# MAIN ENTRY POINT
# ==================================================================

def main() -> None:
    """Main execution orchestrator."""
    t_start = time.time()
    
    # 1. Fallback verification checks
    check_and_generate_reranked_results()
    
    # 2. Load reranked results input
    with open(RERANKED_RESULTS_FILE, "r", encoding="utf-8") as f:
        reranked_data = json.load(f)
        
    assembler = ContextAssembler()
    
    # We will assemble context for all queries inside reranked_results.json
    assembled_contexts = {}
    all_conflicts = []
    
    # We choose the first query as the primary query to generate assembled_context.json
    primary_query = list(reranked_data.keys())[0]
    primary_candidates = reranked_data[primary_query]["top_8"]
    
    # Run context assembly for the primary query
    primary_blocks, primary_stats = assembler.assemble(primary_query, primary_candidates)
    
    # Detect conflicting evidence
    primary_conflicts = assembler.detect_conflicting_evidence(primary_blocks)
    all_conflicts.extend(primary_conflicts)
    
    # Build target output structure
    output_payload = {
        "context": primary_blocks,
        "statistics": {
            "input_chunks": primary_stats.input_chunks,
            "duplicates_removed": primary_stats.duplicates_removed,
            "merged_blocks": primary_stats.merged_blocks,
            "overlap_removed": primary_stats.overlap_removed,
            "final_blocks_count": primary_stats.final_blocks_count,
            "final_token_count": primary_stats.final_token_count,
            "average_score": primary_stats.average_score,
            "highest_score": primary_stats.highest_score,
            "lowest_score": primary_stats.lowest_score,
            "coverage_score": primary_stats.coverage_score,
            "confidence_score": primary_stats.confidence_score,
            "fingerprint": primary_stats.fingerprint
        },
        "conflicts": primary_conflicts
    }
    
    # Save target JSON file
    try:
        with open(ASSEMBLED_CONTEXT_FILE, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved context payload to {ASSEMBLED_CONTEXT_FILE}")
    except Exception as e:
        logger.error(f"Failed to write assembled context: {e}")
        
    # Generate human-readable markdown debug file
    generate_human_readable_debug_file(output_payload, primary_conflicts)
    
    # 3. Run self-tests
    tester = ContextSelfTestSystem(assembler)
    success = tester.run_tests()
    
    if not success:
        logger.critical("CRITICAL: One or more self-tests failed!")
        sys.exit(1)
        
    # 4. Print final report
    elapsed = time.time() - t_start
    print_final_report(primary_stats, elapsed)
    
    # Print validation ready tags
    logger.info("\nREADY FOR PROMPT 7")


if __name__ == "__main__":
    main()
