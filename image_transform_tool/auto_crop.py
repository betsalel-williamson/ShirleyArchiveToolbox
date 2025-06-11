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
        description="Auto-crop by creating a bounding box around filtered content."
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

    # --- 4. Find all content blobs, filter them, and combine ---
    print("[INFO] Finding and filtering content blobs to create a 'point cloud'...")
    contours, _ = cv2.findContours(
        closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # *** NEW: Add dimension thresholds for filtering ***
    contour_area_threshold = 100
    dimension_threshold = 40  # The minimum width or height in pixels
    all_contour_points = []

    for c in contours:
        # Get the non-rotated bounding box
        x, y, w, h = cv2.boundingRect(c)

        # Apply all three filters
        if (
            cv2.contourArea(c) > contour_area_threshold
            and w > dimension_threshold
            and h > dimension_threshold
        ):
            all_contour_points.append(c)
        else:
            # Optional: Log which contours are being filtered out for debugging
            print(f"[DEBUG] Filtering out contour with area={cv2.contourArea(c):.0f}, w={w}, h={h}")
            pass

    if not all_contour_points:
        print(
            "[ERROR] No significant content contours found after filtering. "
            "Try adjusting blur, Canny, or filter thresholds."
        )
        return

    point_cloud = np.vstack(all_contour_points)

    # --- 5. Find the Bounding Box of the Point Cloud ---
    print(
        "[INFO] Calculating the tightest rotated bounding box for the filtered content..."
    )
    rect = cv2.minAreaRect(point_cloud)
    box = cv2.boxPoints(rect)
    box = np.int32(box)  # Use np.int32 for modern numpy compatibility

    if box.size == 0:
        print(
            "[ERROR] Could not determine a valid bounding box from the filtered contours."
        )
        return

    ordered_pts = order_points(box)

    # --- 6. Visualization ---
    print("[INFO] Found document boundary. Saving visualization...")
    detected_path = output_path.replace(".jpg", "_detected.jpg")
    cv2.drawContours(orig_image, [box], 0, (0, 255, 0), 5)
    for point in ordered_pts:
        cv2.circle(orig_image, tuple(point.astype(int)), 15, (0, 0, 255), -1)
    cv2.imwrite(detected_path, orig_image)
    print(f"[INFO] Saved detection visualization to {detected_path}")

    # --- 7. Apply Perspective Transform ---
    (tl, tr, br, bl) = ordered_pts

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
