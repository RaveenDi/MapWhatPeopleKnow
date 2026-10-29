# Agent architecture

Status: implemented and plumbing-tested in **mock mode only**. No live Meta call has been made.

## Hierarchy (code: `apps/api/app/pipeline.py`)

```
Orchestrator (deterministic Python, sequential, traced)
 1. Transcriber            audio -> text            (or passthrough of a supplied transcript)
 2. SpeechReader  ||  SketchReader                  (parallel, model -> observations)
 3. Fuser                  deterministic grouping + contradiction detection
 4. ContradictionReviewer  model writes clarifying QUESTIONS only
 5. BoundaryValidator      deterministic Shapely/pyproj checks
 6. Human confirm          user answers contradictions, confirms anchors
```

Steps 3 and 5 re-run after every answer or confirmation. Each step appends
`{agent, role, model, input_summary, output_summary, duration_ms, status}` to `GET /api/runs/{id}/trace`.

## Meta product per agent

| Agent | Meta product | Mock stand-in | Status |
|---|---|---|---|
| Transcriber | `muse-voice-transcribe-1.0` via `POST /audio/transcriptions` | canned transcript | endpoint shape **UNVERIFIED**, never called |
| SpeechReader | `muse-spark-1.3`, JSON-schema structured output on `api.meta.ai/v1` | regex extraction | **UNVERIFIED**, never called |
| SketchReader | `muse-spark-1.3` with image input | reads a supplied label list (no vision) | **UNVERIFIED**, never called; mock does NOT read pixels |
| ContradictionReviewer | `muse-spark-1.3` | templated question | **UNVERIFIED**, never called |
| Fuser, BoundaryValidator | none (deterministic) | same code | tested |

Open weights (Muse Glimmer, Muse Spark Open) are not used yet; the provider interface would allow swapping them in.

## Deterministic vs model boundary

- Model: turns language/pixels into candidate observations; phrases questions.
- Deterministic: observation identity, grouping, contradiction detection, gazetteer lookup, anchor status, geometry, export.
- The model never resolves a contradiction, picks coordinates, or confirms an anchor.

## Guardrails

- Observations are frozen; answers add a `Resolution`, nothing is deleted or overwritten.
- Contradictions keep every alternative with its source ref; neither modality wins by default.
- A landmark absent from the area gazetteer stays `unresolved`; no location is invented.
- Polygon needs >= 3 explicitly confirmed, ordered anchors; self-intersection, duplicate vertices and area bounds are rejected.
- Export contains confirmed anchors and a polygon only when valid; open contradictions are listed.
- Transcript/model text is treated as data; the system prompt says so (not tested against adversarial input).
- No API key in files; key only from env, only used in `meta` mode.
- Valid geometry does not mean the land exists there (stated in every boundary).

## Evaluation plan (NOT RUN)

Per `docs/planning/04-FEASIBILITY-TEST.md`: four paired cases, one held out. Compare (a) sketch only, (b) sketch + reference transcript,
(c) sketch + real ASR output with identical candidate context and call budgets. Score correct entities/relations, ambiguities resolved,
new wrong matches, contradictions surfaced with both refs, unknowns left unresolved, user corrections needed, latency/usage.
Pass means speech resolves >= 2 preselected ambiguities without a new wrong accepted match.

## Verified vs UNVERIFIED

Verified (by `pytest`, mock providers, one synthetic fictional case): fusion, contradiction preservation, anchor/boundary rules, API flow, trace.
UNVERIFIED / NOT TESTED: every Meta endpoint and response shape, speech accuracy, sketch understanding from pixels,
multi-user or real-land use, any accuracy or user-benefit claim.
