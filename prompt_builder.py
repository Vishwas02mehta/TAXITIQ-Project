"""
prompt_builder.py
=================
Formats structured legal system prompts and injects retrieved context
and chat history for LLM generation.

Provides:
- Original prompts for backward compatibility with 07_answer_engine.py
- Canonical experiment prompts for controlled multi-LLM comparison
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Tuple


class PromptBuilder:
    """Handles structuring system and user prompts with strict contextual instructions."""

    # ── Original prompts (backward compat with 07_answer_engine.py) ──

    @staticmethod
    def get_system_prompt() -> str:
        """Return the standard legal instructions system prompt."""
        return (
            "You are an expert Indian tax law assistant.\n"
            "Your objective is to answer the user's legal question as accurately as possible "
            "based ONLY on the provided retrieved context blocks below.\n\n"
            "Strict Instructions:\n"
            "1. Answer ONLY using the facts, rules, and conditions explicitly stated in the context.\n"
            "2. Never invent legal provisions, section numbers, rates, or facts.\n"
            "3. If the retrieved context does not contain sufficient details to answer the query, "
            "or if there is insufficient information, you must respond with exactly: \"The retrieved legal context does not contain sufficient information to answer this question.\"\n"
            "4. For every legal assertion or rate statement you make, you must cite the source "
            "using the format: [Act: <Act Name>, Section: <Section No>, Subsection: <Subsec No>].\n"
            "5. Do not make any statements outside the scope of the provided legal documents."
        )

    @staticmethod
    def build_user_prompt(
        query: str,
        context_blocks: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]]
    ) -> str:
        """
        Build the user prompt combining context blocks, conversation history, and user query.
        """
        prompt_parts: List[str] = []
        
        # 1. Inject Chat History (if any)
        if conversation_history:
            prompt_parts.append("### CONVERSATION HISTORY")
            for chat in conversation_history:
                prompt_parts.append(f"User: {chat['question']}")
                prompt_parts.append(f"Assistant: {chat['answer']}")
            prompt_parts.append("")
            
        # 2. Inject Legal Context Blocks
        prompt_parts.append("### RETRIEVED LEGAL CONTEXT")
        for idx, block in enumerate(context_blocks):
            prompt_parts.append(f"--- BLOCK #{idx + 1} ---")
            prompt_parts.append(f"Act: {block['act']}")
            prompt_parts.append(f"Chapter: {block['chapter']}")
            prompt_parts.append(f"Section: {block['section']}")
            prompt_parts.append(f"Subsection: {block['subsection']}")
            prompt_parts.append(f"Evidence Category: {block.get('evidence_type', 'Statutory Rule')}")
            prompt_parts.append(f"Text:\n{block['text']}")
            prompt_parts.append("")
            
        # 3. Inject User Question
        prompt_parts.append("### USER QUESTION")
        prompt_parts.append(query)
        
        return "\n".join(prompt_parts)

    # ── Canonical experiment prompts (multi-LLM comparison) ──

    @staticmethod
    def get_canonical_system_prompt() -> str:
        """
        Return the canonical legal QA system prompt for controlled experiments.
        Both models MUST receive this exact same prompt text.
        """
        return (
            "You are an Indian tax law question-answering assistant.\n\n"
            "Answer the user's question using ONLY the legal context provided.\n\n"
            "The retrieved context is the sole authoritative source for this answer.\n\n"
            "Do not use remembered section numbers from pretraining.\n\n"
            "Do not use provisions from older tax legislation unless those provisions "
            "explicitly appear in the provided context.\n\n"
            "Do not invent a section, subsection, chapter, monetary limit, percentage, "
            "deadline, exception, or legal condition.\n\n"
            "Every material legal claim must be supported by the provided context.\n\n"
            "When referring to a legal provision, cite the Act and Section exactly as "
            "represented in the provided context.\n\n"
            "If subsection metadata is available and relevant, include the subsection.\n\n"
            "If the context contains conflicting provisions or rates, explicitly state "
            "that the retrieved context contains potentially conflicting provisions and "
            "avoid resolving the conflict without sufficient evidence.\n\n"
            "If the provided context is insufficient to answer the question, respond exactly:\n\n"
            "'The provided legal context is insufficient to answer this question reliably.'\n\n"
            "Do not guess.\n\n"
            "Do not fill missing legal details from general knowledge.\n\n"
            "Prefer a concise answer followed by supporting legal references."
        )

    @staticmethod
    def build_canonical_user_prompt(
        query: str,
        context_blocks: List[Dict[str, Any]],
    ) -> str:
        """
        Build the canonical user prompt for multi-LLM experiments.
        No conversation history — experiment isolation requires each query
        to be evaluated independently.

        Structure:
        [QUESTION]
        [LEGAL CONTEXT]
        [ANSWER REQUIREMENTS]
        """
        prompt_parts: List[str] = []

        # [QUESTION]
        prompt_parts.append("[QUESTION]")
        prompt_parts.append(query)
        prompt_parts.append("")

        # [LEGAL CONTEXT]
        prompt_parts.append("[LEGAL CONTEXT]")
        for idx, block in enumerate(context_blocks):
            prompt_parts.append(f"--- CONTEXT BLOCK {idx + 1} ---")
            prompt_parts.append(f"Act: {block['act']}")
            prompt_parts.append(f"Chapter: {block['chapter']}")
            prompt_parts.append(f"Section: {block['section']}")
            prompt_parts.append(f"Subsection: {block['subsection']}")
            prompt_parts.append(f"Evidence Category: {block.get('evidence_type', 'Statutory Rule')}")
            prompt_parts.append(f"Text:\n{block['text']}")
            prompt_parts.append("")

        # [ANSWER REQUIREMENTS]
        prompt_parts.append("[ANSWER REQUIREMENTS]")
        prompt_parts.append(
            "Cite legal provisions using: [Act: <Act Name>, Section: <Section No>, Subsection: <Subsec No>]."
        )
        prompt_parts.append(
            "If the context is insufficient, respond exactly: "
            "'The provided legal context is insufficient to answer this question reliably.'"
        )
        prompt_parts.append("Do not invent facts not present in the context above.")

        return "\n".join(prompt_parts)

    @staticmethod
    def compute_prompt_hashes(
        system_prompt: str,
        user_prompt: str,
    ) -> Tuple[str, str]:
        """
        Compute deterministic SHA-256 hashes for the system and user prompts.
        Returns (prompt_sha256, context_sha256).

        prompt_sha256: hash of (system_prompt + user_prompt)
        context_sha256: hash of just the [LEGAL CONTEXT] section of user_prompt
        """
        # Full prompt hash
        full_text = system_prompt + "\n" + user_prompt
        prompt_sha256 = hashlib.sha256(full_text.encode("utf-8")).hexdigest()

        # Context-only hash: extract [LEGAL CONTEXT] section
        context_start = user_prompt.find("[LEGAL CONTEXT]")
        context_end = user_prompt.find("[ANSWER REQUIREMENTS]")
        if context_start >= 0 and context_end >= 0:
            context_text = user_prompt[context_start:context_end]
        else:
            # Fallback: hash entire user prompt
            context_text = user_prompt
        context_sha256 = hashlib.sha256(context_text.encode("utf-8")).hexdigest()

        return prompt_sha256, context_sha256
