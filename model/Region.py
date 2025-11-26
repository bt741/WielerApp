from shapely.geometry import Point

class Region:
    def __init__(self, name, geometry):
        self.name = name
        self.geom = geometry

    def contains(self, lat, lon) -> bool:
        pt = Point(lon, lat)  # shapely uses (x=lon, y=lat)
        return self.geom.covers(pt)