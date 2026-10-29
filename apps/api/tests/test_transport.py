import json
import pytest
from app.transport import Transport, ReplayMiss

def test_record_replay(tmp_path, monkeypatch):
    import httpx
    monkeypatch.setenv('MODEL_API_KEY', 'test-secret')
    monkeypatch.setattr(httpx, 'post', lambda *a, **k: httpx.Response(200, json={'text': 'hello'}, request=httpx.Request('POST', a[0])))
    assert Transport('meta', tmp_path).request('/test', {'model': 'test'}) == {'text': 'hello'}
    saved = next(tmp_path.glob('*.json')).read_text()
    assert 'test-secret' not in saved and 'Authorization' not in saved
    monkeypatch.setattr(httpx, 'post', lambda *a, **k: pytest.fail('replay used network'))
    assert Transport('replay', tmp_path).request('/test', {'model': 'test'}) == {'text': 'hello'}
    with pytest.raises(ReplayMiss):
        Transport('replay', tmp_path).request('/test', {'model': 'different'})
