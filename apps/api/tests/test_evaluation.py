import importlib.util
import json
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('evaluation', ROOT / 'evals/run.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)

def rows():
    return [json.loads(line) for line in (ROOT / 'evals/manifest.jsonl').read_text().splitlines()]

def test_paired_mock_and_global_cap():
    report = evaluation.evaluate(rows(), 'mock', 'dev', ['sketch', 'speech', 'both'], 100)
    assert set(report['summary']) == {'sketch', 'speech', 'both'}
    assert len(report['cases']) == 12
    assert report['summary']['both']['contradictions_surfaced'] >= 1
    assert report['summary']['speech']['relation']['precision'] < 1  # negation trap exposes mock limitations
    assert report['summary']['both']['accepted_anchors'] == 0
    capped = evaluation.evaluate(rows(), 'mock', 'dev', ['both'], 2)
    assert capped['calls'] == 2
    assert all(c['status'].startswith('partial') for c in capped['cases'])

def test_outgoing_requests_exclude_ground_truth_and_replay(tmp_path, monkeypatch):
    fixture = rows()[0]
    fixture['ground_truth']['entities'].append('SECRET_GROUND_TRUTH_SENTINEL')
    fixture['ground_truth']['anchors'] = [{'entity':'SECRET_GROUND_TRUTH_SENTINEL','gazetteer_id':'SECRET_GROUND_TRUTH_SENTINEL'}]
    monkeypatch.setenv('RECORDINGS_DIR', str(tmp_path))
    monkeypatch.setenv('MODEL_API_KEY', 'test-credential')
    outgoing = []
    def post(url, **kwargs):
        body = kwargs['json']
        outgoing.append(body)
        if 'tools' in body:
            message = {'content':None, 'tool_calls':[{'id':'finish', 'type':'function', 'function':{'name':'finish', 'arguments':'{}'}}]}
        else:
            message = {'content':json.dumps({'observations':[]})}
        return httpx.Response(200, json={'choices':[{'message':message}], 'usage':{'prompt_tokens':10,'completion_tokens':5}}, request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx, 'post', post)
    first = evaluation.evaluate([fixture], 'meta', 'dev', ['both'], 10)
    assert len(outgoing) == 3
    assert 'SECRET_GROUND_TRUTH_SENTINEL' not in json.dumps(outgoing)
    assert 'ground_truth' not in json.dumps(outgoing)
    monkeypatch.setattr(httpx, 'post', lambda *a, **k: (_ for _ in ()).throw(AssertionError('network in replay')))
    replay = evaluation.evaluate([fixture], 'replay', 'dev', ['both'], 10)
    assert replay['cases'][0]['metrics'] == first['cases'][0]['metrics']
    assert replay['calls'] == 3
    assert all('test-credential' not in p.read_text() for p in tmp_path.glob('*.json'))
