import gpxpy
from pathlib import Path

def extract_gpx_data(gpx_path: str):
    """
        Extract GPX data from the given file path, handling various encodings.

        Arguments:
        - gpx_path: Path to the GPX file.
    """
    gpx_file_path = Path(gpx_path)
    if not gpx_file_path.exists():
        raise SystemExit(f"GPX file not found: {gpx_path}")

    data = gpx_file_path.read_bytes()
    gpx_text = ""

    for enc in ('utf-8', 'utf-8-sig', 'cp1252', 'latin-1'):
        try:
            gpx_text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        gpx_text = data.decode('utf-8', errors='replace')

    return gpxpy.parse(gpx_text)