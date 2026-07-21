"""NVIDIA NIM provider — OpenAI-compatible HTTP adapter over httpx."""
from __future__ import annotations

from typing import Any

import httpx

from src.llm.providers.base import LLMError, LLMProvider


class NIMProvider(LLMProvider):
    name = "nim"
    default_model = "meta/llama-3-70b-instruct"

    def __init__(self, api_key: str, model: str | None = None, base_url: str = "https://integrate.api.nvidia.com/v1") -> None:
        if not api_key:
            raise LLMError("Missing AGENT_NIM_API_KEY for NVIDIA NIM.")
        self.api_key = api_key
        self.model = model or self.default_model
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0))

    def complete(self, system: str, user: str, *, max_tokens: int = 1024) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = self._client.post("/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
            return body["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 401:
                raise LLMError("NIM auth failed: invalid AGENT_NIM_API_KEY.") from exc
            if status == 429:
                raise LLMError("NIM rate limit hit. Retry later or use a dedicated key.") from exc
            raise LLMError(f"NIM request failed: {exc.response.status_code} {exc.response.text}") from exc
        except Exception as exc:  # pragma: no cover — network edge
            raise LLMError(f"NIM request error: {exc}") from exc
        finally:
            self._client.close()
