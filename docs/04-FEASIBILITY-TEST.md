# First feasibility experiment — two incremental hours

## Hardest assumption

Speech provides useful missing evidence without causing silent conflicts or invented locations. Merely obtaining a transcript or a valid polygon is not a pass.

Use four paired examples from the mapping set: an unclear label clarified by speech; a relation only described orally; a deliberate contradiction; an unknown landmark without a geographic anchor. Keep one pair untouched while tuning. Use an independently written reference transcript and manually checked expected observations.

## Protocol

| Elapsed | Test |
|---|---|
| 0–25 min | Obtain one real transcript; inspect place names, negation and ordering; record errors |
| 25–65 min | Run sketch-only and sketch-plus-reference-transcript under fixed prompts/candidate context; score correct entities/relations |
| 65–95 min | Replace reference transcript with actual ASR output, measure degradation, exercise contradiction/unknown cases |
| 95–120 min | Validate one anchored polygon and one impossible/invalid case; record correction effort and decide |

## Proposed pass gate (not achieved)

- Combined input resolves at least two preselected ambiguities that sketch-only leaves unresolved, without introducing a new wrong accepted match. Report all four examples, not only the improvements.
- Every deliberate contradictory observation is surfaced with both source references. Unknown or unanchored landmarks remain unresolved.
- After transcript review, all task-critical names, negations and vertex order in the spike cases are correct; record required user corrections. Do not claim autonomous transcription accuracy from corrected text.
- A valid draft polygon requires explicitly confirmed anchors. Self-intersecting, degenerate and missing-anchor cases are rejected before export. Geometric validity is not land accuracy.
- Log latency, model usage and total correction time for both modes. Synthetic scenes and one-person recordings cannot establish community usability.

If audio is not yet available, the reference-transcript comparison can be run as an isolated fusion test. Mark ASR and full pipeline **NOT TESTED**. If no real reference parcel is available, use a clearly fictional polygon and keep real-boundary validation **NOT TESTED**.

## Prepared tools

`python map-what-people-know/spike/check_core.py` checks conflict preservation, missing evidence and polygon validity on supplied synthetic observations. It does not extract observations from language. The prepared model probe accepts `--image` and `--text` using the local schema and prompt; that tests sketch/transcript fusion when run later. Real audio upload/transcription is a subsequent adapter test, documented above, not implemented by this image/text probe.

No live model call is made in this preparation turn, following the user's instruction. Record actual outcomes in [05-TEST-RESULTS.md](05-TEST-RESULTS.md).
