import os
import sys
import json
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

# --- Configuration (Loaded from Environment) ---
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
PROCESSOR_ID = os.getenv("PROCESSOR_ID")
# Provide a default model name if it's not in the .env file
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")

# --- Dependencies (Import) ---
from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from google.cloud.documentai_v1.types import Document
from PIL import Image

import vertexai
from vertexai.generative_models import GenerativeModel, Part

# --- Phase 1: Document AI OCR with Caching ---

def process_with_document_ai(image_path: str) -> Dict:
    """
    Performs OCR using Document AI. Caches the result to a local .json file
    to avoid re-processing the same image.
    """
    print("--- Phase 1: Document AI Processing ---")

    # Generate a unique cache filename based on the image path
    cache_dir = os.path.join(os.path.dirname(image_path), ".cache")
    os.makedirs(cache_dir, exist_ok=True)
    image_basename = os.path.basename(image_path)
    cache_filename = os.path.join(cache_dir, f"{image_basename}.docai_cache.json")

    # 1. Check if a cached result exists
    if os.path.exists(cache_filename):
        print(f"✅ Found cache file: {cache_filename}. Loading from cache.")
        with open(cache_filename, "r") as f:
            return json.load(f)

    # 2. If no cache, call the API
    print("... No cache found. Calling the Document AI API...")

    # Configure the client
    opts = ClientOptions(api_endpoint=f"{LOCATION}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    name = client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

    # Load the image
    with open(image_path, "rb") as image_file:
        image_content = image_file.read()

    # Get image dimensions
    with Image.open(image_path) as img:
        width, height = img.size

    # Call the API
    raw_document = documentai.RawDocument(content=image_content, mime_type="image/jpeg")
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)
    result = client.process_document(request=request)
    document = result.document

    # 3. Convert the API response to our custom JSON schema
    # (This is a simplified version of your schema for clarity)
    output_data = {
        "page_number": 1, # Assuming page 1
        "image_source": image_path,
        "image_dimensions": {"width": width, "height": height},
        "lines": [],
        "graphical_elements": [], # Will be populated by Gemini later
    }

    text = document.text
    for page in document.pages:
        for i, line in enumerate(page.lines):
            line_data = {"line_id": f"line-{i+1}", "words": []}
            for token in line.tokens:
                token_text = text[int(token.layout.text_anchor.text_segments[0].start_index): int(token.layout.text_anchor.text_segments[0].end_index)]
                vertices = token.layout.bounding_poly.vertices

                # Determine writing style
                style = "cursive" if token.style_info and token.style_info.handwritten else "pre-printed_sans-serif"

                word_data = {
                    "text": token_text,
                    "bounding_box": {"x_min": min(v.x for v in vertices), "y_min": min(v.y for v in vertices), "x_max": max(v.x for v in vertices), "y_max": max(v.y for v in vertices)},
                    "confidence": round(token.provenance.confidence, 4),
                    "writing_style": style,
                    "decoration": {
                        "is_struckthrough": any(d.type_ == Document.StyleInfo.TextDecorationType.STRIKETHROUGH for d in token.style_info.text_decoration),
                        "is_underlined": any(d.type_ == Document.StyleInfo.TextDecorationType.UNDERLINE for d in token.style_info.text_decoration),
                        "is_insertion": False # To be enriched by Gemini
                    }
                }
                line_data["words"].append(word_data)
            output_data["lines"].append(line_data)

    # 4. Save the result to the cache file before returning
    print(f"✅ API call successful. Saving result to cache: {cache_filename}")
    with open(cache_filename, "w") as f:
        json.dump(output_data, f, indent=2)

    return output_data

# --- Phase 2: Gemini Enrichment ---

def enrich_with_gemini(image_path: str, initial_json: Dict) -> Dict:
    """
    Uses Gemini 1.5 Pro to enrich the initial JSON with contextual details
    by analyzing the image.
    """
    print("\n--- Phase 2: Gemini Enrichment ---")
    print("... Calling the Gemini API for contextual analysis...")

    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = GenerativeModel(GEMINI_MODEL_NAME)

    # The prompt instructs Gemini on its role: act as an analyst to enrich existing data.
    prompt = """
    You are an expert document analyst. Your task is to enrich an existing OCR transcription.
    You will be given an image of a diary page and a JSON object representing the text that has already been transcribed.

    Analyze the image carefully and update the provided JSON with the following information:
    1.  **Graphical Elements:** Look for any non-text elements like doodles, drawings, scribbles, or stains. For each one you find, add an object to the `graphical_elements` array. Describe the element and provide an *approximate* bounding box.
    2.  **Insertions:** Look for any words that appear to be written between the main lines of text. If you find one, update the corresponding word in the JSON by setting its `is_insertion` flag to `true`.

    Return **only** the complete, updated JSON object as a single block of code. Do not add any commentary or explanation outside of the JSON.
    """

    # Load the image data
    with open(image_path, "rb") as f:
        image_data = f.read()

    image_part = Part.from_data(data=image_data, mime_type="image/jpeg")
    json_part = Part.from_text(json.dumps(initial_json, indent=2))

    # Generate the content
    response = model.generate_content([prompt, image_part, json_part])

    # Clean and parse the response
    try:
        # Gemini often wraps its response in ```json ... ```
        cleaned_response = response.text.strip().removeprefix("```json").removesuffix("```").strip()
        enriched_data = json.loads(cleaned_response)
        print("✅ Gemini enrichment successful.")
        return enriched_data
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"❌ Error parsing Gemini response: {e}")
        print("--- Gemini Raw Response ---")
        print(response.text)
        print("---------------------------")
        return initial_json # Return the original data on failure

# --- Main Application Logic ---

if __name__ == "__main__":
    if PROJECT_ID == "your-gcp-project-id" or PROCESSOR_ID == "your-processor-id":
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! PLEASE UPDATE PROJECT_ID and PROCESSOR_ID IN THE SCRIPT !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        sys.exit(1)

    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <path_to_your_image.jpg>")
        sys.exit(1)

    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at '{image_path}'")
        sys.exit(1)

    # Run Phase 1
    doc_ai_result = process_with_document_ai(image_path)

    # Run Phase 2
    final_result = enrich_with_gemini(image_path, doc_ai_result)

    # Save the final enriched result
    image_basename = os.path.basename(image_path)
    final_filename = f"{image_basename}.final.json"
    print(f"\n✅ All phases complete. Saving final enriched data to: {final_filename}")
    with open(final_filename, "w") as f:
        json.dump(final_result, f, indent=2)

    print("\nFinal Result:")
    print(json.dumps(final_result, indent=2))