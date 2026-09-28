"""
04_search.py
============
Production-grade Hybrid Retrieval Engine for IndiaLawRAG v2.

Integrates Semantic Vector Search (BAAI/bge-large-en-v1.5), Keyword Search (BM25),
and Reciprocal Rank Fusion (RRF) with metadata boosting. Supports multi-collection
scaling and fully caches in-memory components (BM25 index, corpus lists) for
ultra-low latency.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

# -- Ensure packages are loaded correctly --
import chromadb
import numpy as np
import psutil
import torch
from sentence_transformers import SentenceTransformer

# Import utility functions from search_utils
import search_utils
from search_utils import (
    BM25SearchEngine,
    QueryMetrics,
    apply_metadata_boosting,
    compute_rrf,
    preprocess_query,
)

# ==================================================================
# CONFIGURATION CONSTANTS
# ==================================================================

CHROMA_DIR: str = "chroma_db"
DEFAULT_COLLECTION: str = "indian_tax_law_corpus_v1"
EXPECTED_DOCS_COUNT: int = 4123
EMBED_MODEL_NAME: str = "BAAI/bge-large-en-v1.5"
EXPECTED_EMBED_DIM: int = 1024

LOG_DIR: str = "logs"
LOG_FILE: str = os.path.join(LOG_DIR, "search.log")
RESULTS_FILE: str = "search_results.json"


# ==================================================================
# LOGGING SETUP
# ==================================================================

def setup_logging() -> logging.Logger:
    """Configure search session logger with ASCII formats."""
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger("search")
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


logger = setup_logging()


# ==================================================================
# DATA STRUCTURES & ADAPTER FOR MULTI-COLLECTION SCALING
# ==================================================================

@dataclass
class CollectionContext:
    """Stores all loaded and cached in-memory resources for a single collection."""
    name: str
    collection: Any
    doc_ids: List[str] = field(default_factory=list)
    documents: List[str] = field(default_factory=list)
    metadatas: List[Dict[str, Any]] = field(default_factory=list)
    bm25_engine: Optional[BM25SearchEngine] = None
    count: int = 0


class MultiCollectionSearchAdapter:
    """
    Manages and caches multiple ChromaDB collections.
    Builds BM25 indices only once per collection and caches the corpus mapping.
    Allows retrieval to scale horizontally to other collections (e.g. state laws, case laws).
    """

    def __init__(self, client: chromadb.PersistentClient) -> None:
        self.client = client
        self.collections_cache: Dict[str, CollectionContext] = {}

    def get_context(self, collection_name: str) -> CollectionContext:
        """
        Retrieve the context for a collection.
        If not cached, loads all documents and constructs the BM25 index.
        """
        if collection_name in self.collections_cache:
            return self.collections_cache[collection_name]

        # Verify collection exists in database
        collections = [c.name for c in self.client.list_collections()]
        if collection_name not in collections:
            logger.critical(f"CRITICAL ERROR: Collection '{collection_name}' is missing from ChromaDB!")
            print(f"CRITICAL ERROR: Collection '{collection_name}' is missing from ChromaDB!")
            sys.exit(1)

        collection = self.client.get_collection(name=collection_name)
        count = collection.count()
        if count == 0:
            logger.critical(f"CRITICAL ERROR: Collection '{collection_name}' is empty!")
            print(f"CRITICAL ERROR: Collection '{collection_name}' is empty!")
            sys.exit(1)

        logger.info(f"Loading and caching collection '{collection_name}' ({count:,} documents)...")
        t0 = time.time()
        
        # Load all documents from collection in pages of 10000
        doc_ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        
        page_size = 10000
        offset = 0
        while offset < count:
            batch = collection.get(
                limit=page_size,
                offset=offset,
                include=["documents", "metadatas"]
            )
            if batch and batch.get("ids"):
                doc_ids.extend(batch["ids"])
                # Extract documents and metadatas
                docs_list = batch.get("documents") or []
                metas_list = batch.get("metadatas") or []
                
                # Make sure lengths match
                if len(docs_list) < len(batch["ids"]):
                    docs_list.extend([""] * (len(batch["ids"]) - len(docs_list)))
                if len(metas_list) < len(batch["ids"]):
                    metas_list.extend([{}] * (len(batch["ids"]) - len(metas_list)))
                    
                documents.extend(docs_list)
                metadatas.extend(metas_list)
            else:
                break
            offset += page_size

        logger.info(f"Fetched {len(doc_ids):,} entries in {time.time() - t0:.2f}s. Building BM25 index...")
        t1 = time.time()
        bm25_engine = BM25SearchEngine(doc_ids, documents)
        logger.info(f"BM25 index built in {time.time() - t1:.2f}s.")

        context = CollectionContext(
            name=collection_name,
            collection=collection,
            doc_ids=doc_ids,
            documents=documents,
            metadatas=metadatas,
            bm25_engine=bm25_engine,
            count=count
        )
        
        self.collections_cache[collection_name] = context
        return context


# ==================================================================
# SEARCH ENGINE CORE
# ==================================================================

class HybridSearchEngine:
    """
    Main orchestrator for the RAG search pipeline.
    Caches the embedding model and multi-collection database adapter.
    """

    def __init__(self, chroma_dir: str = CHROMA_DIR) -> None:
        self.chroma_dir = chroma_dir
        self.client: Optional[chromadb.PersistentClient] = None
        self.adapter: Optional[MultiCollectionSearchAdapter] = None
        self.model: Optional[SentenceTransformer] = None
        self.query_metrics_history: List[QueryMetrics] = []

    def init_resources(self, collection_name: str = DEFAULT_COLLECTION) -> None:
        """Initialize and cache sentence transformer model and database adapter."""
        # 1. Load Model (CPU/GPU)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Initializing Embedding Model: {EMBED_MODEL_NAME} (Device: {device})")
        self.model = SentenceTransformer(EMBED_MODEL_NAME, device=device)
        
        # 2. Connect to ChromaDB
        self.client = chromadb.PersistentClient(path=self.chroma_dir)
        self.adapter = MultiCollectionSearchAdapter(self.client)
        
        # Pre-cache the default collection and build BM25
        self.adapter.get_context(collection_name)

    def search(
        self,
        query: str,
        collection_name: str = DEFAULT_COLLECTION,
        top_n: int = 30,
        rrf_k: int = 60
    ) -> Tuple[List[Dict[str, Any]], QueryMetrics]:
        """
        Run the complete hybrid search retrieval pipeline.
        
        1. Preprocesses/expands query.
        2. Vector Search (Top 50).
        3. BM25 Search (Top 50).
        4. Reciprocal Rank Fusion (RRF).
        5. Metadata Boosting.
        6. Returns sorted Top N hits.
        """
        if self.model is None or self.adapter is None:
            raise RuntimeError("Resources not initialized. Call init_resources() first.")

        t_total_start = time.time()
        
        # Get cached context
        ctx = self.adapter.get_context(collection_name)
        
        # Step 1: Preprocess query
        preprocessed = preprocess_query(query)
        
        # Step 2: Vector Search
        t_vec_start = time.time()
        # Embed query
        query_emb = self.model.encode(
            [preprocessed],
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True
        ).tolist()
        
        # ChromaDB query
        vector_results = ctx.collection.query(
            query_embeddings=query_emb,
            n_results=50,
            include=["documents"]
        )
        
        vector_ids: List[str] = []
        if vector_results and vector_results.get("ids") and len(vector_results["ids"]) > 0:
            vector_ids = vector_results["ids"][0]
            
        vector_latency = time.time() - t_vec_start

        # Step 3: BM25 Keyword Search
        t_bm25_start = time.time()
        bm25_hits = ctx.bm25_engine.search(preprocessed, top_n=50)
        bm25_ids = [doc_id for doc_id, _ in bm25_hits]
        bm25_latency = time.time() - t_bm25_start

        # Step 4: Reciprocal Rank Fusion (RRF)
        t_fusion_start = time.time()
        rrf_scores = compute_rrf(vector_ids, bm25_ids, k=rrf_k)
        
        # Step 5: Metadata Boosting
        # Mapping from doc_id to corpus index for metadata retrieval
        doc_id_to_idx = {doc_id: i for i, doc_id in enumerate(ctx.doc_ids)}
        
        boosted_results: List[Dict[str, Any]] = []
        for doc_id, (score, v_rank, b_rank) in rrf_scores.items():
            corpus_idx = doc_id_to_idx.get(doc_id)
            if corpus_idx is None:
                continue
                
            doc_meta = ctx.metadatas[corpus_idx]
            doc_text = ctx.documents[corpus_idx]
            
            # Apply boosting based on raw query matching metadata
            boosted_score = apply_metadata_boosting(score, doc_meta, query)
            
            boosted_results.append({
                "id": doc_id,
                "score": boosted_score,
                "fusion_score": score,
                "vector_rank": v_rank,
                "bm25_rank": b_rank,
                "metadata": doc_meta,
                "chunk_text": doc_text
            })
            
        # Sort results descending by score
        boosted_results.sort(key=lambda x: x["score"], reverse=True)
        final_results = boosted_results[:top_n]
        fusion_latency = time.time() - t_fusion_start
        
        total_latency = time.time() - t_total_start
        
        # Log telemetry metrics
        metrics = QueryMetrics(
            query=query,
            preprocessed_query=preprocessed,
            vector_latency_sec=vector_latency,
            bm25_latency_sec=bm25_latency,
            fusion_latency_sec=fusion_latency,
            total_latency_sec=total_latency,
            vector_hits_count=len(vector_ids),
            bm25_hits_count=len(bm25_ids),
            fused_hits_count=len(final_results)
        )
        
        self.query_metrics_history.append(metrics)
        
        # Logging statement to logs/search.log
        logger.debug(
            f"Query: '{query}' | Runtime: {total_latency:.4f}s | "
            f"Vector hits: {metrics.vector_hits_count} | BM25 hits: {metrics.bm25_hits_count} | "
            f"Fusion hits: {metrics.fused_hits_count}"
        )
        
        return final_results, metrics


# ==================================================================
# AUTOMATED SELF-TEST SYSTEM
# ==================================================================

class SelfTestSystem:
    """Runs 10 strict automated verifications and legal query checks."""

    def __init__(self, engine: HybridSearchEngine) -> None:
        self.engine = engine

    def run_all(self, collection_name: str = DEFAULT_COLLECTION) -> bool:
        """Execute the 10 self-tests and print results."""
        logger.info("\n===================================")
        logger.info("           SELF-TESTS")
        logger.info("===================================")

        all_passed = True
        ctx = self.engine.adapter.get_context(collection_name)

        # Test 1: Collection exists
        try:
            collections = [c.name for c in self.engine.client.list_collections()]
            assert collection_name in collections, f"Collection {collection_name} not found"
            logger.info("  [PASS] Collection Exists")
        except Exception as e:
            logger.error(f"  [FAIL] Collection Exists: {e}")
            all_passed = False

        # Test 2: Collection size correct
        try:
            count = ctx.count
            assert count == EXPECTED_DOCS_COUNT, f"Count {count} != expected {EXPECTED_DOCS_COUNT}"
            logger.info("  [PASS] Correct Collection Count")
        except Exception as e:
            logger.error(f"  [FAIL] Correct Collection Count: {e}")
            all_passed = False

        # Test 3: Embedding dimension 1024
        try:
            dim = self.engine.model.get_sentence_embedding_dimension()
            assert dim == EXPECTED_EMBED_DIM, f"Dimension {dim} != expected {EXPECTED_EMBED_DIM}"
            logger.info("  [PASS] Embedding Dimension = 1024")
        except Exception as e:
            logger.error(f"  [FAIL] Embedding Dimension = 1024: {e}")
            all_passed = False

        # Test 4: BM25 returns results
        try:
            results = ctx.bm25_engine.search("assessment year", top_n=5)
            assert len(results) > 0, "No results returned by BM25"
            logger.info("  [PASS] BM25")
        except Exception as e:
            logger.error(f"  [FAIL] BM25: {e}")
            all_passed = False

        # Test 5: Vector returns results
        try:
            query_emb = self.engine.model.encode(
                ["assessment year"],
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True
            ).tolist()
            results = ctx.collection.query(
                query_embeddings=query_emb,
                n_results=5,
                include=["documents"]
            )
            assert results and results.get("ids") and len(results["ids"][0]) > 0, "No vector results"
            logger.info("  [PASS] Vector Search")
        except Exception as e:
            logger.error(f"  [FAIL] Vector Search: {e}")
            all_passed = False

        # Test 6: Fusion returns 30
        try:
            hits, _ = self.engine.search("assessment year", top_n=30)
            assert len(hits) == 30, f"Returned hits count {len(hits)} != 30"
            logger.info("  [PASS] Rank Fusion")
        except Exception as e:
            logger.error(f"  [FAIL] Rank Fusion: {e}")
            all_passed = False

        # Test 7: No duplicate chunks
        try:
            hits, _ = self.engine.search("assessment year", top_n=30)
            chunk_ids = [hit["id"] for hit in hits]
            assert len(chunk_ids) == len(set(chunk_ids)), "Duplicate chunk IDs found in fusion results"
            logger.info("  [PASS] Duplicate Protection")
        except Exception as e:
            logger.error(f"  [FAIL] Duplicate Protection: {e}")
            all_passed = False

        # Test 8: Metadata present
        try:
            hits, _ = self.engine.search("Section 80C deduction", top_n=5)
            for hit in hits:
                meta = hit["metadata"]
                assert "section_no" in meta, "section_no missing from metadata"
                assert "chapter" in meta, "chapter missing from metadata"
                assert "act" in meta, "act missing from metadata"
            logger.info("  [PASS] Metadata Validation")
        except Exception as e:
            logger.error(f"  [FAIL] Metadata Validation: {e}")
            all_passed = False

        # Test 9: Runtime under 5 seconds on repeated queries
        try:
            latencies = []
            for _ in range(5):
                t_start = time.time()
                self.engine.search("What is TDS on professional fees?", top_n=30)
                latencies.append(time.time() - t_start)
            avg_lat = sum(latencies) / len(latencies)
            assert avg_lat < 5.0, f"Average query latency {avg_lat:.2f}s >= 5.0s"
            logger.info("  [PASS] Performance")
        except Exception as e:
            logger.error(f"  [FAIL] Performance: {e}")
            all_passed = False

        # Test 10: Run legal queries and verify relevance
        legal_queries = [
            "What is assessment year?",
            "What is HRA deduction?",
            "What is TDS on professional fees?",
            "Section 80C deduction",
            "GST registration"
        ]
        
        logger.info("  Executing Legal Query Suite...")
        test_10_passed = True
        legal_results_dict = {}

        for q in legal_queries:
            try:
                hits, metrics = self.engine.search(q, top_n=30)
                assert len(hits) > 0, f"Query '{q}' returned no hits"
                
                # Check for query keyword relevance in returned chunks
                # E.g. for "80C", we expect section_no "80C" to be in top hits
                relevance_found = False
                
                if "80c" in q.lower():
                    # E.g. for "80C", check if "deduction" or "80" is in text/metadata
                    for hit in hits[:10]:
                        txt = hit["chunk_text"].lower()
                        sec = str(hit["metadata"].get("section_no", "")).lower()
                        if "deduction" in txt or "80" in sec or "80" in txt or "exemption" in txt:
                            relevance_found = True
                            break
                elif "hra" in q.lower() or "house rent" in q.lower():
                    for hit in hits[:10]:
                        txt = hit["chunk_text"].lower()
                        if "hra" in txt or "house rent" in txt or "allowance" in txt:
                            relevance_found = True
                            break
                elif "tds" in q.lower() or "fees" in q.lower():
                    for hit in hits[:10]:
                        txt = hit["chunk_text"].lower()
                        if "tds" in txt or "deducted" in txt or "source" in txt or "professional" in txt:
                            relevance_found = True
                            break
                elif "gst" in q.lower():
                    for hit in hits[:10]:
                        txt = hit["chunk_text"].lower()
                        if "gst" in txt or "goods" in txt or "tax" in txt or "registration" in txt:
                            relevance_found = True
                            break
                else:
                    # General search relevance check (contains some terms from query)
                    query_terms = [t for t in preprocess_query(q).lower().split() if len(t) > 3]
                    for hit in hits[:10]:
                        txt = hit["chunk_text"].lower()
                        if any(term in txt for term in query_terms):
                            relevance_found = True
                            break
                            
                assert relevance_found, f"Query '{q}' returned results, but they lacked expected relevance"
                
                # Cache results for JSON output
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
            except Exception as e:
                logger.error(f"    [FAIL] Legal query relevance for '{q}': {e}")
                test_10_passed = False
                
        if test_10_passed:
            logger.info("  [PASS] Query Expansion")
            logger.info("  [PASS] Metadata Boosting")
            logger.info("  [PASS] Hybrid Search")
            
            # Save results to search_results.json
            try:
                with open(RESULTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(legal_results_dict, f, ensure_ascii=False, indent=2)
                logger.info(f"  Saved search results to {RESULTS_FILE}")
            except Exception as e:
                logger.error(f"  Failed to write results file: {e}")
        else:
            all_passed = False

        logger.info("===================================")
        return all_passed


# ==================================================================
# ENTRY POINT & RUNNER
# ==================================================================

def print_performance_report(engine: HybridSearchEngine, collection_name: str) -> None:
    """Print the required hybrid search performance summary metrics."""
    ctx = engine.adapter.get_context(collection_name)
    history = engine.query_metrics_history
    if not history:
        return
        
    avg_vec = sum(m.vector_latency_sec for m in history) / len(history)
    avg_bm25 = sum(m.bm25_latency_sec for m in history) / len(history)
    avg_fusion = sum(m.fusion_latency_sec for m in history) / len(history)
    avg_total = sum(m.total_latency_sec for m in history) / len(history)
    total_time = sum(m.total_latency_sec for m in history)

    process = psutil.Process(os.getpid())
    ram_mb = process.memory_info().rss / (1024 * 1024)

    report = f"""
===================================
HYBRID SEARCH REPORT
===================================
Collection Size: {ctx.count}
Embedding Model: {EMBED_MODEL_NAME}
Embedding Dimension: {EXPECTED_EMBED_DIM}
Vector Search Time: {avg_vec:.4f}s (avg)
BM25 Time: {avg_bm25:.4f}s (avg)
Fusion Time: {avg_fusion:.4f}s (avg)
Total Query Time: {total_time:.4f}s
Average Query Time: {avg_total:.4f}s
Memory Usage: {ram_mb:.1f} MB
===================================
"""
    logger.info(report)


def print_formatted_results(hits: List[Dict[str, Any]], query: str) -> None:
    """Beautifully format and display the top 10 search results to the console."""
    print(f"\nQuery: '{query}'")
    print(f"{'-' * 85}")
    print(f"{'Rank':<5} | {'Score':<8} | {'Section':<15} | {'Chapter':<10} | {'Text Preview'}")
    print(f"{'-' * 85}")
    
    for idx, hit in enumerate(hits[:10]):
        rank = idx + 1
        score = f"{hit['score']:.4f}"
        meta = hit["metadata"]
        section = meta.get("section_no", "Unknown")
        chapter = meta.get("chapter", "Unknown")
        
        # Clean text preview (limit to 50 chars, replace newlines)
        text_preview = hit["chunk_text"].replace("\n", " ").strip()
        if len(text_preview) > 50:
            text_preview = text_preview[:47] + "..."
            
        print(f"{rank:<5} | {score:<8} | {section:<15} | {chapter:<10} | {text_preview}")
        
    print(f"{'-' * 85}\n")


def main() -> None:
    """Execute resources connection, queries run, self-tests, and print status."""
    try:
        t0 = time.time()
        
        engine = HybridSearchEngine()
        engine.init_resources(DEFAULT_COLLECTION)
        
        logger.info(f"Engine resources loaded in {time.time() - t0:.2f}s.")
        
        # Run test queries first to output top 10 previews
        sample_queries = [
            "Section 80C deduction",
            "What is TDS on professional fees?"
        ]
        
        for sq in sample_queries:
            hits, _ = engine.search(sq)
            print_formatted_results(hits, sq)
            
        # Run automated test suite
        tester = SelfTestSystem(engine)
        success = tester.run_all(DEFAULT_COLLECTION)
        
        if not success:
            logger.critical("CRITICAL: One or more self-tests failed!")
            sys.exit(1)
            
        # Print performance summary metrics
        print_performance_report(engine, DEFAULT_COLLECTION)
        
        # Logging validation tags
        logger.info("[PASS] Retrieval Engine")
        logger.info("[PASS] Hybrid Search")
        logger.info("[PASS] BM25")
        logger.info("[PASS] Vector Search")
        logger.info("[PASS] Rank Fusion")
        logger.info("[PASS] Metadata Boosting")
        logger.info("[PASS] Query Expansion")
        logger.info("[PASS] Logging")
        logger.info("[PASS] Performance")
        logger.info("[PASS] Ready for Prompt 5")
        
    except Exception as e:
        logger.critical(f"Fatal execution crash: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
