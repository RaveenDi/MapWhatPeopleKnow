from app.telemetry import Session

def test_usage_and_totals():
    trace = []
    s = Session(trace, 2)
    s.invoke('muse-spark-1.3', 'test', lambda: {'usage': {'prompt_tokens': 100, 'completion_tokens': 50}})
    assert s.totals()['tokens'] == 150
    assert s.totals()['estimated_cost_usd'] == 0.0003375  # (100*1.25 + 50*4.25) per M tokens
    assert trace[0].prompt_version and trace[0].latency_ms >= 0
    assert s.totals()['pricing_status'].startswith('published')

def test_trace_totals_api():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    run = client.post('/api/runs', data={'sketch_labels_json':'[{"label":"well"}]'}).json()
    trace = client.get('/api/runs/' + run['id'] + '/trace').json()
    assert trace[-1]['totals'] == run['telemetry']
    assert sum(t.get('model_calls', 0) for t in trace) == run['telemetry']['calls']
    assert all(t['latency_ms'] >= 0 for t in trace[:-1])
