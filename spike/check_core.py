"""Checks supplied evidence and simple polygons; does not interpret language."""
import json
import math


def reconcile(observations):
    grouped = {}
    for item in observations:
        if not item.get("source") or not item.get("evidence_id"):
            raise ValueError("Source evidence is required")
        grouped.setdefault((item["subject"], item["predicate"]), []).append(item)
    return [{"subject": key[0], "predicate": key[1], "observations": items,
             "status": "needs_confirmation" if len({i["value"] for i in items}) > 1 else "proposed"}
            for key, items in grouped.items()]


def cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def on_segment(a, b, p):
    return abs(cross(a, b, p)) < 1e-9 and all(min(a[i], b[i]) <= p[i] <= max(a[i], b[i]) for i in (0, 1))


def intersect(a, b, c, d):
    if cross(a, b, c) * cross(a, b, d) < 0 and cross(c, d, a) * cross(c, d, b) < 0:
        return True
    return any([on_segment(a, b, c), on_segment(a, b, d), on_segment(c, d, a), on_segment(c, d, b)])


def valid_polygon(vertices, confirmed, closure_confirmed):
    if not closure_confirmed or len(vertices) < 3 or len(confirmed) != len(vertices) or not all(confirmed):
        return False
    if any(len(p) != 2 or not all(math.isfinite(v) for v in p) for p in vertices):
        return False
    if len(set(map(tuple, vertices))) != len(vertices):
        return False
    edges = list(zip(vertices, vertices[1:] + vertices[:1]))
    area2 = sum(a[0] * b[1] - b[0] * a[1] for a, b in edges)
    if abs(area2) < 1e-9:
        return False
    for i, (a, b) in enumerate(edges):
        for j, (c, d) in enumerate(edges):
            if j <= i or j == i + 1 or (i == 0 and j == len(edges) - 1):
                continue
            if intersect(a, b, c, d):
                return False
    return True


def main():
    evidence = [
        {"subject": "path", "predicate": "side_of_school", "value": "east", "source": "sketch", "evidence_id": "region-1"},
        {"subject": "path", "predicate": "side_of_school", "value": "west", "source": "transcript", "evidence_id": "turn-2"},
    ]
    result = reconcile(evidence)
    square = [[0, 0], [4, 0], [4, 3], [0, 3]]
    missing_rejected = False
    try:
        reconcile([{**evidence[0], "evidence_id": None}])
    except ValueError:
        missing_rejected = True
    checks = {
        "contradiction_requires_confirmation": result[0]["status"] == "needs_confirmation",
        "both_source_observations_preserved": result[0]["observations"] == evidence,
        "agreement_is_proposal_not_confirmation": reconcile([evidence[0]])[0]["status"] == "proposed",
        "missing_evidence_rejected": missing_rejected,
        "confirmed_simple_polygon_accepted": valid_polygon(square, [True] * 4, True),
        "unconfirmed_anchor_rejected": not valid_polygon(square, [True, False, True, True], True),
        "closure_not_inferred": not valid_polygon(square, [True] * 4, False),
        "crossing_edges_rejected": not valid_polygon([[0, 0], [5, 4], [0, 3], [4, 0]], [True] * 4, True),
        "collinear_polygon_rejected": not valid_polygon([[0, 0], [1, 0], [2, 0]], [True] * 3, True),
        "nonfinite_vertex_rejected": not valid_polygon([[0, 0], [1, 0], [1, float('nan')]], [True] * 3, True),
    }
    print(json.dumps({"kind": "supplied_evidence_and_synthetic_geometry_only", "checks": checks,
                      "passed": sum(checks.values()), "total": len(checks),
                      "model_tested": False, "speech_tested": False}, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
