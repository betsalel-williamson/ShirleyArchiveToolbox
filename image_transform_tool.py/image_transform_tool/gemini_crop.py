import google.generativeai as genai
import cv2
import numpy as np
import argparse
import os
import json
from PIL import Image
from dotenv import load_dotenv

load_dotenv()


def main():
    # --- 1. Setup and Argument Parsing ---
    if "GOOGLE_API_KEY" not in os.environ:
        print("[ERROR] GOOGLE_API_KEY environment variable not set.")
        print("[INFO] Please get an API key from Google AI Studio and set it.")
        return

    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

    ap = argparse.ArgumentParser(
        description="Auto-crop a document using the Gemini Vision API."
    )
    ap.add_argument("-i", "--image", required=True, help="Path to the input image")
    ap.add_argument(
        "-o", "--output", required=True, help="Path for the output cropped image"
    )
    args = vars(ap.parse_args())

    image_path = args["image"]
    output_path = args["output"]

    # --- 2. Ask Gemini to Find the Corners ---
    print(f"[INFO] Loading image: {image_path}")
    img = Image.open(image_path)
    model = genai.GenerativeModel("models/gemini-2.5-flash-preview-05-20")

    # This is the prompt that tells the model exactly what to do.
    prompt = """
You are a high-precision, metrology-grade image analysis system. Your task is to find the precise pixel coordinates of the four outer corners of the visible white paper pages of an open diary. You MUST adhere to the following physical, geometric, and positional constraints.

**Critical Constraints:**

1.  **Positional Constraint:** The target diary will **always be located in the central region of the image**. Your search should be focused on the middle of the frame, ignoring any potential objects or noise near the edges.
2.  **Fixed Scale & Absolute Dimensions:** The diary is captured from a fixed distance at a consistent resolution. Therefore, the dimensions of the paper pages in the image are constant. The quadrilateral you identify **must** have side lengths that correspond to a **2437 pixel width and a 1704 pixel height**.
    *   The **top and bottom edges** of the quadrilateral in the image should each measure close to **2437 pixels** in length.
    *   The **left and right sides** of the quadrilateral should each measure close to **1704 pixels** in length.
    .
3.  **Target the Paper Pages:** The coordinates must correspond to the corners of the paper itself, not the outer book cover or hands holding it.
4.  **Handle Occlusion:** If a corner is obscured by a hand or finger, you must logically estimate its true position by completing the shape based on the known dimensions and visible edges.

**Output Format:**
Return your final answer as a single, clean JSON object. This object must have one key, "corners", containing a list of four [x, y] lists. The required order is strictly: top-left, top-right, bottom-right, bottom-left, relative to the orientation of the text. Do not include markdown formatting or any other text."""

    print(
        "[INFO] Asking Gemini to find the document corners... (this may take a moment)"
    )
    try:
        response = model.generate_content([prompt, img])
        # Clean up the response to ensure it's valid JSON
        json_str = (
            response.text.strip().replace("```json", "").replace("```", "").strip()
        )
        data = json.loads(json_str)
        corners = np.array(data["corners"], dtype="float32")
    except (ValueError, KeyError, IndexError, Exception) as e:
        print(f"[ERROR] Failed to parse coordinates from Gemini response: {e}")
        print(f"[DEBUG] Raw response from API: {response.text}")
        return

    print(f"[INFO] Gemini identified corners at: {corners.tolist()}")

    # --- 3. Apply Perspective Transform (using OpenCV) ---
    # Load the image with OpenCV for the transformation part
    orig_image = cv2.imread(image_path)
    (tl, tr, br, bl) = corners

    # Calculate the width of the new image
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    # Calculate the height of the new image
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    # Define the destination points for the top-down view
    dst = np.array(
        [[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]],
        dtype="float32",
    )

    # Get the perspective transformation matrix and apply it
    M = cv2.getPerspectiveTransform(corners, dst)
    warped = cv2.warpPerspective(orig_image, M, (maxWidth, maxHeight))

    print("[INFO] Perspective transform applied.")

    # --- 4. Save the Final Image ---
    cv2.imwrite(output_path, warped)
    print(f"[SUCCESS] Cropped and straightened image saved to {output_path}")


if __name__ == "__main__":
    main()
