# validator_app/utils.py
import os
import json
import math
from flask import current_app


def get_json_files():
    """Get a sorted list of all unique JSON files from all data directories."""
    config = current_app.config
    files = set(os.listdir(config["SOURCE_DATA_DIR"]))
    files.update(os.listdir(config["IN_PROGRESS_DATA_DIR"]))
    files.update(os.listdir(config["VALIDATED_DATA_DIR"]))
    return sorted([f for f in files if f.endswith(".json")])


def get_file_status(json_filename):
    """Check the status of a file: 'validated', 'in_progress', or 'source'."""
    config = current_app.config
    if os.path.exists(os.path.join(config["VALIDATED_DATA_DIR"], json_filename)):
        return "validated"
    if os.path.exists(os.path.join(config["IN_PROGRESS_DATA_DIR"], json_filename)):
        return "in_progress"
    return "source"


def load_data(json_filename):
    """Load data with 3-tier priority: In Progress > Validated > Source."""
    config = current_app.config
    in_progress_path = os.path.join(config["IN_PROGRESS_DATA_DIR"], json_filename)
    validated_path = os.path.join(config["VALIDATED_DATA_DIR"], json_filename)
    source_path = os.path.join(config["SOURCE_DATA_DIR"], json_filename)

    load_path = None
    if os.path.exists(in_progress_path):
        load_path = in_progress_path
    elif os.path.exists(validated_path):
        load_path = validated_path
    elif os.path.exists(source_path):
        load_path = source_path

    if not load_path:
        return None

    with open(load_path, "r") as f:
        return json.load(f)


def apply_transformations_to_data(form_data):
    """Helper to apply form changes to a data object."""
    data = json.loads(form_data["json_data"])
    offsetX = float(form_data.get("offsetX", 0))
    offsetY = float(form_data.get("offsetY", 0))
    rotation_deg = float(form_data.get("rotation", 0))
    scale = float(form_data.get("scale", 1.0))
    is_transformed = offsetX != 0 or offsetY != 0 or rotation_deg != 0 or scale != 1.0

    if is_transformed:
        img_dims = data.get("image_dimensions", {})
        cx = img_dims.get("width", 0) / 2
        cy = img_dims.get("height", 0) / 2
        rotation_rad = math.radians(rotation_deg)
        cos_rad = math.cos(rotation_rad)
        sin_rad = math.sin(rotation_rad)

    all_words = {
        word["id"]: word
        for line in data.get("lines", [])
        for word in line.get("words", [])
    }

    for key, value in form_data.items():
        if key.startswith("text_"):
            word_id = key.replace("text_", "")
            if word_id in all_words:
                all_words[word_id]["text"] = value

    if is_transformed:
        for word in all_words.values():
            if "bounding_box" not in word:
                continue
            bbox = word["bounding_box"]
            corners = [
                (bbox["x_min"], bbox["y_min"]),
                (bbox["x_max"], bbox["y_min"]),
                (bbox["x_max"], bbox["y_max"]),
                (bbox["x_min"], bbox["y_max"]),
            ]
            transformed_corners = []
            for x, y in corners:
                x_scaled = cx + (x - cx) * scale
                y_scaled = cy + (y - cy) * scale
                x_rot = cx + (x_scaled - cx) * cos_rad - (y_scaled - cy) * sin_rad
                y_rot = cy + (x_scaled - cx) * sin_rad + (y_scaled - cy) * cos_rad
                transformed_corners.append((x_rot + offsetX, y_rot + offsetY))

            word["bounding_box"] = {
                "x_min": int(round(min(p[0] for p in transformed_corners))),
                "y_min": int(round(min(p[1] for p in transformed_corners))),
                "x_max": int(round(max(p[0] for p in transformed_corners))),
                "y_max": int(round(max(p[1] for p in transformed_corners))),
            }
    return data
