"""Sequential evidence extraction, fusion, bounded resolver and human review."""
import time
import uuid

from .boundaries import validate_boundary
from .contracts import AgentStep, Observation, Resolution
from .fusion import build_anchors, fuse
from .providers import get_providers, provider_name
from .resolver import resolve
from .telemetry import Session, CallCap, ProviderFailure
from .transport import ReplayMiss

RUNS: dict[str, dict] = {}


def _timed(trace: list, agent: str, role: str, model: str, inp: str, fn, summarize):
    t0 = time.perf_counter()
    try:
        res = fn()
        trace.append(AgentStep(agent=agent, role=role, model=model, input_summary=inp,
                               output_summary=summarize(res), duration_ms=round((time.perf_counter() - t0) * 1000, 2)))
        return res
    except Exception as e:  # recorded, then re-raised
        trace.append(AgentStep(agent=agent, role=role, model=model, input_summary=inp, output_summary=type(e).__name__,
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
               sketch_png: bytes | None, sketch_labels: list[dict], max_calls: int | None = None) -> dict:
    trace: list[AgentStep] = []
    session = Session(trace, max_calls)
    speech, reason = get_providers(session)
    failures = []
    def safe(agent, model, inp, fn, fallback):
        try:
            return _timed(trace, agent, 'extract evidence', model, inp, fn, lambda r: f'{len(r)} items')
        except ReplayMiss:
            raise  # exact replay misses are configuration/data errors, never silent fallbacks
        except (CallCap, ProviderFailure, ValueError, KeyError, TypeError):
            failures.append('partial_call_cap' if session.calls >= session.limit else 'unresolved')
            return fallback
    if transcript is not None:
        text = _timed(trace, 'Transcriber', 'supplied transcript', 'none', 'text', lambda: transcript, lambda t: f'{len(t)} chars')
    elif audio:
        text = safe('Transcriber', speech.model, 'audio', lambda: speech.transcribe(audio, audio_name), '')
    else:
        text = ''
    sp_rows = safe('SpeechReader', reason.model, f'{len(text)} chars', lambda: reason.extract_speech(text, area), []) if text.strip() else []
    sk_rows = safe('SketchReader', reason.model, f'{len(sketch_labels)} labels', lambda: reason.extract_sketch(sketch_labels, area, sketch_png), []) if sketch_labels or sketch_png else []
    obs = _to_obs(sk_rows, "sketch", "sk") + _to_obs(sp_rows, "speech", "sp")
    fused = _timed(trace, "Fuser", "deterministic group + contradiction detection", "none", f"{len(obs)} observations",
                   lambda: fuse(obs), lambda r: f"{len(r[0])} groups, {len(r[1])} contradictions")
    contras = fused[1]
    payload = [{"id": c.id, "entity": c.entity, "predicate": c.predicate,
                "observations": [o.model_dump() for o in c.observations]} for c in contras]
    from .providers import MockReason
    questions = _timed(trace, 'ContradictionReviewer', 'deterministic fallback questions; resolver may refine', 'none', f'{len(contras)} contradictions', lambda: MockReason().clarify(payload), lambda q: f'{len(q)} questions')
    rid = uuid.uuid4().hex[:10]
    run = {"id": rid, "area": area, "provider_mode": provider_name(), "transcript": text,
           "observations": obs, "trace": trace, "sketch_png": sketch_png,
           "_session": session, "_obs": obs, "_questions": questions, "_resolutions": {}, "_confirmed": set()}
    recompute(run)
    run['_failures'] = failures
    run['_reason'] = reason
    resume_resolver(run)
    recompute(run)
    apply_status(run)
    RUNS[rid] = run
    return run


def apply_status(run):
    status = run.get('resolver_status', '')
    if run.get('_failures'):
        run['status'] = run['_failures'][0]
    elif not run['observations'] and not status.startswith('partial'):
        run['status'] = 'unresolved'
    elif status.startswith('partial') or status == 'unresolved':
        run['status'] = status


def resume_resolver(run):
    try:
        resolve(run, run['_reason'])
    except CallCap:
        run['resolver_status'] = 'partial_call_cap'
    except ProviderFailure:
        run['resolver_status'] = 'unresolved'


def answer(run: dict, contradiction_id: str, chosen: str | None, note: str = "") -> None:
    c = next((c for c in run["contradictions"] if c.id == contradiction_id), None)
    if c is None:
        raise KeyError("unknown contradiction")
    if chosen is not None and chosen not in {o.id for o in c.observations}:
        raise ValueError("chosen observation is not one of the alternatives")
    run["_resolutions"][contradiction_id] = Resolution(contradiction_id=contradiction_id,
                                                       chosen_observation_id=chosen, note=note)
    recompute(run)
    resume_resolver(run)
    recompute(run)
    apply_status(run)


def confirm(run: dict, anchor_ids: list[str]) -> None:
    known = {a.id: a for a in run["anchors"]}
    for aid in anchor_ids:
        a = known.get(aid)
        if a is None or a.lon is None or a.order is None:
            raise ValueError(f"anchor {aid} cannot be confirmed (missing or unresolved)")
    run["_confirmed"].update(anchor_ids)
    recompute(run)
    apply_status(run)


def view(run: dict) -> dict:
    out = {k: v for k, v in run.items() if not k.startswith("_") and k not in ("sketch_png", "trace")}
    out["observations"] = [o.model_dump() for o in run["observations"]]
    out["contradictions"] = [c.model_dump() for c in run["contradictions"]]
    out["anchors"] = [a.model_dump() for a in run["anchors"]]
    out["boundary"] = run["boundary"].model_dump()
    out["resolutions"] = {k: v.model_dump() for k, v in run["_resolutions"].items()}
    out["telemetry"] = run["_session"].totals()
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
