"""Ollama 어댑터. JSON 스키마로 출력 형식을 강제하고, Qwen3의 thinking은 끈다."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.llm.ports import LLMRaw, Message, Usage


class OllamaError(RuntimeError):
    pass


class OllamaLLM:
    def __init__(
        self,
        model: str = "qwen3:8b",
        base_url: str = "http://127.0.0.1:11434",
        timeout: float = 120.0,
        keep_alive: str = "30m",
    ) -> None:
        self.model_id = f"ollama:{model}"
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.keep_alive = keep_alive

    def _payload(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None,
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
            "think": False,
            "keep_alive": self.keep_alive,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if json_schema is not None:
            payload["format"] = json_schema
        return payload

    async def complete(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> LLMRaw:
        payload = self._payload(
            messages,
            json_schema=json_schema,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama 호출 실패: {exc!r}") from exc
        data = response.json()
        return LLMRaw(
            text=data.get("message", {}).get("content", ""),
            model_id=self.model_id,
            latency_ms=(time.perf_counter() - started) * 1000,
            usage=Usage(data.get("prompt_eval_count", 0), data.get("eval_count", 0)),
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> AsyncIterator[str]:
        payload = self._payload(
            messages,
            json_schema=json_schema,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        try:
            async with (
                httpx.AsyncClient(timeout=self.timeout) as client,
                client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response,
            ):
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    piece = chunk.get("message", {}).get("content", "")
                    if piece:
                        yield piece
                    if chunk.get("done"):
                        break
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama 스트리밍 실패: {exc!r}") from exc
