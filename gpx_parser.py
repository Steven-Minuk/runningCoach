import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any


GPX_NS = {"gpx": "http://www.topografix.com/GPX/1/1"}


def parse_gpx(file_path: str) -> dict[str, Any]:
    tree = ET.parse(file_path)
    root = tree.getroot()

    name_elem = root.find(".//gpx:trk/gpx:name", GPX_NS)
    track_time_elem = root.find(".//gpx:trk/gpx:time", GPX_NS)
    point_elems = root.findall(".//gpx:trkseg/gpx:trkpt", GPX_NS)

    activity_name = name_elem.text if name_elem is not None else "Unknown Run"
    track_time = parse_time(track_time_elem.text) if track_time_elem is not None else None

    points: list[dict[str, Any]] = []

    for idx, pt in enumerate(point_elems):
        lat = float(pt.attrib["lat"])
        lon = float(pt.attrib["lon"])

        ele_elem = pt.find("gpx:ele", GPX_NS)
        time_elem = pt.find("gpx:time", GPX_NS)

        elevation = float(ele_elem.text) if ele_elem is not None else None
        point_time = parse_time(time_elem.text) if time_elem is not None else None

        points.append(
            {
                "point_index": idx,
                "latitude": lat,
                "longitude": lon,
                "elevation_m": elevation,
                "point_time": point_time,
            }
        )

    return {
        "activity_name": activity_name,
        "track_time": track_time,
        "points": points,
    }


def parse_time(time_str: str | None) -> datetime | None:
    if not time_str:
        return None

    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))