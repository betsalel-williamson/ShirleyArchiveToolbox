import cv2
import numpy as np
import argparse


def order_points(pts):
    """
    Initializes a list of coordinates that will be ordered such that
    the first entry in the list is the top-left, the second entry
    is the top-right, the third is the bottom-right, and the fourth
    is the bottom-left.
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

    # --- PRO-TIP: Make the outline more robust ---
    # The Canny edges can be disconnected. Dilation helps to close these gaps.
    print("[INFO] Applying dilation to close gaps in edges...")
    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(edged, kernel, iterations=1)

    # --- 3. Find the Document Contour ---
    print("[INFO] STEP 2: Finding document contour...")
    # Find contours in the DILATED image, not the original edged one.
    contours, _ = cv2.findContours(
        dilated.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    screenCnt = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            screenCnt = approx
            break

    if screenCnt is None:
        print(
            "[ERROR] No 4-point document contour found. This can happen with complex backgrounds or lighting."
        )
        print(
            "[DEBUG] To see why it failed, check the 'edged' and 'dilated' intermediate images."
        )
        # Save intermediate steps for debugging
        cv2.imwrite(output_path.replace(".jpg", "_edged.jpg"), edged)
        cv2.imwrite(output_path.replace(".jpg", "_dilated.jpg"), dilated)
        return

    print("[INFO] STEP 3: Document contour found.")

    detected_path = output_path.replace(".jpg", "_detected.jpg").replace(
        ".png", "_detected.png"
    )
    cv2.drawContours(image, [screenCnt], -1, (0, 255, 0), 2)
    cv2.imwrite(detected_path, image)
    print(f"[INFO] Saved detection visualization to {detected_path}")

    # --- 4. Apply Perspective Transform and Crop ---
    ordered_pts = order_points(screenCnt.reshape(4, 2) * ratio)
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
