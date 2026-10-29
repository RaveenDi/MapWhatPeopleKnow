"""Deterministic evidence fusion. Alternatives are kept; disagreement is surfaced, never merged."""
import hashlib
import re
from collections import OrderedDict

from .contracts import Anchor, Contradiction, Observation, Resolution


def norm(text: str) -> str:
    t = re.sub(r"^(the|a|an)\s+", "", text.strip().lower())
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def fuse(observations: list[Observation]):
    """Group by (entity, predicate). Returns (groups, contradictions)."""
    groups: "OrderedDict[tuple[str, str], list[Observation]]" = OrderedDict()
    for o in observations:
        if not o.source_ref or not o.id:
            raise ValueError("Source evidence is required")
        groups.setdefault((o.entity, o.predicate), []).append(o)
    contradictions = []
    for (entity, pred), items in groups.items():
        if len({o.value for o in items}) > 1:
            cid = "c-" + hashlib.sha1(f"{entity}|{pred}".encode()).hexdigest()[:8]
            contradictions.append(Contradiction(id=cid, entity=entity, predicate=pred,
                                                observations=tuple(items)))
    return groups, contradictions


def build_anchors(observations: list[Observation], gazetteer: dict, contradictions: list[Contradiction],
                  resolutions: dict[str, Resolution], confirmed: set[str]) -> list[Anchor]:
    """boundary_corner observations become anchors. No gazetteer match -> unresolved, never guessed."""
    by_id = {o.id: o for o in observations}
    contested = {(c.entity, c.predicate): c for c in contradictions}
    corners: "OrderedDict[str, list[Observation]]" = OrderedDict()
    for o in observations:
        if o.predicate == "boundary_corner":
            corners.setdefault(o.entity, []).append(o)
    anchors = []
    for entity, items in corners.items():
        label = items[0].wording or entity
        c = contested.get((entity, "boundary_corner"))
        chosen = items[0]
        reason = ""
        if c is not None:
            r = resolutions.get(c.id)
            if r is None or r.chosen_observation_id is None or r.chosen_observation_id not in by_id:
                anchors.append(Anchor(id="a-" + entity, entity=entity, label=label, status="unresolved",
                                      evidence=tuple(o.id for o in items),
                                      reason="Order contradicted between sources; awaiting user answer"))
                continue
            chosen = by_id[r.chosen_observation_id]
        if not chosen.value.isdigit() or int(chosen.value) < 1:
            anchors.append(Anchor(id='a-' + entity, entity=entity, label=label, evidence=tuple(o.id for o in items), reason='Invalid boundary order'))
            continue
        place = gazetteer.get(entity)
        ev = tuple(o.id for o in items)
        if place is None:
            anchors.append(Anchor(id="a-" + entity, entity=entity, label=label, status="unresolved",
                                  evidence=ev, reason="No candidate in area gazetteer; location not invented"))
            continue
        aid = "a-" + entity
        anchors.append(Anchor(id=aid, entity=entity, label=place.get("name", label), order=int(chosen.value),
                              lon=place["lon"], lat=place["lat"],
                              status="confirmed" if aid in confirmed else "proposed",
                              evidence=ev, reason=reason))
    return sorted(anchors, key=lambda a: (a.order is None, a.order or 0))
