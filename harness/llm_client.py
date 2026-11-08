"""Budgeted OpenRouter calls with JSON schema validation and sanitized failures."""
import json
import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from harness.artifacts import ROOT, digest
from harness.costs import Budget, estimate_cost, rates
from harness.schemas import CRITERIA

load_dotenv(ROOT / '.env')
OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'
DEFAULT_TIMEOUT = 180
_client = None


class ModelCallError(RuntimeError):
    def __init__(self, message, metadata):
        super().__init__(message)
        self.metadata = metadata


def get_client():
    global _client
    if _client is None:
        key = os.environ.get('OPENROUTER_API_KEY', '').strip()
        if not key:
            raise RuntimeError('OPENROUTER_API_KEY is empty; configure the local ignored .env file.')
        _client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=key, max_retries=0)
    return _client


def output_schema(schema_model):
    schema = schema_model.model_json_schema()
    criteria = schema.get('properties', {}).get('criteria')
    if criteria:
        item = criteria['additionalProperties']
        criteria.clear()
        criteria.update(type='object', properties={key: item for key in CRITERIA},
                        required=list(CRITERIA), additionalProperties=False)
    return schema


def call_structured(model, system, user, schema_model, max_tokens, timeout=DEFAULT_TIMEOUT):
    client = get_client()
    schema = output_schema(schema_model)
    rate = rates(model)
    # UTF-8 byte count is deliberately conservative, with extra protocol overhead.
    input_bound = len((system + user + json.dumps(schema)).encode('utf-8')) + 4096
    reservation = estimate_cost(model, input_bound, max_tokens)
    budget = Budget()
    budget.reserve(reservation, model)
    meta = {'model': model, 'temperature': 0, 'max_tokens': max_tokens,
            'request_sha256': digest({'model': model, 'system': system, 'user': user, 'schema': schema}),
            'prompt_tokens': None, 'completion_tokens': None, 'total_tokens': None,
            'estimated_cost_usd': None, 'budget_reserved_usd': reservation,
            'pricing': rate, 'cost_status': 'unknown_reserved'}
    started = time.monotonic()
    try:
        response = client.chat.completions.create(
            model=model, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            response_format={'type': 'json_schema', 'json_schema': {
                'name': schema_model.__name__, 'strict': True, 'schema': schema}},
            temperature=0, max_tokens=max_tokens, timeout=timeout,
            extra_body={'provider': {'require_parameters': True, 'max_price': {
                'prompt': rate['input_per_million_usd'], 'completion': rate['output_per_million_usd']}}})
    except Exception as error:
        meta['latency_seconds'] = time.monotonic() - started
        # Provider exception strings may contain request data or secrets. Never persist them.
        raise ModelCallError(f'Model request failed ({type(error).__name__}); cost unknown, reservation retained.', meta) from None
    meta['latency_seconds'] = time.monotonic() - started
    usage = getattr(response, 'usage', None)
    for key in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
        meta[key] = getattr(usage, key, None)
    meta.update(response_id=getattr(response, 'id', None), resolved_model=getattr(response, 'model', model))
    if all(type(meta[k]) is int and meta[k] >= 0 for k in ('prompt_tokens', 'completion_tokens')):
        cost = estimate_cost(model, meta['prompt_tokens'], meta['completion_tokens'])
        meta.update(estimated_cost_usd=cost, cost_status='estimated_from_usage')
        reported_cost = getattr(usage, 'cost', None)
        if type(reported_cost) in (int, float) and reported_cost >= 0:
            meta['provider_reported_cost_usd'] = reported_cost
        budget.settle(reservation, max(cost, reported_cost) if type(reported_cost) in (int, float) else cost, model)
    choice = response.choices[0] if response.choices else None
    meta['finish_reason'] = getattr(choice, 'finish_reason', None)
    if not choice or choice.finish_reason != 'stop' or not choice.message.content:
        raise ModelCallError('Missing, refused or truncated model response.', meta)
    try:
        parsed = schema_model.model_validate_json(choice.message.content)
    except Exception:
        raise ModelCallError('Invalid structured model response; no grade assigned.', meta) from None
    return parsed, meta
