import cv2
import numpy as np
import argparse


def order_points(pts):
    """
    Takes a set of points and finds the top-left, top-right,
    bottom-right, and bottom-left corners among them.
    """
    rect = np.zeros((4, 2), dtype="float32")

    # The top-left point will have the smallest sum (x+y)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]

    # The bottom-right point will have the largest sum (x+y)
    rect[2] = pts[np.argmax(s)]

    # The top-right point will have the largest difference (x-y)
    # The bottom-left will have the smallest difference (x-y)
    # Note: np.diff is y-x, so we find min for top-right and max for bottom-left
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect


def main():
    # --- 1. Set up Argument Parser ---
    ap = argparse.ArgumentParser(
        description="Auto-crop and straighten a document from an image."
    )
    ap.add_argument("-i", "--image", required=True, help="Path to the input image")
    ap.add_argument(
        "-o", "--output", required=True, help="Path for the output cropped image"
    )
    args = vars(ap.parse_args())

    image_path = args["image"]
    output_path = args["output"]

    # --- 2. Load and Pre-process the Image ---
    print("[INFO] Loading image and starting pre-processing...")
    image = cv2.imread(image_path)
    if image is None:
        print(f"[ERROR] Could not load image from path: {image_path}")
        return

    orig_image = image.copy()
    ratio = image.shape[0] / 500.0
    image = cv2.resize(image, (int(image.shape[1] / ratio), 500))

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)

    print("[INFO] STEP 1: Edge Detection complete.")

    # --- 3. Find the Document Contour ---
    print("[INFO] STEP 2: Finding document contour...")

    contours, _ = cv2.findContours(
        edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if len(contours) == 0:
        print("[ERROR] No contours found. Check Canny edge detection parameters.")
        return

    # Assume the largest contour is the document
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    document_contour = contours[0]

    # *** THIS IS THE MAJOR CHANGE ***
    # Instead of approximating the polygon, we find the extreme corner points
    # of the largest contour. This is robust to occlusions like hands.
    print("[INFO] STEP 3: Found largest contour. Identifying extreme corner points...")
    ordered_pts_resized = order_points(document_contour.reshape(-1, 2))

    # For visualization, draw the found contour and corners on the resized image
    detected_path = output_path.replace(".jpg", "_detected.jpg").replace(
        ".png", "_detected.png"
    )
    # Draw the full contour
    cv2.drawContours(image, [document_contour], -1, (0, 255, 0), 2)
    # Draw circles on the identified corners
    for point in ordered_pts_resized:
        cv2.circle(image, tuple(point.astype(int)), 5, (0, 0, 255), -1)
    cv2.imwrite(detected_path, image)
    print(f"[INFO] Saved detection visualization to {detected_path}")

    # --- 4. Apply Perspective Transform and Crop ---
    # Scale the corner points back to the original image size
    ordered_pts = ordered_pts_resized * ratio
    (tl, tr, br, bl) = ordered_pts

    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    dst = np.array(
        [[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]],
        dtype="float32",
    )

    M = cv2.getPerspectiveTransform(ordered_pts, dst)
    warped = cv2.warpPerspective(orig_image, M, (maxWidth, maxHeight))

    print("[INFO] STEP 4: Perspective transform applied.")

    # --- 5. Save the Final Image ---
    cv2.imwrite(output_path, warped)
    print(f"[SUCCESS] Cropped and straightened image saved to {output_path}")


if __name__ == "__main__":
    main()
