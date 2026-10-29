# Combined: Map What People Know

Status: **user-selected finalist; architecture proposed; real-model spike pending**. Updated 2026-10-29. This is a planning folder with small feasibility probes, not a separate Git repository or completed app.

**Promise:** combine a person's sketch and spoken explanation into map features and, where sufficient anchors exist, a draft boundary they can inspect and correct. This is the selected combined concept; a voice clarification feature alone is a smaller fallback, not proof of the full concept.

| Read | Purpose |
|---|---|
| [01-WORKFLOW.md](01-WORKFLOW.md) | Sketch, explanation, contradiction review and draft geometry |
| [02-ARCHITECTURE.md](02-ARCHITECTURE.md) | Evidence-preserving fusion and boundary validation |
| [03-PROJECT-STRUCTURE.md](03-PROJECT-STRUCTURE.md) | Modular implementation design and sharing with Drawn to Scale |
| [04-FEASIBILITY-TEST.md](04-FEASIBILITY-TEST.md) | Test whether speech improves the sketch result |
| [05-TEST-RESULTS.md](05-TEST-RESULTS.md) | Actual local checks and still-missing evidence |

Run local checks: `python map-what-people-know/spike/check_core.py`. They test contradiction and polygon rules on supplied observations, not speech recognition or model reasoning.

The common budget is **45 hours for selection plus one delivered project**, not 45 hours per folder. The full sketch-and-boundary vision was estimated at 60–65 hours in [the prior review](../../anthropic/research/round4-redteam-spoken-boundaries.md); that is a planning estimate, not a measured requirement. A 45-hour version must support one small known area, a limited relation vocabulary and explicit confirmations.

The [Drawn to Scale core](../../drawn-to-scale/docs/README.md) is the first dependency. Spend at most two additional hours checking multimodal value after that core spike. Without a working mapping core, a successful transcript parser cannot justify building the full app.

No validated adoption, survey accuracy or winning probability is claimed. Sources: [Spoken Boundaries concept and corrections](../../anthropic/ideas/idea-18-spoken-boundaries.md), [prior review](../../anthropic/research/round4-redteam-spoken-boundaries.md), [scorecard](../../12-IDEA-SCORECARD.md).
