"""Content-addressed transport; credentials never enter recording payloads."""
import base64
import hashlib
import json
import os
from pathlib import Path

class ReplayMiss(RuntimeError):
    pass

class Transport:
    def __init__(self, mode=None, directory=None):
        self.mode = mode or os.getenv('MODEL_PROVIDER', 'mock')
        self.directory = Path(directory or os.getenv('RECORDINGS_DIR', 'data/recordings'))

    def request(self, endpoint, body):
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
