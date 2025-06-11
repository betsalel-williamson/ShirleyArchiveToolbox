import cv2
import numpy as np
import argparse

# --- HELPER FUNCTIONS ---


def order_points(pts):
    """
    Takes a set of 4 points and orders them: top-left, top-right, bottom-right, bottom-left.
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


# --- PROCESSING PIPELINE FUNCTIONS ---


def load_and_preprocess_image(image_path):
    """
    Step 1: Loads an image, converts it to grayscale, blurs it, and finds edges.
    Returns the original image and the edge-detected image.
    """
    print("[INFO] Step 1: Loading and pre-processing image...")
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not load image from path: {image_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edged = cv2.Canny(blurred, 50, 150)
    return image, edged


def create_content_mask(edged_image, kernel_w, kernel_h, erosion_k, output_path_prefix):
    """
    Step 2: Takes an edge map, applies morphological closing to form blobs,
    then uses erosion to filter out thin lines, creating a clean content mask.
    Returns the final cleaned mask.
    """
    # Create a rectangular kernel that is wider than it is tall to connect words horizontally.
    print(
        f"[INFO] Step 2a: Applying morphological closing with kernel ({kernel_w}, {kernel_h})..."
    )
    closing_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, kernel_h))
    closed = cv2.morphologyEx(edged_image, cv2.MORPH_CLOSE, closing_kernel)
    cv2.imwrite(f"{output_path_prefix}_closed.jpg", closed)

    # Use a square kernel to test for thickness and remove thin lines (e.g., page edges).
    print(
        f"[INFO] Step 2b: Filtering thin lines with erosion kernel {erosion_k}x{erosion_k}..."
    )
    erosion_kernel = np.ones((erosion_k, erosion_k), np.uint8)
    eroded = cv2.erode(closed, erosion_kernel, iterations=1)

    # Dilate back to restore the original size of the thick, surviving blobs.
    reconstructed = cv2.dilate(eroded, erosion_kernel, iterations=1)
    cv2.imwrite(f"{output_path_prefix}_reconstructed.jpg", reconstructed)
    print("[DEBUG] Saved intermediate images for inspection.")
    return reconstructed


def find_document_boundary(cleaned_mask):
    """
    Step 3: Takes the cleaned content mask, finds all content blobs,
    and returns the ordered corner points of the tightest rotated bounding box that encloses all of them.
    """
    print("[INFO] Step 3: Finding the boundary of the document content...")
    contours, _ = cv2.findContours(
        cleaned_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        raise ValueError(
            "No contours remained after filtering. Try adjusting kernel sizes."
        )

    # Combine all found blobs into a single "point cloud"
    point_cloud = np.vstack(contours)

    # Find the tightest rotated rectangle around the entire point cloud
    rect = cv2.minAreaRect(point_cloud)
    box = cv2.boxPoints(rect)

    ordered_pts = order_points(box)
    return ordered_pts


def warp_and_crop_image(original_image, ordered_pts, margin):
    """
    Step 4: Takes the original image, the ordered corners of the document, and a margin.
    It performs a perspective warp to straighten the document and adds the specified margin.
    Returns the final cropped and straightened image.
    """
    print("[INFO] Step 4: Applying perspective warp and adding margin...")
    (tl, tr, br, bl) = ordered_pts

    # Compute the width and height of the detected document
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    print(f"[INFO] Detected document dimensions: {maxWidth}w x {maxHeight}h")

    # Define destination points with a margin to create a slightly larger output canvas
    dst = np.array(
        [
            [margin, margin],
            [maxWidth - 1 + margin, margin],
            [maxWidth - 1 + margin, maxHeight - 1 + margin],
            [margin, maxHeight - 1 + margin],
        ],
        dtype="float32",
    )

    # Compute the perspective transform matrix and apply it
    M = cv2.getPerspectiveTransform(ordered_pts.astype("float32"), dst)
    final_canvas_w = maxWidth + 2 * margin
    final_canvas_h = maxHeight + 2 * margin
    warped = cv2.warpPerspective(original_image, M, (final_canvas_w, final_canvas_h))

    print(
        f"[INFO] Final crop created. Output size: {warped.shape[1]}w x {warped.shape[0]}h"
    )
    return warped


# --- MAIN COORDINATOR ---


def main(image_path, output_path, margin, kernel_w, kernel_h, erosion_k):
    """
    Main pipeline coordinator that calls the processing functions in sequence.
    Accepts named arguments for clarity.
    """
    try:
        # Step 1: Load and pre-process
        original_image, edged_image = load_and_preprocess_image(image_path)

        # Step 2: Create the clean content mask
        output_prefix = output_path.replace(".jpg", "")
        cleaned_mask = create_content_mask(
            edged_image, kernel_w, kernel_h, erosion_k, output_prefix
        )

        # Step 3: Find the boundary of the document
        ordered_pts = find_document_boundary(cleaned_mask)

        # Step 4: Warp, crop, and add a margin
        final_image = warp_and_crop_image(original_image, ordered_pts, margin)

        # Step 5: Save the final output
        cv2.imwrite(output_path, final_image)
        print(f"[SUCCESS] Cropped and straightened image saved to {output_path}")

    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] A critical error occurred: {e}")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")


# --- ARGUMENT PARSING AND EXECUTION ---

if __name__ == "__main__":
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
    ap.add_argument(
        "--kernel-w",
        type=int,
        default=30,
        help="Width of the rectangular morphological closing kernel. Used to connect words on the same line.",
    )
    ap.add_argument(
        "--kernel-h",
        type=int,
        default=10,
        help="Height of the rectangular morphological closing kernel. Should be smaller than the space between lines.",
    )
    ap.add_argument(
        "--erosion-k",
        type=int,
        default=12,
        help="Size of the square erosion kernel. Used to remove thin lines and noise.",
    )

    args = ap.parse_args()

    main(
        image_path=args.image,
        output_path=args.output,
        margin=args.margin,
        kernel_w=args.kernel_w,
        kernel_h=args.kernel_h,
        erosion_k=args.erosion_k,
    )
