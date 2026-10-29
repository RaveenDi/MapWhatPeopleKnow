import pytest
from app import demo, pipeline
from app.resolver import execute

def make():
    return pipeline.create_run(demo.AREA, demo.TRANSCRIPT, None, '', None, [])

def test_resolver_tools_and_pause(monkeypatch):
    monkeypatch.setenv('MODEL_PROVIDER', 'mock')
    run = make()
    assert any(t.agent == 'ResolverTool' for t in run['trace'])
    with pytest.raises(ValueError):
        execute(run, 'propose_anchor', {'entity': 'invented', 'gazetteer_id': 'invented', 'evidence_ids': ['fake']})
    with pytest.raises(ValueError):
        execute(run, 'finish', {'coordinates': [1, 2]})
    assert not run['_confirmed'] and not run['_resolutions']
    assert execute(run, 'validate_boundary', {'anchor_ids': []})['status'] != 'valid_draft'

def test_step_cap(monkeypatch):
    monkeypatch.setenv('RESOLVER_MAX_STEPS', '1')
    assert make()['status'] == 'partial_step_cap'
