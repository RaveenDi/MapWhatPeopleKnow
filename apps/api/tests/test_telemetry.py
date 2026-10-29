from app.telemetry import Session

def test_usage_and_totals():
    trace = []
    s = Session(trace, 2)
    s.invoke('muse-spark-1.3', 'test', lambda: {'usage': {'prompt_tokens': 100, 'completion_tokens': 50}})
    assert s.totals()['tokens'] == 150
    assert s.totals()['estimated_cost_usd'] == 0.00015
    assert trace[0].prompt_version and trace[0].latency_ms >= 0
    assert s.totals()['pricing_status'] == 'UNVERIFIED'
