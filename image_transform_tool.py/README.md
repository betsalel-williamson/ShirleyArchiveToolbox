# Image Transformation Tools

This directory contains a collection of Python scripts designed for various image transformation tasks, primarily focused on document scanning and processing.

## Scripts

Below is a summary of the scripts available in this directory:

### 1. `auto_crop.py`

* **Purpose**: This script automatically detects and crops a document from an image. It uses a tunable, erosion-based computer vision algorithm to identify the document boundaries, performs a perspective warp to straighten the document, and then saves the cropped result.
* **Details**: For detailed usage instructions and tunable parameters, please refer to the script's internal help (`python auto_crop.py -h`).

#### Sample

Arguments:

```bash
auto_crop.py \
  -i samples/image00008.jpg \
  -o samples/image00008_crop.jpg \
  --verbose \
  --debug \
  --margin 150 \
  --kernel-w 90 \
  --kernel-h 30 \
  --erosion-k 30
```

##### Original Image

![alt text](samples/image00008.jpg "Original Image")

##### Closed

Converted to black and white and features shown

![alt text](samples/image00008_crop_closed.jpg "Original Image")

##### Reconstructed

Small features removed

![alt text](samples/image00008_crop_reconstructed.jpg "Reconstructed")

##### Detected

Bounding box constructed

![alt text](samples/image00008_crop_detected.jpg "Detected")

##### Cropped

Final cropped image

![alt text](samples/image00008_crop.jpg "Cropped")

#### Tasks

Add step to auto rotate based on any line information in the photo

### 2. `crop_image.py`

* **Purpose**: A simple utility script that crops an image based on explicitly provided pixel coordinates.
* **Details**: The script is configured by editing the `input_filename`, `crop_coordinates`, and `output_filename` variables directly within the file.

### 3. `gemini_crop.py`

* **Purpose**: This script leverages the Google Gemini Vision API to identify the corners of a document within an image and then performs a perspective crop.
* **Details**: Requires a `GOOGLE_API_KEY` environment variable.
