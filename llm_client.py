"""
llm_client.py
=============
Encapsulates communication with local Ollama service.
Supports dynamic model selection for multi-LLM experiments.
Ensures service and model presence on startup.
"""

from __future__ import annotations

import glob
import logging
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

import requests
from tqdm import tqdm

# Configuration Constants
OLLAMA_HOST: str = "http://localhost:11434"
OLLAMA_PORT: int = 11434
DEFAULT_MODEL: str = "qwen2.5:7b-instruct"
logger = logging.getLogger("answer_engine")


def _find_ollama_executable() -> Optional[str]:
    """
    Attempt to locate the Ollama executable on Windows.
    Checks PATH first, then common installation directories.
    Does NOT hard-code any username.
    """
    import shutil

    # 1. Check PATH
    found = shutil.which("ollama")
    if found:
        return found

    # 2. Common Windows install locations (user-agnostic)
    user_local = os.environ.get("LOCALAPPDATA", "")
    candidates = []
    if user_local:
        candidates.append(os.path.join(user_local, "Programs", "Ollama", "ollama.exe"))
        # Some installers put it in LOCALAPPDATA directly
        candidates.append(os.path.join(user_local, "Ollama", "ollama.exe"))

    candidates.append(os.path.join("C:\\", "Program Files", "Ollama", "ollama.exe"))
    candidates.append(os.path.join("C:\\", "Program Files (x86)", "Ollama", "ollama.exe"))

    for path in candidates:
        if os.path.isfile(path):
            return path

    return None


def _is_port_reachable(host: str = OLLAMA_HOST, timeout: float = 3.0) -> bool:
    """Check if the Ollama HTTP API is reachable."""
    try:
        res = requests.get(f"{host}/api/tags", timeout=timeout)
        return res.status_code == 200
    except Exception:
        return False


def _try_start_ollama_service(exe_path: str, timeout: int = 30) -> bool:
    """
    Attempt to start the Ollama service in the background.
    Waits up to `timeout` seconds for the health endpoint to respond.
    Returns True if the service becomes reachable.
    """
    try:
        logger.info(f"Attempting to start Ollama service from: {exe_path}")
        # Launch ollama serve in background (detached on Windows)
        subprocess.Popen(
            [exe_path, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) | subprocess.DETACHED_PROCESS,
        )
        # Poll for readiness
        for i in range(timeout):
            time.sleep(1)
            if _is_port_reachable():
                logger.info(f"Ollama service started successfully after {i + 1}s.")
                return True
        logger.warning(f"Ollama service did not become reachable within {timeout}s.")
        return False
    except Exception as e:
        logger.warning(f"Failed to start Ollama service: {e}")
        return False


def detect_ollama_runtime() -> Dict[str, Any]:
    """
    Full Ollama runtime detection.
    Returns a dict with:
        executable_path: str or None
        service_reachable: bool
        service_started_by_us: bool
        ollama_version: str or None
    """
    result: Dict[str, Any] = {
        "executable_path": None,
        "service_reachable": False,
        "service_started_by_us": False,
        "ollama_version": None,
    }

    # Check if service is already running
    if _is_port_reachable():
        result["service_reachable"] = True
        # Try to get version
        try:
            ver_resp = requests.get(f"{OLLAMA_HOST}/api/version", timeout=3)
            if ver_resp.status_code == 200:
                result["ollama_version"] = ver_resp.json().get("version", "unknown")
        except Exception:
            pass
        # Find executable for metadata
        result["executable_path"] = _find_ollama_executable()
        return result

    # Service not running — try to find executable
    exe_path = _find_ollama_executable()
    result["executable_path"] = exe_path

    if exe_path is None:
        return result

    # Found executable but service not running — try to start it
    started = _try_start_ollama_service(exe_path)
    if started:
        result["service_reachable"] = True
        result["service_started_by_us"] = True
        try:
            ver_resp = requests.get(f"{OLLAMA_HOST}/api/version", timeout=3)
            if ver_resp.status_code == 200:
                result["ollama_version"] = ver_resp.json().get("version", "unknown")
        except Exception:
            pass

    return result


class LLMClient:
    """
    Client for interacting with local Ollama service.
    Handles service check, pulling models with progress bars, warmup,
    and dynamic model selection for multi-LLM experiments.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self.model_name = model_name

    def health_check(self) -> bool:
        """Verify that the Ollama service port is reachable."""
        return _is_port_reachable()

    def check_model_exists(self, model_name: Optional[str] = None) -> bool:
        """Check if the requested model exists in Ollama local tags."""
        target = model_name or self.model_name
        try:
            res = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
            if res.status_code != 200:
                return False
            data = res.json()
            models_list = data.get("models", [])
            for m in models_list:
                name = m.get("model", "") or m.get("name", "")
                if name == target or name.startswith(target):
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to list local Ollama models: {e}")
            return False

    def pull_model(self, model_name: Optional[str] = None) -> None:
        """Pull the model through Ollama API with console progress tracker."""
        target = model_name or self.model_name
        logger.info(f"Ollama model '{target}' not found locally. Starting pull...")
        print(f"\nPulling Ollama model '{target}'... This may take several minutes.")

        try:
            import ollama as ollama_client
            current_digest = ""
            pbar = None

            for progress in ollama_client.pull(target, stream=True):
                status = progress.get("status", "")
                completed = progress.get("completed") or 0
                total = progress.get("total") or 0
                digest = progress.get("digest") or ""

                if digest and digest != current_digest:
                    if pbar:
                        pbar.close()
                    current_digest = digest
                    pbar = tqdm(
                        total=total,
                        initial=completed,
                        unit="B",
                        unit_scale=True,
                        desc=f"Downloading layer {digest[:10]}"
                    )
                elif pbar and completed:
                    pbar.n = completed
                    pbar.refresh()

            if pbar:
                pbar.close()
            print(f"Model '{target}' successfully downloaded!\n")
            logger.info(f"Model '{target}' pulled successfully.")
        except Exception as e:
            logger.critical(f"Failed to pull Ollama model '{target}': {e}")
            print(f"\nCRITICAL ERROR: Failed to pull Ollama model '{target}': {e}")
            print("Please ensure your internet connection is active and Ollama is running.")
            raise RuntimeError(f"Model pull failed for '{target}': {e}")

    def ensure_model(self, model_name: str) -> bool:
        """
        Ensure a specific model is available. Pull if missing.
        Returns True if model is available after check/pull, False on failure.
        """
        if self.check_model_exists(model_name):
            return True
        try:
            self.pull_model(model_name)
            return self.check_model_exists(model_name)
        except RuntimeError:
            return False

    def initialize(self) -> None:
        """Verify Ollama exists and that the default model is pulled."""
        if not self.health_check():
            raise RuntimeError("Ollama service not running.")

        if not self.check_model_exists():
            self.pull_model()

    def warmup(self, model_name: Optional[str] = None) -> None:
        """Perform a small warmup call to load model weights into memory."""
        target = model_name or self.model_name
        logger.info(f"Warming up local model '{target}'...")
        t0 = time.time()
        try:
            import ollama as ollama_client
            ollama_client.generate(
                model=target,
                prompt="Initialize warmup query.",
                options={"num_predict": 5}
            )
            logger.info(f"Warmup finished in {time.time() - t0:.2f}s.")
        except Exception as e:
            logger.warning(f"Model warmup failed: {e}")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        top_p: float = 0.9,
        max_tokens: int = 1200,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """
        Execute chat generation using Ollama APIs.
        If model_name is provided, uses that model instead of self.model_name.
        This allows a single client instance to drive multiple models.
        """
        target = model_name or self.model_name
        logger.debug(f"Executing LLM generation on '{target}' with temperature={temperature}, top_p={top_p}")
        try:
            import ollama as ollama_client
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            options: Dict[str, Any] = {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_tokens,
            }
            if seed is not None:
                options["seed"] = seed

            response = ollama_client.chat(
                model=target,
                messages=messages,
                options=options,
            )
            content = response.get("message", {}).get("content", "")
            return content.strip()
        except Exception as e:
            logger.error(f"Ollama generation call failed for model '{target}': {e}")
            raise e
