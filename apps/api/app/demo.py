"""Built-in FICTIONAL demo case: Lantern Cove. Coordinates are invented, not a real place."""
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parents[3] / "data" / "demo"

AREA = {
    "name": "Lantern Cove (fictional)",
    "gazetteer": {
        "old_well": {"name": "Old Well", "lon": 20.0000, "lat": 5.0000},
        "mill_bridge": {"name": "Mill Bridge", "lon": 20.0020, "lat": 5.0000},
        "stone_gate": {"name": "Stone Gate", "lon": 20.0020, "lat": 5.0015},
        "banyan_tree": {"name": "Banyan Tree", "lon": 20.0000, "lat": 5.0015},
        "school": {"name": "School", "lon": 20.0010, "lat": 5.0007},
    },
}

TRANSCRIPT = (
    "My family field is bounded by the Old Well, then Mill Bridge, then Stone Gate, then the Banyan Tree, "
    "and then the red shrine. The footpath runs west of the school."
)

# Stand-in for a vision model: what a sketch reader would report (label, pixel position, stated relation).
SKETCH_LABELS = [
    {"label": "Old Well", "x": 80, "y": 380},
    {"label": "Mill Bridge", "x": 420, "y": 380},
    {"label": "Stone Gate", "x": 420, "y": 120},
    {"label": "Banyan Tree", "x": 80, "y": 120},
    {"label": "School", "x": 250, "y": 250},
    {"label": "Red Shrine", "x": 250, "y": 60},
    {"label": "Footpath", "x": 360, "y": 250, "relations": {"side_of_school": "east"}},
]
