import os
import json
import math
from flask import Flask, render_template, request, redirect, url_for, abort, jsonify
from PIL import Image

# --- Configuration ---
app = Flask(__name__)
SOURCE_DATA_DIR = 'data_source'
IN_PROGRESS_DATA_DIR = 'data_in_progress'
VALIDATED_DATA_DIR = 'data_validated'
IMAGE_DIR = os.path.join('static', 'images')

# Ensure all directories exist on startup
os.makedirs(SOURCE_DATA_DIR, exist_ok=True)
os.makedirs(IN_PROGRESS_DATA_DIR, exist_ok=True)
os.makedirs(VALIDATED_DATA_DIR, exist_ok=True)


# --- Helper Functions ---

def get_json_files():
    """Get a sorted list of all unique JSON files from all data directories."""
    files = set(os.listdir(SOURCE_DATA_DIR))
    files.update(os.listdir(IN_PROGRESS_DATA_DIR))
    files.update(os.listdir(VALIDATED_DATA_DIR))
    return sorted([f for f in files if f.endswith('.json')])

def get_file_status(json_filename):
    """Check the status of a file: 'validated', 'in_progress', or 'source'."""
    if os.path.exists(os.path.join(VALIDATED_DATA_DIR, json_filename)):
        return 'validated'
    if os.path.exists(os.path.join(IN_PROGRESS_DATA_DIR, json_filename)):
        return 'in_progress'
    return 'source'

def load_data(json_filename):
    """
    Load data with 3-tier priority: In Progress > Validated > Source.
    """
    in_progress_path = os.path.join(IN_PROGRESS_DATA_DIR, json_filename)
    validated_path = os.path.join(VALIDATED_DATA_DIR, json_filename)
    source_path = os.path.join(SOURCE_DATA_DIR, json_filename)

    load_path = None
    if os.path.exists(in_progress_path):
        load_path = in_progress_path
    elif os.path.exists(validated_path):
        load_path = validated_path
    elif os.path.exists(source_path):
        load_path = source_path

    if not load_path:
        return None

    with open(load_path, 'r') as f:
        return json.load(f)

def apply_transformations_to_data(form_data):
    """
    Helper to apply form changes to a data object. Reusable for autosave and commit.
    """
    # Create a deep copy to avoid modifying the original data object in memory
    data = json.loads(form_data['json_data'])

    # Get transformation parameters
    offsetX = float(form_data.get('offsetX', 0))
    offsetY = float(form_data.get('offsetY', 0))
    rotation_deg = float(form_data.get('rotation', 0))
    scale = float(form_data.get('scale', 1.0))

    is_transformed = (offsetX != 0 or offsetY != 0 or rotation_deg != 0 or scale != 1.0)

    if is_transformed:
        img_dims = data.get('image_dimensions', {})
        cx = img_dims.get('width', 0) / 2
        cy = img_dims.get('height', 0) / 2
        rotation_rad = math.radians(rotation_deg)
        cos_rad = math.cos(rotation_rad)
        sin_rad = math.sin(rotation_rad)

    # This loop structure assumes word IDs are in 'lineidx_wordidx' format
    all_words = {}
    for line in data.get('lines', []):
        for word in line.get('words', []):
             all_words[word['id']] = word

    for key, value in form_data.items():
        if key.startswith('text_'):
            word_id = key.replace('text_', '')
            if word_id in all_words:
                all_words[word_id]['text'] = value

    if is_transformed:
        for word in all_words.values():
            if 'bounding_box' not in word: continue
            bbox = word['bounding_box']
            corners = [
                (bbox['x_min'], bbox['y_min']), (bbox['x_max'], bbox['y_min']),
                (bbox['x_max'], bbox['y_max']), (bbox['x_min'], bbox['y_max']),
            ]
            transformed_corners = []
            for x, y in corners:
                x_scaled = cx + (x - cx) * scale
                y_scaled = cy + (y - cy) * scale
                x_rot = cx + (x_scaled - cx) * cos_rad - (y_scaled - cy) * sin_rad
                y_rot = cy + (x_scaled - cx) * sin_rad + (y_scaled - cy) * cos_rad
                transformed_corners.append((x_rot + offsetX, y_rot + offsetY))

            word['bounding_box'] = {
                'x_min': int(round(min(p[0] for p in transformed_corners))),
                'y_min': int(round(min(p[1] for p in transformed_corners))),
                'x_max': int(round(max(p[0] for p in transformed_corners))),
                'y_max': int(round(max(p[1] for p in transformed_corners))),
            }

    return data


# --- Routes ---

@app.route('/')
def index():
    """Homepage: shows a list of files and their status."""
    files = get_json_files()
    file_statuses = [{'filename': f, 'status': get_file_status(f)} for f in files]
    return render_template('index.html', files=file_statuses)

@app.route('/validate/<string:json_filename>')
def validate(json_filename):
    data = load_data(json_filename)
    if not data:
        abort(404, "JSON file not found.")

    # Flatten words and add unique IDs
    annotations = []
    word_counter = 0
    for line_idx, line in enumerate(data.get('lines', [])):
        for word_idx, word in enumerate(line.get('words', [])):
            word_info = word.copy()
            word_info['id'] = f"{line_idx}_{word_idx}"
            word_info['display_id'] = word_counter + 1
            # Update the original data object with this ID for consistency
            word['id'] = word_info['id']
            annotations.append(word_info)
            word_counter += 1

    return render_template(
        'validate.html',
        json_filename=json_filename,
        image_filename=data['image_source'],
        image_dimensions=data.get('image_dimensions', {}),
        annotations=annotations,
        # Pass the full data object as a JSON string for the frontend to use
        json_data_string=json.dumps(data)
    )

@app.route('/autosave/<string:json_filename>', methods=['POST'])
def autosave(json_filename):
    """Auto-saves the current state to the in_progress directory."""
    transformed_data = apply_transformations_to_data(request.form)

    save_path = os.path.join(IN_PROGRESS_DATA_DIR, json_filename)
    with open(save_path, 'w') as f:
        json.dump(transformed_data, f, indent=2)

    return jsonify({'status': 'ok', 'message': 'Draft saved.'})

@app.route('/commit/<string:json_filename>', methods=['POST'])
def commit(json_filename):
    """Commits the final changes to the validated directory."""
    transformed_data = apply_transformations_to_data(request.form)
    transformed_data['validated'] = True

    # Save to validated directory
    validated_path = os.path.join(VALIDATED_DATA_DIR, json_filename)
    with open(validated_path, 'w') as f:
        json.dump(transformed_data, f, indent=2)

    # Remove from in_progress directory
    in_progress_path = os.path.join(IN_PROGRESS_DATA_DIR, json_filename)
    if os.path.exists(in_progress_path):
        os.remove(in_progress_path)

    # Redirect to the next unvalidated/in-progress file
    all_files = get_json_files()
    current_index = all_files.index(json_filename) if json_filename in all_files else -1

    for i in range(current_index + 1, len(all_files)):
        if get_file_status(all_files[i]) != 'validated':
            return redirect(url_for('validate', json_filename=all_files[i]))

    return redirect(url_for('index'))

# --- NEW ROUTE ---
@app.route('/get_source_data/<string:json_filename>')
def get_source_data(json_filename):
    """
    Endpoint to fetch the raw, unmodified JSON data from the source directory.
    """
    source_path = os.path.join(SOURCE_DATA_DIR, json_filename)

    if not os.path.exists(source_path):
        abort(404, f"Source file '{json_filename}' not found.")

    with open(source_path, 'r') as f:
        data = json.load(f)

    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
