"""Draw the synthetic sketch PNG and write transcript + sketch labels for the fictional demo case."""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))
from app.demo import DEMO_DIR, SKETCH_LABELS, TRANSCRIPT  # noqa: E402


def make(out: Path = DEMO_DIR) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (500, 460), "white")
    d = ImageDraw.Draw(img)
    pts = {l["label"]: (l["x"], l["y"]) for l in SKETCH_LABELS}
    d.polygon([pts["Old Well"], pts["Mill Bridge"], pts["Stone Gate"], pts["Banyan Tree"]], outline="black", width=3)
    for l in SKETCH_LABELS:
        x, y = l["x"], l["y"]
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill="darkred" if "Shrine" in l["label"] else "navy")
        d.text((x + 8, y - 6), l["label"], fill="black")
    d.line([(360, 300), (360, 200)], fill="green", width=3)
    img.save(out / "sketch.png")
    (out / "transcript.txt").write_text(TRANSCRIPT, encoding="utf-8")
    (out / "sketch_labels.json").write_text(json.dumps(SKETCH_LABELS, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    print("wrote", make())
