import json
import httpx
import pytest
from app import pipeline, demo
from app.providers import MetaReason, MockReason
from app.transport import Transport
from app.telemetry import Session, ProviderFailure

@pytest.mark.parametrize('fault', ['timeout', 429, 503])
def test_retry_bound(fault, tmp_path, monkeypatch):
    monkeypatch.setenv('MODEL_API_KEY', 'test')
    sleeps, calls = [], []
    monkeypatch.setattr('app.transport.time.sleep', sleeps.append)
    def post(url, **kwargs):
        calls.append(1)
        if fault == 'timeout':
            raise httpx.ReadTimeout('private text')
        return httpx.Response(fault, headers={'retry-after': '1'}, request=httpx.Request('POST', url))
    monkeypatch.setattr(httpx, 'post', post)
    session = Session([], 10)
    with pytest.raises(ProviderFailure):
        Transport('meta', tmp_path, session).request('/test', {'model': 'test'})
    assert len(calls) == session.calls == 3 and len(sleeps) == 2
    if fault == 429:
        assert sleeps == [1, 1]

@pytest.mark.parametrize('repair_ok', [False, True])
def test_malformed_repair(monkeypatch, repair_ok):
    provider = MetaReason()
    calls = []
    def response(*a):
        calls.append(a)
        content = json.dumps({'observations': []}) if repair_ok and len(calls) == 2 else 'bad json'
        return {'choices': [{'message': {'content': content}}]}
    monkeypatch.setattr(provider.transport, 'request', response)
    if repair_ok:
        assert provider.extract_speech('hello', {}) == []
    else:
        with pytest.raises(ProviderFailure):
            provider.extract_speech('hello', {})
    assert len(calls) == 2

def test_call_cap_and_empty(monkeypatch):
    monkeypatch.setenv('MODEL_PROVIDER', 'mock')
    monkeypatch.setenv('MODEL_MAX_CALLS', '1')
    run = pipeline.create_run(demo.AREA, '', None, '', None, [])
    assert not run['observations'] and run['status'] == 'partial_call_cap'
    assert run['_session'].totals()['calls'] == 1

def test_tool_errors_recover(monkeypatch):
    turns = iter([
        {'tool_calls': [{'id': '1', 'function': {'name': 'invent_coordinates', 'arguments': '{}'}}]},
        {'tool_calls': [{'id': '2', 'function': {'name': 'propose_anchor', 'arguments': '{'}}]},
        {'tool_calls': [{'id': '3', 'function': {'name': 'finish', 'arguments': '{}'}}]},
    ])
    monkeypatch.setattr(MockReason, 'resolve_turn', lambda *args: next(turns))
    run = pipeline.create_run(demo.AREA, '', None, '', None, [])
    assert run['resolver_status'] == 'finished'
    assert len([s for s in run['trace'] if s.agent == 'ResolverTool' and s.status == 'error']) == 2

def test_provider_failure_preserves_partial_evidence(monkeypatch):
    def fail(*args):
        raise ProviderFailure('Malformed response')
    monkeypatch.setattr(MockReason, 'extract_speech', fail)
    run = pipeline.create_run(demo.AREA, 'hello', None, '', None, [{'label': 'school'}])
    assert run['status'] == 'unresolved'
    assert len(run['observations']) == 1

def test_retry_success_and_call_cap(tmp_path, monkeypatch):
    from app.telemetry import CallCap
    monkeypatch.setenv('MODEL_API_KEY', 'test')
    monkeypatch.setattr('app.transport.time.sleep', lambda _: None)
    calls = []
    def post(url, **kw):
        calls.append(1)
        return httpx.Response(503 if len(calls) == 1 else 200, json={'text':'ok'}, request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx, 'post', post)
    session = Session([], 2)
    assert Transport('meta', tmp_path, session).request('/test', {'model':'test'}) == {'text':'ok'}
    assert session.calls == 2
    calls.clear()
    with pytest.raises(CallCap):
        Transport('meta', tmp_path, Session([], 1)).request('/other', {'model':'test'})
    assert len(calls) == 1


def test_malformed_meta_run_is_unresolved(tmp_path, monkeypatch):
    monkeypatch.setenv('MODEL_PROVIDER', 'meta')
    monkeypatch.setenv('MODEL_API_KEY', 'test')
    monkeypatch.setenv('RECORDINGS_DIR', str(tmp_path))
    monkeypatch.setattr(httpx, 'post', lambda url, **kw: httpx.Response(200, json={'choices':[]}, request=httpx.Request('POST', url)))
    run = pipeline.create_run(demo.AREA, 'text', None, '', None, [])
    assert run['status'] == 'unresolved' and run['_session'].calls == 4
    assert any(t.agent == 'Resolver' and t.status == 'error' for t in run['trace'])


def test_empty_transcript_is_unresolved(monkeypatch):
    monkeypatch.setenv('MODEL_PROVIDER', 'mock')
    run = pipeline.create_run(demo.AREA, '   ', None, '', None, [])
    assert run['status'] == 'unresolved' and run['observations'] == []
