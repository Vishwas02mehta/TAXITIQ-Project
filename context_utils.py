"""
context_utils.py
================
Core utility algorithms for the Context Assembly Engine of IndiaLawRAG v2.

Provides:
1. Reusable ContextAssembler class: exposed as a python module.
2. Deduplication engine at chunk and sentence levels.
3. Chunks & Subsections merging engine.
4. Evidence classifier & conflict detector.
5. Tiktoken-based future LLM token estimator.
6. Coverage, confidence, and context fingerprint calculations.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import tiktoken

# Configuration Constants
LOG_DIR: str = "logs"
LOG_FILE: str = os.path.join(LOG_DIR, "context_builder.log")
MAX_TOKEN_BUDGET: int = 3500
LLM_ENCODING_NAME: str = "cl100k_base"  # Tiktoken cl100k_base (GPT-4 / GPT-3.5)


# Setup context builder logging
def setup_builder_logging() -> logging.Logger:
    """Configure search session logger with ASCII formats."""
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger("context_builder")
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


logger = setup_builder_logging()


@dataclass
class AssemblyStatistics:
    """Stores assembly execution counts and metrics."""
    input_chunks: int = 0
    duplicates_removed: int = 0
    merged_blocks: int = 0
    overlap_removed: int = 0
    final_blocks_count: int = 0
    final_token_count: int = 0
    average_score: float = 0.0
    highest_score: float = 0.0
    lowest_score: float = 0.0
    coverage_score: float = 0.0
    confidence_score: float = 0.0
    fingerprint: str = ""


class ContextAssembler:
    """
    Context Assembly Engine wrapper.
    Processes candidates, merges texts, detects conflicts, classifies evidence,
    trims to token budget, and computes coverage metadata.
    """

    def __init__(self, token_budget: int = MAX_TOKEN_BUDGET) -> None:
        self.token_budget = token_budget
        try:
            self.tokenizer = tiktoken.get_encoding(LLM_ENCODING_NAME)
            logger.debug(f"Using tiktoken encoding: {LLM_ENCODING_NAME}")
        except Exception as e:
            logger.warning(f"Failed to load tiktoken encoding. Falling back to char estimation: {e}")
            self.tokenizer = None

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using tiktoken or fallback word/char count."""
        if self.tokenizer is not None:
            return len(self.tokenizer.encode(text))
        # Fallback: approx 4 chars per token for English text
        return len(text) // 4

    def remove_duplicate_chunks(self, candidates: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
        """
        Remove duplicate chunks by ID or normalized text.
        Preserves the highest-ranked (first occurrence in candidates).
        """
        seen_ids: Set[str] = set()
        seen_texts: Set[str] = set()
        deduplicated: List[Dict[str, Any]] = []
        removed_count = 0

        for cand in candidates:
            chunk_id = cand.get("id") or cand.get("metadata", {}).get("id", "")
            if not chunk_id:
                chunk_id = hashlib.sha256(cand["chunk_text"].encode("utf-8")).hexdigest()[:32]
                cand["id"] = chunk_id
                
            norm_text = re.sub(r"\s+", "", cand["chunk_text"].lower().strip())
            
            if chunk_id in seen_ids or norm_text in seen_texts:
                removed_count += 1
                logger.debug(f"Removing duplicate chunk ID: {chunk_id}")
                continue
                
            seen_ids.add(chunk_id)
            seen_texts.add(norm_text)
            deduplicated.append(cand)
            
        return deduplicated, removed_count

    def classify_evidence_type(self, text: str, metadata: Dict[str, Any]) -> str:
        """Classify chunk content into legal evidence categories."""
        text_lower = text.lower()
        title_lower = str(metadata.get("section_title", "")).lower()
        
        # Priority 1: Definition
        if "definitions" in title_lower or re.search(r"\bmeans\b|\bshall mean\b|\bshall be deemed to be\b", text_lower):
            return "Definition"
            
        # Priority 2: Exemption / Deduction
        if any(term in text_lower for term in ["deduction", "exemption", "rebate", "shall not apply", "tax-free"]):
            return "Exemption/Deduction"
            
        # Priority 3: Penalty / Interest
        if any(term in text_lower for term in ["penalty", "fine", "imprisonment", "interest", "prosecution", "punished"]):
            return "Penalty/Interest"
            
        # Priority 4: Procedural / Administrative
        if any(term in text_lower for term in ["assessment", "return", "filing", "officer", "notice", "appeal", "procedure"]):
            return "Procedural/Administrative"
            
        return "Statutory Rule"

    def detect_conflicting_evidence(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Compare context blocks to flag potential conflicts or contradictions
        (e.g., matching section names across different acts, or opposing rates).
        """
        conflicts: List[Dict[str, Any]] = []
        for i in range(len(blocks)):
            for j in range(i + 1, len(blocks)):
                b1 = blocks[i]
                b2 = blocks[j]
                
                # Check for same section number but different act
                if b1["section"] == b2["section"] and b1["section"] != "" and b1["act"] != b2["act"]:
                    conflict_desc = (
                        f"Section {b1['section']} appears in two different acts: "
                        f"'{b1['act']}' vs '{b2['act']}'."
                    )
                    conflicts.append({
                        "type": "Cross-Act Section Overlap",
                        "description": conflict_desc,
                        "sections": [b1["section"]],
                        "source_ids": [b1["source_ids"], b2["source_ids"]]
                    })
                    logger.warning(f"Conflict Detected: {conflict_desc}")
                    
                # Check for rate percentage conflicts in the same section number
                if b1["section"] == b2["section"] and b1["section"] != "":
                    rates_b1 = set(re.findall(r"\b\d+%\b", b1["text"]))
                    rates_b2 = set(re.findall(r"\b\d+%\b", b2["text"]))
                    shared_rates = rates_b1 & rates_b2
                    # If they have different sets of rates in the same section number, flag it
                    if rates_b1 and rates_b2 and not shared_rates:
                        conflict_desc = (
                            f"Section {b1['section']} contains differing rates: "
                            f"'{', '.join(rates_b1)}' vs '{', '.join(rates_b2)}'."
                        )
                        conflicts.append({
                            "type": "Differing Rates in Section",
                            "description": conflict_desc,
                            "sections": [b1["section"]],
                            "source_ids": [b1["source_ids"], b2["source_ids"]]
                        })
                        logger.warning(f"Conflict Detected: {conflict_desc}")
        return conflicts

    def deduplicate_sentences(self, text: str) -> Tuple[str, int]:
        """
        Detect repeated sentences in a block and remove subsequent occurrences.
        Returns the deduplicated text and the count of sentences removed.
        """
        # Split sentences preserving punctuation boundaries
        sentences = re.split(r"(?<=[.!?])\s+", text)
        seen_sentences: Set[str] = set()
        unique_sentences: List[str] = []
        removed = 0

        for sentence in sentences:
            trimmed = sentence.strip()
            if not trimmed:
                continue
            # Normalize sentence text for duplicate comparison
            norm = re.sub(r"\s+", "", trimmed.lower())
            
            if norm in seen_sentences:
                removed += 1
                continue
                
            seen_sentences.add(norm)
            unique_sentences.append(trimmed)

        return " ".join(unique_sentences), removed

    def merge_candidate_chunks(
        self,
        candidates: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Merge consecutive chunks belonging to the same section.
        Also combines sequential subsections (e.g. 80C(1), 80C(2)).
        
        Returns:
            Tuple: (merged_blocks, merged_chunks_count, overlap_sentences_removed)
        """
        if not candidates:
            return [], 0, 0
            
        merged_blocks: List[Dict[str, Any]] = []
        merged_count = 0
        total_overlap_removed = 0
        
        # We process step-by-step
        current_block: Optional[Dict[str, Any]] = None
        
        for cand in candidates:
            meta = cand.get("metadata", {})
            act = meta.get("act", "Income-tax Act 2025")
            chapter = meta.get("chapter", "IV")
            sec_no = meta.get("section_no", "")
            subsec = meta.get("subsection", "")
            score = cand.get("reranker_score") or cand.get("score") or 0.0
            orig_rank = cand.get("rank") or cand.get("original_hybrid_rank") or -1
            chunk_id = cand["id"]
            
            # Extract numerical/alphanumeric subsection for sequence matching
            sub_seq_num = None
            if subsec:
                match = re.search(r"\((\d+)\)", subsec)
                if match:
                    sub_seq_num = int(match.group(1))

            text = cand["chunk_text"].strip()

            # Rule check: Can we merge with the current_block?
            # Merge condition: Same Act AND Same Section Number AND we are either matching adjacent chunks
            # or neighbouring sequential subsections (e.g. current_seq_num + 1 == sub_seq_num).
            can_merge = False
            if current_block is not None:
                is_same_sec = (current_block["act"] == act and current_block["section"] == sec_no)
                
                # Check for subsection sequential merge
                is_sequential_sub = False
                if is_same_sec and sub_seq_num is not None and current_block["_last_subsec_seq"] is not None:
                    diff = sub_seq_num - current_block["_last_subsec_seq"]
                    if diff in [0, 1]:  # same or consecutive next subsection
                        is_sequential_sub = True
                        
                # General adjacent chunk merge (if no subsection constraints or matching sequence)
                if is_same_sec and (is_sequential_sub or subsec == current_block["subsection"] or not subsec or not current_block["subsection"]):
                    can_merge = True

            if can_merge and current_block is not None:
                # Merge chunks!
                merged_count += 1
                logger.debug(f"Merging chunk {chunk_id} into block for Section {sec_no}")
                
                # Update text
                combined_text = current_block["text"] + "\n" + text
                # Deduplicate sentences on the merged text
                clean_text, sentence_removed = self.deduplicate_sentences(combined_text)
                total_overlap_removed += sentence_removed
                
                current_block["text"] = clean_text
                current_block["source_ids"].append(chunk_id)
                current_block["original_ranks"].append(orig_rank)
                current_block["_scores"].append(score)
                current_block["average_score"] = float(sum(current_block["_scores"]) / len(current_block["_scores"]))
                
                # Accumulate subsections
                if subsec and subsec not in current_block["subsection"]:
                    if current_block["subsection"]:
                        current_block["subsection"] += f", {subsec}"
                    else:
                        current_block["subsection"] = subsec
                        
                if sub_seq_num is not None:
                    current_block["_last_subsec_seq"] = sub_seq_num
            else:
                # Close current block and start a new one
                if current_block is not None:
                    # Clean internal tracking variables before finalize
                    clean_block = self._finalize_block_fields(current_block)
                    merged_blocks.append(clean_block)
                    
                # Create new block structure
                title = f"{act} | Chapter {chapter} | Section {sec_no}"
                if subsec:
                    title += f" ({subsec})"
                    
                current_block = {
                    "title": title,
                    "act": act,
                    "chapter": chapter,
                    "section": sec_no,
                    "subsection": subsec,
                    "text": text,
                    "source_ids": [chunk_id],
                    "original_ranks": [orig_rank],
                    "average_score": score,
                    "evidence_type": self.classify_evidence_type(text, meta),
                    "_scores": [score],
                    "_last_subsec_seq": sub_seq_num
                }

        if current_block is not None:
            clean_block = self._finalize_block_fields(current_block)
            merged_blocks.append(clean_block)

        return merged_blocks, merged_count, total_overlap_removed

    def _finalize_block_fields(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """Convert list fields and format citations for output."""
        citation = (
            f"Act: {block['act']}, Chapter: {block['chapter']}, "
            f"Section: {block['section']}, Subsection: {block['subsection']}, "
            f"Source IDs: {', '.join(block['source_ids'])}"
        )
        final_block = {
            "title": block["title"],
            "act": block["act"],
            "chapter": block["chapter"],
            "section": block["section"],
            "subsection": block["subsection"],
            "text": block["text"],
            "citations": citation,
            "token_count": self.estimate_tokens(block["text"]),
            "average_score": block["average_score"],
            "evidence_type": block["evidence_type"],
            "source_ids": block["source_ids"],
            "original_ranks": block["original_ranks"]
        }
        return final_block

    def compute_coverage(self, query: str, assembled_text: str) -> float:
        """
        Calculate term coverage score: percentage of meaningful query words
        present in the assembled text.
        """
        q_words = set(re.findall(r"\b\w{4,}\b", query.lower()))
        # Remove common stop words from check
        stop_words = {"what", "where", "when", "with", "from", "that", "this", "under", "shall"}
        meaningful_q_words = q_words - stop_words
        
        if not meaningful_q_words:
            return 1.0
            
        found_words = sum(1 for w in meaningful_q_words if w in assembled_text.lower())
        return float(found_words / len(meaningful_q_words))

    def assemble(self, query: str, candidates: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], AssemblyStatistics]:
        """
        Main assembly routine.
        
        Processes candidates:
        - Deduplicates chunk entries.
        - Merges text of sequential sections.
        - Classifies legal evidence types.
        - Generates formatted citation blocks.
        - Trims blocks exceeding 3500 token budget.
        - Computes coverage and builds a SHA-256 fingerprint.
        
        Returns:
            Tuple (blocks_list, stats)
        """
        t0 = time.time()
        input_count = len(candidates)
        
        # Step 1: Remove duplicates
        deduplicated, dups_removed = self.remove_duplicate_chunks(candidates)
        
        # Step 2: Merge adjacent chunks and subsections
        merged_blocks, merged_count, sentence_overlaps_removed = self.merge_candidate_chunks(deduplicated)
        
        # Step 3: Estimate tokens and enforce budget limit <= 3500 tokens
        # If total tokens exceeds budget, trim lowest-ranked blocks first
        total_tokens = sum(b["token_count"] for b in merged_blocks)
        
        if total_tokens > self.token_budget:
            logger.warning(f"Context total tokens {total_tokens} exceeds budget limit {self.token_budget}. Trimming blocks...")
            # Sort copy by score descending (highest priority stays)
            scored_blocks = sorted(
                enumerate(merged_blocks),
                key=lambda x: x[1]["average_score"],
                reverse=True
            )
            
            accumulated_tokens = 0
            keep_indices: Set[int] = set()
            for original_idx, block in scored_blocks:
                block_tokens = block["token_count"]
                if accumulated_tokens + block_tokens <= self.token_budget:
                    accumulated_tokens += block_tokens
                    keep_indices.add(original_idx)
                else:
                    logger.debug(f"Trimming block: Section {block['section']} due to token budget limits")
            
            # Rebuild merged list preserving original index sequence, dropping discarded ones
            merged_blocks = [block for idx, block in enumerate(merged_blocks) if idx in keep_indices]
            total_tokens = sum(b["token_count"] for b in merged_blocks)

        # Step 4: Sort blocks (Primary: Reranker Score descending, Secondary: Section Order ascending)
        def sort_key(block: Dict[str, Any]) -> Tuple[float, int]:
            # Extracted numerical section number
            sec_num = 999999
            sec_str = str(block["section"])
            match = re.search(r"\d+", sec_str)
            if match:
                sec_num = int(match.group(0))
            # Primary: reranker score descending (multiply by -1 for ascending key sort)
            # Secondary: section number ascending
            return (-1.0 * block["average_score"], sec_num)

        merged_blocks.sort(key=sort_key)
        
        # Step 5: Compute text indicators
        combined_text = "\n\n".join(b["text"] for b in merged_blocks)
        coverage_val = self.compute_coverage(query, combined_text)
        
        # Confidence is the average of reranker score of all final blocks
        confidence_val = float(sum(b["average_score"] for b in merged_blocks) / len(merged_blocks)) if merged_blocks else 0.0
        
        # SHA-256 fingerprinting
        fingerprint_hash = hashlib.sha256(combined_text.encode("utf-8")).hexdigest()
        
        scores = [b["average_score"] for b in merged_blocks]
        stats = AssemblyStatistics(
            input_chunks=input_count,
            duplicates_removed=dups_removed,
            merged_blocks=merged_count,
            overlap_removed=sentence_overlaps_removed,
            final_blocks_count=len(merged_blocks),
            final_token_count=total_tokens,
            average_score=float(sum(scores)/len(scores)) if scores else 0.0,
            highest_score=max(scores) if scores else 0.0,
            lowest_score=min(scores) if scores else 0.0,
            coverage_score=coverage_val,
            confidence_score=confidence_val,
            fingerprint=fingerprint_hash
        )
        
        logger.debug(
            f"Finished context assembly. Blocks: {stats.final_blocks_count} | Tokens: {stats.final_token_count} | "
            f"Duplicates removed: {stats.duplicates_removed} | Overlap sentences removed: {stats.overlap_removed} | "
            f"Coverage: {stats.coverage_score:.2f} | Confidence: {stats.confidence_score:.2f} | Fingerprint: {stats.fingerprint[:10]}"
        )
        
        return merged_blocks, stats
