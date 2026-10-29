"""Content-addressed transport; credentials never enter recording payloads."""
import base64
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

class ReplayMiss(RuntimeError):
    pass

class Transport:
    def __init__(self, mode=None, directory=None, session=None):
        self.session = session
        self.mode = mode or os.getenv('MODEL_PROVIDER', 'mock')
        self.directory = Path(directory or os.getenv('RECORDINGS_DIR', 'data/recordings'))

    def request(self, endpoint, body):
        import httpx
        from .telemetry import ProviderFailure
        for attempt in range(3):
            try:
                fn = lambda: self._request(endpoint, body)
                return self.session.invoke(body.get('model', 'unknown'), endpoint, fn) if self.session else fn()
            except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                retryable = isinstance(exc, httpx.TimeoutException) or exc.response.status_code == 429 or exc.response.status_code >= 500
                if not retryable or attempt == 2:
                    raise ProviderFailure('Provider timeout or HTTP failure') from None
                delay = 0.25 * (2 ** attempt)
                if isinstance(exc, httpx.HTTPStatusError):
                    value = exc.response.headers.get('retry-after')
                    if value:
                        try:
                            delay = max(delay, float(value))
                        except ValueError:
                            try:
                                delay = max(delay, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
                            except (TypeError, ValueError):
                                pass
                # Do not block a request for arbitrarily long server delays.
                if delay > 30:
                    raise ProviderFailure('Retry-After exceeds 30-second wait limit') from None
                time.sleep(delay)
            except httpx.RequestError:
                raise ProviderFailure('Provider connection failed') from None

    def _request(self, endpoint, body):
        request = {'endpoint': endpoint, 'body': body}
        digest = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        path = self.directory / (digest + '.json')
        if self.mode == 'replay':
            if not path.exists():
                raise ReplayMiss('Replay miss: ' + digest)
            saved = json.loads(path.read_text(encoding='utf-8'))
            if saved['request'] != request:
                raise ReplayMiss('Recording request mismatch: ' + digest)
            return saved['response']
        if self.mode != 'meta':
            raise ValueError('Network transport requires meta or replay')
        import httpx
        kwargs = {'headers': {'Authorization': 'Bearer ' + os.environ['MODEL_API_KEY']}, 'timeout': 90}
        if endpoint == '/audio/transcriptions':
            kwargs.update(files={'file': (body['filename'], base64.b64decode(body['audio']))}, data={'model': body['model']})
        else:
            kwargs['json'] = body
        response = httpx.post('https://api.meta.ai/v1' + endpoint, **kwargs)
        response.raise_for_status()
        result = response.json()
        self.directory.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'request': request, 'response': result}, ensure_ascii=False), encoding='utf-8')
        return result
