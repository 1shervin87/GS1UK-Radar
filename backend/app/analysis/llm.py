"""Thin provider-agnostic LLM client returning parsed JSON."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..config import Settings

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


def _extract_json(text: str) -> Any:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
        if start < 0:
            raise LLMError(f"model did not return JSON: {text[:200]!r}")
        depth, end = 0, None
        opener, closer = text[start], "}" if text[start] == "{" else "]"
        for i, ch in enumerate(text[start:], start):
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is None:
            raise LLMError("unterminated JSON in model output")
        return json.loads(text[start:end])


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = settings.llm_provider
        if self.provider == "anthropic":
            if not settings.anthropic_api_key:
                raise LLMError("ANTHROPIC_API_KEY is not set")
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            self.model = settings.anthropic_model
        else:
            if not settings.openai_api_key:
                raise LLMError("OPENAI_API_KEY is not set")
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url or None)
            self.model = settings.openai_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20), retry=retry_if_exception_type(Exception), reraise=True)
    async def complete_json(self, system: str, user: str, *, max_tokens: int = 4000, temperature: float = 0.2) -> Any:
        if self.provider == "anthropic":
            msg = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
        else:
            resp = await self._client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
            text = resp.choices[0].message.content or ""
        return _extract_json(text)


async def gather_limited(coros, limit: int = 4):
    sem = asyncio.Semaphore(limit)

    async def _wrap(c):
        async with sem:
            return await c

    return await asyncio.gather(*(_wrap(c) for c in coros), return_exceptions=True)
