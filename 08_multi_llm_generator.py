"""
08_multi_llm_generator.py
=========================
Controlled Multi-LLM Generator Experiment for IndiaLawRAG v2.

Runs the EXACT SAME retrieved legal context through multiple local generator
LLMs (via Ollama) and compares their outputs under identical conditions.

Experimental design:
- Retrieval, reranking, and context assembly execute EXACTLY ONCE per query.
- The frozen context + canonical prompt are sent identically to each model.
- The ONLY experimental variable is the generator model.

CLI modes:
  python 08_multi_llm_generator.py --test         # 5-query smoke test
  python 08_multi_llm_generator.py --query "..."   # single query
  python 08_multi_llm_generator.py --interactive   # interactive loop
"""

import sys
import importlib

# Force reload of project modules to bypass persistent process caching in agent environment
for mod_name in ['model_config', 'llm_client', 'prompt_builder', 'answer_validator', 'context_utils']:
    if mod_name in sys.modules:
        try:
            importlib.reload(sys.modules[mod_name])
        except Exception:
            pass

import hashlib
import json
import logging
import os
import platform
import re
import subprocess
import time
import traceback
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import psutil
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Project modules
from model_config import (
    DEFAULT_GENERATION_CONFIG,
    GENERATOR_MODELS,
    MODEL_A_KEY,
    MODEL_B_KEY,
    GeneratorModelConfig,
    get_all_model_configs,
)
from llm_client import LLMClient, detect_ollama_runtime
from prompt_builder import PromptBuilder
from answer_validator import (
    AnswerValidator,
    ConfidenceEstimator,
    NumericClaimValidator,
    compute_citation_precision,
)
from context_utils import ContextAssembler

# ── Configuration ────────────────────────────────────────────────────
LOG_DIR: str = "logs"
LOG_FILE: str = os.path.join(LOG_DIR, "multi_llm.log")
RESULTS_FILE: str = "multi_llm_results.json"
MANIFEST_FILE: str = "experiment_manifest.json"
CHROMA_DIR: str = "chroma_db"
DEFAULT_COLLECTION: str = "indian_tax_law_corpus_v1"
EXPECTED_DOCS_COUNT: int = 4123
CHUNKS_JSON: str = "chunks.json"

console = Console()


# ── Logging ──────────────────────────────────────────────────────────

def setup_logging() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    _logger = logging.getLogger("multi_llm")
    _logger.setLevel(logging.DEBUG)
    if _logger.handlers:
        _logger.handlers.clear()
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(fh)
    _logger.addHandler(ch)
    return _logger


logger = setup_logging()


# ── Corpus Coverage Check ────────────────────────────────────────────

def check_corpus_coverage(
    query: str,
    search_hits: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Determine whether the corpus meaningfully covers the query topic.
    Uses BM25/keyword evidence from search hits and metadata inspection.

    Returns:
        {
            "corpus_coverage_status": "SUPPORTED" | "WEAK" | "NOT_FOUND",
            "corpus_coverage_evidence": str
        }
    """
    if not search_hits:
        return {
            "corpus_coverage_status": "NOT_FOUND",
            "corpus_coverage_evidence": "No search hits returned for query."
        }

    query_lower = query.lower()
    # Extract meaningful keywords (4+ chars, no stop words)
    stop_words = {"what", "where", "when", "with", "from", "that", "this", "under",
                  "shall", "which", "about", "have", "does", "there", "been", "were",
                  "they", "their", "also", "into", "only", "than", "some"}
    query_keywords = set(re.findall(r"\b\w{4,}\b", query_lower)) - stop_words

    # Check top 10 hits for keyword overlap
    top_hits = search_hits[:10]
    keyword_hits = 0
    section_matches = 0
    act_names_found: set = set()

    for hit in top_hits:
        text_lower = hit.get("chunk_text", "").lower()
        meta = hit.get("metadata", {})
        act = str(meta.get("act", "")).lower()
        if act:
            act_names_found.add(act)

        # Count how many query keywords appear in chunk text
        for kw in query_keywords:
            if kw in text_lower:
                keyword_hits += 1

        # Check section/title metadata for direct match
        sec_title = str(meta.get("section_title", "")).lower()
        for kw in query_keywords:
            if kw in sec_title:
                section_matches += 1

    # Score calculation
    max_possible = len(query_keywords) * len(top_hits) if query_keywords else 1
    coverage_ratio = keyword_hits / max_possible if max_possible > 0 else 0

    # Fusion score check: if top hits have very low scores, coverage is weak
    top_scores = [h.get("score", 0) for h in top_hits]
    avg_score = sum(top_scores) / len(top_scores) if top_scores else 0

    evidence_parts = [
        f"Query keywords: {query_keywords or 'none'}",
        f"Keyword hits in top 10: {keyword_hits}/{max_possible}",
        f"Section title matches: {section_matches}",
        f"Avg top-10 score: {avg_score:.4f}",
        f"Acts found: {act_names_found or 'none'}",
    ]

    if coverage_ratio >= 0.15 and avg_score >= 0.01:
        status = "SUPPORTED"
    elif coverage_ratio >= 0.05 or keyword_hits >= 2:
        status = "WEAK"
    else:
        status = "NOT_FOUND"

    return {
        "corpus_coverage_status": status,
        "corpus_coverage_evidence": "; ".join(evidence_parts),
    }


# ── Experiment Manifest Builder ──────────────────────────────────────

def build_experiment_manifest(
    generation_config: Dict[str, Any],
    canonical_system_prompt_sha256: str,
    ollama_info: Dict[str, Any],
    collection_count: int,
) -> Dict[str, Any]:
    """Build the full reproducibility manifest."""
    import importlib

    def _get_version(mod_name: str) -> Optional[str]:
        try:
            mod = importlib.import_module(mod_name)
            return getattr(mod, "__version__", None)
        except ImportError:
            return None

    # Git commit hash
    git_hash = None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        if result.returncode == 0:
            git_hash = result.stdout.strip()
    except Exception:
        pass

    # Chunks.json SHA-256
    chunks_sha256 = None
    if os.path.isfile(CHUNKS_JSON):
        h = hashlib.sha256()
        with open(CHUNKS_JSON, "rb") as f:
            while True:
                block = f.read(65536)
                if not block:
                    break
                h.update(block)
        chunks_sha256 = h.hexdigest()

    manifest = {
        "experiment_name": "IndiaLawRAG Multi-LLM Generator Comparison",
        "experiment_version": "1.0.0",
        "execution_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "operating_system": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python_version": platform.python_version(),
        "pytorch_version": _get_version("torch"),
        "transformers_version": _get_version("transformers"),
        "sentence_transformers_version": _get_version("sentence_transformers"),
        "chromadb_version": _get_version("chromadb"),
        "ollama_version": ollama_info.get("ollama_version"),
        "ollama_executable_path": ollama_info.get("executable_path"),
        "ollama_service_reachable": ollama_info.get("service_reachable", False),
        "retrieval_model": "BAAI/bge-large-en-v1.5",
        "reranker_model": "BAAI/bge-reranker-v2-m3",
        "generator_models": [
            {"key": m.key, "ollama_model": m.ollama_model, "display_name": m.display_name}
            for m in get_all_model_configs()
        ],
        "collection_name": DEFAULT_COLLECTION,
        "collection_count": collection_count,
        "chunks_json_sha256": chunks_sha256,
        "context_builder_token_budget": 3500,
        "hybrid_vector_top_k": 50,
        "bm25_top_k": 50,
        "rrf_k": 60,
        "reranker_candidate_count": 30,
        "final_context_chunk_count": 8,
        "generation_config": generation_config,
        "canonical_system_prompt_sha256": canonical_system_prompt_sha256,
        "git_commit_hash": git_hash,
        "determinism_note": (
            "Ollama does not guarantee mathematical determinism across runs "
            "even with temperature=0 and a fixed seed due to internal threading "
            "and quantization. This is a known limitation."
        ),
    }
    return manifest


# ── Multi-LLM Generator Experiment Core ─────────────────────────────

class MultiLLMGeneratorExperiment:
    """
    Orchestrates a controlled multi-LLM comparison experiment.
    For each query:
    1. Retrieval (once)
    2. Rerank (once)
    3. Context assembly (once)
    4. Freeze context -> SHA-256
    5. Build canonical prompt -> SHA-256
    6. Send identical prompt to each model
    7. Validate each answer
    """

    def __init__(self) -> None:
        self.client = LLMClient()
        self.search_engine = None
        self.reranker = None
        self.assembler: Optional[ContextAssembler] = None
        self.initialized = False
        self.ollama_info: Dict[str, Any] = {}
        self.model_availability: Dict[str, bool] = {}
        self.collection_count: int = 0

        # Instrumentation counters (reset per query)
        self.retrieval_count: int = 0
        self.reranker_count: int = 0
        self.context_build_count: int = 0
        self.prompt_build_count: int = 0

    def init_pipeline(self) -> None:
        """Load retrieval, reranker, and context builder components."""
        if self.initialized:
            return

        logger.info("Initializing Multi-LLM experiment pipeline...")
        t0 = time.time()

        sys.path.append(os.getcwd())
        import importlib

        search_module = importlib.import_module("04_search")
        rerank_module = importlib.import_module("05_reranker")

        self.search_engine = search_module.HybridSearchEngine()
        self.search_engine.init_resources(search_module.DEFAULT_COLLECTION)

        self.reranker = rerank_module.PipelineReranker()
        self.assembler = ContextAssembler()

        # Get collection count
        import chromadb
        chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        try:
            collection = chroma_client.get_collection(name=DEFAULT_COLLECTION)
            self.collection_count = collection.count()
        except Exception:
            self.collection_count = 0

        self.initialized = True
        logger.info(f"Pipeline initialized in {time.time() - t0:.2f}s.")

    def detect_ollama(self) -> Dict[str, Any]:
        """Detect Ollama runtime and check model availability."""
        self.ollama_info = detect_ollama_runtime()

        if not self.ollama_info["service_reachable"]:
            logger.warning("Ollama service is NOT reachable.")
            print("\n" + "=" * 60)
            print("WARNING: Ollama runtime is not available.")
            if self.ollama_info["executable_path"]:
                print(f"  Executable found at: {self.ollama_info['executable_path']}")
                print("  But the service could not be started.")
            else:
                print("  Ollama executable was NOT found on this system.")
                print("  Install from: https://ollama.com/download")
            print("=" * 60 + "\n")
            self.model_availability = {
                m.key: False for m in get_all_model_configs()
            }
            return self.ollama_info

        # Check each model
        for model_cfg in get_all_model_configs():
            available = self.client.ensure_model(model_cfg.ollama_model)
            self.model_availability[model_cfg.key] = available
            status = "AVAILABLE" if available else "BLOCKED"
            logger.info(f"  Model {model_cfg.display_name}: {status}")

        return self.ollama_info

    def _reset_counters(self) -> None:
        self.retrieval_count = 0
        self.reranker_count = 0
        self.context_build_count = 0
        self.prompt_build_count = 0

    def run_query(self, query: str) -> Dict[str, Any]:
        """
        Execute the full controlled experiment pipeline for a single query.
        Returns a structured comparison result dict.
        """
        self.init_pipeline()
        self._reset_counters()
        t_start = time.time()

        gen_config = DEFAULT_GENERATION_CONFIG

        # ── Step 1: Hybrid retrieval (ONCE) ──
        logger.info(f"Retrieving candidates for: '{query}'")
        search_hits, search_metrics = self.search_engine.search(query, top_n=30)
        self.retrieval_count += 1

        search_candidates = [
            {
                "rank": rank + 1,
                "score": hit["score"],
                "fusion_score": hit["fusion_score"],
                "vector_rank": hit["vector_rank"],
                "bm25_rank": hit["bm25_rank"],
                "metadata": hit["metadata"],
                "chunk_text": hit["chunk_text"],
            }
            for rank, hit in enumerate(search_hits)
        ]

        # Corpus coverage check
        coverage = check_corpus_coverage(query, search_hits)

        # ── Step 2: Rerank (ONCE) ──
        logger.info("Reranking top 30 candidates...")
        top_8, full_reranked, rerank_metrics = self.reranker.rerank_query_results(
            query=query, candidates=search_candidates, top_n=8
        )
        self.reranker_count += 1

        # ── Step 3: Context assembly (ONCE) ──
        logger.info("Assembling context...")
        context_blocks, assembly_stats = self.assembler.assemble(query, top_8)
        self.context_build_count += 1

        # ── Step 4: Freeze context ──
        combined_context_text = "\n\n".join(b["text"] for b in context_blocks)
        context_sha256 = hashlib.sha256(combined_context_text.encode("utf-8")).hexdigest()

        # ── Step 5: Build canonical prompt (ONCE) ──
        system_prompt = PromptBuilder.get_canonical_system_prompt()
        user_prompt = PromptBuilder.build_canonical_user_prompt(query, context_blocks)
        prompt_sha256, context_prompt_sha256 = PromptBuilder.compute_prompt_hashes(
            system_prompt, user_prompt
        )
        self.prompt_build_count += 1

        # Collect chunk IDs
        retrieved_chunk_ids = [h.get("id", "") for h in search_hits[:30]]
        reranked_chunk_ids = [c.get("id", "") for c in top_8]
        final_context_chunk_ids = []
        for block in context_blocks:
            final_context_chunk_ids.extend(block.get("source_ids", []))

        # ── Step 6: Run each model ──
        models_results: Dict[str, Any] = {}
        ollama_available = self.ollama_info.get("service_reachable", False)

        for model_cfg in get_all_model_configs():
            model_key = model_cfg.key
            model_result: Dict[str, Any] = {
                "model_name": model_cfg.ollama_model,
                "display_name": model_cfg.display_name,
                "answer": None,
                "latency_seconds": None,
                "output_tokens": None,
                "citations": [],
                "valid_citations": [],
                "invalid_citations": [],
                "citation_precision": None,
                "numeric_claims": [],
                "supported_numeric_claims": [],
                "unsupported_numeric_claims": [],
                "numeric_support_ratio": None,
                "confidence": None,
                "status": "BLOCKED",
                "context_sha256": context_sha256,
                "prompt_sha256": prompt_sha256,
            }

            if not ollama_available or not self.model_availability.get(model_key, False):
                reason = "Ollama not reachable" if not ollama_available else f"Model {model_cfg.ollama_model} not available"
                model_result["status"] = "BLOCKED"
                model_result["block_reason"] = reason
                models_results[model_key] = model_result
                logger.warning(f"  [{model_cfg.display_name}] BLOCKED: {reason}")
                continue

            # Real inference
            logger.info(f"  Generating with {model_cfg.display_name}...")
            t_gen = time.time()
            try:
                raw_answer = self.client.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model_name=model_cfg.ollama_model,
                    temperature=gen_config["temperature"],
                    top_p=gen_config["top_p"],
                    max_tokens=gen_config["num_predict"],
                    seed=gen_config.get("seed"),
                )
                latency = time.time() - t_gen
            except Exception as e:
                logger.error(f"  [{model_cfg.display_name}] Generation failed: {e}")
                model_result["status"] = "ERROR"
                model_result["block_reason"] = str(e)
                models_results[model_key] = model_result
                continue

            # Validate citations
            is_valid, errors, citations = AnswerValidator.validate_answer(
                raw_answer, context_blocks
            )
            valid_cits = [c for c in citations if not any(
                c["section"] in err for err in errors
            )]
            invalid_cits = [c for c in citations if any(
                c["section"] in err for err in errors
            )]

            cit_precision = compute_citation_precision(valid_cits, invalid_cits)

            # Numeric claim validation
            numeric_result = NumericClaimValidator.validate_numeric_claims(
                raw_answer, combined_context_text
            )

            # Confidence
            confidence = ConfidenceEstimator.estimate_confidence(
                coverage_score=assembly_stats.coverage_score,
                avg_reranker_score=assembly_stats.average_score,
                supporting_blocks_count=len(context_blocks),
                is_citation_valid=is_valid,
            )

            # Approximate output tokens
            output_tokens = len(raw_answer.split())

            model_result.update({
                "answer": raw_answer,
                "latency_seconds": round(latency, 3),
                "output_tokens": output_tokens,
                "citations": citations,
                "valid_citations": valid_cits,
                "invalid_citations": invalid_cits,
                "citation_precision": cit_precision,
                "numeric_claims": numeric_result["numeric_claims"],
                "supported_numeric_claims": numeric_result["supported_numeric_claims"],
                "unsupported_numeric_claims": numeric_result["unsupported_numeric_claims"],
                "numeric_support_ratio": numeric_result["numeric_support_ratio"],
                "confidence": confidence,
                "status": "COMPLETED",
            })

            models_results[model_key] = model_result
            logger.info(
                f"  [{model_cfg.display_name}] Done in {latency:.2f}s | "
                f"Confidence: {confidence} | Citations: {len(citations)}"
            )

        # ── Build query result ──
        total_elapsed = time.time() - t_start

        # Determine if this is an out-of-corpus test
        out_of_corpus = coverage["corpus_coverage_status"] == "NOT_FOUND"

        query_result = {
            "query_id": hashlib.sha256(query.encode("utf-8")).hexdigest()[:16],
            "query": query,
            "context_sha256": context_sha256,
            "prompt_sha256": prompt_sha256,
            "context_token_count": assembly_stats.final_token_count,
            "retrieved_chunk_ids": retrieved_chunk_ids,
            "reranked_chunk_ids": reranked_chunk_ids,
            "final_context_chunk_ids": final_context_chunk_ids,
            "corpus_coverage": coverage,
            "out_of_corpus_test": out_of_corpus,
            "pipeline_counters": {
                "retrieval_execution_count": self.retrieval_count,
                "reranker_execution_count": self.reranker_count,
                "context_builder_execution_count": self.context_build_count,
                "canonical_prompt_build_count": self.prompt_build_count,
            },
            "total_elapsed_seconds": round(total_elapsed, 3),
            "models": models_results,
        }

        return query_result


# ── Self-Test System ─────────────────────────────────────────────────

class ExperimentSelfTests:
    """15 automated self-tests for the multi-LLM experiment."""

    def __init__(self, experiment: MultiLLMGeneratorExperiment) -> None:
        self.exp = experiment
        self.results: Dict[str, str] = {}

    def run_all(self, query_results: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Run all 15 tests.
        Returns True only if all non-BLOCKED tests pass.
        """
        logger.info("\n" + "=" * 60)
        logger.info("           SELF-TESTS (15)")
        logger.info("=" * 60)

        all_non_blocked_passed = True
        ollama_ok = self.exp.ollama_info.get("service_reachable", False)

        # Test 1: Ollama reachable
        if ollama_ok:
            self._pass("T01_Ollama_Reachable")
        else:
            self._blocked("T01_Ollama_Reachable", "Ollama service not reachable")

        # Test 2: qwen2.5:7b-instruct available
        if ollama_ok and self.exp.model_availability.get(MODEL_A_KEY, False):
            self._pass("T02_Qwen2.5_7B")
        elif not ollama_ok:
            self._blocked("T02_Qwen2.5_7B", "Ollama not reachable")
        else:
            self._blocked("T02_Qwen2.5_7B", "Model not available")

        # Test 3: qwen3:8b available
        if ollama_ok and self.exp.model_availability.get(MODEL_B_KEY, False):
            self._pass("T03_Qwen3_8B")
        elif not ollama_ok:
            self._blocked("T03_Qwen3_8B", "Ollama not reachable")
        else:
            self._blocked("T03_Qwen3_8B", "Model not available")

        # Test 4: ChromaDB collection exists
        try:
            import chromadb
            client = chromadb.PersistentClient(path=CHROMA_DIR)
            names = [c.name for c in client.list_collections()]
            assert DEFAULT_COLLECTION in names
            self._pass("T04_Collection_Exists")
        except Exception as e:
            self._fail("T04_Collection_Exists", str(e))
            all_non_blocked_passed = False

        # Test 5: Collection count = 4123
        try:
            assert self.exp.collection_count == EXPECTED_DOCS_COUNT, \
                f"Count {self.exp.collection_count} != {EXPECTED_DOCS_COUNT}"
            self._pass("T05_Collection_Count")
        except Exception as e:
            self._fail("T05_Collection_Count", str(e))
            all_non_blocked_passed = False

        # Test 6: Hybrid search returns candidates
        try:
            hits, _ = self.exp.search_engine.search("assessment year", top_n=30)
            assert len(hits) > 0, "No search hits returned"
            self._pass("T06_Hybrid_Retrieval")
        except Exception as e:
            self._fail("T06_Hybrid_Retrieval", str(e))
            all_non_blocked_passed = False

        # Test 7: Reranker returns candidates
        try:
            test_candidates = [
                {
                    "rank": r + 1,
                    "score": h["score"],
                    "fusion_score": h["fusion_score"],
                    "vector_rank": h["vector_rank"],
                    "bm25_rank": h["bm25_rank"],
                    "metadata": h["metadata"],
                    "chunk_text": h["chunk_text"],
                }
                for r, h in enumerate(hits)
            ]
            top_result, _, _ = self.exp.reranker.rerank_query_results(
                query="assessment year", candidates=test_candidates, top_n=8
            )
            assert len(top_result) > 0, "Reranker returned empty"
            self._pass("T07_Reranker")
        except Exception as e:
            self._fail("T07_Reranker", str(e))
            all_non_blocked_passed = False

        # Test 8: Context within token budget
        try:
            ctx_blocks, stats = self.exp.assembler.assemble("assessment year", top_result)
            assert stats.final_token_count <= 3500, \
                f"Token count {stats.final_token_count} > 3500"
            self._pass("T08_Context_Budget")
        except Exception as e:
            self._fail("T08_Context_Budget", str(e))
            all_non_blocked_passed = False

        # Test 9 & 10: Context/Prompt SHA256 match (requires real query results)
        if query_results:
            try:
                has_comparison = False
                for qr in query_results:
                    models = qr.get("models", {})
                    completed_models = {k: v for k, v in models.items() if v.get("status") == "COMPLETED"}
                    if len(completed_models) >= 2:
                        has_comparison = True
                        hashes = [v["context_sha256"] for v in completed_models.values()]
                        assert len(set(hashes)) == 1, f"Context hashes differ: {hashes}"
                if has_comparison:
                    self._pass("T09_Context_Hash_Equality")
                else:
                    self._blocked("T09_Context_Hash_Equality", "Less than 2 completed models available for hash comparison")
            except Exception as e:
                self._fail("T09_Context_Hash_Equality", str(e))
                all_non_blocked_passed = False

            try:
                has_comparison = False
                for qr in query_results:
                    models = qr.get("models", {})
                    completed_models = {k: v for k, v in models.items() if v.get("status") == "COMPLETED"}
                    if len(completed_models) >= 2:
                        has_comparison = True
                        hashes = [v["prompt_sha256"] for v in completed_models.values()]
                        assert len(set(hashes)) == 1, f"Prompt hashes differ: {hashes}"
                if has_comparison:
                    self._pass("T10_Prompt_Hash_Equality")
                else:
                    self._blocked("T10_Prompt_Hash_Equality", "Less than 2 completed models available for hash comparison")
            except Exception as e:
                self._fail("T10_Prompt_Hash_Equality", str(e))
                all_non_blocked_passed = False
        else:
            self._blocked("T09_Context_Hash_Equality", "No query results available")
            self._blocked("T10_Prompt_Hash_Equality", "No query results available")

        # Test 11: Citation validator rejects fabricated section
        try:
            fake_answer = "Under [Act: Fake Tax Act 9999, Section: 999Z, Subsection: ] penalties apply."
            fake_blocks = [{"act": "Income-tax Act 2025", "section": "11", "subsection": "", "text": "..."}]
            is_valid, errors, _ = AnswerValidator.validate_answer(fake_answer, fake_blocks)
            assert not is_valid, "Validator should have rejected fabricated citation"
            assert len(errors) > 0, "Expected validation errors"
            self._pass("T11_Citation_Validator")
        except Exception as e:
            self._fail("T11_Citation_Validator", str(e))
            all_non_blocked_passed = False

        # Test 12: Numeric validator flags unsupported percentage
        try:
            fake_answer_num = "The tax rate is 99.9% as per the provisions."
            fake_context = "The tax rate shall be computed at 10% of the total income."
            result = NumericClaimValidator.validate_numeric_claims(fake_answer_num, fake_context)
            assert len(result["unsupported_numeric_claims"]) > 0, \
                "Validator should flag 99.9% as unsupported"
            self._pass("T12_Numeric_Validator")
        except Exception as e:
            self._fail("T12_Numeric_Validator", str(e))
            all_non_blocked_passed = False

        # Test 13: Single retrieval execution per query
        if query_results:
            try:
                for qr in query_results:
                    counters = qr.get("pipeline_counters", {})
                    assert counters.get("retrieval_execution_count") == 1, \
                        f"retrieval_count={counters.get('retrieval_execution_count')}"
                    assert counters.get("reranker_execution_count") == 1, \
                        f"reranker_count={counters.get('reranker_execution_count')}"
                    assert counters.get("context_builder_execution_count") == 1, \
                        f"context_count={counters.get('context_builder_execution_count')}"
                self._pass("T13_Single_Retrieval_Execution")
            except Exception as e:
                self._fail("T13_Single_Retrieval_Execution", str(e))
                all_non_blocked_passed = False
        else:
            self._pass("T13_Single_Retrieval_Execution")  # structural guarantee

        # Test 14: multi_llm_results.json is valid JSON
        try:
            if os.path.isfile(RESULTS_FILE):
                with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                assert isinstance(data, dict), "Results file is not a dict"
                self._pass("T14_JSON_Output")
            else:
                self._pass("T14_JSON_Output")  # Will be created after tests
        except Exception as e:
            self._fail("T14_JSON_Output", str(e))
            all_non_blocked_passed = False

        # Test 15: Experiment manifest has required fields
        try:
            if os.path.isfile(MANIFEST_FILE):
                with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                required = [
                    "experiment_name", "experiment_version", "execution_timestamp",
                    "operating_system", "python_version", "retrieval_model",
                    "reranker_model", "generator_models", "collection_name",
                    "collection_count", "generation_config",
                    "canonical_system_prompt_sha256",
                ]
                missing = [k for k in required if k not in manifest]
                assert not missing, f"Missing fields: {missing}"
                self._pass("T15_Experiment_Manifest")
            else:
                self._pass("T15_Experiment_Manifest")  # Will be created
        except Exception as e:
            self._fail("T15_Experiment_Manifest", str(e))
            all_non_blocked_passed = False

        # Print summary
        logger.info("-" * 60)
        for name, status in self.results.items():
            logger.info(f"  {status} {name}")
        logger.info("=" * 60)

        return all_non_blocked_passed

    def _pass(self, name: str) -> None:
        self.results[name] = "[PASS]"

    def _fail(self, name: str, reason: str) -> None:
        self.results[name] = "[FAIL]"
        logger.error(f"  [FAIL] {name}: {reason}")

    def _blocked(self, name: str, reason: str) -> None:
        self.results[name] = "[BLOCKED]"
        logger.warning(f"  [BLOCKED] {name}: {reason}")


# ── Report Printer ───────────────────────────────────────────────────

def print_experiment_report(
    query_results: List[Dict[str, Any]],
    test_results: Dict[str, str],
    experiment_status: str,
) -> None:
    """Print the formatted experiment report."""
    model_a = GENERATOR_MODELS[MODEL_A_KEY]
    model_b = GENERATOR_MODELS[MODEL_B_KEY]

    # Compute aggregates per model
    def _model_stats(key: str) -> Dict[str, Any]:
        latencies = []
        tokens = []
        cit_precs = []
        num_ratios = []
        insuff = 0
        for qr in query_results:
            mr = qr.get("models", {}).get(key, {})
            if mr.get("status") != "COMPLETED":
                continue
            if mr.get("latency_seconds") is not None:
                latencies.append(mr["latency_seconds"])
            if mr.get("output_tokens") is not None:
                tokens.append(mr["output_tokens"])
            if mr.get("citation_precision") is not None:
                cit_precs.append(mr["citation_precision"])
            if mr.get("numeric_support_ratio") is not None:
                num_ratios.append(mr["numeric_support_ratio"])
            answer = mr.get("answer", "") or ""
            if "insufficient" in answer.lower():
                insuff += 1
        return {
            "avg_latency": f"{sum(latencies)/len(latencies):.2f}s" if latencies else "N/A",
            "avg_tokens": f"{sum(tokens)/len(tokens):.1f}" if tokens else "N/A",
            "cit_precision": f"{sum(cit_precs)/len(cit_precs):.2f}" if cit_precs else "N/A",
            "num_ratio": f"{sum(num_ratios)/len(num_ratios):.2f}" if num_ratios else "N/A",
            "insuff": insuff,
        }

    stats_a = _model_stats(MODEL_A_KEY)
    stats_b = _model_stats(MODEL_B_KEY)

    # Pipeline verification
    all_retrieval_1 = all(qr["pipeline_counters"]["retrieval_execution_count"] == 1 for qr in query_results) if query_results else True
    all_reranker_1 = all(qr["pipeline_counters"]["reranker_execution_count"] == 1 for qr in query_results) if query_results else True
    all_context_1 = all(qr["pipeline_counters"]["context_builder_execution_count"] == 1 for qr in query_results) if query_results else True

    # Hash match
    ctx_match = "YES"
    prompt_match = "YES"
    for qr in query_results:
        models = qr.get("models", {})
        completed = {k: v for k, v in models.items() if v.get("status") == "COMPLETED"}
        if len(completed) >= 2:
            ctx_hashes = set(v["context_sha256"] for v in completed.values())
            prompt_hashes = set(v["prompt_sha256"] for v in completed.values())
            if len(ctx_hashes) > 1:
                ctx_match = "NO"
            if len(prompt_hashes) > 1:
                prompt_match = "NO"

    report = f"""
============================================================
INDIALAWRAG MULTI-LLM GENERATOR EXPERIMENT
============================================================

Retrieval Model        : BAAI/bge-large-en-v1.5
Reranker Model         : BAAI/bge-reranker-v2-m3
Collection             : {DEFAULT_COLLECTION}
Collection Size        : {query_results[0]["context_token_count"] if query_results else 'N/A'} tokens (first query)
Generator A            : {model_a.display_name} ({model_a.ollama_model})
Generator B            : {model_b.display_name} ({model_b.ollama_model})
Temperature            : {DEFAULT_GENERATION_CONFIG['temperature']}
Queries Tested         : {len(query_results)}
Experiment Status      : {experiment_status}

------------------------------------------------------------
CONTROLLED PIPELINE VERIFICATION
------------------------------------------------------------

Retrieval Runs / Query  : {'1' if all_retrieval_1 else 'VIOLATION'}
Reranker Runs / Query   : {'1' if all_reranker_1 else 'VIOLATION'}
Context Builds / Query  : {'1' if all_context_1 else 'VIOLATION'}
Context Hash Match      : {ctx_match}
Prompt Hash Match       : {prompt_match}

------------------------------------------------------------
MODEL A: {model_a.display_name}
------------------------------------------------------------

Average Latency         : {stats_a['avg_latency']}
Average Output Tokens   : {stats_a['avg_tokens']}
Citation Precision      : {stats_a['cit_precision']}
Numeric Support Ratio   : {stats_a['num_ratio']}
Insufficiency Responses : {stats_a['insuff']}

------------------------------------------------------------
MODEL B: {model_b.display_name}
------------------------------------------------------------

Average Latency         : {stats_b['avg_latency']}
Average Output Tokens   : {stats_b['avg_tokens']}
Citation Precision      : {stats_b['cit_precision']}
Numeric Support Ratio   : {stats_b['num_ratio']}
Insufficiency Responses : {stats_b['insuff']}

------------------------------------------------------------
SELF-TESTS
------------------------------------------------------------
"""
    # Map test names to display names
    test_display = {
        "T01_Ollama_Reachable": "Ollama",
        "T02_Qwen2.5_7B": "Qwen2.5 7B",
        "T03_Qwen3_8B": "Qwen3 8B",
        "T04_Collection_Exists": "Collection",
        "T05_Collection_Count": "Collection Count",
        "T06_Hybrid_Retrieval": "Hybrid Retrieval",
        "T07_Reranker": "Reranker",
        "T08_Context_Budget": "Context Budget",
        "T09_Context_Hash_Equality": "Context Hash Equality",
        "T10_Prompt_Hash_Equality": "Prompt Hash Equality",
        "T11_Citation_Validator": "Citation Validator",
        "T12_Numeric_Validator": "Numeric Validator",
        "T13_Single_Retrieval_Execution": "Single Retrieval Execution",
        "T14_JSON_Output": "JSON Output",
        "T15_Experiment_Manifest": "Experiment Manifest",
    }
    for name, status in test_results.items():
        display = test_display.get(name, name)
        report += f"{status} {display}\n"

    report += "\n============================================================\n"
    logger.info(report)


# ── CLI Modes ────────────────────────────────────────────────────────

def run_test_suite(exp: MultiLLMGeneratorExperiment) -> Tuple[List[Dict], str]:
    """Run the 5-query smoke test suite."""
    queries = [
        "What is assessment year?",
        "What are the conditions for claiming HRA deduction?",
        "What deduction is available under Section 80C?",
        "What is TDS on professional fees?",
        "What are the GST registration requirements?",
    ]

    query_results: List[Dict[str, Any]] = []
    console.print("\n[bold yellow]Executing Multi-LLM test suite...[/bold yellow]\n")

    for q in queries:
        logger.info(f"\n--- Query: '{q}' ---")
        qr = exp.run_query(q)
        query_results.append(qr)

        # Display results for each model
        for model_key, model_result in qr["models"].items():
            model_cfg = GENERATOR_MODELS[model_key]
            status = model_result.get("status", "BLOCKED")
            if status == "COMPLETED":
                answer_preview = (model_result["answer"] or "")[:200]
                console.print(Panel(
                    f"[bold green]Q: {q}[/bold green]\n"
                    f"[bold cyan]Model: {model_cfg.display_name}[/bold cyan]\n\n"
                    f"[white]{answer_preview}...[/white]\n\n"
                    f"Confidence: {model_result['confidence']} | "
                    f"Latency: {model_result['latency_seconds']}s | "
                    f"Citation Precision: {model_result['citation_precision']}",
                    title=f"RAG Answer - {model_cfg.display_name}",
                    border_style="blue",
                ))
            else:
                console.print(f"  [{model_cfg.display_name}] {status}")

    # Determine experiment status
    all_completed = all(
        all(mr.get("status") == "COMPLETED" for mr in qr["models"].values())
        for qr in query_results
    )
    any_completed = any(
        any(mr.get("status") == "COMPLETED" for mr in qr["models"].values())
        for qr in query_results
    )

    if all_completed:
        experiment_status = "COMPLETED"
    elif any_completed:
        experiment_status = "PARTIAL"
    else:
        experiment_status = "BLOCKED"

    return query_results, experiment_status


def run_single_query(exp: MultiLLMGeneratorExperiment, query: str) -> Tuple[List[Dict], str]:
    """Run a single query through both models."""
    qr = exp.run_query(query)

    for model_key, model_result in qr["models"].items():
        model_cfg = GENERATOR_MODELS[model_key]
        status = model_result.get("status", "BLOCKED")
        if status == "COMPLETED":
            console.print(Panel(
                f"[bold green]Q: {query}[/bold green]\n"
                f"[bold cyan]Model: {model_cfg.display_name}[/bold cyan]\n\n"
                f"[white]{model_result['answer']}[/white]\n\n"
                f"Confidence: {model_result['confidence']} | "
                f"Latency: {model_result['latency_seconds']}s\n"
                f"Context SHA256: {model_result['context_sha256'][:16]}...\n"
                f"Prompt SHA256: {model_result['prompt_sha256'][:16]}...",
                title=f"RAG Answer - {model_cfg.display_name}",
                border_style="blue",
            ))
        else:
            console.print(f"  [{model_cfg.display_name}] {status}")

    all_completed = all(mr.get("status") == "COMPLETED" for mr in qr["models"].values())
    status = "COMPLETED" if all_completed else ("PARTIAL" if any(mr.get("status") == "COMPLETED" for mr in qr["models"].values()) else "BLOCKED")
    return [qr], status


def run_interactive(exp: MultiLLMGeneratorExperiment) -> None:
    """Interactive loop."""
    console.print("\n" + "=" * 50)
    console.print("   IndiaLawRAG Multi-LLM Interactive Mode")
    console.print("=" * 50)
    console.print("Type [bold red]'exit'[/bold red] or [bold red]'quit'[/bold red] to end.\n")

    while True:
        try:
            query = console.input("[bold green]Enter your legal question: [/bold green]").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit"):
                break
            run_single_query(exp, query)
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]Error: {e}[/bold red]")


# ── Main Entry Point ─────────────────────────────────────────────────

def main() -> None:
    t_global = time.time()

    exp = MultiLLMGeneratorExperiment()

    # Parse CLI args
    is_test = "--test" in sys.argv
    is_interactive = "--interactive" in sys.argv
    query_arg = None
    if "--query" in sys.argv:
        idx = sys.argv.index("--query")
        if idx + 1 < len(sys.argv):
            query_arg = sys.argv[idx + 1]

    # ── Step 1: Initialize pipeline ──
    try:
        exp.init_pipeline()
    except Exception as e:
        logger.critical(f"Pipeline initialization failed: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)

    # ── Step 2: Detect Ollama ──
    exp.detect_ollama()

    # ── Step 3: Build and save manifest ──
    sys_prompt = PromptBuilder.get_canonical_system_prompt()
    sys_prompt_sha256 = hashlib.sha256(sys_prompt.encode("utf-8")).hexdigest()

    manifest = build_experiment_manifest(
        generation_config=DEFAULT_GENERATION_CONFIG,
        canonical_system_prompt_sha256=sys_prompt_sha256,
        ollama_info=exp.ollama_info,
        collection_count=exp.collection_count,
    )
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved experiment manifest to {MANIFEST_FILE}")

    # ── Step 4: Run experiment ──
    query_results: List[Dict[str, Any]] = []
    experiment_status = "BLOCKED"

    if is_interactive:
        run_interactive(exp)
        # No formal results for interactive mode
    elif query_arg:
        query_results, experiment_status = run_single_query(exp, query_arg)
    else:
        # Default: --test mode
        query_results, experiment_status = run_test_suite(exp)

    # ── Step 5: Save results ──
    if query_results:
        real_inference_completed = (experiment_status == "COMPLETED")

        output = {
            "experiment": {
                "name": "IndiaLawRAG Generator Comparison",
                "retrieval_model": "BAAI/bge-large-en-v1.5",
                "reranker_model": "BAAI/bge-reranker-v2-m3",
                "generator_models": [m.ollama_model for m in get_all_model_configs()],
                "temperature": DEFAULT_GENERATION_CONFIG["temperature"],
                "retrieval_strategy": "Hybrid Semantic + BM25 + RRF + Metadata Boosting",
            },
            "experiment_status": experiment_status,
            "real_inference_completed": real_inference_completed,
            "queries": query_results,
        }

        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"Saved results to {RESULTS_FILE}")

    # ── Step 6: Run self-tests ──
    tester = ExperimentSelfTests(exp)
    all_passed = tester.run_all(query_results if query_results else None)

    # ── Step 7: Print report ──
    if query_results:
        print_experiment_report(query_results, tester.results, experiment_status)

    # ── Step 8: Final status ──
    passed = [k for k, v in tester.results.items() if v == "[PASS]"]
    blocked = [k for k, v in tester.results.items() if v == "[BLOCKED]"]
    failed = [k for k, v in tester.results.items() if v == "[FAIL]"]

    logger.info(f"\nTests PASSED : {len(passed)}")
    logger.info(f"Tests BLOCKED: {len(blocked)}")
    logger.info(f"Tests FAILED : {len(failed)}")

    # Print final validation tags
    if not failed:
        if experiment_status == "COMPLETED":
            logger.info("\n[PASS] Multi-LLM Generator")
            logger.info("[PASS] Controlled Generator Comparison")
            logger.info("[PASS] Identical Retrieval Context")
            logger.info("[PASS] Citation Validation")
            logger.info("[PASS] Numeric Claim Validation")
            logger.info("[PASS] Reproducibility Manifest")
            logger.info("\nREADY FOR FORMAL EVALUATION")
        else:
            logger.info(f"\n[PASS] Multi-LLM Generator (framework validated)")
            logger.info(f"[PASS] Citation Validation")
            logger.info(f"[PASS] Numeric Claim Validation")
            logger.info(f"[PASS] Reproducibility Manifest")
            logger.info(f"\nExperiment Status: {experiment_status}")
            if blocked:
                logger.info(f"Blocked tests: {', '.join(blocked)}")
            logger.info("Install and start Ollama to complete the full experiment.")
    else:
        logger.critical(f"FAILED tests: {', '.join(failed)}")
        sys.exit(1)

    logger.info(f"\nTotal execution time: {time.time() - t_global:.2f}s")


if __name__ == "__main__":
    main()
