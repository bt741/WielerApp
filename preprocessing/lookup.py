from typing import Dict, List
from model.Region import Region

def smart_lookup(
    point,
    provinces_lookup: List[Region],
    provinces_regions_map: Dict[str, List[Region]],
) -> str:
    """
        Perform a smart lookup to find the region a point belongs to by first identifying the province.

        Arguments:
        - point: The point to lookup.
        - provinces_lookup: A list of Region objects representing provinces.
        - provinces_regions_map: A mapping of province names to lists of Region objects within those provinces

        Returns:
        - The name of the region the point belongs to, or an empty string if not found
    """
    for province in provinces_lookup:
        if province.contains(point.latitude, point.longitude):
            for region in provinces_regions_map[province.name]:
                if region.contains(point.latitude, point.longitude):
                    return region.name
    return ""

def neighbour_lookup(
    point,
    previous_region_name: str,
    region_map: Dict[str, Region],
    neighbour_map: Dict[str, List[str]],
    provinces_lookup: List[Region],
    provinces_regions_map: Dict[str, List[Region]],
) -> str:
    """
        Lookup to which region a point belongs, by first checking the neighbour regions of the previous region. If
        not found in the neighbours, a smart lookup is performed to find the region.

        Arguments:
        - point: The point to lookup.
        - previous_region_name: The name of the previous region.
        - region_map: A mapping of region names to Region objects.
        - neighbour_map: A mapping of region names to lists of neighbouring region names.
        - provinces_lookup: A list of Region objects representing provinces.
        - provinces_regions_map: A mapping of province names to lists of Region objects within those provinces

        Returns:
        - str: The name of the region the point belongs to, or an empty string if not found
    """
    current_region = region_map.get(previous_region_name, None)
    if current_region and current_region.contains(point.latitude, point.longitude):
        return previous_region_name

    neighbours = neighbour_map.get(previous_region_name, [])
    for neighbour_name in neighbours:
        neighbour_region = region_map.get(neighbour_name, None)
        if neighbour_region and neighbour_region.contains(point.latitude, point.longitude):
            return neighbour_name

    # fallback to smart lookup
    return smart_lookup(point, provinces_lookup, provinces_regions_map)