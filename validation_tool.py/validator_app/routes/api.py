# validator_app/routes/api.py
import os
import json
from flask import Blueprint, request, redirect, url_for, jsonify, abort, current_app
from validator_app.utils import (
    apply_transformations_to_data,
    get_json_files,
    get_file_status,
)

api_bp = Blueprint("api", __name__)


@api_bp.route("/autosave/<string:json_filename>", methods=["POST"])
def autosave(json_filename):
    """Auto-saves the current state to the in_progress directory."""
    transformed_data = apply_transformations_to_data(request.form)
    save_path = os.path.join(current_app.config["IN_PROGRESS_DATA_DIR"], json_filename)
    with open(save_path, "w") as f:
        json.dump(transformed_data, f, indent=2)
    return jsonify({"status": "ok", "message": "Draft saved."})


@api_bp.route("/commit/<string:json_filename>", methods=["POST"])
def commit(json_filename):
    """Commits the final changes to the validated directory."""
    config = current_app.config
    transformed_data = apply_transformations_to_data(request.form)
    transformed_data["validated"] = True

    validated_path = os.path.join(config["VALIDATED_DATA_DIR"], json_filename)
    with open(validated_path, "w") as f:
        json.dump(transformed_data, f, indent=2)

    in_progress_path = os.path.join(config["IN_PROGRESS_DATA_DIR"], json_filename)
    if os.path.exists(in_progress_path):
        os.remove(in_progress_path)

    all_files = get_json_files()
    current_index = all_files.index(json_filename) if json_filename in all_files else -1
    for i in range(current_index + 1, len(all_files)):
        if get_file_status(all_files[i]) != "validated":
            # Use blueprint name in url_for: 'main.validate'
            return redirect(url_for("main.validate", json_filename=all_files[i]))

    return redirect(url_for("main.index"))


@api_bp.route("/get_source_data/<string:json_filename>")
def get_source_data(json_filename):
    """Endpoint to fetch the raw, unmodified JSON data."""
    source_path = os.path.join(current_app.config["SOURCE_DATA_DIR"], json_filename)
    if not os.path.exists(source_path):
        abort(404, f"Source file '{json_filename}' not found.")
    with open(source_path, "r") as f:
        data = json.load(f)
    return jsonify(data)
