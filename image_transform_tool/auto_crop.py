import cv2
import numpy as np
import argparse


def order_points(pts):
    """
    Takes a set of points and finds the top-left, top-right,
    bottom-right, and bottom-left corners among them.
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def validate_dimensions(contour, expected_width, expected_height, tolerance=0.15):
    """
    Checks if the dimensions of a contour match the expected physical dimensions
    of the diary within a given tolerance.
    """
    # Get the minimum area rectangle that encloses the contour
    rect = cv2.minAreaRect(contour)
    # The dimensions of this rectangle are a good approximation of the object's size
    (width, height) = rect[1]

    # The rectangle might be oriented as width x height or height x width
    dim1, dim2 = sorted((width, height))  # Smallest and largest dimension
    exp_dim1, exp_dim2 = sorted((expected_width, expected_height))

    # Check if the measured dimensions are within the tolerance of expected dimensions
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
    # --- 1. Set up Argument Parser with New Configuration ---
    ap = argparse.ArgumentParser(
        description="Auto-crop and straighten a document using physical constraints."
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

    # --- 2. Load and Pre-process the Image ---
    print("[INFO] Loading image...")
    image = cv2.imread(image_path)
    if image is None:
        print(f"[ERROR] Could not load image from path: {image_path}")
        return

    orig_image = image.copy()
    (H, W) = image.shape[:2]

    # --- 3. Positional Filtering: Create a mask for the central region ---
    print("[INFO] Applying positional filter to focus on the center of the image...")
    mask = np.zeros(image.shape[:2], dtype="uint8")
    # Define the central region (e.g., inner 75% of the image)
    center_x, center_y = W // 2, H // 2
    roi_w, roi_h = int(W * 0.75), int(H * 0.85)
    cv2.rectangle(
        mask,
        (center_x - roi_w // 2, center_y - roi_h // 2),
        (center_x + roi_w // 2, center_y + roi_h // 2),
        255,
        -1,
    )

    # Apply blur and edge detection only within the masked region
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (11, 11), 0)
    edged = cv2.Canny(blurred, 40, 120)
    edged = cv2.bitwise_and(edged, edged, mask=mask)  # Keep edges only in the center

    # Save the filtered edge map for debugging
    edged_path = output_path.replace(".jpg", "_edged_filtered.jpg")
    cv2.imwrite(edged_path, edged)
    print(f"[DEBUG] Saved filtered edge map to {edged_path}")

    # --- 4. Find and Validate Contour ---
    print("[INFO] Finding and validating contours based on physical dimensions...")
    contours, _ = cv2.findContours(
        edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if len(contours) == 0:
        print("[ERROR] No contours found in the central region.")
        return

    # Sort contours by area, but we will validate each one
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    document_contour = None

    for c in contours:
        # ** NEW: VALIDATE AGAINST PHYSICAL DIMENSIONS **
        # Note: We do this on the original image scale, so no resizing is needed.
        if validate_dimensions(c, EXPECTED_WIDTH, EXPECTED_HEIGHT):
            document_contour = c
            break  # Found our match

    if document_contour is None:
        print("[ERROR] No contour found that matches the expected physical dimensions.")
        return

    print("[INFO] Found a valid document contour. Identifying extreme corner points...")
    ordered_pts = order_points(document_contour.reshape(-1, 2))

    # For visualization, draw on the original image
    detected_path = output_path.replace(".jpg", "_detected.jpg")
    cv2.drawContours(orig_image, [document_contour], -1, (0, 255, 0), 5)  # Thicker line
    for point in ordered_pts:
        cv2.circle(
            orig_image, tuple(point.astype(int)), 15, (0, 0, 255), -1
        )  # Bigger circles
    cv2.imwrite(detected_path, orig_image)
    print(f"[INFO] Saved detection visualization to {detected_path}")

    # --- 5. Apply Perspective Transform and Crop ---
    # The points are already on the original scale, so no ratio multiplication needed
    (tl, tr, br, bl) = ordered_pts

    # Use the known dimensions for the output image for consistency
    maxWidth = EXPECTED_WIDTH
    maxHeight = EXPECTED_HEIGHT

    dst = np.array(
        [[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]],
        dtype="float32",
    )

    M = cv2.getPerspectiveTransform(ordered_pts, dst)
    warped = cv2.warpPerspective(orig_image, M, (maxWidth, maxHeight))

    print("[INFO] STEP 4: Perspective transform applied.")

    # --- 6. Save the Final Image ---
    cv2.imwrite(output_path, warped)
    print(f"[SUCCESS] Cropped and straightened image saved to {output_path}")


if __name__ == "__main__":
    main()
