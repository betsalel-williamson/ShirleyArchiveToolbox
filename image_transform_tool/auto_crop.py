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
        description="Auto-crop using erosion-based filtering to remove thin lines."
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

    # --- 4. *** NEW: Filter thin lines using Erosion ***
    print("[INFO] Filtering thin lines via erosion...")
    # Create a kernel for erosion. A 3x3 kernel will remove lines of 1 or 2 pixels thick.
    erosion_kernel = np.ones((12, 12), np.uint8)

    # Erode the image - this will make thin lines disappear
    eroded_image = cv2.erode(closed, erosion_kernel, iterations=1)
    cv2.imwrite(output_path.replace(".jpg", "_eroded.jpg"), eroded_image)

    # Find the contours of the surviving "thick" blobs
    contours, _ = cv2.findContours(
        eroded_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # Create a new mask to reconstruct the full shape of the thick blobs
    cleaned_mask = np.zeros_like(closed)
    # Draw the full contours that survived onto the new mask
    # We find these contours in the original 'closed' image by checking which ones contain the eroded blobs.
    # A simpler and effective approach is to just use the eroded contours as seeds and dilate them back a bit.

    # Dilate the eroded image to regain some of the lost shape of the thick blobs
    # The number of iterations should match the erosion iterations
    reconstructed_image = cv2.dilate(eroded_image, erosion_kernel, iterations=1)
    cv2.imwrite(output_path.replace(".jpg", "_reconstructed.jpg"), reconstructed_image)
    print("[DEBUG] Saved eroded and reconstructed images for inspection.")

    # --- 5. Find Contours on the RECONSTRUCTED image ---
    print("[INFO] Finding contours on the reconstructed (cleaned) image...")
    contours, _ = cv2.findContours(
        reconstructed_image.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        print("[ERROR] No contours remained after erosion filtering.")
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
