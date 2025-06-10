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
    # The order is: top-left, top-right, bottom-right, bottom-left
    rect = np.zeros((4, 2), dtype="float32")

    # The top-left point will have the smallest sum (x+y), whereas
    # the bottom-right point will have the largest sum.
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # The top-right point will have the smallest difference (y-x),
    # whereas the bottom-left will have the largest difference.
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    # Return the ordered coordinates
    return rect

def main():
    # --- 1. Set up Argument Parser ---
    # This makes our script a real command-line tool.
    ap = argparse.ArgumentParser(description="Auto-crop and straighten a document from an image.")
    ap.add_argument("-i", "--image", required=True, help="Path to the input image")
    ap.add_argument("-o", "--output", required=True, help="Path for the output cropped image")
    args = vars(ap.parse_args())

    image_path = args["image"]
    output_path = args["output"]

    # --- 2. Load and Pre-process the Image ---
    print("[INFO] Loading image and starting pre-processing...")
    image = cv2.imread(image_path)
    if image is None:
        print(f"[ERROR] Could not load image from path: {image_path}")
        return

    # Keep a copy of the original image for the final transformation
    orig_image = image.copy()

    # Resize for faster processing, preserving aspect ratio
    ratio = image.shape[0] / 500.0
    image = cv2.resize(image, (int(image.shape[1] / ratio), 500))

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to reduce high-frequency noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Use Canny edge detection to find the outlines
    edged = cv2.Canny(blurred, 75, 200)

    print("[INFO] STEP 1: Edge Detection complete.")

    # --- 3. Find the Document Contour ---
    print("[INFO] STEP 2: Finding document contour...")
    # Find contours in the edged image, keeping only the largest ones
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    # Sort contours by area in descending order and keep the top 5
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    screenCnt = None # This will hold our document contour

    # Loop over the sorted contours
    for c in contours:
        # Approximate the contour shape
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        # If our approximated contour has four points, we can
        # assume that we have found our screen (the document)
        if len(approx) == 4:
            screenCnt = approx
            break

    if screenCnt is None:
        print("[ERROR] No 4-point document contour found. Try adjusting Canny thresholds or check image quality.")
        return

    print("[INFO] STEP 3: Document contour found.")

    # For visualization, draw the found contour on the resized image
    cv2.drawContours(image, [screenCnt], -1, (0, 255, 0), 2)

    # Save the image with the detected contour for debugging
    detected_path = output_path.replace('.jpg', '_detected.jpg').replace('.png', '_detected.png')
    cv2.imwrite(detected_path, image)
    print(f"[INFO] Saved detection visualization to {detected_path}")


    # --- 4. Apply Perspective Transform and Crop ---
    # The contour points need to be scaled back to the original image size
    # screenCnt now contains the 4 corner points of the document
    ordered_pts = order_points(screenCnt.reshape(4, 2) * ratio)
    (tl, tr, br, bl) = ordered_pts

    # Calculate the width of the new image
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    # Calculate the height of the new image
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    # Define the destination points for the top-down view
    # This creates a new rectangle with the calculated max width and height
    dst = np.array([
        [0, 0],                  # Top-left
        [maxWidth - 1, 0],       # Top-right
        [maxWidth - 1, maxHeight - 1], # Bottom-right
        [0, maxHeight - 1]],     # Bottom-left
        dtype="float32")

    # Get the perspective transformation matrix
    M = cv2.getPerspectiveTransform(ordered_pts, dst)

    # Apply the transformation to the *original* image
    warped = cv2.warpPerspective(orig_image, M, (maxWidth, maxHeight))

    print("[INFO] STEP 4: Perspective transform applied.")

    # --- 5. Save the Final Image ---
    cv2.imwrite(output_path, warped)
    print(f"[SUCCESS] Cropped and straightened image saved to {output_path}")

if __name__ == "__main__":
    main()