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
    contour, expected_width, expected_height, tolerance=0.20
):  # Increased tolerance
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
        description="Auto-crop and straighten a document using physical and content-based constraints."
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
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(
        gray, (7, 7), 0
    )  # Slightly less blur to preserve text edges
    edged = cv2.Canny(blurred, 50, 150)

    # --- 3. *** NEW: Morphological Closing to find the text block ***
    print("[INFO] Applying morphological closing to merge text into a content block...")
    # A large rectangular kernel to connect lines of text
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 40))
    closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)

    # Save the intermediate steps for debugging
    cv2.imwrite(output_path.replace(".jpg", "_edged.jpg"), edged)
    cv2.imwrite(output_path.replace(".jpg", "_closed.jpg"), closed)
    print("[DEBUG] Saved 'edged' and 'closed' images for inspection.")

    # --- 4. Find Contour of the Content Block ---
    print("[INFO] Finding contour of the merged content block...")
    # Find contours in the 'closed' image now
    contours, _ = cv2.findContours(
        closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if len(contours) == 0:
        print("[ERROR] No contours found after morphological closing.")
        return

    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    document_contour = None

    for c in contours:
        # Validate the dimensions of this content blob
        if validate_dimensions(c, EXPECTED_WIDTH, EXPECTED_HEIGHT):
            document_contour = c
            break

    if document_contour is None:
        print("[ERROR] No contour found that matches the expected physical dimensions.")
        return

    # --- 5. Get Corners from the Rotated Bounding Box ---
    print(
        "[INFO] Found a valid content block. Calculating corners from its bounding box..."
    )
    # Get the minimum area rectangle, which is more stable than finding extreme points
    rect = cv2.minAreaRect(document_contour)
    box = cv2.boxPoints(rect)
    box = np.int0(box)

    # Now order these 4 box points correctly
    ordered_pts = order_points(box)

    # Visualization
    detected_path = output_path.replace(".jpg", "_detected.jpg")
    cv2.drawContours(orig_image, [box], 0, (0, 255, 0), 5)
    for point in ordered_pts:
        cv2.circle(orig_image, tuple(point.astype(int)), 15, (0, 0, 255), -1)
    cv2.imwrite(detected_path, orig_image)
    print(f"[INFO] Saved detection visualization to {detected_path}")

    # --- 6. Apply Perspective Transform ---
    (tl, tr, br, bl) = ordered_pts
    maxWidth = EXPECTED_WIDTH
    maxHeight = EXPECTED_HEIGHT

    dst = np.array(
        [[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]],
        dtype="float32",
    )

    M = cv2.getPerspectiveTransform(ordered_pts, dst)
    warped = cv2.warpPerspective(orig_image, M, (maxWidth, maxHeight))

    print("[INFO] Perspective transform applied.")
    cv2.imwrite(output_path, warped)
    print(f"[SUCCESS] Cropped and straightened image saved to {output_path}")


if __name__ == "__main__":
    main()
