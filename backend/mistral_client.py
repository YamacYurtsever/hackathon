import os

from mistralai import Mistral

_client: Mistral | None = None


def _get_client() -> Mistral:
    global _client
    if _client is None:
        _client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    return _client


def complete(messages: list[dict], model: str = "mistral-large-latest") -> str:
    response = _get_client().chat.complete(model=model, messages=messages)
    return response.choices[0].message.content
