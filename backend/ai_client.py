"""MiniMax API client with structured JSON output and tenacity retries."""
from __future__ import annotations

import json
import logging
import re

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings

log = logging.getLogger("ai_client")
log.setLevel(settings.LOG_LEVEL)


_MOCK_FALLBACK = True  # toggle: when no API key, return deterministic mock JSON


class _ParseError(Exception):
    """Raised when the LLM body cannot be turned into a dict."""


def _mock_for_schema(schema: dict) -> dict:
    """Produce a deterministic mock object that matches `schema` shape."""
    props = schema.get("properties", {}) if isinstance(schema, dict) else {}
    out: dict = {}
    for name, sub in props.items():
        t = sub.get("type") if isinstance(sub, dict) else None
        if t == "array":
            out[name] = [
                _mock_for_schema(sub.get("items", {"type": "string"}))
                if isinstance(sub.get("items"), dict)
                and sub.get("items", {}).get("type") == "object"
                else f"sample {name} item"
            ]
        elif t == "object":
            out[name] = _mock_for_schema(sub)
        else:
            out[name] = f"sample {name}"
    return out


def _extract_json(content: str) -> dict:
    """Strip ```json fences (open or closed) and parse the first JSON object."""
    s = (content or "").strip()
    # Strip a leading ```json fence even if the closing fence is missing.
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```\s*$", "", s)
    try:
        return json.loads(s)
    except Exception:
        pass
    # Fall back to the first balanced {...} substring.
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise _ParseError("no_json_object_in_response")


async def _post_once(prompt: str, schema: dict) -> dict:
    """One HTTP attempt. Raises httpx errors OR _ParseError."""
    if _MOCK_FALLBACK and not settings.MINIMAX_API_KEY:
        return _mock_for_schema(schema)

    payload = {
        "model": settings.MINIMAX_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.MINIMAX_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
        r = await client.post(
            settings.MINIMAX_API_URL, json=payload, headers=headers
        )
        status_code = r.status_code
        body = r.text
        try:
            data = r.json()
        except Exception:
            data = {}

        tokens = (
            data.get("usage", {}).get("total_tokens")
            if isinstance(data, dict)
            else None
        )
        # SAFE LOG: status_code + model + tokens only — never prompt or key.
        log.info(
            "minimax status=%s model=%s tokens=%s",
            status_code,
            settings.MINIMAX_MODEL,
            tokens,
        )

        if status_code == 429 or status_code >= 500:
            raise httpx.HTTPStatusError(
                f"transient_{status_code}", request=r.request, response=r
            )
        if status_code >= 400:
            return {"error": f"http_{status_code}", "raw": body}

        content = (
            data.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
        return _extract_json(content)


def _is_parse_or_http(exc: BaseException) -> bool:
    return isinstance(exc, (httpx.HTTPError, httpx.TimeoutException, _ParseError))


@retry(
    retry=retry_if_exception(_is_parse_or_http),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=3, max=10),
    reraise=True,
)
async def _post_with_retry(prompt: str, schema: dict) -> dict:
    return await _post_once(prompt, schema)


async def generate_structured(
    prompt: str, schema: dict, max_retries: int = 2
) -> dict:
    """Call MiniMax with retries on 5xx/timeout/parse/429, return parsed dict."""
    try:
        return await _post_with_retry(prompt, schema)
    except (RetryError, httpx.HTTPError, httpx.TimeoutException, _ParseError) as e:
        return {"error": f"failed_after_retries:{type(e).__name__}", "raw": str(e)}