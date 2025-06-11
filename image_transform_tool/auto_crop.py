import cv2
import numpy as np
import argparse


def order_points(pts):
    """
    Takes a set of points and orders them: top-left, top-right, bottom-right, bottom-left.
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def main():
    # --- 1. Argument Parser ---
    ap = argparse.ArgumentParser(
        description="Auto-crop using local window filtering to clean the binary mask."
    )
    ap.add_argument("-i", "--image", required=True, help="Path to the input image")
    ap.add_argument(
        "-o", "--output", required=True, help="Path for the output cropped image"
    )
    ap.add_argument(
        "--width",
        type=int,
        default=2437,
        help="Expected final width of the journal in pixels",
    )
    ap.add_argument(
        "--height",
        type=int,
        default=1704,
        help="Expected final height of the journal in pixels",
    )
    args = vars(ap.parse_args())

    image_path = args["image"]
    output_path = args["output"]
    FINAL_WIDTH = args["width"]
    FINAL_HEIGHT = args["height"]

    # --- 2. Load and Pre-process ---
    print("[INFO] Loading image...")
    image = cv2.imread(image_path)
    if image is None:
        print(f"[ERROR] Could not load image from path: {image_path}")
        return

    orig_image = image.copy()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edged = cv2.Canny(blurred, 50, 150)

    # --- 3. Morphological Closing ---
    print("[INFO] Applying morphological closing to create initial content blobs...")
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 10))
    closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
    cv2.imwrite(output_path.replace(".jpg", "_closed.jpg"), closed)

    # --- 4. *** NEW: Local Filtering with a Sliding Window ***
    print("[INFO] Applying local thickness filter with a sliding window...")
    (h_img, w_img) = closed.shape
    step_size = 4
    window_size = 4
    min_thickness = 3

    # Create a new, clean image to draw the filtered components onto
    cleaned_image = np.zeros_like(closed)

    # Iterate through the image with a sliding window
    for y in range(0, h_img - window_size, step_size):
        for x in range(0, w_img - window_size, step_size):
            # Extract the window (Region of Interest)
            roi = closed[y : y + window_size, x : x + window_size]

            # If there are no white pixels in the window, skip it
            if cv2.countNonZero(roi) == 0:
                continue

            # Find contours within this small window
            contours, _ = cv2.findContours(roi, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

            is_thick_enough = False
            for c in contours:
                # Check the bounding box of the contour piece inside the window
                _, _, w_roi, h_roi = cv2.boundingRect(c)
                if w_roi > min_thickness and h_roi > min_thickness:
                    is_thick_enough = True
                    break  # Found a thick enough piece, no need to check others in this window

            # If a thick enough piece was found, copy this window to the cleaned image
            if is_thick_enough:
                cleaned_image[y : y + window_size, x : x + window_size] = roi

    cv2.imwrite(output_path.replace(".jpg", "_cleaned.jpg"), cleaned_image)
    print("[DEBUG] Saved the locally filtered binary image for inspection.")

    # --- 5. Find Contours on the CLEANED image ---
    print("[INFO] Finding contours on the cleaned image...")
    contours, _ = cv2.findContours(
        cleaned_image.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        print(
            "[ERROR] No contours remained after local filtering. "
            "Try adjusting window_size, step_size, or min_thickness."
        )
        return

    point_cloud = np.vstack(contours)

    # --- 6. Find the Bounding Box of the Point Cloud ---
    print("[INFO] Calculating the tightest rotated bounding box for the content...")
    rect = cv2.minAreaRect(point_cloud)
    box = cv2.boxPoints(rect)
    box = np.int32(box)

    ordered_pts = order_points(box)

    # --- 7. Visualization & Transform ---
    print("[INFO] Found document boundary. Saving visualization and cropping...")
    detected_path = output_path.replace(".jpg", "_detected.jpg")
    cv2.drawContours(orig_image, [box], 0, (0, 255, 0), 5)
    cv2.imwrite(detected_path, orig_image)

    dst = np.array(
        [
            [0, 0],
            [FINAL_WIDTH - 1, 0],
            [FINAL_WIDTH - 1, FINAL_HEIGHT - 1],
            [0, FINAL_HEIGHT - 1],
        ],
        dtype="float32",
    )
    M = cv2.getPerspectiveTransform(ordered_pts, dst)
    warped = cv2.warpPerspective(orig_image, M, (FINAL_WIDTH, FINAL_HEIGHT))
    cv2.imwrite(output_path, warped)
    print(f"[SUCCESS] Cropped and straightened image saved to {output_path}")


if __name__ == "__main__":
    main()
