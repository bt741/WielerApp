import geojson
import gpxpy
import json
import time
import unicodedata
from pathlib import Path
from shapely.ops import nearest_points
from shapely.geometry import shape as geom_shape, GeometryCollection
from pyproj import Geod
from typing import Dict, List

from Fetch import fetch_provinces
from Region import Region

def compute_neighbors(regions, max_km: float):
    """
        regions: iterable of Region objects exposing `.name` and `.geom` (Shapely geometry).
        Returns: dict { region_name: [neighbour_name, ...] }
        Neighbours are regions that touch/intersect (excluding pure containment) or whose
        borders lie within `max_km` kilometers of each other.
    """
    geod = Geod(ellps="WGS84")
    max_m = max_km * 1000.0

    neighbors = {r.name: set() for r in regions}

    for i, r1 in enumerate(regions):
        print(f"{r1.name} ({i + 1}/{len(regions)})")

        g1 = r1.geom
        for r2 in regions[i + 1:]:
            g2 = r2.geom
            try:
                # immediate adjacency / intersection test (excluding containment)
                if g1.touches(g2) or (g1.intersects(g2) and not (g1.within(g2) or g2.within(g1))):
                    neighbors[r1.name].add(r2.name)
                    neighbors[r2.name].add(r1.name)
                    continue

                # skip empty geometries
                if g1.is_empty or g2.is_empty:
                    continue

                # find nearest boundary points and compute geodesic distance (meters)
                p1, p2 = nearest_points(g1, g2)  # returns (Point on g1, Point on g2)
                lon1, lat1 = p1.x, p1.y
                lon2, lat2 = p2.x, p2.y

                _, _, dist_m = geod.inv(lon1, lat1, lon2, lat2)
                if dist_m <= max_m:
                    neighbors[r1.name].add(r2.name)
                    neighbors[r2.name].add(r1.name)

            except Exception:
                # skip invalid geometry comparisons
                continue

    return {name: sorted(list(nb)) for name, nb in neighbors.items()}

def save_neighbors(neighbor_map: Dict[str, List[str]], path: str | Path) -> None:
    """
    Save neighbor_map to `path` as UTF-8 JSON.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8') as f:
        json.dump(neighbor_map, f, ensure_ascii=False, indent=2)

def load_neighbors(path: str | Path = Path('neighbors_map.json')) -> Dict[str, List[str]]:
    """
    Load neighbor_map from `path`. Returns a dict of region name -> list of neighbour names.
    """
    p = Path(path)
    with p.open('r', encoding='utf-8') as f:
        return json.load(f)

def fix_mojibake(s: str) -> str:
    # If the string looks like mojibake (contains sequences like 'Ã' + accent),
    # try re-decoding as latin-1 -> utf-8. Otherwise return original.
    if "Ã" in s or "Â" in s:
        try:
            return s.encode("latin-1").decode("utf-8")
        except Exception:
            return s
    return s

def smart_lookup(
    point,
    provinces_lookup: List[Region],
    provinces_regions_map: Dict[str, List[Region]],
) -> str:
    for province in provinces_lookup:
        if province.contains(point.latitude, point.longitude):
            for region in provinces_regions_map[province.name]:
                if region.contains(point.latitude, point.longitude):
                    return region.name
    return ""

def neighbour_lookup(
    point,
    current_region_name: str,
    region_map: Dict[str, Region],
    neighbour_map: Dict[str, List[str]],
    provinces_lookup: List[Region],
    provinces_regions_map: Dict[str, List[Region]],
) -> str:
    current_region = region_map.get(current_region_name, None)
    if current_region and current_region.contains(point.latitude, point.longitude):
        return current_region_name

    neighbours = neighbour_map.get(current_region_name, [])
    for neighbour_name in neighbours:
        neighbour_region = region_map.get(neighbour_name, None)
        if neighbour_region and neighbour_region.contains(point.latitude, point.longitude):
            return neighbour_name

    # fallback to smart lookup
    return smart_lookup(point, provinces_lookup, provinces_regions_map)

if __name__ == '__main__':
    neighbour_map = load_neighbors("neighbours_map_5.0.json")
    province_map = json.load(open('province_map.json', 'r', encoding='utf-8'))

    province_names = ["WEST-VLAANDEREN", "OOST-VLAANDEREN", "ANTWERPEN", "LIMBURG", "VLAAMS-BRABANT", "BRUSSEL", "BRABANT WALLON", "NAMUR", "LIÈGE", "HAINAUT", "LUXEMBOURG"]
    provinces_regions_map = {}

    for province_name in province_names:
        provinces_regions_map[province_name] = []

    municipalities_geojson_data = geojson.load(open('BELGIUM_-_Municipalities.geojson'))
    region_map = {}
    regions = []

    for feature in municipalities_geojson_data['features']:
        raw = feature['properties'].get('Communes', '')
        raw = fix_mojibake(raw)
        name = unicodedata.normalize('NFC', raw).upper()

        if name == "Ã‰CAUSSINNES":
            name = "ÉCAUSSINNES"

        geometry = feature.get("geometry", {})
        geom_type = geometry.get("type", "").lower()
        coords = geometry.get("coordinates", [])

        if not geom_type or not coords:
            shapely_geom = GeometryCollection()
        else:
            if geom_type == "polygon":
                coords = [coords]
                geom_type = "multipolygon"
            geom_mapping = {"type": geom_type.title(), "coordinates": coords}
            shapely_geom = geom_shape(geom_mapping)

        region = Region(name, shapely_geom)
        regions.append(region)
        region_map[name] = region

        province_name = province_map[name]
        provinces_regions_map[province_name].append(region)

    provinces_lookup = []
    provinces_name_mapping = {
        "West-Vlaanderen" : "WEST-VLAANDEREN",
        "Oost-Vlaanderen" : "OOST-VLAANDEREN",
        "Antwerpen" : "ANTWERPEN",
        "Limburg" : "LIMBURG",
        "Vlaams Brabant" : "VLAAMS-BRABANT",
        "Brussel" : "BRUSSEL",
        "Waals Brabant" : "BRABANT WALLON",
        "Namen" : "NAMUR",
        "Luik" : "LIÈGE",
        "Henegouwen" : "HAINAUT",
        "Luxemburg" : "LUXEMBOURG"
    }

    provinces_geojson_data = geojson.load(open('BELGIUM_-_Provinces.geojson'))
    for feature in provinces_geojson_data['features']:
        name = provinces_name_mapping[feature['properties']['NE_Name']]
        geometry = feature.get("geometry", {})
        geom_type = geometry.get("type", "").lower()
        coords = geometry.get("coordinates", [])

        if not geom_type or not coords:
            shapely_geom = GeometryCollection()
        else:
            if geom_type == "polygon":
                coords = [coords]
                geom_type = "multipolygon"
            geom_mapping = {"type": geom_type.title(), "coordinates": coords}
            shapely_geom = geom_shape(geom_mapping)

        region = Region(name, shapely_geom)
        provinces_lookup.append(region)

    gpx_path = Path('routeyou-testroute.gpx')
    data = gpx_path.read_bytes()
    gpx_text = ""

    for enc in ('utf-8', 'utf-8-sig', 'cp1252', 'latin-1'):
        try:
            gpx_text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        gpx_text = data.decode('utf-8', errors='replace')

    gpx_data = gpxpy.parse(gpx_text)

    found_regions = set()
    current_region = None

    points_checked = 0
    region_checks = 0
    elapsed_brute = 0

    start = time.perf_counter()

    current_region = ""
    for track in gpx_data.tracks:
        for segment in track.segments:
            for point in segment.points:
                current_region = neighbour_lookup(point, current_region, region_map, neighbour_map, provinces_lookup, provinces_regions_map)
                if current_region != "":
                    found_regions.add(current_region)

    elapsed = time.perf_counter() - start
    print(f"{found_regions = } {elapsed = }s")