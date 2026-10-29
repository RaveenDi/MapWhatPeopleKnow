# Core workflow

1. **Choose a known area and task.** User selects a local reference map and whether they are describing places/routes or a draft bounded area. State the output type clearly.
2. **Upload sketch and short recording.** Record or upload up to about 60 seconds for the first version. Keep the sketch usable without speech. Start with one tested language; verify supported languages and quality before promising multilingual use.
3. **Review transcript.** Show the recognized words and allow correction of place names before geographic matching. Preserve original transcript and edits.
4. **Inspect observations.** Extract observations separately from the sketch and speech. Each landmark/relation points back to its image region or transcript turn.
5. **Resolve contradictions.** If speech says a path lies east of the school and an explicitly oriented sketch puts it west, show both observations and ask. Do not choose the more confident-looking modality silently. Page orientation alone is insufficient evidence of compass direction.
6. **Confirm geographic anchors.** Retrieve candidates inside the selected area. Ask for a pin when local descriptions such as 'the old tree' lack reliable geographic evidence. No anchor means no exact coordinate.
7. **Construct supported geometry.** For routes, preserve ordered confirmed anchors. For a draft polygon, require at least three distinct, non-collinear confirmed vertices, explicit sequence/closure confirmation and no self-intersection. An automatically closed polygon is not proof of a real boundary.
8. **Export with provenance.** Include drawing, corrected transcript, source observations, confirmations, geometry and unresolved gaps. Map review makes the boundary's draft status visible.

## Product value to prove

The test is whether speech helps users finish an accurate map with fewer corrections than sketch alone. 'Supports two input types' is not an outcome. Potential benefit: preserve geographic knowledge that a person finds easier to explain than draw. Wider community usefulness remains untested.

## Demonstration

Use a known, non-sensitive owned example or clearly labeled fictional exercise. Show sketch-only ambiguity, then an explanation that resolves it. Introduce a contradictory phrase and show the app ask for clarification. Export one checked draft geometry only if adequate anchors exist. Show before/after evaluation against the same sketch-only baseline.

## Scope

One task, known area, 4–8 anchors and a limited grammar: labels, near, between, follows, explicit compass relations and ordered boundary vertices. Voice-to-accurate-land-parcel for arbitrary terrain, ownership adjudication, public boundary publication, satellite detection of named individual trees and real-time pen-to-word alignment are outside the deliverable. The recorded speech API exposes turn timestamps; fine-grained stroke/word alignment would require additional work. [Meta speech documentation](https://dev.meta.ai/docs/speech-to-text).
