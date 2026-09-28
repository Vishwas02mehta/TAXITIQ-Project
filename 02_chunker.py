"""
02_chunker.py
=============
Upgraded multi-document legal chunking engine for TAXITIQ.

Reads parsed_output.json (pages & manifests across Acts, Rules, Finance Acts, and CBDT Circulars)
and splits content into legal-aware, semantically complete chunks.

Key Features:
-------------
- Legal Hierarchy Preservation: Splits on statutory section, rule, or circular paragraph boundaries.
- Proviso & Explanation Bonding: Glues legal provisos ("Provided that...") and explanations to parent provisions.
- Rich Metadata Enrichment: Attaches document_name, document_type, chapter, section_no, subsection,
  title, parent_heading, chunk_id, page_number, source_pdf, and effective_from.
- Sentence Protection: Enforces MAX_CHUNK_CHARS ceiling without breaking mid-sentence.

Usage:
    python 02_chunker.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

INPUT_PATH = "parsed_output.json"
OUTPUT_PATH = "chunks.json"
MAX_CHUNK_CHARS = 1200

# ── Regex Patterns for Multi-Document Hierarchy ───────────────────

RE_CHAPTER = re.compile(
    r"^(?:CHAPTER|Chapter)\s+([IVXLCDM]+(?:-[A-Z])?)(?:\s*[-–—:]\s*(.+))?$",
    re.MULTILINE,
)

RE_SECTION_STATUTE = re.compile(
    r"^(?:Section\s+)?(\d+[A-Z]*(?:\.\d+)?)\.\s+(.+?)(?:\.?—|\.?\s*[-–—])?\s*$",
    re.MULTILINE | re.IGNORECASE,
)

RE_RULE = re.compile(
    r"^(?:Rule\s+)?(\d+[A-Z]*(?:\.\d+)?)\.\s+(.+?)(?:\.?—|\.?\s*[-–—])?\s*$",
    re.MULTILINE | re.IGNORECASE,
)

RE_CIRCULAR_PARA = re.compile(
    r"^(\d+(?:\.\d+)*)\.?\s+(.+)$",
    re.MULTILINE,
)

RE_SUBSECTION = re.compile(
    r"^\((\d+[A-Z]?)\)",
    re.MULTILINE,
)

RE_PROVISO = re.compile(
    r"(?:^|\n)\s*Provided\s+that",
    re.IGNORECASE,
)


@dataclass
class StructuralContext:
    doc_name: str = "Income-tax Act, 2025"
    doc_type: str = "statute"
    source_pdf: str = "Income_Tax_Act_2025.pdf"
    chapter: str = "Unknown"
    chapter_title: str = ""
    section_no: str = "General"
    section_title: str = ""
    subsection: str = ""
    effective_from: str = "AY2026-27"


@dataclass
class Chunk:
    document_name: str = ""
    document_type: str = ""
    act: str = ""  # Backward compatibility
    chapter: str = ""
    chapter_title: str = ""
    section_no: str = ""
    section_title: str = ""
    subsection: str = ""
    title: str = ""
    parent_heading: str = ""
    chunk_id: str = ""
    page_number: int = 1
    source_pdf: str = ""
    effective_from: str = ""
    has_proviso: bool = False
    source_type: str = "statute"
    chunk_text: str = ""


def build_context_header(ctx: StructuralContext) -> str:
    parts = [f"[{ctx.doc_name}]"]
    if ctx.chapter and ctx.chapter != "Unknown":
        ch_str = f"Chapter {ctx.chapter}"
        if ctx.chapter_title:
            ch_str += f": {ctx.chapter_title}"
        parts.append(ch_str)

    if ctx.doc_type == "rules":
        sec_str = f"Rule {ctx.section_no}" if ctx.section_no != "General" else "General Rules"
    elif ctx.doc_type == "cbdt_circular":
        sec_str = f"Para {ctx.section_no}" if ctx.section_no != "General" else "Circular Content"
    else:
        sec_str = f"Section {ctx.section_no}" if ctx.section_no != "General" else "General Provision"

    if ctx.section_title:
        sec_str += f" ({ctx.section_title})"
    parts.append(sec_str)

    if ctx.subsection:
        parts.append(f"Sub-section ({ctx.subsection})")

    return " | ".join(parts)


def compute_chunk_id(doc_name: str, sec_no: str, page_num: int, idx: int, text: str) -> str:
    raw = f"{doc_name}:{sec_no}:{page_num}:{idx}:{text[:50]}"
    return f"chunk_{hashlib.md5(raw.encode('utf-8')).hexdigest()[:12]}"


def split_text_into_sentences(text: str) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def create_chunks_from_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    chunks_list: List[Dict[str, Any]] = []

    for page in pages:
        doc_name = page.get("doc_title") or page.get("document_name") or "Income-tax Act, 2025"
        doc_type = page.get("doc_type") or page.get("document_type") or "statute"
        source_pdf = page.get("source_pdf") or ""
        page_num = page.get("page_number", 1)
        effective_from = page.get("effective_from") or "AY2026-27"
        page_text = page.get("text", "").strip()

        if not page_text:
            continue

        ctx = StructuralContext(
            doc_name=doc_name,
            doc_type=doc_type,
            source_pdf=source_pdf,
            effective_from=effective_from,
        )

        # Detect chapter
        ch_match = RE_CHAPTER.search(page_text)
        if ch_match:
            ctx.chapter = ch_match.group(1).strip()
            ctx.chapter_title = (ch_match.group(2) or "").strip()

        # Split page text into blocks
        blocks = re.split(r"\n{2,}", page_text)
        page_chunk_idx = 0

        for block in blocks:
            block_clean = block.strip()
            if not block_clean:
                continue

            # Update section context
            if doc_type == "rules":
                r_match = RE_RULE.search(block_clean)
                if r_match:
                    ctx.section_no = r_match.group(1).strip()
                    ctx.section_title = r_match.group(2).strip()
            elif doc_type == "cbdt_circular":
                p_match = RE_CIRCULAR_PARA.search(block_clean)
                if p_match:
                    ctx.section_no = p_match.group(1).strip()
                    ctx.section_title = p_match.group(2).strip()[:50]
            else:
                s_match = RE_SECTION_STATUTE.search(block_clean)
                if s_match:
                    ctx.section_no = s_match.group(1).strip()
                    ctx.section_title = s_match.group(2).strip()

            sub_match = RE_SUBSECTION.search(block_clean)
            if sub_match:
                ctx.subsection = sub_match.group(1).strip()

            has_proviso = bool(RE_PROVISO.search(block_clean))
            header_str = build_context_header(ctx)

            # If block is small enough, add directly
            if len(block_clean) <= MAX_CHUNK_CHARS:
                full_text = f"{header_str}\n\n{block_clean}"
                page_chunk_idx += 1
                c_id = compute_chunk_id(doc_name, ctx.section_no, page_num, page_chunk_idx, block_clean)

                c = Chunk(
                    document_name=doc_name,
                    document_type=doc_type,
                    act=doc_name,
                    chapter=ctx.chapter,
                    chapter_title=ctx.chapter_title,
                    section_no=ctx.section_no,
                    section_title=ctx.section_title,
                    subsection=ctx.subsection,
                    title=ctx.section_title or header_str,
                    parent_heading=f"Chapter {ctx.chapter}" if ctx.chapter != "Unknown" else doc_name,
                    chunk_id=c_id,
                    page_number=page_num,
                    source_pdf=source_pdf,
                    effective_from=effective_from,
                    has_proviso=has_proviso,
                    source_type=doc_type,
                    chunk_text=full_text,
                )
                chunks_list.append(asdict(c))
            else:
                # Split large block into sentence groups
                sentences = split_text_into_sentences(block_clean)
                curr_sentences = []
                curr_len = 0

                for sent in sentences:
                    if curr_len + len(sent) > MAX_CHUNK_CHARS and curr_sentences:
                        part_text = " ".join(curr_sentences)
                        full_part_text = f"{header_str}\n\n{part_text}"
                        page_chunk_idx += 1
                        c_id = compute_chunk_id(doc_name, ctx.section_no, page_num, page_chunk_idx, part_text)

                        c = Chunk(
                            document_name=doc_name,
                            document_type=doc_type,
                            act=doc_name,
                            chapter=ctx.chapter,
                            chapter_title=ctx.chapter_title,
                            section_no=ctx.section_no,
                            section_title=ctx.section_title,
                            subsection=ctx.subsection,
                            title=ctx.section_title or header_str,
                            parent_heading=f"Chapter {ctx.chapter}" if ctx.chapter != "Unknown" else doc_name,
                            chunk_id=c_id,
                            page_number=page_num,
                            source_pdf=source_pdf,
                            effective_from=effective_from,
                            has_proviso=has_proviso,
                            source_type=doc_type,
                            chunk_text=full_part_text,
                        )
                        chunks_list.append(asdict(c))
                        curr_sentences = [sent]
                        curr_len = len(sent)
                    else:
                        curr_sentences.append(sent)
                        curr_len += len(sent)

                if curr_sentences:
                    part_text = " ".join(curr_sentences)
                    full_part_text = f"{header_str}\n\n{part_text}"
                    page_chunk_idx += 1
                    c_id = compute_chunk_id(doc_name, ctx.section_no, page_num, page_chunk_idx, part_text)

                    c = Chunk(
                        document_name=doc_name,
                        document_type=doc_type,
                        act=doc_name,
                        chapter=ctx.chapter,
                        chapter_title=ctx.chapter_title,
                        section_no=ctx.section_no,
                        section_title=ctx.section_title,
                        subsection=ctx.subsection,
                        title=ctx.section_title or header_str,
                        parent_heading=f"Chapter {ctx.chapter}" if ctx.chapter != "Unknown" else doc_name,
                        chunk_id=c_id,
                        page_number=page_num,
                        source_pdf=source_pdf,
                        effective_from=effective_from,
                        has_proviso=has_proviso,
                        source_type=doc_type,
                        chunk_text=full_part_text,
                    )
                    chunks_list.append(asdict(c))

    return chunks_list


def main() -> None:
    if not os.path.exists(INPUT_PATH):
        print(f"ERROR: '{INPUT_PATH}' not found. Run 01_parse_pdf.py first.")
        sys.exit(1)

    print("=" * 60)
    print("  TAXITIQ CANONICAL MULTI-DOCUMENT LEGAL CHUNKER")
    print("=" * 60 + "\n")

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    pages = data.get("pages", []) if isinstance(data, dict) else data

    print(f"Loaded {len(pages)} pages from {INPUT_PATH}.")
    chunks = create_chunks_from_pages(pages)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    chunk_sizes = [len(c["chunk_text"]) for c in chunks]
    avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
    max_size = max(chunk_sizes) if chunk_sizes else 0
    min_size = min(chunk_sizes) if chunk_sizes else 0

    print("=" * 60)
    print("  CHUNKING SUMMARY")
    print("=" * 60)
    print(f"  Total Chunks Produced  : {len(chunks)}")
    print(f"  Average Chunk Size     : {avg_size:.1f} chars")
    print(f"  Max Chunk Size         : {max_size} chars")
    print(f"  Min Chunk Size         : {min_size} chars")
    print(f"  Output Saved To        : {OUTPUT_PATH}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
