"""Diagnostic script to analyze both JSON files for RAG readiness."""
import json
from collections import Counter

# ─── 1. Analyze parsed_output.json ───────────────────────────────
print("=" * 60)
print("  ANALYSIS: parsed_output.json")
print("=" * 60)

pages = json.load(open("parsed_output.json", "r", encoding="utf-8"))
print(f"Total pages: {len(pages)}")

empty_pages = [p["page_number"] for p in pages if not p["text"].strip()]
short_pages = [p["page_number"] for p in pages if 0 < len(p["text"].strip()) < 50]
no_heading_pages = [p["page_number"] for p in pages if not p["detected_headings"]]

print(f"Empty pages: {len(empty_pages)}")
print(f"Very short pages (<50 chars): {len(short_pages)} -> {short_pages[:20]}")
print(f"Pages with NO headings: {len(no_heading_pages)} / {len(pages)}")

all_headings = []
for p in pages:
    all_headings.extend(p["detected_headings"])
print(f"Total headings detected: {len(all_headings)}")
print("Sample headings (first 15):")
for h in all_headings[:15]:
    print(f"  -> {h[:120]}")

# Check for false-positive headings (footnotes, cross-references)
false_positives = [h for h in all_headings if h.lower().startswith("section ") and "of the" in h.lower()]
print(f"\nLikely FALSE-POSITIVE headings (cross-references like 'section X of the Y Act'): {len(false_positives)}")
for h in false_positives[:10]:
    print(f"  -> {h[:120]}")

total_chars = sum(len(p["text"]) for p in pages)
non_ascii = sum(1 for p in pages for c in p["text"] if ord(c) > 127)
print(f"\nTotal chars: {total_chars:,}  Non-ASCII: {non_ascii:,} ({non_ascii/total_chars*100:.1f}%)")

# ─── 2. Analyze chunks.json ─────────────────────────────────────
print("\n" + "=" * 60)
print("  ANALYSIS: chunks.json")
print("=" * 60)

chunks = json.load(open("chunks.json", "r", encoding="utf-8"))
print(f"Total chunks: {len(chunks)}")

# Metadata completeness
unknown_chapter = sum(1 for c in chunks if c["chapter"] == "Unknown")
unknown_section = sum(1 for c in chunks if c["section_no"] == "Unknown")
empty_chapter_title = sum(1 for c in chunks if not c["chapter_title"])
empty_section_title = sum(1 for c in chunks if not c["section_title"])
empty_subsection = sum(1 for c in chunks if not c["subsection"])

print(f"\n--- Metadata Completeness ---")
print(f"chapter = 'Unknown':     {unknown_chapter} / {len(chunks)} ({unknown_chapter/len(chunks)*100:.1f}%)")
print(f"section_no = 'Unknown':  {unknown_section} / {len(chunks)} ({unknown_section/len(chunks)*100:.1f}%)")
print(f"chapter_title EMPTY:     {empty_chapter_title} / {len(chunks)} ({empty_chapter_title/len(chunks)*100:.1f}%)")
print(f"section_title EMPTY:     {empty_section_title} / {len(chunks)} ({empty_section_title/len(chunks)*100:.1f}%)")
print(f"subsection EMPTY:        {empty_subsection} / {len(chunks)} ({empty_subsection/len(chunks)*100:.1f}%)")

# Chunk size distribution
lengths = [len(c["chunk_text"]) for c in chunks]
buckets = {"<100": 0, "100-200": 0, "200-500": 0, "500-800": 0, "800-1200": 0, "1200-1500": 0, ">1500": 0}
for l in lengths:
    if l < 100: buckets["<100"] += 1
    elif l < 200: buckets["100-200"] += 1
    elif l < 500: buckets["200-500"] += 1
    elif l < 800: buckets["500-800"] += 1
    elif l < 1200: buckets["800-1200"] += 1
    elif l < 1500: buckets["1200-1500"] += 1
    else: buckets[">1500"] += 1

print(f"\n--- Chunk Size Distribution ---")
for bucket, count in buckets.items():
    bar = "#" * (count // 20)
    print(f"  {bucket:>10}: {count:>5} ({count/len(chunks)*100:5.1f}%)  {bar}")

# Proviso detection accuracy
proviso_in_text = sum(1 for c in chunks if "provided that" in c["chunk_text"].lower())
proviso_flag = sum(1 for c in chunks if c["has_proviso"])
print(f"\n--- Proviso Detection ---")
print(f"has_proviso=True flag:       {proviso_flag}")
print(f"'Provided that' in text:     {proviso_in_text}")
print(f"MISSED (text but no flag):   {proviso_in_text - proviso_flag}")

# Section title quality — detect body text captured as title
bad_titles = [(c["section_no"], c["section_title"]) for c in chunks if len(c["section_title"]) > 80]
unique_bad = list(set(bad_titles))
print(f"\n--- Section Title Quality ---")
print(f"Titles > 80 chars (likely body text as title): {len(unique_bad)} unique")
for sno, t in unique_bad[:8]:
    print(f"  Section {sno}: \"{t[:100]}...\"")

# Duplicate chunks
texts = [c["chunk_text"] for c in chunks]
dupes = len(texts) - len(set(texts))
print(f"\n--- Duplicates ---")
print(f"Exact duplicate chunks: {dupes}")

# Sample chunks with Unknown metadata
print(f"\n--- Sample chunks with chapter='Unknown' ---")
for c in chunks[:5]:
    if c["chapter"] == "Unknown":
        print(f"  [{c['section_no']}] {c['chunk_text'][:150]}...")

# Chunks that are too small to be useful for RAG
tiny_chunks = [(i, c) for i, c in enumerate(chunks) if len(c["chunk_text"]) < 100]
print(f"\n--- Tiny Chunks (<100 chars, likely noise) ---")
print(f"Count: {len(tiny_chunks)}")
for i, c in tiny_chunks[:5]:
    print(f"  Chunk #{i}: \"{c['chunk_text']}\"")

# Overall score
print("\n" + "=" * 60)
print("  RAG READINESS SCORECARD")
print("=" * 60)
issues = []
if unknown_chapter / len(chunks) > 0.05:
    issues.append(f"HIGH: {unknown_chapter/len(chunks)*100:.0f}% chunks have chapter='Unknown'")
if unknown_section / len(chunks) > 0.05:
    issues.append(f"HIGH: {unknown_section/len(chunks)*100:.0f}% chunks have section='Unknown'")
if empty_chapter_title / len(chunks) > 0.50:
    issues.append(f"MEDIUM: {empty_chapter_title/len(chunks)*100:.0f}% chunks missing chapter_title")
if empty_section_title / len(chunks) > 0.20:
    issues.append(f"MEDIUM: {empty_section_title/len(chunks)*100:.0f}% chunks missing section_title")
if len(unique_bad) > 10:
    issues.append(f"HIGH: {len(unique_bad)} sections have body text captured as section_title")
if proviso_in_text - proviso_flag > 5:
    issues.append(f"HIGH: {proviso_in_text - proviso_flag} chunks contain 'Provided that' but has_proviso=False")
if dupes > 10:
    issues.append(f"MEDIUM: {dupes} exact duplicate chunks")
if len(tiny_chunks) > 20:
    issues.append(f"LOW: {len(tiny_chunks)} chunks under 100 chars (noise)")
over_1200 = sum(1 for l in lengths if l > 1200)
if over_1200 / len(chunks) > 0.10:
    issues.append(f"MEDIUM: {over_1200/len(chunks)*100:.0f}% chunks exceed 1200-char limit")

if issues:
    print(f"  Found {len(issues)} issue(s):\n")
    for issue in issues:
        print(f"  [!] {issue}")
else:
    print("  [OK] No major issues found!")
print("=" * 60)
