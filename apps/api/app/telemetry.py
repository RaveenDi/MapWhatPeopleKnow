"""One budget covers extraction, resolution, retries, repair and resumed turns."""
import time
from .config import PROMPT_VERSION, PRICES_UNVERIFIED, max_calls
from .contracts import AgentStep

class CallCap(RuntimeError):
    pass

class ProviderFailure(RuntimeError):
    pass

class Session:
    def __init__(self, trace, limit=None):
        self.trace = trace
        self.limit = max_calls() if limit is None else limit
        self.calls = 0

    def invoke(self, model, operation, fn):
        if self.calls >= self.limit:
            raise CallCap('Model call cap reached')
        self.calls += 1
        start = time.perf_counter()
        status, result = 'ok', None
        try:
            result = fn()
            return result
        except Exception:
            status = 'error'
            raise
        finally:
            usage = result.get('usage', {}) if isinstance(result, dict) else {}
            pt, ct = usage.get('prompt_tokens'), usage.get('completion_tokens')
            price = PRICES_UNVERIFIED.get(model)
            cost = ((pt * price['input'] + ct * price['output']) / 1_000_000 if price and isinstance(pt, int) and isinstance(ct, int) else (0.0 if model.startswith('mock') else None))
            elapsed = round((time.perf_counter() - start) * 1000, 3)
            self.trace.append(AgentStep(agent='ModelCall', role=operation, model=model, input_summary='provider request', output_summary=status, duration_ms=elapsed, latency_ms=elapsed, status=status, prompt_version=PROMPT_VERSION, prompt_tokens=pt, completion_tokens=ct, estimated_cost_usd=cost, model_calls=1))

    def totals(self):
        entries = [s for s in self.trace if s.model_calls]
        return {'calls': self.calls, 'steps': sum(s.agent == 'Resolver' for s in self.trace),
                'prompt_tokens': sum(s.prompt_tokens or 0 for s in entries),
                'completion_tokens': sum(s.completion_tokens or 0 for s in entries),
                'tokens': sum((s.prompt_tokens or 0) + (s.completion_tokens or 0) for s in entries),
                'usage_complete': all(s.prompt_tokens is not None and s.completion_tokens is not None for s in entries),
                'latency_ms': round(sum(s.latency_ms for s in entries), 3),
                'estimated_cost_usd': round(sum(s.estimated_cost_usd or 0 for s in entries), 8),
                'cost_complete': all(s.estimated_cost_usd is not None for s in entries),
                'pricing_status': 'UNVERIFIED'}

class MeteredMock:
    def __init__(self, provider, session):
        self.provider, self.session, self.model = provider, session, provider.model

    def __getattr__(self, name):
        method = getattr(self.provider, name)
        return lambda *a, **kw: self.session.invoke(self.model, name, lambda: method(*a, **kw))
