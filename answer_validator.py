"""
answer_validator.py
===================
Validates LLM citations against assembled context.
Calculates confidence score based on retrieval statistics.
Detects unsupported numeric claims (heuristic).

IMPORTANT: The numeric claim validator is a heuristic tool.
It uses regex-based pattern matching and normalized string comparison.
Limitations:
- Cannot detect paraphrased numeric claims (e.g., "ten percent" vs "10%").
- May miss numeric expressions in unusual formats.
- Does not understand contextual equivalence (e.g., "1.5 lakh" vs "Rs. 1,50,000").
- Should NOT be treated as a formal legal correctness verifier.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple


class AnswerValidator:
    """Checks LLM response text for hallucinations, unsupported claims, or invalid citations."""

    @staticmethod
    def extract_citations(answer: str) -> List[Dict[str, str]]:
        """
        Extract structured citations in format:
        [Act: <Act Name>, Section: <Section No>, Subsection: <Subsec No>]
        """
        citations: List[Dict[str, str]] = []
        # Pattern to capture [Act: ..., Section: ..., Subsection: ...]
        pattern = r"\[Act:\s*([^,\]]+),\s*Section:\s*([^,\]]+),\s*Subsection:\s*([^,\]]*)\]"
        matches = re.findall(pattern, answer)
        
        for match in matches:
            citations.append({
                "act": match[0].strip(),
                "section": match[1].strip(),
                "subsection": match[2].strip()
            })
            
        # Also scan for unstructured citations (e.g. "Section 80C")
        sec_pattern = r"\bSection\s+(\d+[A-Z]*)\b"
        sec_matches = re.findall(sec_pattern, answer)
        for sec in sec_matches:
            # Avoid adding duplicate if already captured by structured parser
            if not any(c["section"].lower() == sec.lower() for c in citations):
                citations.append({
                    "act": "Unknown",
                    "section": sec.strip(),
                    "subsection": ""
                })
                
        return citations

    @classmethod
    def validate_answer(
        cls,
        answer: str,
        context_blocks: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str], List[Dict[str, str]]]:
        """
        Validate that every citation exists in the retrieved context blocks.
        
        Returns:
            Tuple (is_valid, validation_errors_list, citations_list)
        """
        # If response is the standard fallback, it is valid without citations
        if "does not contain sufficient information" in answer:
            return True, [], []
        if "insufficient to answer this question reliably" in answer:
            return True, [], []

        citations = cls.extract_citations(answer)
        errors: List[str] = []
        
        if not citations:
            errors.append("No citation tags found in the generated answer.")
            return False, errors, []

        valid_citations: List[Dict[str, str]] = []
        invalid_citations: List[Dict[str, str]] = []

        for cit in citations:
            act_cit = cit["act"].lower().strip()
            sec_cit = cit["section"].lower().strip()
            
            # Verify if this section exists in context
            matched = False
            for block in context_blocks:
                act_block = str(block.get("act", "")).lower().strip()
                sec_block = str(block.get("section", "")).lower().strip()
                
                # Loose matching to allow prefix/suffix or minor discrepancies
                if sec_cit in sec_block or sec_block in sec_cit:
                    if act_cit == "unknown" or act_cit in act_block or act_block in act_cit:
                        matched = True
                        break
                        
            if matched:
                valid_citations.append(cit)
            else:
                invalid_citations.append(cit)
                errors.append(f"Citation mismatch: Section '{cit['section']}' (Act: '{cit['act']}') is cited but does not exist in context.")

        is_valid = len(errors) == 0
        return is_valid, errors, citations


class ConfidenceEstimator:
    """Determines RAG confidence levels (HIGH, MEDIUM, LOW) based on context statistics."""

    @staticmethod
    def estimate_confidence(
        coverage_score: float,
        avg_reranker_score: float,
        supporting_blocks_count: int,
        is_citation_valid: bool
    ) -> str:
        """Estimate final confidence rating string."""
        if not is_citation_valid or supporting_blocks_count == 0 or coverage_score < 0.3:
            return "LOW"
            
        if coverage_score >= 0.75 and avg_reranker_score >= 0.12 and supporting_blocks_count >= 3:
            return "HIGH"
            
        return "MEDIUM"


class NumericClaimValidator:
    """
    Heuristic validator for numeric claims in LLM-generated legal answers.

    Extracts percentages, monetary amounts, dates, time periods, and tax rates
    from the generated answer and checks whether each claim is supported by
    the provided legal context text.

    LIMITATIONS (documented as required):
    - Pattern-based extraction may miss unusual numeric formats.
    - Normalization is approximate: "1,50,000" and "150000" are treated
      as equivalent, but "one lakh fifty thousand" is NOT matched.
    - Contextual paraphrasing is not detected.
    - This is a diagnostic heuristic, NOT a formal legal correctness verifier.
    """

    # Regex patterns for numeric claim extraction
    # NOTE: \b cannot appear after non-word characters like %; use lookahead instead.
    PATTERNS: List[Tuple[str, str]] = [
        # Percentages: "10%", "20 per cent", "20 percent"
        (r"\b(\d+(?:\.\d+)?)\s*(?:%|per\s*cent\b|percent\b)", "percentage"),
        # Indian Rupee amounts: "Rs. 1,50,000", "Rs.150000", "₹1,50,000", "₹ 150000"
        (r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)", "monetary"),
        # Plain large numbers in Indian format (e.g., "1,50,000")
        (r"\b(\d{1,2},\d{2},\d{3})\b", "monetary_indian"),
        # Dates: "31 March 2026", "1st April 2025"
        (r"\b(\d{1,2})\s*(?:st|nd|rd|th)?\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\s*(\d{4})\b", "date"),
        # Dates: "31-03-2026", "01/04/2025"
        (r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", "date_numeric"),
        # Time periods: "30 days", "three years", "6 months"
        (r"\b(\d+)\s*(?:days?|months?|years?)\b", "time_period"),
    ]

    @classmethod
    def extract_numeric_claims(cls, text: str) -> List[Dict[str, str]]:
        """
        Extract all numeric claims from the given text.
        Returns a list of dicts with keys: 'raw', 'normalized', 'type'.
        """
        claims: List[Dict[str, str]] = []
        seen_raw: Set[str] = set()

        for pattern, claim_type in cls.PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                raw = match.group(0).strip()
                if raw in seen_raw:
                    continue
                seen_raw.add(raw)

                normalized = cls._normalize_numeric(raw)
                claims.append({
                    "raw": raw,
                    "normalized": normalized,
                    "type": claim_type,
                })

        return claims

    @classmethod
    def validate_numeric_claims(
        cls,
        answer: str,
        context_text: str,
    ) -> Dict[str, Any]:
        """
        Extract numeric claims from the answer and check each against the context.

        Returns a dict with:
            numeric_claims: List[Dict]
            supported_numeric_claims: List[Dict]
            unsupported_numeric_claims: List[Dict]
            numeric_support_ratio: float or None
        """
        # If answer is an insufficiency response, no claims to validate
        if "insufficient to answer" in answer.lower() or "does not contain sufficient" in answer.lower():
            return {
                "numeric_claims": [],
                "supported_numeric_claims": [],
                "unsupported_numeric_claims": [],
                "numeric_support_ratio": None,
            }

        claims = cls.extract_numeric_claims(answer)
        if not claims:
            return {
                "numeric_claims": [],
                "supported_numeric_claims": [],
                "unsupported_numeric_claims": [],
                "numeric_support_ratio": None,
            }

        # Normalize the context text for comparison
        context_normalized = cls._normalize_numeric(context_text)
        context_lower = context_text.lower()

        supported: List[Dict[str, str]] = []
        unsupported: List[Dict[str, str]] = []

        for claim in claims:
            raw_lower = claim["raw"].lower()
            norm = claim["normalized"]

            # Check 1: Raw claim text appears in context
            if raw_lower in context_lower:
                supported.append(claim)
                continue

            # Check 2: Normalized numeric value appears in normalized context
            if norm and norm in context_normalized:
                supported.append(claim)
                continue

            # Check 3: For percentages, check if the number + "%" appears
            if claim["type"] == "percentage":
                pct_match = re.search(r"(\d+(?:\.\d+)?)", claim["raw"])
                if pct_match:
                    pct_num = pct_match.group(1)
                    if f"{pct_num}%" in context_lower or f"{pct_num} per cent" in context_lower:
                        supported.append(claim)
                        continue

            unsupported.append(claim)

        total = len(claims)
        ratio = float(len(supported) / total) if total > 0 else None

        return {
            "numeric_claims": [c["raw"] for c in claims],
            "supported_numeric_claims": [c["raw"] for c in supported],
            "unsupported_numeric_claims": [c["raw"] for c in unsupported],
            "numeric_support_ratio": ratio,
        }

    @staticmethod
    def _normalize_numeric(text: str) -> str:
        """
        Normalize numeric text for comparison:
        - Remove commas from numbers
        - Remove currency symbols and prefixes
        - Lowercase
        """
        result = text.lower()
        # Remove Rs., INR, ₹
        result = re.sub(r"(?:rs\.?|inr|₹)\s*", "", result)
        # Remove commas in numbers
        result = re.sub(r"(\d),(\d)", r"\1\2", result)
        # Repeat for Indian format (1,50,000 -> 150000)
        result = re.sub(r"(\d),(\d)", r"\1\2", result)
        return result


def compute_citation_precision(
    valid_citations: List[Dict[str, str]],
    invalid_citations: List[Dict[str, str]],
) -> Optional[float]:
    """
    Compute citation precision: valid / total.
    Returns None if no citations exist (do not falsely report 1.0).
    """
    total = len(valid_citations) + len(invalid_citations)
    if total == 0:
        return None
    return float(len(valid_citations) / total)
