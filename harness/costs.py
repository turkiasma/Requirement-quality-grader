"""Dated pricing and a process-safe cumulative $2 reservation ledger (Linux/macOS)."""
import fcntl
import json
from pathlib import Path
from harness.artifacts import ROOT, timestamp

PRICING_PATH = ROOT / 'data/model_pricing.json'
LEDGER_PATH = ROOT / '.api-budget.json'


def rates(model):
    data = json.loads(PRICING_PATH.read_text())
    if model not in data['models']:
        raise ValueError('Model has no verified pricing snapshot; add pricing before paid calls.')
    return data['models'][model]


def estimate_cost(model, prompt_tokens, completion_tokens):
    rate = rates(model)
    return (prompt_tokens * rate['input_per_million_usd'] +
            completion_tokens * rate['output_per_million_usd']) / 1_000_000


class Budget:
    """Reserve worst-case cost before sending; uncertain failures retain reservations.

    Reservations persist across commands, including process crashes. No SDK retries.
    The ledger is local and must not be deleted to bypass the authorized cap.
    """
    def __init__(self, path=LEDGER_PATH, cap=2.0):
        if not 0 < cap <= 2:
            raise ValueError('Budget cap must be greater than zero and at most US$2.')
        self.path, self.cap = Path(path), cap

    def update(self, amount, event):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('a+', encoding='utf-8') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.seek(0)
            data = json.loads(stream.read() or '{"reserved_or_spent_usd":0,"events":[]}')
            total = data['reserved_or_spent_usd'] + amount
            if total > self.cap + 1e-12:
                raise RuntimeError('US$2 cumulative budget would be exceeded; paid execution stopped.')
            data['reserved_or_spent_usd'] = max(0, total)
            data['events'].append({'timestamp': timestamp(), 'usd_adjustment': amount, **event})
            stream.seek(0); stream.truncate(); json.dump(data, stream, indent=2); stream.flush()
        return total

    def reserve(self, amount, model):
        self.update(amount, {'type': 'reservation', 'model': model})

    def settle(self, reserved, actual, model):
        # Never lower the charge for an unknown actual cost.
        return self.update(actual - reserved, {'type': 'settlement', 'model': model})
