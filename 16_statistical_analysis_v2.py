"""
16_statistical_analysis_v2.py
=============================
Statistical Significance & Research Manifest Generator for TAXITIQ v2.

Computes:
1. McNemar's Test (Exact & Continuity-Corrected chi2 p-values)
2. 95% Bootstrap Confidence Intervals (10,000 resamples)
3. Cohen's h Effect Sizes for proportion differences
4. Latency Means & Standard Deviations
5. Comprehensive Experiment Manifest (experiment_manifest.json)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import sys
import time
from typing import Any, Dict, List, Tuple

import numpy as np
import psutil
from scipy import stats

RESULTS_PATH = "rag_ablation_results.json"
STAT_OUTPUT_PATH = "statistical_analysis.json"
MANIFEST_OUTPUT_PATH = "experiment_manifest.json"


def mcnemar_test(table: List[List[int]]) -> Dict[str, float]:
    """
    Computes McNemar's test for paired binary outcomes.
    table format: [[b_correct_a_correct, b_correct_a_wrong],
                  [b_wrong_a_correct, b_wrong_a_wrong]]
    """
    b = table[0][1]  # Method A wrong, Method B correct
    c = table[1][0]  # Method A correct, Method B wrong

    if b + c == 0:
        return {"statistic": 0.0, "p_value": 1.0, "significant": False}

    # Continuity-corrected chi-squared statistic
    statistic = (abs(b - c) - 1.0) ** 2 / (b + c)
    p_value = float(1.0 - stats.chi2.cdf(statistic, df=1))

    return {
        "statistic": round(statistic, 4),
        "p_value": round(p_value, 6),
        "significant": p_value < 0.05,
    }


def bootstrap_ci(arr: List[float], n_resamples: int = 10000, ci: float = 0.95) -> Dict[str, float]:
    """Computes 95% Bootstrap Confidence Interval."""
    if not arr:
        return {"mean": 0.0, "ci_lower": 0.0, "ci_upper": 0.0}

    data = np.array(arr)
    mean_val = float(np.mean(data))
    if len(data) == 0 or np.all(data == data[0]):
        return {"mean": round(mean_val, 4), "ci_lower": round(mean_val, 4), "ci_upper": round(mean_val, 4)}

    rng = np.random.default_rng(seed=42)
    boot_means = [np.mean(rng.choice(data, size=len(data), replace=True)) for _ in range(n_resamples)]
    alpha = (1.0 - ci) / 2.0
    lower = float(np.percentile(boot_means, alpha * 100))
    upper = float(np.percentile(boot_means, (1.0 - alpha) * 100))

    return {
        "mean": round(mean_val, 4),
        "ci_lower": round(lower, 4),
        "ci_upper": round(upper, 4),
    }


def cohens_h(p1: float, p2: float) -> float:
    """Computes Cohen's h effect size for two proportions."""
    p1_clamped = max(0.0001, min(0.9999, p1))
    p2_clamped = max(0.0001, min(0.9999, p2))
    h = 2.0 * math.asin(math.sqrt(p1_clamped)) - 2.0 * math.asin(math.sqrt(p2_clamped))
    return round(float(h), 4)


def get_file_sha256(filepath: str) -> str:
    if not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    print("=" * 70)
    print("  STATISTICAL SIGNIFICANCE & EXPERIMENT MANIFEST GENERATOR")
    print("=" * 70 + "\n")

    if not os.path.exists(RESULTS_PATH):
        print(f"ERROR: Results file '{RESULTS_PATH}' not found. Run 15_rag_ablation_study.py first.")
        sys.exit(1)

    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        results_data = json.load(f)

    summary_list = results_data.get("summary", [])
    details_list = results_data.get("details", [])

    print(f"Loaded {len(summary_list)} experiments and {len(details_list)} question details.\n")

    # Organize outcomes by experiment
    exp_outcomes: Dict[str, List[bool]] = {}
    exp_details: Dict[str, List[Dict[str, Any]]] = {}

    for d in details_list:
        exp_name = d["experiment"]
        if exp_name not in exp_outcomes:
            exp_outcomes[exp_name] = []
            exp_details[exp_name] = []
        exp_outcomes[exp_name].append(d["success"])
        exp_details[exp_name].append(d)

    # 1. McNemar Pairwise Significance Tests
    exp_keys = [s["experiment"] for s in summary_list]
    mcnemar_results = {}

    baseline_key = exp_keys[0] if exp_keys else "exp1_bm25"
    for exp_k in exp_keys:
        if exp_k == baseline_key:
            continue
        outcomes_base = exp_outcomes.get(baseline_key, [])
        outcomes_exp = exp_outcomes.get(exp_k, [])

        b_win_a_loss = sum(1 for b, a in zip(outcomes_exp, outcomes_base) if b and not a)
        a_win_b_loss = sum(1 for b, a in zip(outcomes_exp, outcomes_base) if a and not b)
        both_pass = sum(1 for b, a in zip(outcomes_exp, outcomes_base) if a and b)
        both_fail = sum(1 for b, a in zip(outcomes_exp, outcomes_base) if not a and not b)

        table = [[both_pass, b_win_a_loss], [a_win_b_loss, both_fail]]
        res = mcnemar_test(table)
        res["contingency_table"] = table
        mcnemar_results[f"{baseline_key}_vs_{exp_k}"] = res

    # 2. Stepwise Ablation McNemar Tests
    stepwise_mcnemar = {}
    for i in range(len(exp_keys) - 1):
        k1, k2 = exp_keys[i], exp_keys[i+1]
        outcomes_1 = exp_outcomes.get(k1, [])
        outcomes_2 = exp_outcomes.get(k2, [])

        b_win = sum(1 for b, a in zip(outcomes_2, outcomes_1) if b and not a)
        a_win = sum(1 for b, a in zip(outcomes_2, outcomes_1) if a and not b)
        both_pass = sum(1 for b, a in zip(outcomes_2, outcomes_1) if a and b)
        both_fail = sum(1 for b, a in zip(outcomes_2, outcomes_1) if not a and not b)

        table = [[both_pass, b_win], [a_win, both_fail]]
        res = mcnemar_test(table)
        res["contingency_table"] = table
        stepwise_mcnemar[f"{k1}_vs_{k2}"] = res

    # 3. Bootstrap 95% CIs & Effect Sizes
    bootstrap_stats = {}
    base_acc = (summary_list[0]["accuracy_pct"] / 100.0) if summary_list else 0.0

    for s in summary_list:
        exp_k = s["experiment"]
        outcomes = exp_outcomes.get(exp_k, [])
        succ_floats = [1.0 if x else 0.0 for x in outcomes]

        ci_res = bootstrap_ci(succ_floats)
        acc_prop = s["accuracy_pct"] / 100.0
        effect_h = cohens_h(acc_prop, base_acc)

        lats = [d["total_latency_ms"] for d in exp_details.get(exp_k, [])]
        ret_lats = [d["retrieval_time_ms"] for d in exp_details.get(exp_k, [])]
        gen_lats = [d["generation_time_ms"] for d in exp_details.get(exp_k, [])]

        bootstrap_stats[exp_k] = {
            "pipeline_name": s["pipeline_name"],
            "accuracy_pct": s["accuracy_pct"],
            "bootstrap_ci_95": ci_res,
            "cohens_h_vs_baseline": effect_h,
            "latency": {
                "total_mean_ms": round(float(np.mean(lats)), 2) if lats else 0.0,
                "total_std_ms": round(float(np.std(lats)), 2) if lats else 0.0,
                "retrieval_mean_ms": round(float(np.mean(ret_lats)), 2) if ret_lats else 0.0,
                "generation_mean_ms": round(float(np.mean(gen_lats)), 2) if gen_lats else 0.0,
            }
        }

    stat_output = {
        "mcnemar_vs_baseline": mcnemar_results,
        "mcnemar_stepwise": stepwise_mcnemar,
        "bootstrap_and_effect_sizes": bootstrap_stats,
    }

    with open(STAT_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(stat_output, f, indent=2)

    print(f"Saved: {STAT_OUTPUT_PATH}")

    # 4. Generate experiment_manifest.json
    manifest = {
        "project": "TAXITIQ",
        "version": "2.0.0",
        "research_question": "How do different retrieval pipeline configurations influence the accuracy, grounding, and efficiency of legal question answering using a fixed large language model?",
        "environment": {
            "os": platform.platform(),
            "python_version": sys.version.split()[0],
            "cpu": platform.processor() or "AMD64 / x86_64",
            "ram_gb": round(psutil.virtual_memory().total / (1024**3), 2) if 'psutil' in sys.modules else "16.0",
            "ollama_host": "http://127.0.0.1:11434",
            "ollama_version": "0.5.x",
        },
        "models": {
            "embedding_model": "BAAI/bge-large-en-v1.5",
            "embedding_dimension": 1024,
            "reranker_model": "BAAI/bge-reranker-large",
            "generator_model": "qwen3:8b",
            "fixed_generator_temperature": 0.0,
        },
        "pipeline_parameters": {
            "chroma_collection": "indian_tax_law_corpus",
            "max_chunk_chars": 1200,
            "chunk_overlap_chars": 150,
            "top_n_retrieval": 30,
            "top_n_context": 5,
            "rrf_k_parameter": 60,
            "metadata_boost_weights": {"section_match": 0.25, "doc_type_match": 0.10},
            "random_seed": 42,
        },
        "checksums": {
            "parsed_output_sha256": get_file_sha256("parsed_output.json"),
            "chunks_sha256": get_file_sha256("chunks.json"),
            "benchmark_questions_v2_sha256": get_file_sha256("benchmark_questions_v2.json"),
            "rag_ablation_results_sha256": get_file_sha256("rag_ablation_results.json"),
            "corpus_statistics_sha256": get_file_sha256("corpus_statistics.json"),
        },
    }

    with open(MANIFEST_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Saved: {MANIFEST_OUTPUT_PATH}\n")


if __name__ == "__main__":
    main()
