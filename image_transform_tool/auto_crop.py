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


def validate_dimensions(
    contour, expected_width, expected_height, tolerance=0.25
):  # Slightly increased tolerance
    """
    Checks if the dimensions of a contour match the expected physical dimensions.
    """
    rect = cv2.minAreaRect(contour)
    (width, height) = rect[1]
    dim1, dim2 = sorted((width, height))
    exp_dim1, exp_dim2 = sorted((expected_width, expected_height))

    height_ok = (1 - tolerance) * exp_dim1 < dim1 < (1 + tolerance) * exp_dim1
    width_ok = (1 - tolerance) * exp_dim2 < dim2 < (1 + tolerance) * exp_dim2

    if height_ok and width_ok:
        print(
            f"[DEBUG] Contour validation PASSED. "
            f"Measured (w,h): ({width:.0f}, {height:.0f}), "
            f"Expected (w,h): ({expected_width}, {expected_height})"
        )
        return True
    else:
        print(
            f"[DEBUG] Contour validation FAILED. "
            f"Measured (w,h): ({width:.0f}, {height:.0f}), "
            f"Expected (w,h): ({expected_width}, {expected_height})"
        )
        return False


def main():
    # --- 1. Argument Parser ---
    ap = argparse.ArgumentParser(
        description="Auto-crop using a hybrid of positional and content-based constraints."
    )
    ap.add_argument("-i", "--image", required=True, help="Path to the input image")
    ap.add_argument(
        "-o", "--output", required=True, help="Path for the output cropped image"
    )
    ap.add_argument(
        "--width",
        type=int,
        default=2437,
        help="Expected width of the journal in pixels",
    )
    ap.add_argument(
        "--height",
        type=int,
        default=1704,
        help="Expected height of the journal in pixels",
    )
    args = vars(ap.parse_args())

    image_path = args["image"]
    output_path = args["output"]
    EXPECTED_WIDTH = args["width"]
    EXPECTED_HEIGHT = args["height"]

    # --- 2. Load and Pre-process ---
    print("[INFO] Loading image...")
    image = cv2.imread(image_path)
    if image is None:
        print(f"[ERROR] Could not load image from path: {image_path}")
        return

    orig_image = image.copy()
    (H, W) = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edged = cv2.Canny(blurred, 50, 150)

    # --- 3. Morphological Closing to find the text block ---
    print("[INFO] Applying refined morphological closing...")
    # ** NEW: Smaller, rectangular kernel for more controlled merging **
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 10))
    closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)

    # --- 4. Positional Filtering ---
    print("[INFO] Applying positional filter to focus on the center...")
    mask = np.zeros(closed.shape, dtype="uint8")
    center_x, center_y = W // 2, H // 2
    # Define a generous central region (85% width, 90% height)
    roi_w, roi_h = int(W * 0.85), int(H * 0.90)
    cv2.rectangle(
        mask,
        (center_x - roi_w // 2, center_y - roi_h // 2),
        (center_x + roi_w // 2, center_y + roi_h // 2),
        255,
        -1,
    )

    # Apply the mask to the 'closed' image
    closed_masked = cv2.bitwise_and(closed, closed, mask=mask)

    # Save debug images
    cv2.imwrite(output_path.replace(".jpg", "_closed.jpg"), closed)
    cv2.imwrite(output_path.replace(".jpg", "_closed_masked.jpg"), closed_masked)
    print("[DEBUG] Saved 'closed' and 'closed_masked' images for inspection.")

    # --- 5. Find and Select the Best Contour ---
    print("[INFO] Finding and validating contours in the central region...")
    # Find contours in the masked image
    contours, _ = cv2.findContours(
        closed_masked.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if len(contours) == 0:
        print("[ERROR] No contours found in the central region.")
        return

    # ** NEW: Find ALL valid contours first **
    valid_contours = []
    for c in contours:
        if validate_dimensions(c, EXPECTED_WIDTH, EXPECTED_HEIGHT):
            valid_contours.append(c)

    if not valid_contours:
        print("[ERROR] No contour found that matches the expected physical dimensions.")
        return

    # Select the largest contour from the valid ones
    document_contour = max(valid_contours, key=cv2.contourArea)
    print("[INFO] Successfully identified and validated the document contour.")

    # --- 6. Get Corners and Transform ---
    rect = cv2.minAreaRect(document_contour)
    box = cv2.boxPoints(rect)
    ordered_pts = order_points(box)

    # Visualization
    detected_path = output_path.replace(".jpg", "_detected.jpg")
    cv2.drawContours(orig_image, [np.int0(box)], 0, (0, 255, 0), 5)
    for point in ordered_pts:
        cv2.circle(orig_image, tuple(point.astype(int)), 15, (0, 0, 255), -1)
    cv2.imwrite(detected_path, orig_image)
    print(f"[INFO] Saved detection visualization to {detected_path}")

    # Apply perspective transform
    dst = np.array(
        [
            [0, 0],
            [EXPECTED_WIDTH - 1, 0],
            [EXPECTED_WIDTH - 1, EXPECTED_HEIGHT - 1],
            [0, EXPECTED_HEIGHT - 1],
        ],
        dtype="float32",
    )
    M = cv2.getPerspectiveTransform(ordered_pts, dst)
    warped = cv2.warpPerspective(orig_image, M, (EXPECTED_WIDTH, EXPECTED_HEIGHT))

    cv2.imwrite(output_path, warped)
    print(f"[SUCCESS] Cropped and straightened image saved to {output_path}")


if __name__ == "__main__":
    main()
