"""Model API backends.

Two real backends cover all nine models:
  - "anthropic": native Messages API (Claude Opus 4.8)
  - "openai": OpenAI-compatible /chat/completions, used by OpenAI, Gemini
    (OpenAI-compat endpoint), xAI, DeepSeek, Moonshot, Mistral, DashScope
    (Qwen), and Thinking Machines (Inkling)

Plus "mock-gold" / "mock-none" for offline pipeline validation.

All calls: temperature 0, no thinking/reasoning mode requested (standard
non-thinking condition), bounded retries with exponential backoff on
429/5xx/timeouts. Uses stdlib urllib only - no SDK version drift.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_MAX_TOKENS = 8192
DEFAULT_TIMEOUT = 300
MAX_RETRIES = 6


class BackendError(RuntimeError):
    pass


def _post(url: str, headers: dict, body: dict, timeout: int = DEFAULT_TIMEOUT) -> dict:
    data = json.dumps(body).encode("utf-8")
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(url, data=data, method="POST",
                                     headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            payload = ""
            try:
                payload = e.read().decode("utf-8", "replace")[:2000]
            except Exception:
                pass
            if e.code in (408, 409, 429, 500, 502, 503, 504, 529) and attempt < MAX_RETRIES - 1:
                retry_after = e.headers.get("retry-after")
                wait = float(retry_after) if retry_after and retry_after.replace(".", "", 1).isdigit() \
                    else min(60.0, 2.0 ** attempt)
                time.sleep(wait)
                last_err = BackendError(f"HTTP {e.code}: {payload}")
                continue
            raise BackendError(f"HTTP {e.code}: {payload}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(min(60.0, 2.0 ** attempt))
                last_err = e
                continue
            raise BackendError(f"network error: {e}") from e
    raise BackendError(f"retries exhausted: {last_err}")


def _key(entry: dict) -> str:
    env = entry.get("api_key_env", "")
    key = os.environ.get(env, "")
    if not key:
        raise BackendError(f"missing API key: set ${env} for model {entry['name']}")
    return key


def call_anthropic(entry: dict, system: str, user: str, max_tokens: int) -> str:
    body = {
        "model": entry["model"],
        "max_tokens": max_tokens,
        "temperature": 0,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    try:
        resp = _post(
            entry["api_base"].rstrip("/") + "/v1/messages",
            {"x-api-key": _key(entry), "anthropic-version": "2023-06-01"},
            body,
        )
    except BackendError as e:
        if "temperature" in str(e) and "deprecated" in str(e):
            body.pop("temperature", None)
            resp = _post(
                entry["api_base"].rstrip("/") + "/v1/messages",
                {"x-api-key": _key(entry), "anthropic-version": "2023-06-01"},
                body,
            )
        else:
            raise
    if resp.get("stop_reason") == "max_tokens":
        raise BackendError("truncated at max_tokens; raise --max-tokens")
    parts = [b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text"]
    text = "".join(parts).strip()
    if not text:
        raise BackendError(f"empty completion: {json.dumps(resp)[:500]}")
    return text


def call_openai_compat(entry: dict, system: str, user: str, max_tokens: int) -> str:
    body = {
        "model": entry["model"],
        "temperature": 0,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    body.update(entry.get("extra_params") or {})
    url = entry["api_base"].rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {_key(entry)}"}
    for _ in range(3):
        try:
            resp = _post(url, headers, body)
            break
        except BackendError as e:
            msg = str(e)
            low = msg.lower()
            # Newer OpenAI-style APIs reject max_tokens in favor of
            # max_completion_tokens; retry with the new parameter name.
            if "max_tokens" in body and "max_tokens" in msg and (
                "unsupported" in low or "max_completion_tokens" in msg
            ):
                body["max_completion_tokens"] = body.pop("max_tokens")
            # Some models pin sampling and reject temperature != default.
            elif "temperature" in body and "temperature" in low and (
                "unsupported" in low or "deprecated" in low
                or "invalid" in low or "not allowed" in low or "only" in low
            ):
                body.pop("temperature")
            else:
                raise
    else:
        raise BackendError("still rejected after parameter fallbacks")
    choices = resp.get("choices") or []
    if not choices:
        raise BackendError(f"no choices: {json.dumps(resp)[:500]}")
    if choices[0].get("finish_reason") == "length":
        raise BackendError("truncated at max tokens; raise --max-tokens")
    msg = choices[0].get("message", {})
    text = (msg.get("content") or "").strip()
    if not text:
        raise BackendError(f"empty completion: {json.dumps(resp)[:500]}")
    return text


def call_mock(entry: dict, system: str, user: str, max_tokens: int, gold_json: str | None) -> str:
    if entry["backend"] == "mock-none":
        return '{"biases_present": ["NONE"], "triggers": []}'
    if gold_json is None:
        raise BackendError("mock-gold backend needs gold_json")
    return gold_json


def complete(entry: dict, system: str, user: str,
             max_tokens: int = DEFAULT_MAX_TOKENS, gold_json: str | None = None) -> str:
    backend = entry["backend"]
    if backend == "anthropic":
        return call_anthropic(entry, system, user, max_tokens)
    if backend == "openai":
        return call_openai_compat(entry, system, user, max_tokens)
    if backend in ("mock-gold", "mock-none"):
        return call_mock(entry, system, user, max_tokens, gold_json)
    raise BackendError(f"unknown backend {backend!r}")


def load_registry(path: str = "models.json") -> dict[str, dict]:
    with open(path, encoding="utf-8") as f:
        reg = json.load(f)
    return {m["name"]: m for m in reg["models"]}
