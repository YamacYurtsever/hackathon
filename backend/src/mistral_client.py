import json
import os
import time
from dataclasses import dataclass

# SDK v2 moved the client here; `from mistralai import Mistral` resolves to a
# namespace package with nothing in it.
from mistralai.client import Mistral

DEFAULT_MODEL = "mistral-large-latest"

_client: Mistral | None = None


def _get_client() -> Mistral:
    global _client
    if _client is None:
        _client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    return _client


@dataclass
class JSONResult:
    """A parsed JSON response plus what it cost, so callers can report timings."""

    data: dict
    raw: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: int


def complete_json(system: str, user: str, model: str = DEFAULT_MODEL) -> JSONResult:
    started = time.monotonic()
    response = _get_client().chat.complete(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
    )
    latency_ms = int((time.monotonic() - started) * 1000)

    raw = response.choices[0].message.content
    usage = getattr(response, "usage", None)

    return JSONResult(
        data=json.loads(raw),
        raw=raw,
        prompt_tokens=getattr(usage, "prompt_tokens", None),
        completion_tokens=getattr(usage, "completion_tokens", None),
        latency_ms=latency_ms,
    )
