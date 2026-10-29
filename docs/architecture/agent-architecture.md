# Agent architecture

Status: implemented and verified with offline tests and synthetic dev cases.
No live Meta calls; Meta endpoints, tool-call compatibility and pricing **UNVERIFIED**.

## Execution

`apps/api/app/pipeline.py` runs sequential stages so one shared call budget is
predictable: Transcriber -> SpeechReader / SketchReader -> Fuser -> Resolver ->
BoundaryValidator -> human review. Empty modalities skip extraction calls.
The contradiction reviewer supplies deterministic fallback questions; the resolver
may phrase a question through `ask_user`. Answers add immutable resolutions and
resume the resolver with the same run budget. Confirmations revalidate geometry.

## Provider boundary

- `mock`: offline regex extraction and a scripted policy using the same tool loop.
  Sketch labels stand in for vision; mock audio uses a canned transcript.
- `meta`: Muse Voice transcription and `muse-spark-1.3` structured extraction plus
  OpenAI-compatible `tools` / `tool_calls`, isolated in `providers.py`.
- `replay`: canonical request SHA-256 lookup in private `data/recordings/`.
  No network; exact misses raise `ReplayMiss`. Successful Meta responses are recorded.
  Credentials/authorization headers are excluded. Inputs may be sensitive.

## Plan, act, verify, recover

The resolver sees an evidence-review objective and selects deterministic tools:
`list_observations(entity?)`, `lookup_gazetteer(name)`, `list_contradictions()`,
`ask_user(contradiction_id, question)`,
`propose_anchor(entity, gazetteer_id|null, evidence_ids)`,
`validate_boundary(anchor_ids)`, `finish()`.

The scripted policy inspects evidence, asks about disagreements (pausing the run),
otherwise looks up and proposes anchors, validates and finishes. Model-selected
plans use the same dispatcher. Every model turn and tool invocation is traced.
Unknown tools, invalid arguments or unsupported evidence return tool errors for
recovery. The model cannot write resolutions, confirmations or coordinates.
Proposals must match the evidence entity exactly in the supplied gazetteer;
unknown/misheard names stay unresolved. Deterministic fusion supplies anchor
candidates even if the resolver pauses before proposing them.

Maximum eight resolver turns per run, including resumed work; maximum 16 tool
calls per model turn. `MODEL_MAX_CALLS` (default 24) covers extraction, resolver,
retries and repairs. `RESOLVER_MAX_STEPS` may lower the eight-turn limit.
Timeouts and HTTP 429/5xx get at most two retries with exponential backoff and
Retry-After. Delays above 30 seconds fail unresolved rather than wait indefinitely.
Malformed structured responses get one repair attempt, then unresolved status.
Caps yield honest partial status; usable evidence survives provider failures.

## Trust and geometry

Observations are frozen. Conflicting alternatives and source refs remain visible.
Only user answers resolve contradictions; only user confirmation accepts anchors.
Coordinates come from the area gazetteer. Only deterministic `validate_boundary`
can produce a valid draft polygon, using at least three confirmed ordered anchors.
It rejects duplicate vertices, intersections and area violations. Geometric
validity does not establish real-world correctness. Inputs/model text are data,
not instructions; prompt-injection resistance is **NOT TESTED**.

## Telemetry

Trace entries include model, prompt version, latency, returned tokens and estimated
USD. `ModelCall` entries count actual provider attempts (script invocations for
mock); stage/tool entries do not double-count calls. Missing usage is incomplete.
`GET /api/runs/{id}/trace` retains its array shape and appends a `RunTotals` entry.
The run response and web page also expose totals. Prices in `config.py` are
**UNVERIFIED placeholders**. Replay measures local latency, not original latency.

## Evaluation and evidence

`evals/run.py` compares sketch, speech and both; truth is scored after inference
and excluded through an input allowlist. Tests inspect outgoing HTTP payloads.
Reports include entity/relation precision/recall, surfaced contradictions, wrong
accepted/proposed anchors, turns/calls/tokens/latency/cost and incomplete runs.
The four synthetic dev traps cover contradiction, unknown landmark, misheard name
and negation. The checked-in dev report used 61 scripted calls, zero network calls.
These numbers verify plumbing, not model accuracy or user benefit. No anchors
were automatically accepted. Synthetic held-out has **NOT BEEN RUN**.

Verified offline: original evidence/geometry/API flow, recording/replay, bounded
resolver, usage aggregation, fault recovery, budget enforcement and eval isolation.
UNVERIFIED: every live Meta shape, prices, speech/vision quality, adversarial input,
real-land utility, multi-user operation and production durability. Runs remain
in-memory in one process. See `evals/README.md` for protocol and metric definitions.
