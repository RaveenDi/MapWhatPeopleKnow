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

def test_contradiction_requires_user_and_resume_budget(monkeypatch):
    monkeypatch.setenv('MODEL_PROVIDER', 'mock')
    labels = [{'label':'Old Well', 'relations':{'boundary_corner':'2'}}]
    run = pipeline.create_run(demo.AREA, 'Bounded by Old Well.', None, '', None, labels)
    assert run['resolver_status'] == 'awaiting_user'
    c = run['contradictions'][0]
    assert run['_resolutions'] == {}
    anchor = execute(run, 'propose_anchor', {'entity':'old_well','gazetteer_id':'old_well','evidence_ids':['sk2']})
    assert anchor['status'] == 'unresolved' and anchor['lon'] is None
    with pytest.raises(ValueError):
        execute(run, 'resolve_contradiction', {'contradiction_id':c.id})
    with pytest.raises(ValueError):
        execute(run, 'propose_anchor', {'entity':'old_well','gazetteer_id':'mill_bridge','evidence_ids':['sk2']})
    first_calls = run['_session'].calls
    pipeline.answer(run, c.id, c.observations[0].id)
    assert run['_session'].calls > first_calls
    assert run['anchors'][0].status == 'proposed' and run['_confirmed'] == set()
    assert sum(s.agent == 'Resolver' for s in run['trace']) <= 8
    pipeline.answer(run, c.id, c.observations[1].id)
    assert run['status'] == 'partial_step_cap'
    assert sum(s.agent == 'Resolver' for s in run['trace']) == 8
