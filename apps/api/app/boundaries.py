"""Deterministic boundary validation in local projected metres (ports spike/check_core.py)."""
import math

from pyproj import Transformer
from shapely.geometry import LinearRing, Polygon

from .contracts import Anchor, DraftBoundary

MIN_ANCHORS = 3
MIN_AREA_M2 = 50.0
MAX_AREA_M2 = 25_000_000.0  # 25 km2 sanity bound for a person-scale boundary


def project(lonlat: list[tuple[float, float]]) -> list[tuple[float, float]]:
    lon0 = sum(p[0] for p in lonlat) / len(lonlat)
    lat0 = sum(p[1] for p in lonlat) / len(lonlat)
    t = Transformer.from_crs("EPSG:4326", f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +units=m", always_xy=True)
    return [t.transform(x, y) for x, y in lonlat]


def validate_xy(xy: list[tuple[float, float]]) -> list[str]:
    """Pure-geometry checks on local metres. Returns error strings (empty = valid)."""
    errors = []
    if any(not math.isfinite(v) for p in xy for v in p):
        return ["non-finite coordinate"]
    if len(set((round(x, 6), round(y, 6)) for x, y in xy)) != len(xy):
        errors.append("duplicate vertices")
        return errors
    if len(xy) < MIN_ANCHORS:
        return [f"needs at least {MIN_ANCHORS} vertices"]
    if not LinearRing(xy).is_simple:
        errors.append("self-intersecting boundary")
    poly = Polygon(xy)
    area = poly.area
    if area < MIN_AREA_M2:
        errors.append(f"area {area:.1f} m2 below minimum {MIN_AREA_M2:.0f}")
    if area > MAX_AREA_M2:
        errors.append(f"area {area:.0f} m2 above maximum {MAX_AREA_M2:.0f}")
    if not errors and not poly.is_valid:
        errors.append("invalid polygon")
    return errors


def validate_boundary(anchors: list[Anchor]) -> DraftBoundary:
    """Only explicitly confirmed, ordered, located anchors are used."""
    usable = [a for a in anchors if a.status == "confirmed" and a.order is not None and a.lon is not None]
    usable.sort(key=lambda a: a.order)
    if len(usable) < MIN_ANCHORS:
        return DraftBoundary(status="insufficient_evidence",
                             errors=(f"{len(usable)} confirmed anchors; need {MIN_ANCHORS}",))
    lonlat = [(a.lon, a.lat) for a in usable]
    xy = project(lonlat)
    errors = validate_xy(xy)
    ids = tuple(a.id for a in usable)
    if errors:
        return DraftBoundary(status="invalid", vertex_ids=ids, errors=tuple(errors),
                             local_xy_m=tuple(xy), lonlat=tuple(lonlat))
    return DraftBoundary(status="valid_draft", vertex_ids=ids, area_m2=round(Polygon(xy).area, 1),
                         local_xy_m=tuple(xy), lonlat=tuple(lonlat))
