import cv2
import numpy as np
import argparse
import logging
import sys
from typing import Tuple
from numpy.typing import NDArray

# --- HELPER FUNCTIONS ---


def order_points(pts: NDArray[np.float32]) -> NDArray[np.float32]:
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


def load_and_preprocess_image(
    image_path: str,
) -> Tuple[NDArray[np.uint8], NDArray[np.uint8]]:
    """
    Step 1: Loads an image, converts it to grayscale, blurs it, and finds edges.
    Returns the original color image and the 8-bit single-channel edge-detected image.
    """
    logging.info("Step 1: Loading and pre-processing image...")
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not load image from path: {image_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edged = cv2.Canny(blurred, 50, 150)
    return image, edged


def create_content_mask(
    edged_image: NDArray[np.uint8],
    kernel_w: int,
    kernel_h: int,
    erosion_k: int,
    output_path_prefix: str,
    debug: bool,
) -> NDArray[np.uint8]:
    """
    Step 2: Takes an edge map, applies morphological closing to form blobs,
    then uses erosion to filter out thin lines, creating a clean content mask.
    Returns the final cleaned mask.
    """
    logging.info(
        f"Step 2a: Applying morphological closing with kernel ({kernel_w}, {kernel_h})..."
    )
    closing_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, kernel_h))
    closed = cv2.morphologyEx(edged_image, cv2.MORPH_CLOSE, closing_kernel)

    logging.info(
        f"Step 2b: Filtering thin lines with erosion kernel {erosion_k}x{erosion_k}..."
    )
    erosion_kernel = np.ones((erosion_k, erosion_k), np.uint8)
    eroded = cv2.erode(closed, erosion_kernel, iterations=1)

    reconstructed = cv2.dilate(eroded, erosion_kernel, iterations=1)

    if debug:
        cv2.imwrite(f"{output_path_prefix}_closed.jpg", closed)
        cv2.imwrite(f"{output_path_prefix}_reconstructed.jpg", reconstructed)
        logging.info("Saved intermediate images for inspection.")

    return reconstructed


def find_document_boundary(
    cleaned_mask: NDArray[np.uint8],
) -> Tuple[NDArray[np.float32], NDArray[np.float32]]:
    """
    Step 3: Finds all content blobs and returns the ordered corner points and the raw box points.
    """
    logging.info("Step 3: Finding the boundary of the document content...")
    contours, _ = cv2.findContours(
        cleaned_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        raise ValueError(
            "No contours remained after filtering. Try adjusting kernel sizes."
        )

    point_cloud = np.vstack(contours)
    rect = cv2.minAreaRect(point_cloud)
    box = cv2.boxPoints(rect)
    ordered_pts = order_points(box)
    return ordered_pts, box


def warp_and_crop_image(
    original_image: NDArray[np.uint8], ordered_pts: NDArray[np.float32], margin: int
) -> NDArray[np.uint8]:
    """
    Step 4: Performs a perspective warp to straighten the document and adds a margin.
    """
    logging.info("Step 4: Applying perspective warp and adding margin...")
    (tl, tr, br, bl) = ordered_pts

    logging.info(
        f"Using ordered points for crop (TL, TR, BR, BL): {ordered_pts.tolist()}"
    )

    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    logging.info(f"Detected document dimensions: {maxWidth}w x {maxHeight}h")

    dst = np.array(
        [
            [margin, margin],
            [maxWidth - 1 + margin, margin],
            [maxWidth - 1 + margin, maxHeight - 1 + margin],
            [margin, maxHeight - 1 + margin],
        ],
        dtype="float32",
    )

    M = cv2.getPerspectiveTransform(ordered_pts.astype("float32"), dst)
    final_canvas_w = maxWidth + 2 * margin
    final_canvas_h = maxHeight + 2 * margin
    warped = cv2.warpPerspective(original_image, M, (final_canvas_w, final_canvas_h))

    logging.info(
        f"Final crop created. Output size: {warped.shape[1]}w x {warped.shape[0]}h"
    )
    return warped


def save_debug_visualization(
    original_image: NDArray[np.uint8],
    detected_box: NDArray[np.float32],
    ordered_pts: NDArray[np.float32],
    output_path_prefix: str,
) -> None:
    """
    Saves a visualization of the detected boundary on the original image.
    """
    logging.info("Saving detection visualization image...")
    viz_image = original_image.copy()
    cv2.drawContours(viz_image, [np.int32(detected_box)], 0, (0, 255, 0), 5)
    for point in ordered_pts:
        cv2.circle(viz_image, tuple(point.astype(int)), 15, (0, 0, 255), -1)

    detected_path = f"{output_path_prefix}_detected.jpg"
    cv2.imwrite(detected_path, viz_image)


# --- MAIN COORDINATOR ---


def main(
    image_path: str,
    output_path: str,
    margin: int,
    kernel_w: int,
    kernel_h: int,
    erosion_k: int,
    debug: bool,
) -> int:
    """
    Main pipeline coordinator that calls processing functions and returns an exit code.
    Returns 0 on success, and a non-zero integer on failure.
    """
    try:
        original_image, edged_image = load_and_preprocess_image(image_path)
        output_prefix = output_path.rsplit(".", 1)[0]
        cleaned_mask = create_content_mask(
            edged_image, kernel_w, kernel_h, erosion_k, output_prefix, debug
        )
        ordered_pts, detected_box = find_document_boundary(cleaned_mask)

        if debug:
            save_debug_visualization(
                original_image, detected_box, ordered_pts, output_prefix
            )

        final_image = warp_and_crop_image(original_image, ordered_pts, margin)

        cv2.imwrite(output_path, final_image)
        logging.info(
            f"Successfully cropped and straightened image and saved to {output_path}"
        )
        return 0  # Success

    except FileNotFoundError as e:
        logging.error(f"Input file not found: {e}")
        return 2  # Specific error code for file not found
    except ValueError as e:
        logging.error(f"Processing error: {e}")
        return 3  # Specific error code for processing failure (e.g., no contours)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return 1  # General error code for all other exceptions


# --- ARGUMENT PARSING AND EXECUTION ---

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Auto-crop a document from an image using a tunable, erosion-based algorithm."
    )
    ap.add_argument("-i", "--image", required=True, help="Path to the input image file")
    ap.add_argument(
        "-o", "--output", required=True, help="Path for the output cropped image file"
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
        help="Size of the square erosion kernel for noise removal",
    )
    ap.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging to the console"
    )
    ap.add_argument(
        "--debug",
        action="store_true",
        help="Enable saving of intermediate processing images",
    )

    args = ap.parse_args()

    log_level = logging.INFO if args.verbose else logging.ERROR
    logging.basicConfig(level=log_level, format="[%(levelname)s] %(message)s")

    # Capture the return code from main and exit with it
    exit_code = main(
        image_path=args.image,
        output_path=args.output,
        margin=args.margin,
        kernel_w=args.kernel_w,
        kernel_h=args.kernel_h,
        erosion_k=args.erosion_k,
        debug=args.debug,
    )

    sys.exit(exit_code)
