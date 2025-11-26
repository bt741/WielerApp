import geojson
import json
import unicodedata
from shapely.ops import nearest_points
from pyproj import Geod
from typing import Dict, List, Set

from pathlib import Path
from shapely.geometry import shape as geom_shape, GeometryCollection
from model.Region import Region

def compute_neighbours(
    regions,
    max_km: float
) -> dict[str, Set[str]]:
    """
        Compute neighbour regions within `max_km` kilometers.

        Returns:
        - Dict[str, Set[str]]: A mapping of region name -> set of neighbour region names.
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

def save_neighbours(
    neighbor_map: Dict[str, List[str]],
    path: str
) -> None:
    """
        Save the neighbour_map to `path` as a JSON file.

        Arguments:
        - neighbor_map: A mapping of region name -> list of neighbour names.
        - path: Path to save the neighbor_map JSON file to.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8') as f:
        json.dump(neighbor_map, f, ensure_ascii=False, indent=2)

def load_neighbours(path: str) -> Dict[str, List[str]]:
    """
        Load the neighbour_map from `path` as a JSON file.

        Arguments:
        - path: Path to load the neighbor_map JSON file from.
    """
    p = Path(path)
    with p.open('r', encoding='utf-8') as f:
        return json.load(f)

def fix_mojibake(s: str) -> str:
    """
        Fix common mojibake issues in the input string `s`.

        Arguments:
        - s: The input string to fix.

        Returns:
        - The fixed string.
    """
    if "Ã" in s or "Â" in s:
        try:
            return s.encode("latin-1").decode("utf-8")
        except Exception:
            return s
    return s

def preprocess_data(
    neighbours_mapping_path: str,
    provinces_mapping_path: str,
    provinces_geojson_path: str,
    municipalities_geojson_path: str
):
    """
        Preprocess the data and return the region map, neighbour map, provinces lookup and provinces regions map.

        Arguments:
        - neighbours_mapping_path: path to the neighbours mapping JSON file.
        - provinces_mapping_path: path to the provinces mapping JSON file.
        - provinces_geojson_path: path to the provinces GeoJSON file.
        - municipalities_geojson_path: path to the municipalities GeoJSON file.

        Returns:
        - region_map: A mapping of region names to Region objects.
        - neighbour_map: A mapping of region names to lists of neighbouring region names.
        - provinces_lookup: A list of Region objects representing provinces.
        - provinces_regions_map: A mapping of province names to lists of Region objects within those provinces
    """
    neighbour_map = load_neighbours(neighbours_mapping_path)
    province_map = json.load(open(provinces_mapping_path, 'r', encoding='utf-8'))

    province_names = ["WEST-VLAANDEREN", "OOST-VLAANDEREN", "ANTWERPEN", "LIMBURG", "VLAAMS-BRABANT", "BRUSSEL",
                      "BRABANT WALLON", "NAMUR", "LIÈGE", "HAINAUT", "LUXEMBOURG"]
    provinces_regions_map = {}

    for province_name in province_names:
        provinces_regions_map[province_name] = []

    municipalities_geojson_data = geojson.load(open(municipalities_geojson_path))
    region_map = {}
    regions = []

    for feature in municipalities_geojson_data['features']:
        raw = feature['properties'].get('Communes', '')
        raw = fix_mojibake(raw)
        name = unicodedata.normalize('NFC', raw).upper()

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
        "West-Vlaanderen": "WEST-VLAANDEREN",
        "Oost-Vlaanderen": "OOST-VLAANDEREN",
        "Antwerpen": "ANTWERPEN",
        "Limburg": "LIMBURG",
        "Vlaams Brabant": "VLAAMS-BRABANT",
        "Brussel": "BRUSSEL",
        "Waals Brabant": "BRABANT WALLON",
        "Namen": "NAMUR",
        "Luik": "LIÈGE",
        "Henegouwen": "HAINAUT",
        "Luxemburg": "LUXEMBOURG"
    }

    provinces_geojson_data = geojson.load(open(provinces_geojson_path))
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

    return region_map, neighbour_map, provinces_lookup, provinces_regions_map