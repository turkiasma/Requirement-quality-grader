"""Shared OpenRouter chat client for structured-output model calls.

Centralizes the request/response/validation pattern both LLM1 and the second
assessor use: call the model with a JSON-object response format, then
validate the returned JSON against a Pydantic schema. Invalid or truncated
output is a RuntimeError, not a grade.
"""

import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'
DEFAULT_TIMEOUT = 180

_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get('OPENROUTER_API_KEY')
        if not api_key:
            raise RuntimeError(
                'OPENROUTER_API_KEY is not set. Put it in a local .env file '
                '(gitignored, never commit it) or export it in your shell.'
            )
        _client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
    return _client


def call_structured(model, system, user, schema_model, max_tokens, timeout=DEFAULT_TIMEOUT):
    """Call an OpenRouter chat model and validate the JSON response against schema_model.

    Returns (parsed_model, metadata) where metadata carries latency_seconds
    and token usage for the cost/latency report.
    """
    client = get_client()
    started = time.monotonic()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
            response_format={'type': 'json_object'},
            temperature=0,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    except Exception as error:
        raise RuntimeError(f"Model call failed using '{model}': {error}") from error
    latency_seconds = time.monotonic() - started

    choice = response.choices[0] if response.choices else None
    content = choice.message.content if choice and choice.message else None
    if not content:
        raise RuntimeError(f"Model '{model}' returned no content.")

    try:
        parsed = schema_model.model_validate_json(content)
    except Exception as error:
        raise RuntimeError(f"Invalid structured output from '{model}': {error}") from error

    usage = getattr(response, 'usage', None)
    metadata = {
        'model': model,
        'latency_seconds': latency_seconds,
        'prompt_tokens': getattr(usage, 'prompt_tokens', None),
        'completion_tokens': getattr(usage, 'completion_tokens', None),
        'total_tokens': getattr(usage, 'total_tokens', None),
    }
    return parsed, metadata
