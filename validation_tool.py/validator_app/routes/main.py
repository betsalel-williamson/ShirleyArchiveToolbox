# validator_app/routes/main.py
import json
from flask import Blueprint, render_template, abort
from validator_app.utils import get_json_files, get_file_status, load_data

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Homepage: shows a list of files and their status."""
    files = get_json_files()
    file_statuses = [{"filename": f, "status": get_file_status(f)} for f in files]
    return render_template("index.html", files=file_statuses)


@main_bp.route("/validate/<string:json_filename>")
def validate(json_filename):
    data = load_data(json_filename)
    if not data:
        abort(404, "JSON file not found.")

    annotations = []
    word_counter = 0
    for line_idx, line in enumerate(data.get("lines", [])):
        for word_idx, word in enumerate(line.get("words", [])):
            word_info = word.copy()
            word_id = f"{line_idx}_{word_idx}"
            word_info["id"] = word_id
            word_info["display_id"] = word_counter + 1
            word["id"] = word_id
            annotations.append(word_info)
            word_counter += 1

    return render_template(
        "validate.html",
        json_filename=json_filename,
        image_filename=data["image_source"],
        image_dimensions=data.get("image_dimensions", {}),
        annotations=annotations,
        json_data_string=json.dumps(data),
    )
