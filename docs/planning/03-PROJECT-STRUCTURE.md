# Proposed implementation structure

If selected, use the same single product repo layout as Drawn to Scale, with these feature modules. No separate repos, microservices or deployed apps have been created.

```text
map-what-people-know/
  apps/web/src/features/
    sketch/
    recording/                 # short capture/upload and transcript correction
    map-review/
    conflict-review/           # evidence side by side
    boundary-review/           # vertex order and draft confirmation
    export/
  apps/api/app/
    domain/
      sketch_graph.py
      observations.py          # source-bearing immutable facts
      fusion.py                # proposals, alternatives, contradictions
      matching.py
      alignment.py
      boundaries.py            # geometric validity, explicit confirmation
    providers/
      meta_vision.py
      meta_speech.py
      geodata.py
    workflows/
      map_run.py
    prompts/
      sketch_extract.v1.md
      speech_extract.v1.md
      fusion.v1.md
      schemas/
    api/
    storage/
  evals/
    manifest.jsonl
    fixtures/sketches/
    fixtures/audio/
    ground_truth/              # corrected transcripts and reference anchors
    compare_modalities.py
    reports/
  docs/
  submission/
```

Use the base environment files, locks, deployment and API-contract generation. Retain model IDs, prompt/schema versions, fixture IDs and source hashes for every result. A known transcript can test semantic fusion, but it must be labeled separately from actual audio-transcription performance.

Build order: mapping extraction gate → paired sketch/transcript comparison → real speech smoke test → contradiction handling → geographic candidate review → optional bounded polygon → minimal interface → evaluation/video. If speech does not improve the paired cases, stop the combined extension and keep Drawn to Scale as a candidate.

Budget: use the shared 45-hour allocation in the base structure. The two-hour combined experiment is incremental after the three-hour mapping experiment. If run alone without the mapping work, allow up to three hours for a shallow extraction/fusion probe and do not call that an end-to-end mapping pass.
