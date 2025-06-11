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
        description="Auto-crop using Connected Components to filter content blobs."
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
    print("[INFO] Applying morphological closing to merge text into content blobs...")
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 10))
    closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
    cv2.imwrite(output_path.replace(".jpg", "_closed.jpg"), closed)

    # --- 4. *** NEW: Filter blobs using Connected Components Analysis ***
    print("[INFO] Filtering blobs by size using Connected Components Analysis...")
    # Find all connected components and their stats
    num_labels, labels_im, stats, centroids = cv2.connectedComponentsWithStats(
        closed, connectivity=8
    )

    # Create a new, clean image to draw the filtered components onto
    cleaned_image = np.zeros_like(closed)

    # Define minimum dimensions for a blob to be kept
    min_width = 3
    min_height = 3

    # Loop over all components, starting from 1 (0 is the background)
    for i in range(1, num_labels):
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]

        # If the component meets the size criteria, add it to the clean image
        if w > min_width and h > min_height:
            # Create a mask for the current component
            component_mask = (labels_im == i).astype("uint8") * 255
            # Add the valid component to our final mask
            cleaned_image = cv2.bitwise_or(cleaned_image, component_mask)

    cv2.imwrite(output_path.replace(".jpg", "_cleaned.jpg"), cleaned_image)
    print("[DEBUG] Saved the cleaned binary image for inspection.")

    # --- 5. Find Contours on the CLEANED image ---
    print("[INFO] Finding contours on the cleaned image...")
    # Now find contours on the cleaned image, which contains only "good" blobs
    contours, _ = cv2.findContours(
        cleaned_image.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        print(
            "[ERROR] No contours remained after filtering. "
            "Try adjusting the min_width/min_height thresholds or the morphological kernel."
        )
        return

    point_cloud = np.vstack(contours)

    # --- 6. Find the Bounding Box of the Point Cloud ---
    print("[INFO] Calculating the tightest rotated bounding box for the content...")
    rect = cv2.minAreaRect(point_cloud)
    box = cv2.boxPoints(rect)
    box = np.int32(box)

    ordered_pts = order_points(box)

    # --- 7. Visualization ---
    print("[INFO] Found document boundary. Saving visualization...")
    detected_path = output_path.replace(".jpg", "_detected.jpg")
    cv2.drawContours(orig_image, [box], 0, (0, 255, 0), 5)
    for point in ordered_pts:
        cv2.circle(orig_image, tuple(point.astype(int)), 15, (0, 0, 255), -1)
    cv2.imwrite(detected_path, orig_image)

    # --- 8. Apply Perspective Transform ---
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
