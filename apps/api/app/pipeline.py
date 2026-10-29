"""Orchestration: Transcriber -> (SpeechReader || SketchReader) -> Fuser -> Contradiction Reviewer
-> Boundary Validator -> Human confirm. Every step is traced."""
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from .boundaries import validate_boundary
from .contracts import AgentStep, Contradiction, Observation, Resolution
from .fusion import build_anchors, fuse
from .providers import get_providers

RUNS: dict[str, dict] = {}


def _timed(trace: list, agent: str, role: str, model: str, inp: str, fn, summarize):
    t0 = time.perf_counter()
    try:
        res = fn()
        trace.append(AgentStep(agent=agent, role=role, model=model, input_summary=inp,
                               output_summary=summarize(res), duration_ms=round((time.perf_counter() - t0) * 1000, 2)))
        return res
    except Exception as e:  # recorded, then re-raised
        trace.append(AgentStep(agent=agent, role=role, model=model, input_summary=inp, output_summary=str(e)[:200],
                               duration_ms=round((time.perf_counter() - t0) * 1000, 2), status="error"))
        raise


def _to_obs(rows: list[dict], modality: str, prefix: str) -> list[Observation]:
    return [Observation(id=f"{prefix}{i}", modality=modality, entity=r["entity"], predicate=r["predicate"],
                        value=str(r["value"]), source_ref=f"{modality}:{prefix}{i}", wording=r.get("wording", ""))
            for i, r in enumerate(rows, 1)]


def recompute(run: dict) -> None:
    """Deterministic stages after extraction; re-run after every answer/confirmation."""
    obs = run["_obs"]
    _, contras = fuse(obs)
    qs = run["_questions"]
    contras = [c.model_copy(update={"question": qs.get(c.id, "")}) for c in contras]
    res = run["_resolutions"]
    anchors = build_anchors(obs, run["area"]["gazetteer"], contras, res, run["_confirmed"])
    t0 = time.perf_counter()
    boundary = validate_boundary(anchors)
    run["trace"].append(AgentStep(agent="BoundaryValidator", role="deterministic Shapely/pyproj check", model="none",
                                  input_summary=f"{sum(a.status == 'confirmed' for a in anchors)} confirmed anchors",
                                  output_summary=boundary.status + (f" {boundary.errors}" if boundary.errors else ""),
                                  duration_ms=round((time.perf_counter() - t0) * 1000, 2)))
    run["contradictions"] = contras
    run["anchors"] = anchors
    run["boundary"] = boundary
    open_c = [c for c in contras if c.id not in res or res[c.id].chosen_observation_id is None]
    run["status"] = "awaiting_user" if open_c or boundary.status != "valid_draft" else "draft_ready"


def create_run(area: dict, transcript: str | None, audio: bytes | None, audio_name: str,
               sketch_png: bytes | None, sketch_labels: list[dict]) -> dict:
    speech, reason = get_providers()
    trace: list[AgentStep] = []
    if transcript:
        text = _timed(trace, "Transcriber", "passthrough of supplied transcript", "none", "text", lambda: transcript,
                      lambda t: f"{len(t)} chars")
    elif audio:
        text = _timed(trace, "Transcriber", "speech to text", speech.model, f"{len(audio)} bytes audio",
                      lambda: speech.transcribe(audio, audio_name), lambda t: f"{len(t)} chars")
    else:
        text = ""
    with ThreadPoolExecutor(2) as ex:
        f_sp = ex.submit(_timed, trace, "SpeechReader", "transcript to observations", reason.model,
                         f"{len(text)} chars", lambda: reason.extract_speech(text, area), lambda r: f"{len(r)} observations")
        f_sk = ex.submit(_timed, trace, "SketchReader", "sketch labels to observations", reason.model,
                         f"{len(sketch_labels)} labels" + (", image" if sketch_png else ""),
                         lambda: reason.extract_sketch(sketch_labels, area, sketch_png), lambda r: f"{len(r)} observations")
        sp_rows, sk_rows = f_sp.result(), f_sk.result()
    obs = _to_obs(sk_rows, "sketch", "sk") + _to_obs(sp_rows, "speech", "sp")
    fused = _timed(trace, "Fuser", "deterministic group + contradiction detection", "none", f"{len(obs)} observations",
                   lambda: fuse(obs), lambda r: f"{len(r[0])} groups, {len(r[1])} contradictions")
    contras = fused[1]
    payload = [{"id": c.id, "entity": c.entity, "predicate": c.predicate,
                "observations": [o.model_dump() for o in c.observations]} for c in contras]
    questions = _timed(trace, "ContradictionReviewer", "model proposes questions only; never resolves", reason.model,
                       f"{len(contras)} contradictions", lambda: reason.clarify(payload) if contras else {},
                       lambda q: f"{len(q)} questions")
    rid = uuid.uuid4().hex[:10]
    run = {"id": rid, "area": area, "provider_mode": type(reason).__name__, "transcript": text,
           "observations": obs, "trace": trace, "sketch_png": sketch_png,
           "_obs": obs, "_questions": questions, "_resolutions": {}, "_confirmed": set()}
    recompute(run)
    RUNS[rid] = run
    return run


def answer(run: dict, contradiction_id: str, chosen: str | None, note: str = "") -> None:
    c = next((c for c in run["contradictions"] if c.id == contradiction_id), None)
    if c is None:
        raise KeyError("unknown contradiction")
    if chosen is not None and chosen not in {o.id for o in c.observations}:
        raise ValueError("chosen observation is not one of the alternatives")
    run["_resolutions"][contradiction_id] = Resolution(contradiction_id=contradiction_id,
                                                       chosen_observation_id=chosen, note=note)
    recompute(run)


def confirm(run: dict, anchor_ids: list[str]) -> None:
    known = {a.id: a for a in run["anchors"]}
    for aid in anchor_ids:
        a = known.get(aid)
        if a is None or a.lon is None or a.order is None:
            raise ValueError(f"anchor {aid} cannot be confirmed (missing or unresolved)")
    run["_confirmed"].update(anchor_ids)
    recompute(run)


def view(run: dict) -> dict:
    out = {k: v for k, v in run.items() if not k.startswith("_") and k not in ("sketch_png", "trace")}
    out["observations"] = [o.model_dump() for o in run["observations"]]
    out["contradictions"] = [c.model_dump() for c in run["contradictions"]]
    out["anchors"] = [a.model_dump() for a in run["anchors"]]
    out["boundary"] = run["boundary"].model_dump()
    out["resolutions"] = {k: v.model_dump() for k, v in run["_resolutions"].items()}
    out["has_sketch"] = bool(run["sketch_png"])
    return out


def export_geojson(run: dict) -> dict:
    feats = []
    for a in run["anchors"]:
        if a.status == "confirmed":
            feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [a.lon, a.lat]},
                          "properties": {"kind": "confirmed_anchor", "name": a.label, "order": a.order,
                                         "evidence": list(a.evidence)}})
    b = run["boundary"]
    if b.status == "valid_draft":
        ring = [list(p) for p in b.lonlat] + [list(b.lonlat[0])]
        feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
                      "properties": {"kind": "draft_boundary", "area_m2": b.area_m2, "note": b.note,
                                     "draft": True}})
    return {"type": "FeatureCollection", "features": feats,
            "properties": {"area": run["area"]["name"], "fictional": True,
                           "open_contradictions": [c.id for c in run["contradictions"]
                                                   if c.id not in run["_resolutions"]
                                                   or run["_resolutions"][c.id].chosen_observation_id is None]}}
