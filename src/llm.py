"""
CircuitSathi Ollama Local LLM Wrapper
Interfaces directly with local Ollama instance (Gemma 3 / open-weight models).
Zero cloud dependencies, transparent error handling, and exact setup commands.
"""

from typing import Any, Generator
import json
import base64
import httpx
from config import settings


class OllamaClient:
    """Client for local Ollama API."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.timeout = 120.0  # Allow adequate timeout for local model generation

    def check_status(self) -> dict[str, Any]:
        """
        Check if Ollama server is running and detect available models.
        Returns status dictionary with clear diagnostic messages.
        """
        try:
            with httpx.Client(timeout=4.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    
                    # Detect presence of recommended models
                    has_gemma3_4b = any("gemma3:4b" in m for m in models)
                    has_gemma3_1b = any("gemma3:1b" in m for m in models)
                    has_any_gemma = any("gemma" in m.lower() for m in models)
                    
                    return {
                        "online": True,
                        "base_url": self.base_url,
                        "models": models,
                        "has_default_model": has_gemma3_4b,
                        "has_fallback_model": has_gemma3_1b,
                        "has_any_gemma": has_any_gemma,
                        "message": "Ollama is running locally."
                    }
                else:
                    return {
                        "online": False,
                        "base_url": self.base_url,
                        "models": [],
                        "has_default_model": False,
                        "has_fallback_model": False,
                        "has_any_gemma": False,
                        "message": f"Ollama returned HTTP status {resp.status_code}."
                    }
        except httpx.ConnectError:
            return {
                "online": False,
                "base_url": self.base_url,
                "models": [],
                "has_default_model": False,
                "has_fallback_model": False,
                "has_any_gemma": False,
                "message": (
                    "Ollama is not running. Please start Ollama or run 'ollama serve' in your terminal."
                )
            }
        except Exception as e:
            return {
                "online": False,
                "base_url": self.base_url,
                "models": [],
                "has_default_model": False,
                "has_fallback_model": False,
                "has_any_gemma": False,
                "message": f"Ollama connection check failed: {str(e)}"
            }

    def list_models(self) -> list[str]:
        """Return list of model names installed in local Ollama."""
        status = self.check_status()
        return status.get("models", [])

    def get_download_command(self, model_name: str | None = None) -> str:
        """Returns the exact shell command to pull or run the model."""
        target = model_name or settings.default_model
        return f"ollama pull {target}"

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        images: list[str] | None = None,
        stream: bool = False
    ) -> str | Generator[str, None, None]:
        """
        Generate completion using Ollama's /api/generate endpoint.
        Supports text and base64 encoded images for vision models.
        """
        active_model = model or settings.active_model
        temp = temperature if temperature is not None else settings.model_temperature

        payload: dict[str, Any] = {
            "model": active_model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temp,
            }
        }
        if system_prompt:
            payload["system"] = system_prompt
        if images:
            payload["images"] = images

        if stream:
            return self._stream_generate(payload)
        else:
            return self._sync_generate(payload)

    def _sync_generate(self, payload: dict[str, Any]) -> str:
        """Execute non-streaming generation request."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/api/generate", json=payload)
                if resp.status_code == 404:
                    model_name = payload.get("model")
                    cmd = self.get_download_command(model_name)
                    raise RuntimeError(
                        f"Model '{model_name}' is not found in your local Ollama instance.\n"
                        f"Run this command in PowerShell to download it:\n\n    {cmd}\n"
                    )
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
        except httpx.ConnectError:
            raise ConnectionError(
                "Cannot connect to local Ollama. Please ensure Ollama is running at "
                f"{self.base_url}."
            )

    def _stream_generate(self, payload: dict[str, Any]) -> Generator[str, None, None]:
        """Stream response tokens from Ollama generation endpoint."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as resp:
                    if resp.status_code == 404:
                        model_name = payload.get("model")
                        cmd = self.get_download_command(model_name)
                        yield (
                            f"\n⚠️ **Model Not Found**: Model '{model_name}' is not downloaded yet.\n"
                            f"Open PowerShell and execute:\n\n```powershell\n{cmd}\n```"
                        )
                        return
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if line:
                            data = json.loads(line)
                            yield data.get("response", "")
                            if data.get("done", False):
                                break
        except httpx.ConnectError:
            yield (
                "\n⚠️ **Connection Error**: Could not connect to Ollama. "
                f"Make sure Ollama is running at {self.base_url}."
            )
        except Exception as e:
            yield f"\n⚠️ **Inference Error**: {str(e)}"

    def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        stream: bool = False
    ) -> str | Generator[str, None, None]:
        """
        Execute chat completion through Ollama's /api/chat endpoint.
        """
        active_model = model or settings.active_model
        temp = temperature if temperature is not None else settings.model_temperature

        payload: dict[str, Any] = {
            "model": active_model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temp,
            }
        }

        if stream:
            return self._stream_chat(payload)
        else:
            return self._sync_chat(payload)

    def _sync_chat(self, payload: dict[str, Any]) -> str:
        """Non-streaming chat completion."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/api/chat", json=payload)
                if resp.status_code == 404:
                    model_name = payload.get("model")
                    cmd = self.get_download_command(model_name)
                    raise RuntimeError(
                        f"Model '{model_name}' is not found.\nRun:\n    {cmd}"
                    )
                resp.raise_for_status()
                data = resp.json()
                msg = data.get("message", {})
                return msg.get("content", "")
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to local Ollama at {self.base_url}. Please ensure Ollama is running."
            )

    def _stream_chat(self, payload: dict[str, Any]) -> Generator[str, None, None]:
        """Stream tokens from chat endpoint."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                    if resp.status_code == 404:
                        model_name = payload.get("model")
                        cmd = self.get_download_command(model_name)
                        yield (
                            f"\n⚠️ **Model Not Found**: Model '{model_name}' is not downloaded yet.\n"
                            f"Open PowerShell and execute:\n\n```powershell\n{cmd}\n```"
                        )
                        return
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if line:
                            data = json.loads(line)
                            msg = data.get("message", {})
                            content = msg.get("content", "")
                            if content:
                                yield content
                            if data.get("done", False):
                                break
        except httpx.ConnectError:
            yield (
                "\n⚠️ **Connection Error**: Could not reach local Ollama. "
                f"Please start Ollama at {self.base_url}."
            )
        except Exception as e:
            yield f"\n⚠️ **Inference Error**: {str(e)}"


# Global default client
llm_client = OllamaClient()
