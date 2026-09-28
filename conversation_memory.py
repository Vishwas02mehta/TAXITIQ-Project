"""
conversation_memory.py
======================
Manages short-term conversation state.
Maintains a ring buffer of the last 10 QA pairs.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List


class ConversationMemory:
    """Short-term conversational state memory ring buffer (limit 10)."""

    def __init__(self, limit: int = 10) -> None:
        self.limit = limit
        self.history: List[Dict[str, Any]] = []

    def add_interaction(self, question: str, answer: str, sources: List[str]) -> None:
        """Add a new QA interaction to history. Evict oldest if limit exceeded."""
        interaction = {
            "question": question,
            "answer": answer,
            "timestamp": time.time(),
            "sources": sources
        }
        self.history.append(interaction)
        # Evict oldest if limit exceeded
        if len(self.history) > self.limit:
            self.history.pop(0)

    def get_history(self) -> List[Dict[str, Any]]:
        """Retrieve full conversation history list."""
        return self.history

    def clear(self) -> None:
        """Clear memory buffer."""
        self.history.clear()
