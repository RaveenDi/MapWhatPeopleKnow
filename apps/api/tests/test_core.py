import json
import os

os.environ["MODEL_PROVIDER"] = "mock"

import pytest
from fastapi.testclient import TestClient

from app import demo
from app.boundaries import validate_boundary, validate_xy
from app.contracts import Anchor, Observation
from app.fusion import build_anchors, fuse
from app.main import app


def ob(i, mod, ent, pred, val):
    return Observation(id=i, modality=mod, entity=ent, predicate=pred, value=val, source_ref=f"{mod}:{i}")


def test_agreement_no_contradiction():
    groups, c = fuse([ob("a", "sketch", "path", "side_of_school", "east"), ob("b", "speech", "path", "side_of_school", "east")])
    assert c == [] and len(groups) == 1


def test_contradiction_keeps_both_sources():
    _, c = fuse([ob("a", "sketch", "path", "side_of_school", "east"), ob("b", "speech", "path", "side_of_school", "west")])
    assert len(c) == 1 and {o.source_ref for o in c[0].observations} == {"sketch:a", "speech:b"}


def test_missing_source_rejected():
    with pytest.raises(ValueError):
        fuse([Observation(id="a", modality="sketch", entity="e", predicate="p", value="v", source_ref="")])


def test_observation_immutable():
    with pytest.raises(Exception):
        ob("a", "sketch", "e", "p", "v").value = "x"


def test_unknown_landmark_unresolved():
    o = [ob("a", "speech", "red_shrine", "boundary_corner", "1")]
    a = build_anchors(o, demo.AREA["gazetteer"], [], {}, set())
    assert a[0].status == "unresolved" and a[0].lon is None


def anc(i, lon, lat, order, status="confirmed"):
    return Anchor(id=i, entity=i, label=i, order=order, lon=lon, lat=lat, status=status)


SQUARE = [(20.0, 5.0), (20.002, 5.0), (20.002, 5.0015), (20.0, 5.0015)]


def test_valid_boundary():
    b = validate_boundary([anc(f"a{i}", x, y, i + 1) for i, (x, y) in enumerate(SQUARE)])
    assert b.status == "valid_draft" and 30000 < b.area_m2 < 40000


def test_missing_anchors():
    assert validate_boundary([anc("a", 20, 5, 1), anc("b", 20.001, 5, 2)]).status == "insufficient_evidence"


def test_unconfirmed_anchor_not_used():
    anchors = [anc(f"a{i}", x, y, i + 1, "confirmed" if i < 3 else "proposed") for i, (x, y) in enumerate(SQUARE)]
    assert validate_boundary(anchors).status == "valid_draft"
    anchors[2] = anc("a2", *SQUARE[2], 3, "proposed")
    assert validate_boundary(anchors).status == "insufficient_evidence"


def test_self_intersection_rejected():
    order = [1, 3, 2, 4]  # bow-tie
    b = validate_boundary([anc(f"a{i}", x, y, order[i]) for i, (x, y) in enumerate(SQUARE)])
    assert b.status == "invalid" and "self-intersecting boundary" in b.errors


def test_area_bounds_and_degenerate():
    assert validate_xy([(0, 0), (1, 0), (1, 1), (0, 1)])  # too small
    assert validate_xy([(0, 0), (10, 0), (20, 0)])  # collinear -> area too small


def test_pipeline_end_to_end():
    c = TestClient(app)
    run = c.post("/api/runs/demo").json()
    rid = run["id"]
    assert len(run["contradictions"]) == 1
    con = run["contradictions"][0]
    assert {o["modality"] for o in con["observations"]} == {"sketch", "speech"} and con["question"]
    unresolved = [a for a in run["anchors"] if a["status"] == "unresolved"]
    assert [a["entity"] for a in unresolved] == ["red_shrine"]
    assert run["boundary"]["status"] == "insufficient_evidence"
    assert json.dumps(c.get(f"/api/runs/{rid}/export").json())  # export before confirm has no polygon
    assert not [f for f in c.get(f"/api/runs/{rid}/export").json()["features"] if f["geometry"]["type"] == "Polygon"]
    with_bad = c.post(f"/api/runs/{rid}/confirm", json={"anchor_ids": ["a-red_shrine"]})
    assert with_bad.status_code == 422
    props = [a["id"] for a in run["anchors"] if a["status"] == "proposed"]
    r = c.post(f"/api/runs/{rid}/confirm", json={"anchor_ids": props}).json()
    assert r["boundary"]["status"] == "valid_draft"
    r = c.post(f"/api/runs/{rid}/answers", json={"contradiction_id": con["id"],
                                                  "chosen_observation_id": con["observations"][0]["id"]}).json()
    assert r["status"] == "draft_ready" and len(r["observations"]) == len(run["observations"])  # nothing deleted
    ex = c.get(f"/api/runs/{rid}/export").json()
    assert any(f["geometry"]["type"] == "Polygon" for f in ex["features"])
    trace = c.get(f"/api/runs/{rid}/trace").json()
    assert {"Transcriber", "SpeechReader", "SketchReader", "Fuser", "ContradictionReviewer", "BoundaryValidator"} <= {t["agent"] for t in trace}
    assert c.get("/").status_code == 200
