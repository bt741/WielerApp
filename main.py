import argparse
import time
import tempfile
import os
import json
import logging

from preprocessing.setup import preprocess_data
from preprocessing.lookup import neighbour_lookup
from preprocessing.gpx_extractor import extract_gpx_data

def process_gpx_path(path):
    logger = logging.getLogger(__name__)
    start = time.time()
    gpx_data = extract_gpx_data(path)

    found_regions = set()
    current_region = ""
    for track in gpx_data.tracks:
        for segment in track.segments:
            for point in segment.points:
                current_region = neighbour_lookup(
                    point,
                    current_region,
                    region_map,
                    neighbour_map,
                    provinces_lookup,
                    provinces_regions_map,
                )
                if current_region:
                    found_regions.add(current_region)

    elapsed = time.time() - start
    logger.info("Processed %s: found %d regions in %.2fs", path, len(found_regions), elapsed)

    return {
        "regions": sorted(found_regions),
    }

def process_gpx_bytes(bts):
    # write to temp file and reuse path-based extractor
    with tempfile.NamedTemporaryFile(delete=False, suffix=".gpx") as tmp:
        tmp.write(bts)
        tmp_path = tmp.name
    try:
        return process_gpx_path(tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a GPX file or run a small JSON backend.")
    parser.add_argument('-f', '--file', required=False, help="path to your GPX file")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # load preprocessing data once
    region_map, neighbour_map, provinces_lookup, provinces_regions_map = preprocess_data(
        "neighbours_map_5.0.json",
        "province_map.json",
        "BELGIUM_-_Provinces.geojson",
        "BELGIUM_-_Municipalities.geojson",
    )

    if args.file:
        res = process_gpx_path(args.file)
        print(json.dumps(res))
    else:
        try:
            from flask import Flask, request, jsonify
        except Exception:
            print("Flask is required for server mode. Install with: pip install Flask")
            raise

        app = Flask(__name__)

        @app.route("/upload", methods=["POST"])
        def upload_path():
            # accept JSON { "path": "..." } or form field 'path'
            data = request.get_json(silent=True) or {}
            path = data.get("path") or request.form.get("path")
            if not path:
                return jsonify({"error": "missing `path` in JSON body or form data"}), 400

            if not os.path.isfile(path):
                return jsonify({"error": "file not found"}), 404

            _, ext = os.path.splitext(path.lower())
            if ext != ".gpx":
                return jsonify({"error": "only .gpx files are supported"}), 400

            result = process_gpx_path(path)
            return jsonify(result)

        # run on localhost:5000
        app.run(host="127.0.0.1", port=5000)