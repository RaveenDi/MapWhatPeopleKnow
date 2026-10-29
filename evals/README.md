# Evaluation

Write ground truth before inference. Tune on `dev` only; freeze prompts, code,
recordings and scoring before reporting held-out once. Do not inspect or tune to
held-out errors afterward. The supplied manifest is synthetic, hand-authored and
public; it is a plumbing demo, not a credible blind performance benchmark.
The synthetic held-out row has **NOT BEEN RUN** for this implementation.

```powershell
.venv\Scripts\python.exe evals/run.py --provider mock --manifest evals/manifest.jsonl --split dev --max-calls 100
```

Omit `--mode` for the key paired sketch/speech/both comparison. Set
`--mode sketch|speech|both` for one arm. Use `--provider replay` with existing
recordings for offline replay; a missing exact request fails loudly. `meta`
requires explicit authorization and a key in the environment; endpoint/tool
shapes are **UNVERIFIED**. No live calls were made for this implementation.
`--max-calls` is a global cap over all cases/modes including retries and repairs;
exhausted runs remain partial and are counted, never silently discarded. Choose
a cap large enough to cover all arms; a low global cap biases later arms.

Each JSONL row has `id`, `split` (`dev` or `heldout`), `area` (`name`, `gazetteer`),
`sketch` (image path, or `{image?, labels:[{label, x?, y?, relations?}]}`),
`audio_or_transcript` (literal transcript string, `{transcript:...}`, or
`{audio:relative_path}`), and `ground_truth`. Media paths are relative to the
manifest and must remain inside this repo. Ground truth has:

- `entities`: normalized entity strings.
- `relations`: `{entity,predicate,value}` triples; boundary order counts as a relation.
- `contradictions`: `{entity,predicate}` pairs with incompatible evidence.
- `anchors`: `{entity,gazetteer_id}` expected matches.

Only allowlisted input fields enter the pipeline; truth is scored afterward.
An HTTP-capture test checks outgoing requests for a ground-truth sentinel.
Matching is exact; precision/recall uses sets and micro aggregation. An empty
prediction has precision 0 if truth is nonempty, otherwise 1; empty truth has
recall 1. Contradiction metrics compare surfaced pairs against expected pairs.
Accepted anchors mean human-confirmed anchors; this harness does not simulate
user confirmation. Always read wrong accepted alongside accepted count (zero
accepted is no accuracy claim). Wrong proposed anchors are also reported.

Reports: `evals/reports/<UTC stamp>-<split>.json` and `.md`. They include per-case
statuses, entity/relation precision and recall, contradictions surfaced, wrong
accepted/proposed anchors, resolver turns, model calls, reported tokens, provider
latency, wall latency, and estimated USD. Missing usage is marked incomplete;
prices in `apps/api/app/config.py` are **UNVERIFIED placeholders**. Replay latency
measures local replay, not original network latency. Mock calls are scripted
policy invocations, not network calls; token usage is unavailable.

Trap cases include contradiction, unknown landmark, misheard name and negation.
The regex mock deliberately has no general negation or name-repair ability;
these failures must remain visible. Mock sketch inputs are labels, not vision.
Do not interpret these synthetic numbers as model accuracy or user benefit.
