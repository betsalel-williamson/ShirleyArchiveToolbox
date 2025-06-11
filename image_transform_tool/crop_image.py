from PIL import Image


def crop_image_with_coords(image_path, coords, output_path):
    """
    Crops an image using the provided coordinates.

    Args:
        image_path (str): The path to the original image.
        coords (tuple): A tuple of (left, upper, right, lower) coordinates.
        output_path (str): The path to save the cropped image.
    """
    try:
        # Open the original image
        with Image.open(image_path) as img:
            # Crop the image
            cropped_img = img.crop(coords)

            # Save the cropped image
            cropped_img.save(output_path)
            print(f"Image successfully cropped and saved to '{output_path}'")

    except FileNotFoundError:
        print(f"Error: The file '{image_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


# --- Configuration ---
# Replace 'original_image.jpg' with the actual name of your image file.
input_filename = "image00005.jpg"

# The coordinates [x_min, y_min, x_max, y_max] for the crop
crop_coordinates = (191, 321, 871, 839)

# The name for your new cropped image file.
output_filename = "cropped_image.jpg"

# --- Run the script ---
crop_image_with_coords(input_filename, crop_coordinates, output_filename)
