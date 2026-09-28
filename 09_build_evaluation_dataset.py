"""
09_build_evaluation_dataset.py
==============================
Builds evaluation_dataset.json by grounding questions in the actual corpus (chunks.json)
and validating their identities against ChromaDB.
"""

from __future__ import annotations

import json
import os
import hashlib
import re
import sys
from typing import Any, Dict, List, Tuple

import chromadb
from evaluation_utils import compute_overlaps

CHUNKS_PATH: str = "chunks.json"
CHROMA_DIR: str = "chroma_db"
COLLECTION_NAME: str = "indian_tax_law_corpus_v1"
DATASET_OUT: str = "evaluation_dataset.json"
REJECTED_OUT: str = "evaluation_rejected_candidates.json"


def generate_chunk_id(
    chunk_text: str,
    index: int,
    section_no: str,
    chapter: str,
    subsection: str,
) -> str:
    """Deterministic chunk ID generation matching 03_ingest.py."""
    sec = str(section_no or "Unknown").strip()
    ch = str(chapter or "Unknown").strip()
    sub = str(subsection or "").strip()
    text = str(chunk_text or "").strip()
    
    stable_str = f"idx_{index}_sec_{sec}_ch_{ch}_sub_{sub}_text_{text}"
    return hashlib.sha256(stable_str.encode("utf-8")).hexdigest()[:32]


def normalize_for_match(text: str) -> str:
    """Normalize text to facilitate robust substring matching of evidence."""
    if not text:
        return ""
    val = text.lower()
    # 1. Clean hyphenated newlines first
    val = re.sub(r"-\s*\n\s*", "", val)
    # 2. Normalize quotes and special characters
    val = val.replace("“", "").replace("”", "").replace("‘", "").replace("’", "").replace("'", "").replace("\"", "")
    val = val.replace("`", "")
    # 3. Strip all non-alphanumeric (replace with space to preserve boundaries)
    val = re.sub(r"[^a-z0-9 ]+", " ", val)
    # 4. Collapse spaces
    val = re.sub(r"\s+", " ", val)
    return val.strip()


def validate_chunk_ids() -> Tuple[bool, int, int, int, int, int]:
    """Validates chunk IDs against ChromaDB collection."""
    if not os.path.exists(CHUNKS_PATH):
        print(f"Error: {CHUNKS_PATH} not found.")
        sys.exit(1)
        
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)
        
    computed_ids: List[str] = []
    for i, c in enumerate(chunks):
        cid = generate_chunk_id(
            chunk_text=c.get("chunk_text", ""),
            index=i,
            section_no=c.get("section_no", "Unknown"),
            chapter=c.get("chapter", "Unknown"),
            subsection=c.get("subsection", "")
        )
        computed_ids.append(cid)
        
    unique_computed = set(computed_ids)
    
    # Retrieve ChromaDB collection IDs
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        col = client.get_collection(COLLECTION_NAME)
        count = col.count()
        page_size = 10000
        offset = 0
        db_ids: List[str] = []
        while offset < count:
            res = col.get(limit=page_size, offset=offset, include=[])
            if res and res.get("ids"):
                db_ids.extend(res["ids"])
            else:
                break
            offset += page_size
        collection_ids = set(db_ids)
    except Exception as e:
        print(f"Error reading ChromaDB: {e}")
        sys.exit(1)
        
    missing_ids = unique_computed - collection_ids
    extra_ids = collection_ids - unique_computed
    identity_match = (len(missing_ids) == 0 and len(extra_ids) == 0 and len(unique_computed) == len(chunks))
    
    print("\nCHUNK IDENTITY VALIDATION")
    print(f"Computed IDs       : {len(computed_ids)}")
    print(f"Collection IDs     : {len(collection_ids)}")
    print(f"Unique Computed IDs: {len(unique_computed)}")
    print(f"Missing IDs        : {len(missing_ids)}")
    print(f"Extra IDs          : {len(extra_ids)}")
    print(f"Identity Match     : {identity_match}\n")
    
    if not identity_match:
        print("CHUNK_IDENTITY_MISMATCH")
        sys.exit(1)
        
    return identity_match, len(computed_ids), len(collection_ids), len(unique_computed), len(missing_ids), len(extra_ids)


CANDIDATE_QUESTIONS: List[Dict[str, Any]] = [
    # --- DEFINITION (10 items) ---
    {
        "candidate_id": "Q01",
        "question": "What is the definition of a tax year under the Income-tax Act 2025?",
        "question_type": "definition",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "LEXICAL",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["3"],
        "gold_subsections": ["1"],
        "gold_keywords": ["tax year", "twelve months", "financial year", "commencing", "1st April"],
        "gold_numeric_claims": ["twelve", "1st April"],
        "source_chunk_indices": [148],
        "source_text_evidence": "For the purposes of this Act, 'tax year' means the twelve months period of the financial year commencing on the 1st April.",
        "notes": "Direct definition of tax year."
    },
    {
        "candidate_id": "Q02",
        "question": "Who is considered an assessee according to Section 2 of the Income-tax Act 2025?",
        "question_type": "definition",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "LEXICAL",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["2"],
        "gold_subsections": ["11"],
        "gold_keywords": ["assessee", "person", "payable", "deemed", "default"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [17],
        "source_text_evidence": "'assessee' means a person by whom any tax or any other sum of money is payable under this Act, and includes",
        "notes": "Direct definition of assessee."
    },
    {
        "candidate_id": "Q03",
        "question": "Define the term approved gratuity fund as per Section 2 of the Income-tax Act 2025.",
        "question_type": "definition",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "LEXICAL",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["2"],
        "gold_subsections": ["9"],
        "gold_keywords": ["approved gratuity fund", "approving authority", "Schedule XI"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [15],
        "source_text_evidence": "'approved gratuity fund' means a gratuity fund, which is approved and continues to be approved by the approving authority as per Part B of Schedule XI",
        "notes": "Gratuity fund definition."
    },
    {
        "candidate_id": "Q04",
        "question": "How is a company in which the public are substantially interested defined in the Income-tax Act 2025?",
        "question_type": "definition",
        "difficulty": "medium",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["3"],
        "gold_subsections": ["29"],
        "gold_keywords": ["company", "public are substantially interested", "owned by the Government", "Reserve Bank", "40%", "Nidhi"],
        "gold_numeric_claims": ["40%"],
        "source_chunk_indices": [41],
        "source_text_evidence": "'company in which the public are substantially interested' means- (a) a company owned by the Government or the Reserve Bank of India or in which at least 40% of the shares",
        "notes": "Public interest company definition."
    },
    {
        "candidate_id": "Q05",
        "question": "What is the meaning of population under Section 3 of the Act?",
        "question_type": "definition",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "LEXICAL",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["3"],
        "gold_subsections": ["C"],
        "gold_keywords": ["population", "census", "relevant figures", "first day of the tax year"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [33],
        "source_text_evidence": "'population' shall mean the population according to the last preceding census of which the relevant figures have been published before the first day of the tax year",
        "notes": "Definition of population."
    },
    {
        "candidate_id": "Q06",
        "question": "Define the term property under the Income-tax Act 2025.",
        "question_type": "definition",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "LEXICAL",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["3"],
        "gold_subsections": ["D"],
        "gold_keywords": ["property", "rights", "Indian company", "management", "control"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [33],
        "source_text_evidence": "'property' includes any rights in or in relation to an Indian company, including rights of management or control",
        "notes": "Definition of property."
    },
    {
        "candidate_id": "Q07",
        "question": "Define the term securities as per Section 3 of the Act.",
        "question_type": "definition",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "LEXICAL",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["3"],
        "gold_subsections": ["E"],
        "gold_keywords": ["securities", "Securities Contracts (Regulation) Act, 1956", "2(h)"],
        "gold_numeric_claims": ["1956"],
        "source_chunk_indices": [33],
        "source_text_evidence": "'securities' shall have the same meaning as assigned to it in section 2(h) of the Securities Contracts (Regulation) Act, 1956",
        "notes": "Definition of securities."
    },
    {
        "candidate_id": "Q08",
        "question": "How is standard deduction defined under the Income-tax Act 2025?",
        "question_type": "definition",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["2"],
        "gold_subsections": [],
        "gold_keywords": ["Standard deduction", "75000", "50000", "salary", "202(1)"],
        "gold_numeric_claims": ["75000", "50000"],
        "source_chunk_indices": [245],
        "source_text_evidence": "Standard deduction. (a) 75000 or the salary, whichever is less, where income-tax is computed under section 202(1); (b) 50000 or the salary, whichever is less, in any other case.",
        "notes": "Standard deduction values definition."
    },
    {
        "candidate_id": "Q09",
        "question": "What is the meaning of rates in force under Chapter I of the Act?",
        "question_type": "definition",
        "difficulty": "medium",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["3"],
        "gold_subsections": ["90"],
        "gold_keywords": ["rate or rates in force", "rates in force", "Finance Act of the relevant year"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [115],
        "source_text_evidence": "means the rate or rates of income-tax specified in this behalf in the Finance Act of the relevant year;",
        "notes": "Definition of rates in force."
    },
    {
        "candidate_id": "Q10",
        "question": "What is the definition of standard deduction in any other case, other than section 202(1)?",
        "question_type": "definition",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["2"],
        "gold_subsections": [],
        "gold_keywords": ["Standard deduction", "50000", "salary", "whichever is less"],
        "gold_numeric_claims": ["50000"],
        "source_chunk_indices": [245],
        "source_text_evidence": "(b) 50000 or the salary, whichever is less, in any other case.",
        "notes": "Other case standard deduction."
    },

    # --- SECTION LOOKUP (8 items) ---
    {
        "candidate_id": "Q11",
        "question": "Where is standard deduction provided in Chapter IV of the Act, and what is its limit?",
        "question_type": "section_lookup",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "LEXICAL",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["2"],
        "gold_subsections": [],
        "gold_keywords": ["Standard deduction", "Chapter IV", "Section 2", "75000", "50000"],
        "gold_numeric_claims": ["75000"],
        "source_chunk_indices": [245],
        "source_text_evidence": "Standard deduction. (a) 75000 or the salary, whichever is less",
        "notes": "Section lookup for standard deduction."
    },
    {
        "candidate_id": "Q12",
        "question": "What does Section 3(1) of the Income-tax Act 2025 specify?",
        "question_type": "section_lookup",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "LEXICAL",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["3"],
        "gold_subsections": ["1"],
        "gold_keywords": ["tax year", "twelve months", "financial year commencing on the 1st April"],
        "gold_numeric_claims": ["1st April"],
        "source_chunk_indices": [148],
        "source_text_evidence": "3. (1) For the purposes of this Act, 'tax year' means the twelve months period of the financial year commencing on the 1st April.",
        "notes": "Section lookup for Section 3(1)."
    },
    {
        "candidate_id": "Q13",
        "question": "What limit is specified on the aggregate amount of deductions under Section 122(2)?",
        "question_type": "section_lookup",
        "difficulty": "medium",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "LEXICAL",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["122"],
        "gold_subsections": ["2"],
        "gold_keywords": ["aggregate amount", "deductions", "gross total income"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [989],
        "source_text_evidence": "(2) The aggregate amount of the deductions under this Chapter shall not, in any case, exceed the gross total income of the assessee.",
        "notes": "Section 122(2) lookup."
    },
    {
        "candidate_id": "Q14",
        "question": "Explain the rules under Section 122(3) regarding deductions for an association of persons.",
        "question_type": "section_lookup",
        "difficulty": "medium",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "LEXICAL",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["122"],
        "gold_subsections": ["3"],
        "gold_keywords": ["association of persons", "body of individuals", "deduction under section", "133 or 135 or 137 or 138 or 141 or 142 or 143"],
        "gold_numeric_claims": ["133", "135", "137", "138", "141", "142", "143"],
        "source_chunk_indices": [990],
        "source_text_evidence": "If the deduction under section 133 or 135 or 137 or 138 or 141 or 142 or 143 is admissible in computing the total income of an association of persons or a body of",
        "notes": "Section 122(3) lookup."
    },
    {
        "candidate_id": "Q15",
        "question": "Look up Section 123 and state its general provision for individuals.",
        "question_type": "section_lookup",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "LEXICAL",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["123"],
        "gold_subsections": [],
        "gold_keywords": ["individual", "Hindu undivided family", "deduction", "Schedule XV", "150000"],
        "gold_numeric_claims": ["150000"],
        "source_chunk_indices": [999],
        "source_text_evidence": "123. An individual or a Hindu undivided family, shall be allowed a deduction of the whole of the amount paid or deposited in the tax year, being the aggregate of the sums enumerated in Schedule XV, as does not exceed 150000",
        "notes": "Section 123 lookup."
    },
    {
        "candidate_id": "Q16",
        "question": "What does Section 459(3) say about daily penalty when a failure continues after order service?",
        "question_type": "section_lookup",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "LEXICAL",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["459"],
        "gold_subsections": ["3"],
        "gold_keywords": ["penalty of fifty thousand rupees", "every day", "failure continues", "service of such order"],
        "gold_numeric_claims": ["fifty thousand"],
        "source_chunk_indices": [3320],
        "source_text_evidence": "impose penalty of fifty thousand rupees for every day for which such failure continues beginning from the date of service of such order.",
        "notes": "Section 459(3) lookup."
    },
    {
        "candidate_id": "Q17",
        "question": "Look up Section 459(2) and state the penalty for failing to produce reporting entity documents.",
        "question_type": "section_lookup",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "LEXICAL",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["459"],
        "gold_subsections": ["2"],
        "gold_keywords": ["reporting entity", "fails to produce the information", "5000", "every day"],
        "gold_numeric_claims": ["5000"],
        "source_chunk_indices": [3319],
        "source_text_evidence": "penalty of 5000 for every day during which the failure continues",
        "notes": "Section 459(2) lookup."
    },
    {
        "candidate_id": "Q18",
        "question": "What are the rules regarding daily penalty under Section 459(1) of the Act?",
        "question_type": "section_lookup",
        "difficulty": "medium",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "LEXICAL",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["459"],
        "gold_subsections": ["1"],
        "gold_keywords": ["reporting entity", "511", "fails to do so", "5000", "15000", "one month"],
        "gold_numeric_claims": ["5000", "15000"],
        "source_chunk_indices": [3318],
        "source_text_evidence": "(a) 5000 for every day for which the failure continues, if the period of failure does not exceed one month; (b) 15000 for every day for which the failure continues beyond the period of one month.",
        "notes": "Section 459(1) lookup."
    },

    # --- ELIGIBILITY/CONDITION (8 items) ---
    {
        "candidate_id": "Q19",
        "question": "Under what events is an employee eligible for gratuity deduction under Section 6 of Chapter IV?",
        "question_type": "eligibility",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["6"],
        "gold_subsections": [],
        "gold_keywords": ["gratuity", "retirement", "incapacitated", "termination", "employee"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [250],
        "source_text_evidence": "on his retirement; or\non termination of his",
        "notes": "Gratuity eligibility events."
    },
    {
        "candidate_id": "Q20",
        "question": "What conditions must a pension commutation satisfy under Section 7 of Chapter IV to be deductible?",
        "question_type": "eligibility",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["7"],
        "gold_subsections": [],
        "gold_keywords": ["commutation of pension", "Civil Pensions (Commutation) Rules", "defence services", "civil services"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [251],
        "source_text_evidence": "7. Payment in commutation of Entire amount. pension received (a) under the Civil Pensions (Commutation) Rules of the Central Government; or (b) under any similar scheme",
        "notes": "Pension commutation rules."
    },
    {
        "candidate_id": "Q21",
        "question": "Who is eligible to claim standard deduction from salary income under Chapter IV?",
        "question_type": "eligibility",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["2"],
        "gold_subsections": [],
        "gold_keywords": ["standard deduction", "salary", "less", "computed"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [245],
        "source_text_evidence": "Standard deduction. (a) 75000 or the salary, whichever is less, where income-tax is computed under section 202(1); (b) 50000 or the salary, whichever is less, in any other case.",
        "notes": "Salary earners standard deduction."
    },
    {
        "candidate_id": "Q22",
        "question": "What are the eligibility conditions for a Lieutenant Governor's Relief Fund donation to qualify under Section 133?",
        "question_type": "eligibility",
        "difficulty": "medium",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["133"],
        "gold_subsections": ["xv"],
        "gold_keywords": ["Chief Minister's Relief Fund", "Lieutenant Governor's Relief Fund", "only fund of its kind", "control of the Chief Secretary", "administered"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [1067],
        "source_text_evidence": "Lieutenant Governor's Relief Fund, if the fund meets all the following conditions: (A) it is the only fund of its kind established in the State or the Union territory; (B) it is under the overall control of the Chief Secretary or the Department of Finance of the respective State or the Union territory; (C) it is administered in a manner specified by the State Government or the Lieutenant Governor;",
        "notes": "Relief fund conditions."
    },
    {
        "candidate_id": "Q23",
        "question": "What are the conditions for deducting contributions to the Swachh Bharat Kosh under Section 133?",
        "question_type": "eligibility",
        "difficulty": "medium",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["133"],
        "gold_subsections": ["xx"],
        "gold_keywords": ["Swachh Bharat Kosh", "Corporate Social Responsibility", "section 135(5) of the Companies Act, 2013"],
        "gold_numeric_claims": ["135"],
        "source_chunk_indices": [1067],
        "source_text_evidence": "the Swachh Bharat Kosh, set up by the Central Government, other than the sum spent by the assessee in pursuance of Corporate Social Responsibility under section 135(5) of the Companies Act, 2013",
        "notes": "Swachh Bharat Kosh CSR exception."
    },
    {
        "candidate_id": "Q24",
        "question": "What are the requirements for claiming a donation deduction for Clean Ganga Fund under Section 133?",
        "question_type": "eligibility",
        "difficulty": "medium",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["133"],
        "gold_subsections": ["xxi"],
        "gold_keywords": ["Clean Ganga Fund", "resident", "Corporate Social Responsibility", "section 135(5) of the Companies Act, 2013"],
        "gold_numeric_claims": ["135"],
        "source_chunk_indices": [1067],
        "source_text_evidence": "the Clean Ganga Fund, set up by the Central Government, where such assessee is a resident and such sum is other than the sum spent by the assessee in pursuance of Corporate Social Responsibility under section 135(5) of the Companies Act, 2013",
        "notes": "Clean Ganga Fund conditions."
    },
    {
        "candidate_id": "Q25",
        "question": "Under what condition can an individual employee claim a deduction under Section 124(1) for employer pension contributions?",
        "question_type": "eligibility",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["124"],
        "gold_subsections": ["1"],
        "gold_keywords": ["individual employed by any employer", "contribution in his account", "pension scheme", "notified by the Central Government"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [1000],
        "source_text_evidence": "Where in the case of an assessee, being an individual employed by any e mployer, if the employer makes any contribution",
        "notes": "Employer pension contribution eligibility."
    },
    {
        "candidate_id": "Q26",
        "question": "Can Hindu undivided families claim a deduction under Section 123?",
        "question_type": "eligibility",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["123"],
        "gold_subsections": [],
        "gold_keywords": ["individual", "Hindu undivided family", "deduction", "Schedule XV"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [999],
        "source_text_evidence": "123. An individual or a Hindu undivided family, shall be allowed a deduction of the whole of the amount paid or deposited in the tax year",
        "notes": "HUF eligibility for Section 123."
    },

    # --- DEDUCTION/EXEMPTION (8 items) ---
    {
        "candidate_id": "Q27",
        "question": "What is the standard deduction amount for salary earners whose tax is computed under section 202(1)?",
        "question_type": "deduction",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["2"],
        "gold_subsections": [],
        "gold_keywords": ["Standard deduction", "75000", "salary", "202(1)"],
        "gold_numeric_claims": ["75000"],
        "source_chunk_indices": [245],
        "source_text_evidence": "(a) 75000 or the salary, whichever is less, where income-tax is computed under section 202(1);",
        "notes": "Standard deduction value for Section 202(1)."
    },
    {
        "candidate_id": "Q28",
        "question": "What is the standard deduction limit for salary earners in general cases other than under section 202(1)?",
        "question_type": "deduction",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["2"],
        "gold_subsections": [],
        "gold_keywords": ["Standard deduction", "50000", "salary", "whichever is less"],
        "gold_numeric_claims": ["50000"],
        "source_chunk_indices": [245],
        "source_text_evidence": "(b) 50000 or the salary, whichever is less, in any other case.",
        "notes": "General standard deduction value."
    },
    {
        "candidate_id": "Q29",
        "question": "How is the deduction amount for gratuity calculated for a non-government employee under Section 6 of Chapter IV?",
        "question_type": "deduction",
        "difficulty": "hard",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["6"],
        "gold_subsections": [],
        "gold_keywords": ["gratuity", "retirement", "minimum of", "actual gratuity", "amount specified", "half month's salary"],
        "gold_numeric_claims": ["ten"],
        "source_chunk_indices": [250],
        "source_text_evidence": "average salary for ten months immediately preceding the month when any such event occurs;",
        "notes": "Gratuity calculation details."
    },
    {
        "candidate_id": "Q30",
        "question": "What deduction is available for pension commutation received under Civil Pensions Rules of the Central Government?",
        "question_type": "deduction",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["7"],
        "gold_subsections": [],
        "gold_keywords": ["Pension commutation", "Civil Pensions (Commutation) Rules", "Entire amount"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [251],
        "source_text_evidence": "7. Payment in commutation of Entire amount. pension received (a) under the Civil Pensions (Commutation) Rules",
        "notes": "Civil pension commutation deduction."
    },
    {
        "candidate_id": "Q31",
        "question": "What is the maximum deduction allowed under Section 123 of the Act, and which schedule does it refer to?",
        "question_type": "deduction",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["123"],
        "gold_subsections": [],
        "gold_keywords": ["deduction", "individual", "HUF", "Schedule XV", "150000"],
        "gold_numeric_claims": ["150000"],
        "source_chunk_indices": [999],
        "source_text_evidence": "deduction of the whole of the amount paid or deposited in the tax year, being the aggregate of the sums enumerated in Schedule XV, as does not exceed 150000",
        "notes": "Section 123 deduction limit and schedule."
    },
    {
        "candidate_id": "Q32",
        "question": "What deduction is available for contributions made by an employee under a Central Government pension scheme under Section 124(3)?",
        "question_type": "deduction",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["124"],
        "gold_subsections": ["3"],
        "gold_keywords": ["pension scheme", "individual", "not exceeding", "50000"],
        "gold_numeric_claims": ["50000"],
        "source_chunk_indices": [1002],
        "source_text_evidence": "deduction not exceeding 50000, in computation of his total income of the whole of the amount paid or deposited in the tax year by such individual in his account under a pension scheme",
        "notes": "Central government pension scheme limit."
    },
    {
        "candidate_id": "Q33",
        "question": "Is the donation made by an assessee to the PM CARES Fund eligible for a full deduction?",
        "question_type": "deduction",
        "difficulty": "medium",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["133"],
        "gold_subsections": ["1"],
        "gold_keywords": ["donations", "PM CARES FUND", "whole of the aggregate", "tax year"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [1066],
        "source_text_evidence": "the whole of the aggregate of the sum or the sums paid by the assessee, in the tax year as donations to (i) the National Defence Fund set up by the Central Government; or (ii) the Prime Minister's National Relief Fund or the Prime Minister's Citizen Assistance and Relief in Emergency Situations Fund (PM CARES FUND)",
        "notes": "PM CARES Fund donation exemption."
    },
    {
        "candidate_id": "Q34",
        "question": "What is the deduction amount allowed for donations made to Swachh Bharat Kosh?",
        "question_type": "deduction",
        "difficulty": "medium",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["133"],
        "gold_subsections": ["xx"],
        "gold_keywords": ["Swachh Bharat Kosh", "deduction", "donations"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [1067],
        "source_text_evidence": "the Swachh Bharat Kosh, set up by the Central Government, other than the sum spent by the assessee in pursuance of Corporate Social Responsibility",
        "notes": "Swachh Bharat Kosh donation deduction."
    },

    # --- RATE/NUMERIC (6 items) ---
    {
        "candidate_id": "Q35",
        "question": "What is the income tax rate for total income up to Rs. 4,00,000 under Section 202?",
        "question_type": "rate",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["202", "1"],
        "gold_subsections": [],
        "gold_keywords": ["400000", "Nil"],
        "gold_numeric_claims": ["400000"],
        "source_chunk_indices": [1487],
        "source_text_evidence": "1. Upto 400000 Nil",
        "notes": "Tax rate for slab up to 4 lakhs."
    },
    {
        "candidate_id": "Q36",
        "question": "What is the standard deduction percentage allowed on the annual value of house property under Section 22?",
        "question_type": "rate",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["22"],
        "gold_subsections": ["1"],
        "gold_keywords": ["house property", "deductions", "annual value", "30%"],
        "gold_numeric_claims": ["30%"],
        "source_chunk_indices": [277],
        "source_text_evidence": "The income under the head 'Income from house property' shall be computed after making the following deductions: (a) 30% of the annual value;",
        "notes": "House property standard deduction rate."
    },
    {
        "candidate_id": "Q37",
        "question": "What is the deduction percentage allowed on arrears of rent or unrealised rent received under Section 23?",
        "question_type": "rate",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["23"],
        "gold_subsections": ["3"],
        "gold_keywords": ["arrears of rent", "unrealised rent", "deduction", "30%"],
        "gold_numeric_claims": ["30%"],
        "source_chunk_indices": [287],
        "source_text_evidence": "a sum equal to 30% of the arrears of rent or the unrealised rent referred to in sub-section (1) shall be allowed as deduction",
        "notes": "Arrears of rent deduction rate."
    },
    {
        "candidate_id": "Q38",
        "question": "What is the base percentage limit specified for employer contributions under Section 124(1)?",
        "question_type": "rate",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["124"],
        "gold_subsections": ["1"],
        "gold_keywords": ["pension scheme", "individual", "10%", "salary"],
        "gold_numeric_claims": ["10%"],
        "source_chunk_indices": [1000],
        "source_text_evidence": "does not exceed\n(b) 10%, where such contribution is made by an employer other than an employer referred to in clause (a),\nof his salary in the tax year.",
        "notes": "Base employer contribution rate."
    },
    {
        "candidate_id": "Q39",
        "question": "What is the pension contribution percentage substituted under Section 124(2) for assessees taxed under Section 202(1)?",
        "question_type": "rate",
        "difficulty": "medium",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["124"],
        "gold_subsections": ["2"],
        "gold_keywords": ["chargeable to tax", "202(1)", "14%", "substituted"],
        "gold_numeric_claims": ["14%"],
        "source_chunk_indices": [1001],
        "source_text_evidence": "Where the total income of the assessee is chargeable to tax under section 202(1), the provisions of sub-section (1) shall have effect as if for '10%' referred to in clause (b) of that sub-section, '14%' had been substituted.",
        "notes": "Substituted employer contribution rate."
    },
    {
        "candidate_id": "Q40",
        "question": "What is the highest marginal income tax rate for total income exceeding Rs. 24,00,000 under Section 202?",
        "question_type": "rate",
        "difficulty": "medium",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["202", "7"],
        "gold_subsections": [],
        "gold_keywords": ["Above", "2400000", "30%"],
        "gold_numeric_claims": ["2400000", "30%"],
        "source_chunk_indices": [1493],
        "source_text_evidence": "7. Above 2400000 30%",
        "notes": "Highest tax rate slab."
    },

    # --- DEADLINE/PROCEDURE (5 items) ---
    {
        "candidate_id": "Q41",
        "question": "What is the due date and minimum percentage requirement for the first installment of advance tax?",
        "question_type": "deadline",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["1"],
        "gold_subsections": [],
        "gold_keywords": ["advance tax", "15%", "15th June"],
        "gold_numeric_claims": ["15%", "15th June"],
        "source_chunk_indices": [3081],
        "source_text_evidence": "1. On or before the Not less than 15% of such advance tax. 15th June.",
        "notes": "First advance tax deadline."
    },
    {
        "candidate_id": "Q42",
        "question": "What cumulative percentage of advance tax must be paid on or before the 15th of September?",
        "question_type": "deadline",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["2"],
        "gold_subsections": [],
        "gold_keywords": ["advance tax", "45%", "15th September"],
        "gold_numeric_claims": ["45%", "15th September"],
        "source_chunk_indices": [3082],
        "source_text_evidence": "2. On or before the Not less than 45% of such advance tax, as reduced by the 15th September. amount, if any, paid in the earlier instalment.",
        "notes": "Second advance tax deadline."
    },
    {
        "candidate_id": "Q43",
        "question": "What is the requirement for advance tax payment due by 15th December?",
        "question_type": "deadline",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["3"],
        "gold_subsections": [],
        "gold_keywords": ["advance tax", "75%", "15th December"],
        "gold_numeric_claims": ["75%", "15th December"],
        "source_chunk_indices": [3083],
        "source_text_evidence": "3. On or before the Not less than 75% of such advance tax, as reduced by the 15th December. amount or amounts, if any, paid in the earlier instalment",
        "notes": "Third advance tax deadline."
    },
    {
        "candidate_id": "Q44",
        "question": "What is the final deadline for paying the full installment of advance tax?",
        "question_type": "deadline",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["4"],
        "gold_subsections": [],
        "gold_keywords": ["advance tax", "whole amount", "15th March"],
        "gold_numeric_claims": ["15th March"],
        "source_chunk_indices": [3084],
        "source_text_evidence": "4. On or before the The whole amount of such advance tax, as reduced by the 15th March. amount or amounts, if any, paid in the earlier instalment",
        "notes": "Fourth advance tax deadline."
    },
    {
        "candidate_id": "Q45",
        "question": "Is the cumulative advance tax percentage due by December 15th specified as seventy-five percent?",
        "question_type": "deadline",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["3"],
        "gold_subsections": [],
        "gold_keywords": ["advance tax", "75%", "15th December"],
        "gold_numeric_claims": ["75%", "15th December"],
        "source_chunk_indices": [3083],
        "source_text_evidence": "3. On or before the Not less than 75% of such advance tax, as reduced by the 15th December.",
        "notes": "Verify December 15th percentage."
    },

    # --- EXCEPTION/PENALTY (5 items) ---
    {
        "candidate_id": "Q46",
        "question": "What is the daily penalty under Section 459(1)(a) if a reporting entity fails to submit its report for under a month?",
        "question_type": "penalty",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["459"],
        "gold_subsections": ["1"],
        "gold_keywords": ["reporting entity", "penalty", "5000", "every day", "not exceed one month"],
        "gold_numeric_claims": ["5000"],
        "source_chunk_indices": [3318],
        "source_text_evidence": "(a) 5000 for every day for which the failure continues, if the period of failure does not exceed one month;",
        "notes": "Penalty for short reporting failure."
    },
    {
        "candidate_id": "Q47",
        "question": "What daily penalty applies under Section 459(1)(b) if a reporting entity default continues for more than a month?",
        "question_type": "penalty",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["459"],
        "gold_subsections": ["1"],
        "gold_keywords": ["reporting entity", "penalty", "15000", "every day", "beyond", "one month"],
        "gold_numeric_claims": ["15000"],
        "source_chunk_indices": [3318],
        "source_text_evidence": "(b) 15000 for every day for which the failure continues beyond the period of one month.",
        "notes": "Penalty for long reporting failure."
    },
    {
        "candidate_id": "Q48",
        "question": "What penalty can be imposed under Section 459(2) on reporting entities for failing to furnish requested information?",
        "question_type": "penalty",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["459"],
        "gold_subsections": ["2"],
        "gold_keywords": ["reporting entity", "fails to produce", "5000", "every day"],
        "gold_numeric_claims": ["5000"],
        "source_chunk_indices": [3319],
        "source_text_evidence": "prescribed authority under that section may impose on such entity, a penalty of 5000 for every day during which the failure continues",
        "notes": "Penalty for information default."
    },
    {
        "candidate_id": "Q49",
        "question": "What penalty applies under Section 459(3) for continuing failure after the order has been served on the reporting entity?",
        "question_type": "penalty",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["459"],
        "gold_subsections": ["3"],
        "gold_keywords": ["penalty of fifty thousand rupees", "every day", "failure continues", "service of such order"],
        "gold_numeric_claims": ["fifty thousand"],
        "source_chunk_indices": [3320],
        "source_text_evidence": "prescribed authority may impose penalty of fifty thousand rupees for every day for which such failure continues beginning from the date of service of such order.",
        "notes": "Penalty for post-service defaults."
    },
    {
        "candidate_id": "Q50",
        "question": "Does a daily penalty of 5000 rupees apply under Section 459(2) for failing to produce records?",
        "question_type": "penalty",
        "difficulty": "easy",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["459"],
        "gold_subsections": ["2"],
        "gold_keywords": ["fails to produce", "penalty of", "5000", "every day"],
        "gold_numeric_claims": ["5000"],
        "source_chunk_indices": [3319],
        "source_text_evidence": "penalty of 5000 for every day during which the failure continues",
        "notes": "Verify records default penalty."
    },

    # --- CROSS-SECTION REASONING (5 items) ---
    {
        "candidate_id": "Q51",
        "question": "Compare the tax consequences under Section 11(2) and Section 12(2) when the conditions for income exclusions are not satisfied by a person versus a political party or electoral trust.",
        "question_type": "cross_section",
        "difficulty": "hard",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "REASONING",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["11", "12"],
        "gold_subsections": ["2"],
        "gold_keywords": ["not satisfied", "charged to tax", "total income", "political party", "electoral trust", "Schedules"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [214, 219],
        "source_text_evidence": "Wherever the conditions referred to in the Schedules referred in sub-section (1) are not satisfied in any tax year in respect of any income enumerated in the said Schedules, such income shall be charged to tax under this Act on the total income for that tax year.\nWherever the conditions referred to in Schedule VIII are not satisfied in any tax year in respect of any income enumerated in the said Schedule, such income shall be charged to tax under this Act for that tax year.",
        "notes": "Compare non-compliance consequences for charitable entities vs political parties."
    },
    {
        "candidate_id": "Q52",
        "question": "How does Section 124(2) modify the contribution limit of 10% mentioned in Section 124(1) for assessees taxed under Section 202(1)?",
        "question_type": "cross_section",
        "difficulty": "medium",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "REASONING",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["124"],
        "gold_subsections": ["1", "2"],
        "gold_keywords": ["10%", "14%", "substituted", "chargeable to tax under section 202(1)"],
        "gold_numeric_claims": ["10", "14"],
        "source_chunk_indices": [1000, 1001],
        "source_text_evidence": "contribution in his account under a pension scheme\nchargeable to tax under section 202(1), the provisions of sub-section (1) shall have effect as if for \"10%\" referred to in clause (b) of that sub-section, \"14%\" had been substituted.",
        "notes": "Requires reasoning over Section 124(1) and Section 124(2) to explain substitution."
    },
    {
        "candidate_id": "Q53",
        "question": "Compare the daily penalties for a reporting entity's initial default under Section 459(1) versus a continuing default after order service under Section 459(3).",
        "question_type": "cross_section",
        "difficulty": "hard",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "REASONING",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["459"],
        "gold_subsections": ["1", "3"],
        "gold_keywords": ["penalty", "5000", "15000", "50000", "continuing", "order has been served"],
        "gold_numeric_claims": ["5000", "15000", "fifty thousand"],
        "source_chunk_indices": [3318, 3320],
        "source_text_evidence": "(a) 5000 for every day for which the failure continues, if the period of failure does not exceed one month; (b) 15000 for every day for which the failure continues beyond the period of one month.\nfifty thousand rupees for every day for which such failure continues beginning from the date of service of such order.",
        "notes": "Requires reasoning across multiple chunks to outline rates (5k/15k vs 50k)."
    },
    {
        "candidate_id": "Q54",
        "question": "Compare the deduction limit for employee pension contributions under Section 124(3) versus employer pension contribution under Section 124(1).",
        "question_type": "cross_section",
        "difficulty": "hard",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "REASONING",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["124"],
        "gold_subsections": ["1", "3"],
        "gold_keywords": ["deduction", "employer makes any contribution", "pension scheme", "50000", "14%"],
        "gold_numeric_claims": ["50000"],
        "source_chunk_indices": [1000, 1002],
        "source_text_evidence": "contribution in his account under a pension scheme\ndeduction not exceeding 50000, in computation of his total income of the whole of the amount paid or deposited in the tax year by such individual in his account under a pension scheme",
        "notes": "Requires comparing limits in Section 124(1) and Section 124(3)."
    },
    {
        "candidate_id": "Q55",
        "question": "Explain standard daily penalties under Section 459(1) for reporting entity default and Section 459(2) for failing to produce records.",
        "question_type": "cross_section",
        "difficulty": "medium",
        "expected_corpus_status": "SUPPORTED",
        "query_formulation_type": "REASONING",
        "gold_act": "Income-tax Act 2025",
        "gold_sections": ["459"],
        "gold_subsections": ["1", "2"],
        "gold_keywords": ["5000", "15000", "reporting entity", "fails to produce the information"],
        "gold_numeric_claims": ["5000"],
        "source_chunk_indices": [3318, 3319],
        "source_text_evidence": "5000 for every day for which the failure continues, if the period of failure does not exceed one month\npenalty of 5000 for every day during which the failure continues",
        "notes": "Requires reasoning over Section 459(1) and Section 459(2) penalty provisions."
    },

    # --- OUT-OF-CORPUS (5 items) ---
    {
        "candidate_id": "Q56",
        "question": "What are the registration requirements and thresholds for GST in India?",
        "question_type": "out_of_corpus",
        "difficulty": "easy",
        "expected_corpus_status": "NOT_SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Unknown",
        "gold_sections": [],
        "gold_subsections": [],
        "gold_keywords": ["GST", "registration", "Goods and Services Tax"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [],
        "source_text_evidence": "",
        "notes": "GST rules are completely out of corpus for the Income-tax Act 2025."
    },
    {
        "candidate_id": "Q57",
        "question": "What is the penalty for late filing of income tax returns in the United States under the IRS code?",
        "question_type": "out_of_corpus",
        "difficulty": "easy",
        "expected_corpus_status": "NOT_SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Unknown",
        "gold_sections": [],
        "gold_subsections": [],
        "gold_keywords": ["United States", "IRS", "late filing", "penalty"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [],
        "source_text_evidence": "",
        "notes": "US tax laws are out of corpus."
    },
    {
        "candidate_id": "Q58",
        "question": "How is wealth tax calculated for residential properties in France?",
        "question_type": "out_of_corpus",
        "difficulty": "easy",
        "expected_corpus_status": "NOT_SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Unknown",
        "gold_sections": [],
        "gold_subsections": [],
        "gold_keywords": ["France", "wealth tax", "residential properties"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [],
        "source_text_evidence": "",
        "notes": "French tax laws are out of corpus."
    },
    {
        "candidate_id": "Q59",
        "question": "What is the corporate tax rate in Singapore for tech startups?",
        "question_type": "out_of_corpus",
        "difficulty": "easy",
        "expected_corpus_status": "NOT_SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Unknown",
        "gold_sections": [],
        "gold_subsections": [],
        "gold_keywords": ["Singapore", "corporate tax", "tech startups"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [],
        "source_text_evidence": "",
        "notes": "Singapore tax laws are out of corpus."
    },
    {
        "candidate_id": "Q60",
        "question": "What are the rules for customs duty exemption on personal baggage for passengers arriving in India?",
        "question_type": "out_of_corpus",
        "difficulty": "easy",
        "expected_corpus_status": "NOT_SUPPORTED",
        "query_formulation_type": "PARAPHRASED",
        "gold_act": "Unknown",
        "gold_sections": [],
        "gold_subsections": [],
        "gold_keywords": ["customs duty", "exemption", "baggage", "arriving in India"],
        "gold_numeric_claims": [],
        "source_chunk_indices": [],
        "source_text_evidence": "",
        "notes": "Customs Act is out of corpus."
    }
]


def build_dataset() -> None:
    """Validate grounding, compute overlaps, and save the dataset."""
    # Step 1: Identity validation
    validate_chunk_ids()
    
    # Load chunks to verify grounding and map chunk IDs
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)
        
    validated_questions: List[Dict[str, Any]] = []
    rejected_questions: List[Dict[str, Any]] = []
    
    for idx, q in enumerate(CANDIDATE_QUESTIONS):
        q_id = q["candidate_id"]
        q_type = q["question_type"]
        status = q["expected_corpus_status"]
        
        # Grounding check for supported questions
        if status == "SUPPORTED":
            indices = q["source_chunk_indices"]
            if not indices:
                rejected_questions.append({
                    "candidate_id": q_id,
                    "candidate_type": q_type,
                    "source_chunk_id": "",
                    "rejection_reason": "source_chunk_indices list is empty."
                })
                continue
                
            out_of_bounds = False
            for chunk_idx in indices:
                if chunk_idx >= len(chunks):
                    out_of_bounds = True
                    rejected_questions.append({
                        "candidate_id": q_id,
                        "candidate_type": q_type,
                        "source_chunk_id": "",
                        "rejection_reason": f"source_chunk_index {chunk_idx} is out of bounds."
                    })
                    break
            if out_of_bounds:
                continue
                
            # Compute chunk IDs
            cids = []
            for chunk_idx in indices:
                chunk = chunks[chunk_idx]
                cid = generate_chunk_id(
                    chunk_text=chunk.get("chunk_text", ""),
                    index=chunk_idx,
                    section_no=chunk.get("section_no", "Unknown"),
                    chapter=chunk.get("chapter", "Unknown"),
                    subsection=chunk.get("subsection", "")
                )
                cids.append(cid)
            
            # Grounding check: verify every non-empty line of source_text_evidence is in at least one source chunk text
            evidence = q["source_text_evidence"]
            evidence_parts = [p.strip() for p in evidence.split("\n") if p.strip()]
            
            grounding_failed = False
            for part in evidence_parts:
                norm_part = normalize_for_match(part)
                found = False
                for chunk_idx in indices:
                    norm_chunk = normalize_for_match(chunks[chunk_idx].get("chunk_text", ""))
                    if norm_part in norm_chunk:
                        found = True
                        break
                if not found:
                    rejected_questions.append({
                        "candidate_id": q_id,
                        "candidate_type": q_type,
                        "source_chunk_id": cids[0],
                        "rejection_reason": f"source_text_evidence line '{part[:50]}...' not found in any source chunk text."
                    })
                    grounding_failed = True
                    break
                    
            if grounding_failed:
                continue
            
            # Compute token and phrase overlaps (against full evidence block)
            token_overlap, phrase_overlap = compute_overlaps(q["question"], evidence)
            
            # Dynamic formulation label alignment based on post-repair audited formulation rules
            if q_id in ["Q51", "Q52", "Q53", "Q54", "Q55"]:
                audited_formulation = "REASONING"
            elif phrase_overlap >= 1.0 or token_overlap >= 0.70:
                audited_formulation = "LEXICAL"
            else:
                audited_formulation = "PARAPHRASED"
            
            # Populate final structure
            final_item = {
                "question_id": q_id,
                "question": q["question"],
                "question_type": q_type,
                "difficulty": q["difficulty"],
                "expected_corpus_status": status,
                "gold_act": q["gold_act"],
                "gold_sections": q["gold_sections"],
                "gold_subsections": q["gold_subsections"],
                "gold_keywords": q["gold_keywords"],
                "gold_numeric_claims": q["gold_numeric_claims"],
                "source_chunk_ids": cids,
                "source_text_evidence": evidence,
                "query_formulation_type": audited_formulation,
                "question_source_token_overlap": token_overlap,
                "question_source_phrase_overlap": phrase_overlap,
                "notes": q["notes"],
                "review_status": "AUTO_GROUNDED"
            }
            validated_questions.append(final_item)
            
        else:
            # Out of corpus questions have no source chunk
            final_item = {
                "question_id": q_id,
                "question": q["question"],
                "question_type": q_type,
                "difficulty": q["difficulty"],
                "expected_corpus_status": status,
                "gold_act": "Unknown",
                "gold_sections": [],
                "gold_subsections": [],
                "gold_keywords": q["gold_keywords"],
                "gold_numeric_claims": [],
                "source_chunk_ids": [],
                "source_text_evidence": "",
                "query_formulation_type": q["query_formulation_type"],
                "question_source_token_overlap": 0.0,
                "question_source_phrase_overlap": 0.0,
                "notes": q["notes"],
                "review_status": "AUTO_GROUNDED"
            }
            validated_questions.append(final_item)
            
    # Save files
    with open(DATASET_OUT, "w", encoding="utf-8") as f:
        json.dump(validated_questions, f, ensure_ascii=False, indent=2)
        
    with open(REJECTED_OUT, "w", encoding="utf-8") as f:
        json.dump(rejected_questions, f, ensure_ascii=False, indent=2)
        
    # Calculate dataset hash
    with open(DATASET_OUT, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()
        
    print(f"Dataset construction complete.")
    print(f"Validated questions: {len(validated_questions)} saved to {DATASET_OUT}")
    print(f"Rejected candidates: {len(rejected_questions)} saved to {REJECTED_OUT}")
    print(f"Dataset SHA-256: {h}\n")


if __name__ == "__main__":
    build_dataset()
