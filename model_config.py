"""
model_config.py
===============
Centralized model registry and generation configuration for IndiaLawRAG v2.
All generator model names and inference parameters are defined here.
No model names should be scattered across other Python files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class GeneratorModelConfig:
    """Typed configuration for a single generator LLM."""
    key: str                  # Short identifier, e.g. "qwen2.5-7b"
    ollama_model: str         # Ollama tag, e.g. "qwen2.5:7b-instruct"
    display_name: str         # Human-readable, e.g. "Qwen2.5 7B Instruct"


# ── Model Registry ──────────────────────────────────────────────────
GENERATOR_MODELS: Dict[str, GeneratorModelConfig] = {
    "qwen2.5-7b": GeneratorModelConfig(
        key="qwen2.5-7b",
        ollama_model="qwen2.5:7b-instruct",
        display_name="Qwen2.5 7B Instruct",
    ),
    "qwen3-8b": GeneratorModelConfig(
        key="qwen3-8b",
        ollama_model="qwen3:8b",
        display_name="Qwen3 8B",
    ),
}

MODEL_A_KEY: str = "qwen2.5-7b"
MODEL_B_KEY: str = "qwen3-8b"


# ── Deterministic Generation Configuration ──────────────────────────
# Identical settings sent to EVERY model for experimental reproducibility.
# temperature=0 for maximally deterministic output.
# NOTE: Ollama does not guarantee mathematical determinism across runs
#       even with temperature=0 and a fixed seed, because internal
#       threading and quantization may introduce non-determinism.
#       This limitation is documented in the experiment manifest.
DEFAULT_GENERATION_CONFIG: Dict[str, Any] = {
    "temperature": 0,
    "top_p": 1.0,
    "seed": 42,
    "num_predict": 1200,
}


def get_all_model_configs() -> List[GeneratorModelConfig]:
    """Return all registered generator model configs in registry order."""
    return [GENERATOR_MODELS[MODEL_A_KEY], GENERATOR_MODELS[MODEL_B_KEY]]
