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
        description="Auto-crop using erosion-based filtering with tunable parameters."
    )
    ap.add_argument("-i", "--image", required=True, help="Path to the input image")
    ap.add_argument(
        "-o", "--output", required=True, help="Path for the output cropped image"
    )
    ap.add_argument(
        "--margin",
        type=int,
        default=150,
        help="Pixel margin to add around the final crop",
    )

    # --- KERNEL EXPLANATION ---
    # The goal of this closing operation is to connect individual words on the same horizontal line
    # into a single solid blob, while AVOIDING the connection of separate vertical lines of text.
    # To achieve this, we use a rectangular kernel that is wider than it is tall.
    #
    # KERNEL_W (Width): Must be larger than the average gap between words to ensure they merge.
    # A value of 30 is chosen as a robust default to bridge these horizontal spaces.
    #
    # KERNEL_H (Height): Must be smaller than the average vertical gap between lines of text.
    # A value of 10 is chosen to be short enough that it doesn't accidentally merge a line
    # of text with the one directly above or below it.
    #
    # This anisotropic kernel matches the nature of written text (long horizontally, separated vertically).
    # --------------------------
    ap.add_argument(
        "--kernel-w",
        type=int,
        default=30,
        help="Width of the morphological closing kernel",
    )
    ap.add_argument(
        "--kernel-h",
        type=int,
        default=10,
        help="Height of the morphological closing kernel",
    )

    # --- EROSION KERNEL EXPLANATION ---
    # The primary goal of this erosion step is to eliminate any remaining thin-line artifacts
    # (like page edges or noise) that may have been connected to the main text block during the
    # previous closing operation.
    #
    # Unlike the rectangular closing kernel which was designed to be directional (anisotropic),
    # this erosion kernel is square (`EROSION_K` x `EROSION_K`). This is because its purpose is
    # isotropic (uniform in all directions) – it's a test for 'thickness' regardless of orientation.
    #
    # The erosion operation works by sliding the kernel over the image. A pixel will only survive
    # (remain white) if the entire square kernel fits completely inside the white region around it.
    #
    # Therefore, a value of 12 for `EROSION_K` means we are removing any and all features that are
    # less than 12 pixels thick in any direction. This effectively erases thin horizontal, vertical,
    # and diagonal lines, while preserving the 'cores' of the chunky text blobs.
    # ------------------------------------
    ap.add_argument(
        "--erosion-k", type=int, default=12, help="Size of the square erosion kernel"
    )

    args = vars(ap.parse_args())

    image_path = args["image"]
    output_path = args["output"]
    MARGIN = args["margin"]
    KERNEL_W = args["kernel_w"]
    KERNEL_H = args["kernel_h"]
    EROSION_K = args["erosion_k"]

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
    print(
        f"[INFO] Applying morphological closing with kernel size ({KERNEL_W}, {KERNEL_H})..."
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (KERNEL_W, KERNEL_H))
    closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
    cv2.imwrite(output_path.replace(".jpg", "_closed.jpg"), closed)

    # --- 4. Filter thin lines using Erosion ---
    print(
        f"[INFO] Filtering thin lines via erosion with kernel size {EROSION_K}x{EROSION_K}..."
    )
    erosion_kernel = np.ones((EROSION_K, EROSION_K), np.uint8)
    eroded_image = cv2.erode(closed, erosion_kernel, iterations=1)

    # Dilate back to restore size
    reconstructed_image = cv2.dilate(eroded_image, erosion_kernel, iterations=1)
    cv2.imwrite(output_path.replace(".jpg", "_reconstructed.jpg"), reconstructed_image)
    print("[DEBUG] Saved reconstructed image for inspection.")

    # --- 5. Find Contours and Bounding Box ---
    print("[INFO] Finding contours on the reconstructed (cleaned) image...")
    contours, _ = cv2.findContours(
        reconstructed_image.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        print(
            "[ERROR] No contours remained after erosion filtering. Try adjusting kernel sizes."
        )
        return

    point_cloud = np.vstack(contours)
    rect = cv2.minAreaRect(point_cloud)
    box = cv2.boxPoints(rect)
    box = np.int32(box)
    ordered_pts = order_points(box)

    # --- 6. Apply Perspective Transform with Margin ---
    (tl, tr, br, bl) = ordered_pts

    # Compute the width of the new image
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    # Compute the height of the new image
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    print(f"[INFO] Detected document dimensions: {maxWidth}w x {maxHeight}h")

    # Define destination points with a margin
    dst = np.array(
        [
            [MARGIN, MARGIN],
            [maxWidth - 1 + MARGIN, MARGIN],
            [maxWidth - 1 + MARGIN, maxHeight - 1 + MARGIN],
            [MARGIN, maxHeight - 1 + MARGIN],
        ],
        dtype="float32",
    )

    # Get the perspective transformation matrix
    M = cv2.getPerspectiveTransform(ordered_pts.astype("float32"), dst)

    # Apply the warp
    warped = cv2.warpPerspective(
        orig_image, M, (maxWidth + 2 * MARGIN, maxHeight + 2 * MARGIN)
    )

    print(
        f"[INFO] Final crop with margin applied. Output size: {warped.shape[1]}w x {warped.shape[0]}h"
    )

    # --- 7. Save the Final Image ---
    cv2.imwrite(output_path, warped)
    print(f"[SUCCESS] Cropped and straightened image saved to {output_path}")


if __name__ == "__main__":
    main()
