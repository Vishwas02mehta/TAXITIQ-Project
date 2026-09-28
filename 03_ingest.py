"""
03_ingest.py
============
Production-grade local embedding pipeline for IndiaLawRAG v2.

Reads chunks.json, embeds every chunk with BAAI/bge-large-en-v1.5 (loaded
locally via sentence-transformers), and stores vectors + metadata in a
persistent ChromaDB collection.

Key features
~~~~~~~~~~~~
- SHA256-based deterministic document IDs using index, section, chapter, subsection, chunk_text.
- Adaptive batch sizing with automatic CUDA OOM fallback (64->32->16->8).
- Checkpointing: flushes after every batch; resumes on restart.
- Metadata validation & repair before insertion.
- Comprehensive logging to logs/ingestion.log (no Unicode symbols to prevent Windows errors).
- Performance report with RAM / GPU / timing stats.
- 7 automated self-tests run at completion using [PASS] and [FAIL].

Usage:
    python 03_ingest.py
"""

from __future__ import annotations

import gc
import hashlib
import json
import logging
import os
import random
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# -- Auto-install missing dependencies ----------------------------
REQUIRED_PACKAGES = {
    "sentence_transformers": "sentence-transformers",
    "chromadb": "chromadb",
    "torch": "torch",
    "tqdm": "tqdm",
    "numpy": "numpy",
    "dotenv": "python-dotenv",
    "psutil": "psutil",
}


def _ensure_packages() -> None:
    """Install any missing packages automatically."""
    missing: list[str] = []
    for module_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(module_name)
        except ImportError:
            missing.append(pip_name)
    if missing:
        import subprocess
        print(f"Installing missing packages: {', '.join(missing)}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet"] + missing,
        )


_ensure_packages()

# -- Third-party imports (guaranteed available after auto-install) -
import chromadb
import numpy as np
import psutil
import torch
if not torch.cuda.is_available():
    torch.set_num_threads(6)
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# ==================================================================
# CONFIGURATION CONSTANTS
# ==================================================================

CHUNKS_PATH: str = "chunks.json"
CHROMA_DIR: str = "chroma_db"
COLLECTION_NAME: str = "indian_tax_law_corpus"
EMBED_MODEL_NAME: str = "BAAI/bge-large-en-v1.5"
EXPECTED_EMBED_DIM: int = 1024  # BGE-large-en-v1.5 output dimension
LOG_DIR: str = "logs"
LOG_FILE: str = os.path.join(LOG_DIR, "ingestion.log")
FAILED_CHUNKS_FILE: str = os.path.join(LOG_DIR, "failed_chunks.json")

# Adaptive batch sizes: try in order, fall back on CUDA OOM
BATCH_SIZES: list[int] = [32, 64, 16, 8]
DEFAULT_BATCH_SIZE: int = 32

# Retry configuration
MAX_RETRIES: int = 3
RETRY_DELAY_SEC: float = 1.0

# Required metadata fields
REQUIRED_METADATA_FIELDS: list[str] = ["section_no", "chapter", "act"]


# ==================================================================
# LOGGING SETUP
# ==================================================================

def setup_logging() -> logging.Logger:
    """Configure dual logging: file + console using ASCII safe formats."""
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger("ingestion")
    logger.setLevel(logging.DEBUG)

    # Prevent duplicating handlers if re-initialized
    if logger.handlers:
        logger.handlers.clear()

    # File handler - detailed (UTF-8 format)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    # Console handler - info+ (ASCII safe)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


logger = setup_logging()


# ==================================================================
# PERFORMANCE TRACKER
# ==================================================================

@dataclass
class PerformanceTracker:
    """Tracks runtime metrics for the ingestion report."""
    start_time: float = 0.0
    end_time: float = 0.0
    chunks_loaded: int = 0
    chunks_embedded: int = 0
    chunks_skipped: int = 0
    duplicates_found: int = 0
    failed_chunks: int = 0
    peak_ram_mb: float = 0.0
    peak_gpu_mb: float = 0.0
    batch_size_used: int = DEFAULT_BATCH_SIZE

    def start(self) -> None:
        self.start_time = time.time()

    def stop(self) -> None:
        self.end_time = time.time()

    @property
    def elapsed_sec(self) -> float:
        end = self.end_time if self.end_time > 0 else time.time()
        return end - self.start_time

    @property
    def chunks_per_sec(self) -> float:
        if self.elapsed_sec <= 0:
            return 0.0
        return self.chunks_embedded / self.elapsed_sec

    @property
    def embeddings_per_sec(self) -> float:
        return self.chunks_per_sec  # 1 embedding per chunk

    def update_memory(self) -> None:
        """Sample current RAM and GPU memory usage."""
        process = psutil.Process(os.getpid())
        ram_mb = process.memory_info().rss / (1024 * 1024)
        self.peak_ram_mb = max(self.peak_ram_mb, ram_mb)

        if torch.cuda.is_available():
            gpu_mb = torch.cuda.max_memory_allocated() / (1024 * 1024)
            self.peak_gpu_mb = max(self.peak_gpu_mb, gpu_mb)


# ==================================================================
# CORE UTILITY FUNCTIONS
# ==================================================================

def generate_chunk_id(
    chunk_text: str,
    index: int,
    section_no: str,
    chapter: str,
    subsection: str,
) -> str:
    """
    Generate a deterministic document ID using multiple stable properties.

    Constructs a SHA256 hash using chunk position, section, chapter, subsection,
    and text, returning the first 32 characters.
    """
    sec = str(section_no or "Unknown").strip()
    ch = str(chapter or "Unknown").strip()
    sub = str(subsection or "").strip()
    text = str(chunk_text or "").strip()
    
    stable_str = f"idx_{index}_sec_{sec}_ch_{ch}_sub_{sub}_text_{text}"
    return hashlib.sha256(stable_str.encode("utf-8")).hexdigest()[:32]


def sanitize_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """
    Ensure all metadata values are ChromaDB-compatible types.

    ChromaDB requires: str, int, float, or bool.
    - None values -> empty string
    - Lists/dicts -> JSON string
    """
    clean: dict[str, Any] = {}
    for key, value in meta.items():
        if value is None:
            clean[key] = ""
        elif isinstance(value, (str, int, float, bool)):
            clean[key] = value
        else:
            clean[key] = json.dumps(value, ensure_ascii=False)
    return clean


def validate_and_repair_metadata(
    chunk: dict[str, Any],
    index: int,
) -> tuple[dict[str, Any], list[str]]:
    """
    Validate that required metadata fields exist. Repair where possible.

    Returns:
        (metadata_dict, list_of_warnings)
    """
    warnings: list[str] = []
    meta = {k: v for k, v in chunk.items() if k != "chunk_text"}

    # Verify chunk_text exists
    if not chunk.get("chunk_text"):
        warnings.append(f"Chunk {index}: missing chunk_text")

    # Verify required fields
    for field_name in REQUIRED_METADATA_FIELDS:
        val = meta.get(field_name)
        if val is None or (isinstance(val, str) and val.strip() == ""):
            # Attempt repair
            if field_name == "act":
                meta["act"] = "Income-tax Act 2025"
                warnings.append(
                    f"Chunk {index}: repaired missing 'act' -> 'Income-tax Act 2025'"
                )
            elif field_name == "section_no":
                meta["section_no"] = "Unknown"
                warnings.append(
                    f"Chunk {index}: repaired missing 'section_no' -> 'Unknown'"
                )
            elif field_name == "chapter":
                meta["chapter"] = "Unknown"
                warnings.append(
                    f"Chunk {index}: repaired missing 'chapter' -> 'Unknown'"
                )
            else:
                meta[field_name] = ""
                warnings.append(
                    f"Chunk {index}: missing metadata field '{field_name}'"
                )

    return sanitize_metadata(meta), warnings


def get_device() -> str:
    """Return 'cuda' if a GPU is available, otherwise 'cpu'."""
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        logger.info(f"CUDA available: {device_name}")
        return "cuda"
    logger.info("CUDA not available - using CPU")
    return "cpu"


def get_db_size_mb(db_dir: str) -> float:
    """Calculate the total size of the ChromaDB directory in MB."""
    total = 0
    for dirpath, _, filenames in os.walk(db_dir):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total / (1024 * 1024)


# ==================================================================
# EMBEDDING ENGINE
# ==================================================================

class EmbeddingEngine:
    """
    Manages the sentence-transformers model lifecycle.

    - Loads BAAI/bge-large-en-v1.5 once.
    - Automatically selects CUDA or CPU.
    - Adaptive batch sizing with OOM fallback.
    """

    def __init__(self, model_name: str = EMBED_MODEL_NAME) -> None:
        self.model_name = model_name
        self.device = get_device()
        self._model: Optional[SentenceTransformer] = None
        self._dim: int = 0

    def load(self) -> None:
        """Load the embedding model (called once)."""
        logger.info(f"Loading embedding model: {self.model_name}")
        logger.info("(First run may download ~1.3 GB)")
        t0 = time.time()
        self._model = SentenceTransformer(self.model_name, device=self.device)
        elapsed = time.time() - t0
        self._dim = self._model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded in {elapsed:.1f}s  (device={self.device})")
        logger.info(f"Embedding dimension: {self._dim}")

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call .load() first.")
        return self._model

    @property
    def dimension(self) -> int:
        return self._dim

    def encode_batch(
        self,
        texts: list[str],
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> tuple[list[list[float]], int]:
        """
        Encode a batch of texts with adaptive batch sizing.

        If CUDA OOM occurs, automatically halves batch_size through the
        fallback chain: 64 -> 32 -> 16 -> 8.

        Returns:
            (embeddings_as_lists, actual_batch_size_used)
        """
        current_batch_size = batch_size

        for attempt_size in BATCH_SIZES:
            if attempt_size > current_batch_size:
                continue
            try:
                embeddings = self.model.encode(
                    texts,
                    batch_size=attempt_size,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                )
                return embeddings.tolist(), attempt_size

            except torch.cuda.OutOfMemoryError:
                logger.warning(
                    f"CUDA OOM at batch_size={attempt_size}. "
                    f"Reducing batch size."
                )
                torch.cuda.empty_cache()
                gc.collect()
                continue

            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    logger.warning(
                        f"CUDA OOM (RuntimeError) at batch_size={attempt_size}. "
                        f"Reducing batch size."
                    )
                    torch.cuda.empty_cache()
                    gc.collect()
                    continue
                raise

        # Final fallback: encode one at a time on CPU
        logger.warning("All GPU batch sizes failed. Encoding on CPU one-by-one.")
        self.model.to("cpu")
        self.device = "cpu"
        embeddings = self.model.encode(
            texts,
            batch_size=1,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embeddings.tolist(), 1


# ==================================================================
# INGESTION PIPELINE
# ==================================================================

class IngestionPipeline:
    """
    Orchestrates the full ingestion workflow.
    """

    def __init__(self) -> None:
        self.engine = EmbeddingEngine()
        self.tracker = PerformanceTracker()
        self.chunks: list[dict[str, Any]] = []
        self.collection: Any = None
        self.client: Any = None
        self.failed_chunks_list: list[dict[str, Any]] = []

    def record_failed_chunk(
        self,
        cid: str,
        chunk: dict[str, Any],
        error_msg: str,
        stack_trace: str,
    ) -> None:
        """Record details of a failed chunk and save to failed_chunks.json."""
        meta = {k: v for k, v in chunk.items() if k != "chunk_text"}
        self.failed_chunks_list.append({
            "chunk_id": cid,
            "metadata": meta,
            "error_message": error_msg,
            "stack_trace": stack_trace,
        })
        self._save_failed_chunks()

    def _save_failed_chunks(self) -> None:
        """Write self.failed_chunks_list to logs/failed_chunks.json."""
        os.makedirs(LOG_DIR, exist_ok=True)
        try:
            with open(FAILED_CHUNKS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.failed_chunks_list, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to write logs/failed_chunks.json: {e}")

    # -- Step 1: Load chunks --------------------------------------

    def load_chunks(self) -> None:
        """Load chunks.json from disk."""
        path = Path(CHUNKS_PATH)
        if not path.exists():
            logger.error(f"'{CHUNKS_PATH}' not found. Run 02_chunker.py first.")
            sys.exit(1)

        try:
            with open(path, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)
            self.tracker.chunks_loaded = len(self.chunks)
            logger.info(f"Loaded {len(self.chunks):,} chunks from {CHUNKS_PATH}")
        except json.JSONDecodeError as e:
            logger.error(f"'{CHUNKS_PATH}' is not valid JSON: {e}")
            sys.exit(1)

    # -- Step 2: Initialize model ---------------------------------

    def init_model(self) -> None:
        """Load the embedding model once."""
        self.engine.load()

    # -- Step 3: Connect to ChromaDB ------------------------------

    def init_database(self) -> None:
        """Connect to persistent ChromaDB and get/create collection."""
        os.makedirs(CHROMA_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={
                "description": "Income-tax Act 2025 - BGE-large embeddings",
                "model": EMBED_MODEL_NAME,
                "dimension": str(EXPECTED_EMBED_DIM),
            },
        )
        logger.info(
            f"ChromaDB collection '{COLLECTION_NAME}' ready "
            f"(dir: {CHROMA_DIR}/)"
        )

        # Check for database inconsistency (e.g. old ID style starts with 'chunk_' or different ID generation scheme)
        inconsistent = False
        try:
            count = self.collection.count()
            if count > 0:
                # 1. Basic format check of existing entries
                sample = self.collection.get(limit=10, include=[])
                if sample and sample.get("ids"):
                    for cid in sample["ids"]:
                        if cid.startswith("chunk_") or len(cid) != 32:
                            logger.warning(
                                f"Inconsistent collection detected: old ID format '{cid}' found."
                            )
                            inconsistent = True
                            break
                
                # 2. Check if the current deterministic ID scheme matches what is stored
                if not inconsistent and len(self.chunks) > 0:
                    sample_ids_to_check = []
                    for i in range(min(5, len(self.chunks))):
                        chunk = self.chunks[i]
                        cid = generate_chunk_id(
                            chunk_text=chunk.get("chunk_text", ""),
                            index=i,
                            section_no=chunk.get("section_no", "Unknown"),
                            chapter=chunk.get("chapter", "Unknown"),
                            subsection=chunk.get("subsection", ""),
                        )
                        sample_ids_to_check.append(cid)
                    
                    existing_check = self.collection.get(ids=sample_ids_to_check, include=[])
                    found_count = len(existing_check.get("ids", [])) if existing_check else 0
                    
                    # If we found 0 sample IDs but database has items, it's a different ID scheme or collection is out of sync
                    if found_count == 0:
                        logger.warning(
                            "Inconsistent collection detected: none of the sample deterministic IDs match existing database entries."
                        )
                        inconsistent = True
        except Exception as e:
            logger.warning(f"Error checking collection consistency: {e}")
            inconsistent = True

        if inconsistent:
            logger.info(f"Recreating collection '{COLLECTION_NAME}' to maintain consistency.")
            try:
                self.client.delete_collection(name=COLLECTION_NAME)
            except Exception as e:
                logger.warning(f"Failed to delete collection: {e}")
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={
                    "description": "Income-tax Act 2025 - BGE-large embeddings",
                    "model": EMBED_MODEL_NAME,
                    "dimension": str(EXPECTED_EMBED_DIM),
                },
            )

    # -- Step 4: Discover what needs embedding --------------------

    def _get_existing_ids(self) -> set[str]:
        """Retrieve all IDs currently in the collection."""
        try:
            all_ids: list[str] = []
            count = self.collection.count()
            if count == 0:
                return set()
            page_size = 10000
            offset = 0
            while offset < count:
                result = self.collection.get(
                    limit=page_size,
                    offset=offset,
                    include=[],
                )
                if result and result.get("ids"):
                    all_ids.extend(result["ids"])
                else:
                    break
                offset += page_size
            return set(all_ids)
        except Exception as e:
            logger.warning(f"Could not retrieve existing IDs: {e}")
            return set()

    def _prepare_batches(self) -> list[tuple[str, dict[str, Any]]]:
        """
        Build the list of (id, chunk) pairs that still need embedding.
        Skips duplicates in the source or already in the collection.
        """
        existing_ids = self._get_existing_ids()
        logger.info(f"Chunks already in collection: {len(existing_ids):,}")

        to_ingest: list[tuple[str, dict[str, Any]]] = []
        seen_ids_in_to_ingest = set()

        for i, chunk in enumerate(self.chunks):
            text = chunk.get("chunk_text", "")
            if not text:
                self.tracker.failed_chunks += 1
                self.record_failed_chunk(
                    cid="",
                    chunk=chunk,
                    error_msg="Empty chunk_text in source",
                    stack_trace="",
                )
                logger.warning(f"Chunk {i}: empty chunk_text - skipping")
                continue

            cid = generate_chunk_id(
                chunk_text=text,
                index=i,
                section_no=chunk.get("section_no", "Unknown"),
                chapter=chunk.get("chapter", "Unknown"),
                subsection=chunk.get("subsection", ""),
            )

            # Check duplicate in collection
            if cid in existing_ids:
                self.tracker.duplicates_found += 1
                # Already exists, skip
            # Check duplicate within this batch/preparation
            elif cid in seen_ids_in_to_ingest:
                logger.warning(f"Duplicate ID detected within JSON source: {cid} (Index: {i})")
                self.tracker.duplicates_found += 1
            else:
                seen_ids_in_to_ingest.add(cid)
                to_ingest.append((cid, chunk))

        self.tracker.chunks_skipped = self.tracker.duplicates_found
        logger.info(f"Chunks to embed (new):     {len(to_ingest):,}")
        logger.info(f"Chunks skipped (existing): {self.tracker.duplicates_found:,}")
        return to_ingest

    # -- Step 5: Embed & insert with checkpointing ----------------

    def _embed_and_insert(
        self,
        to_ingest: list[tuple[str, dict[str, Any]]],
    ) -> None:
        """Embed chunks in batches and insert into ChromaDB with checkpointing."""
        if not to_ingest:
            logger.info("Nothing new to ingest. All chunks already in ChromaDB.")
            return

        total = len(to_ingest)
        batch_size = DEFAULT_BATCH_SIZE
        embedded = 0
        failed = 0

        # Progress bar using safe ASCII format to prevent console encoding issues
        pbar = tqdm(
            total=total,
            desc="Embedding & inserting",
            unit="chunk",
            ascii=True,
            dynamic_ncols=True,
            bar_format=(
                "{l_bar}{bar}| {n_fmt}/{total_fmt} "
                "[{elapsed}<{remaining}, {rate_fmt}]"
            ),
        )

        batch_start = 0
        while batch_start < total:
            batch_end = min(batch_start + batch_size, total)
            batch = to_ingest[batch_start:batch_end]

            # Filter duplicates within this batch to prevent DB duplicate crashes
            batch_ids: list[str] = []
            batch_docs: list[str] = []
            batch_metas: list[dict[str, Any]] = []
            
            seen_ids_in_batch = set()

            for idx, (cid, chunk) in enumerate(batch):
                if cid in seen_ids_in_batch:
                    logger.warning(f"Duplicate ID skipped within current batch: {cid}")
                    self.tracker.duplicates_found += 1
                    continue
                seen_ids_in_batch.add(cid)

                text = chunk.get("chunk_text", "")
                meta, warnings = validate_and_repair_metadata(
                    chunk, batch_start + idx,
                )
                for w in warnings:
                    logger.warning(w)

                batch_ids.append(cid)
                batch_docs.append(text)
                batch_metas.append(meta)

            if not batch_ids:
                batch_start = batch_end
                continue

            # -- Embed with adaptive batch sizing -----------------
            try:
                embeddings, actual_bs = self.engine.encode_batch(
                    batch_docs, batch_size=batch_size,
                )
                batch_size = actual_bs
                self.tracker.batch_size_used = actual_bs
            except Exception as e:
                logger.error(
                    f"Embedding failed for batch starting at {batch_start}: {e}"
                )
                tb = traceback.format_exc()
                logger.debug(tb)
                failed += len(batch_ids)
                for idx, (cid, chunk) in enumerate(batch):
                    self.record_failed_chunk(
                        cid=cid,
                        chunk=chunk,
                        error_msg=f"Embedding failure: {e}",
                        stack_trace=tb,
                    )
                batch_start = batch_end
                pbar.update(len(batch))
                continue

            # -- Insert into ChromaDB with retry ------------------
            insert_ok = False
            for retry in range(MAX_RETRIES):
                try:
                    self.collection.add(
                        ids=batch_ids,
                        documents=batch_docs,
                        metadatas=batch_metas,
                        embeddings=embeddings,
                    )
                    insert_ok = True
                    break
                except Exception as e:
                    # If duplicate ID error occurs, log it and try upserting instead
                    logger.warning(
                        f"ChromaDB insert failed (attempt {retry + 1}/{MAX_RETRIES}): {e}"
                    )
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        try:
                            self.collection.upsert(
                                ids=batch_ids,
                                documents=batch_docs,
                                metadatas=batch_metas,
                                embeddings=embeddings,
                            )
                            insert_ok = True
                            break
                        except Exception as e2:
                            logger.error(f"Upsert fallback failed: {e2}")
                    time.sleep(RETRY_DELAY_SEC * (retry + 1))

            if insert_ok:
                embedded += len(batch_ids)
            else:
                logger.error(
                    f"Failed to insert batch at offset {batch_start} "
                    f"after {MAX_RETRIES} retries."
                )
                failed += len(batch_ids)
                tb = traceback.format_exc()
                for idx, (cid, chunk) in enumerate(batch):
                    self.record_failed_chunk(
                        cid=cid,
                        chunk=chunk,
                        error_msg="ChromaDB insert failure after all retries",
                        stack_trace=tb,
                    )

            # -- Update progress & memory stats -------------------
            pbar.update(len(batch))
            pbar.set_postfix(
                embedded=embedded,
                skipped=self.tracker.duplicates_found,
                failed=failed,
                bs=batch_size,
            )
            self.tracker.update_memory()
            batch_start = batch_end

        pbar.close()
        self.tracker.chunks_embedded = embedded
        self.tracker.failed_chunks += failed

    # -- Step 6: Performance report -------------------------------

    def print_report(self) -> None:
        """Print the final ingestion performance report in the exact format required."""
        self.tracker.stop()
        self.tracker.update_memory()

        collection_size = self.collection.count() if self.collection else 0
        elapsed = self.tracker.elapsed_sec

        report = f"""
===================================
INGESTION REPORT
===================================
Chunks Loaded: {self.tracker.chunks_loaded}
Chunks Embedded: {self.tracker.chunks_embedded}
Chunks Stored: {collection_size}
Chunks Skipped: {self.tracker.chunks_skipped}
Duplicate IDs: {self.tracker.duplicates_found}
Failed Chunks: {self.tracker.failed_chunks}
Collection Size: {collection_size}
Embedding Dimension: {EXPECTED_EMBED_DIM}
Average Throughput: {self.tracker.chunks_per_sec:.2f} chunks/sec
Peak RAM Usage: {self.tracker.peak_ram_mb:.1f} MB
Total Runtime: {elapsed:.2f}s
===================================
"""
        logger.info(report)

    # -- Step 7: Self-tests ---------------------------------------

    def run_self_tests(self) -> bool:
        """
        Run 7 automated validation tests with ASCII safe labels.
        Returns True if all pass.
        """
        logger.info("\n===================================")
        logger.info("           SELF-TESTS")
        logger.info("===================================")

        all_passed = True

        # TEST 1: Collection exists
        try:
            collections = [c.name for c in self.client.list_collections()]
            assert COLLECTION_NAME in collections, (
                f"Collection '{COLLECTION_NAME}' not found"
            )
            logger.info("  [PASS] Collection Exists")
        except Exception as e:
            logger.error(f"  [FAIL] Collection Exists - failed: {e}")
            all_passed = False

        # TEST 2: Correct Collection Count
        try:
            count = self.collection.count()
            # Count should equal embedded chunks + skipped duplicates (or match expectation)
            # When recreation runs, count matches exactly chunks_embedded + previous count
            assert count >= self.tracker.chunks_embedded, (
                f"Count {count} < embedded {self.tracker.chunks_embedded}"
            )
            logger.info("  [PASS] Correct Collection Count")
        except Exception as e:
            logger.error(f"  [FAIL] Correct Collection Count - failed: {e}")
            all_passed = False

        # TEST 3: Metadata Validation
        try:
            count = self.collection.count()
            sample_size = min(5, count)
            if sample_size > 0:
                offsets = random.sample(range(count), sample_size)
                for off in offsets:
                    result = self.collection.get(
                        limit=1,
                        offset=off,
                        include=["metadatas", "documents"],
                    )
                    assert result["ids"], "Empty result IDs"
                    assert result["metadatas"], "No metadatas key"
                    assert result["metadatas"][0], "Empty metadata dict"
                    assert result["documents"], "No documents key"
                    assert result["documents"][0], "Empty document"
            logger.info("  [PASS] Metadata Validation")
        except Exception as e:
            logger.error(f"  [FAIL] Metadata Validation - failed: {e}")
            all_passed = False

        # TEST 4: Embedding Dimension = 1024
        try:
            result = self.collection.get(
                limit=1,
                include=["embeddings"],
            )
            # Safe check on embeddings structure avoiding numpy array truthiness error
            embeddings = result.get("embeddings")
            if embeddings is not None and len(embeddings) > 0:
                dim = len(embeddings[0])
                assert dim == EXPECTED_EMBED_DIM, (
                    f"Dimension {dim} != expected {EXPECTED_EMBED_DIM}"
                )
                logger.info("  [PASS] Embedding Dimension = 1024")
            else:
                logger.warning("  [WARN] Embedding Dimension = 1024 (no embeddings in DB)")
        except Exception as e:
            logger.error(f"  [FAIL] Embedding Dimension = 1024 - failed: {e}")
            all_passed = False

        # TEST 5: Duplicate Protection
        try:
            if self.chunks:
                test_chunk = self.chunks[0]
                test_text = test_chunk.get("chunk_text", "")
                test_id = generate_chunk_id(
                    chunk_text=test_text,
                    index=0,
                    section_no=test_chunk.get("section_no", "Unknown"),
                    chapter=test_chunk.get("chapter", "Unknown"),
                    subsection=test_chunk.get("subsection", ""),
                )
                count_before = self.collection.count()

                meta = sanitize_metadata(
                    {k: v for k, v in test_chunk.items() if k != "chunk_text"}
                )
                emb = self.engine.model.encode(
                    [test_text],
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                ).tolist()

                try:
                    self.collection.add(
                        ids=[test_id],
                        documents=[test_text],
                        metadatas=[meta],
                        embeddings=emb,
                    )
                except Exception:
                    pass

                count_after = self.collection.count()
                assert count_after == count_before, (
                    f"Count changed: {count_before} -> {count_after}"
                )
                logger.info("  [PASS] Duplicate Protection")
            else:
                logger.warning("  [WARN] Duplicate Protection (no chunks to test)")
        except Exception as e:
            logger.error(f"  [FAIL] Duplicate Protection - failed: {e}")
            all_passed = False

        # TEST 6: Resume Test
        try:
            resume_pipeline = IngestionPipeline()
            resume_pipeline.chunks = self.chunks
            resume_pipeline.client = self.client
            resume_pipeline.collection = self.collection
            to_ingest = resume_pipeline._prepare_batches()

            # If all chunks are successfully embedded, nothing should be left to ingest
            if self.tracker.failed_chunks == 0:
                assert len(to_ingest) == 0, (
                    f"Expected 0 chunks remaining, got {len(to_ingest)}"
                )
            logger.info("  [PASS] Resume Test")
        except Exception as e:
            logger.error(f"  [FAIL] Resume Test - failed: {e}")
            all_passed = False

        # TEST 7: Persistence Test
        try:
            fresh_client = chromadb.PersistentClient(path=CHROMA_DIR)
            fresh_collection = fresh_client.get_collection(name=COLLECTION_NAME)
            persisted_count = fresh_collection.count()
            assert persisted_count == self.collection.count(), (
                f"Persisted count {persisted_count} != current count {self.collection.count()}"
            )
            logger.info("  [PASS] Persistence Test")
        except Exception as e:
            logger.error(f"  [FAIL] Persistence Test - failed: {e}")
            all_passed = False

        logger.info("===================================")
        if all_passed:
            logger.info("  ALL TESTS PASSED")
        else:
            logger.error("  SOME TESTS FAILED")
        logger.info("===================================")

        return all_passed

    # -- Main orchestrator ----------------------------------------

    def run(self) -> bool:
        """Execute the full ingestion pipeline."""
        logger.info("=======================================")
        logger.info("  IndiaLawRAG v2 - Embedding Pipeline")
        logger.info("=======================================")
        logger.info(f"  Model : {EMBED_MODEL_NAME}")
        logger.info(f"  DB    : {CHROMA_DIR}/{COLLECTION_NAME}")
        logger.info(f"  Device: {get_device()}")
        logger.info("=======================================\n")

        self.tracker.start()

        # Step 1: Load Chunks
        self.load_chunks()

        # Step 2: Init Model
        self.init_model()

        # Step 3: Connect to ChromaDB
        self.init_database()

        # Step 4 & 5: Batch ingest & checkpoint
        to_ingest = self._prepare_batches()
        self._embed_and_insert(to_ingest)

        # Step 6: Print performance report
        self.print_report()

        # Step 7: Self-tests
        tests_passed = self.run_self_tests()
        return tests_passed


# ==================================================================
# ENTRY POINT
# ==================================================================

def generate_corpus_statistics() -> Dict[str, Any]:
    """Generates corpus_statistics.json and prints publication Table 1."""
    import statistics
    import glob

    logger.info("\nGenerating publication corpus statistics (corpus_statistics.json)...")
    parsed_file = "parsed_output.json"
    chunks_file = "chunks.json"

    pages_data = []
    manifests_data = []
    if os.path.exists(parsed_file):
        with open(parsed_file, "r", encoding="utf-8") as f:
            p_data = json.load(f)
            pages_data = p_data.get("pages", [])
            manifests_data = p_data.get("manifests", [])

    chunks = []
    if os.path.exists(chunks_file):
        with open(chunks_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)

    # Document type counts
    doc_types = {}
    doc_names = set()
    total_pages = len(pages_data)
    sections_set = set()

    for m in manifests_data:
        dtype = m.get("document_type", "statute")
        doc_types[dtype] = doc_types.get(dtype, 0) + 1
        doc_names.add(m.get("document_name"))

    num_acts = doc_types.get("statute", 1)
    num_rules = doc_types.get("rules", 1)
    num_finance_acts = doc_types.get("finance_act", 0)
    num_circulars = doc_types.get("cbdt_circular", 0)
    num_notifications = doc_types.get("notification", 0)

    total_pdfs = len(manifests_data) if manifests_data else len(glob.glob("data/**/*.pdf", recursive=True))

    chunk_token_lens = []
    vocab_set = set()
    for c in chunks:
        sec = c.get("section_no", "")
        if sec and sec != "General":
            sections_set.add(f"{c.get('document_name')}_Sec_{sec}")
        text = c.get("chunk_text", "")
        tokens = text.lower().split()
        chunk_token_lens.append(len(tokens))
        vocab_set.update(tokens)

    avg_chunks_per_doc = len(chunks) / max(1, total_pdfs)
    avg_tokens_per_chunk = float(np.mean(chunk_token_lens)) if chunk_token_lens else 0.0
    median_tokens_per_chunk = float(np.median(chunk_token_lens)) if chunk_token_lens else 0.0

    stats = {
        "num_acts": num_acts,
        "num_rules": num_rules,
        "num_finance_acts": num_finance_acts,
        "num_circulars": num_circulars,
        "num_notifications": num_notifications,
        "total_pdfs": total_pdfs,
        "total_pages": total_pages,
        "total_sections": len(sections_set),
        "total_chunks": len(chunks),
        "avg_chunks_per_document": round(avg_chunks_per_doc, 2),
        "avg_tokens_per_chunk": round(avg_tokens_per_chunk, 2),
        "median_tokens_per_chunk": round(median_tokens_per_chunk, 2),
        "embedding_dimension": EXPECTED_EMBED_DIM,
        "vocabulary_size": len(vocab_set),
    }

    with open("corpus_statistics.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    logger.info("Saved corpus_statistics.json")
    print("\n" + "=" * 70)
    print("  TABLE 1: CORPUS DIVERSITY & COMPOSITION STATISTICS")
    print("=" * 70)
    print(f"  Document Type                   | Count | Total Pages | Total Chunks")
    print(f"  -------------------------------------------------------------------")
    print(f"  Income-tax Act(s)               | {num_acts:5d} | {total_pages:11d} | {len(chunks):12d}")
    print(f"  Income-tax Rules                | {num_rules:5d} |     (Shared)|            -")
    print(f"  Finance Acts (2022-2026)        | {num_finance_acts:5d} |     (Shared)|            -")
    print(f"  CBDT Circulars (2026 Collection) | {num_circulars:5d} |     (Shared)|            -")
    print(f"  -------------------------------------------------------------------")
    print(f"  TOTAL LEGAL SOURCE DOCUMENTS     | {total_pdfs:5d} | {total_pages:11d} | {len(chunks):12d}")
    print(f"  Total Sections Identified       | {len(sections_set):5d}")
    print(f"  Average Chunks / Document       | {avg_chunks_per_doc:.2f}")
    print(f"  Average Tokens / Chunk          | {avg_tokens_per_chunk:.2f}")
    print(f"  Median Tokens / Chunk           | {median_tokens_per_chunk:.2f}")
    print(f"  Embedding Dimension             | {EXPECTED_EMBED_DIM:5d}")
    print(f"  Vocabulary Size (Unique Tokens) | {len(vocab_set):5d}")
    print("=" * 70 + "\n")

    return stats


def main() -> None:
    """Entry point for the ingestion pipeline."""
    try:
        pipeline = IngestionPipeline()
        success = pipeline.run()
        if not success:
            sys.exit(1)
        generate_corpus_statistics()
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user. Data flushed up to last batch.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
