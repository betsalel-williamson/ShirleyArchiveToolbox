import os
import sys
import json
from typing import Dict
from dotenv import load_dotenv

# --- Load configuration from .env file ---
load_dotenv()

# --- Configuration (Loaded from Environment) ---
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
PROCESSOR_ID = os.getenv("PROCESSOR_ID")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro-preview-0409")

# --- Dependencies (Import) ---
try:
    from google.api_core.client_options import ClientOptions
    from google.cloud import documentai
    from google.cloud.documentai_v1.types import Document
    from PIL import Image
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part
except ImportError:
    print("Error: Required libraries not found.")
    print(
        "Please run: pip install python-dotenv google-cloud-documentai Pillow google-cloud-aiplatform"
    )
    sys.exit(1)


# --- Phase 1: Document AI OCR with Caching ---


def process_with_document_ai(image_path: str) -> Dict:
    """
    Performs OCR using Document AI. Caches the raw Document object to a local
    .json file to avoid re-processing the same image.
    """
    print("--- Phase 1: Document AI Processing ---")

    cache_dir = os.path.join(os.path.dirname(image_path), ".cache")
    os.makedirs(cache_dir, exist_ok=True)
    image_basename = os.path.basename(image_path)
    cache_filename = os.path.join(cache_dir, f"{image_basename}.docai_cache.json")

    document = None

    # Step 1: Check for a cached result
    if os.path.exists(cache_filename):
        print(f"✅ Found DocAI protobuf cache: {cache_filename}. Loading from cache.")
        with open(cache_filename, "r") as f:
            json_string = f.read()
        # Deserialize the JSON string back into a Document object
        document = Document.from_json(json_string)

    # Step 2: If no cache, call the API
    else:
        print("... No cache found. Calling the Document AI API...")
        try:
            opts = ClientOptions(api_endpoint=f"{LOCATION}-documentai.googleapis.com")
            client = documentai.DocumentProcessorServiceClient(client_options=opts)
            name = client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

            with open(image_path, "rb") as image_file:
                image_content = image_file.read()

            raw_document = documentai.RawDocument(
                content=image_content, mime_type="image/jpeg"
            )
            request = documentai.ProcessRequest(name=name, raw_document=raw_document)

            result = client.process_document(request=request)
            document = result.document

            # Step 3: Save the raw Document object to the cache before returning
            print(
                f"✅ API call successful. Caching raw Document AI result to: {cache_filename}"
            )
            # Serialize the Document object to a JSON string
            json_string = Document.to_json(document)
            with open(cache_filename, "w") as f:
                f.write(json_string)

        except Exception as e:
            print(f"❌ An error occurred during Document AI processing: {e}")
            return None  # Exit the function if the API call fails

    # Step 4: Convert the Document object (from cache or API) to our custom schema
    print("... Converting Document AI result to custom JSON schema.")

    with Image.open(image_path) as img:
        width, height = img.size

    output_data = {
        "page_number": 1,
        "image_source": image_path,
        "image_dimensions": {"width": width, "height": height},
        "lines": [],
        "graphical_elements": [],  # To be populated by Gemini
    }

    text = document.text
    for page in document.pages:
        for i, line in enumerate(page.lines):
            line_data = {"line_id": f"line-{i+1}", "words": []}
            for token in line.tokens:
                # This helper function is safer for extracting text
                def get_text(text_anchor, text):
                    if not text_anchor.text_segments:
                        return ""
                    return "".join(
                        text[int(segment.start_index) : int(segment.end_index)]
                        for segment in text_anchor.text_segments
                    )

                token_text = get_text(token.layout.text_anchor, text)
                vertices = token.layout.bounding_poly.vertices

                style = (
                    "cursive"
                    if token.style_info and token.style_info.handwritten
                    else "pre-printed_sans-serif"
                )

                word_data = {
                    "text": token_text,
                    "bounding_box": {
                        "x_min": min(v.x for v in vertices),
                        "y_min": min(v.y for v in vertices),
                        "x_max": max(v.x for v in vertices),
                        "y_max": max(v.y for v in vertices),
                    },
                    "confidence": (
                        round(token.provenance.confidence, 4)
                        if token.provenance
                        else 0.0
                    ),
                    "writing_style": style,
                    "decoration": {
                        "is_struckthrough": any(
                            d.type_
                            == Document.StyleInfo.TextDecorationType.STRIKETHROUGH
                            for d in (token.style_info.text_decoration or [])
                        ),
                        "is_underlined": any(
                            d.type_ == Document.StyleInfo.TextDecorationType.UNDERLINE
                            for d in (token.style_info.text_decoration or [])
                        ),
                        "is_insertion": False,
                    },
                }
                line_data["words"].append(word_data)
            output_data["lines"].append(line_data)

    return output_data


# --- Phase 2: Gemini Enrichment (No changes needed here) ---
def enrich_with_gemini(image_path: str, initial_json: Dict) -> Dict:
    """Uses Gemini to enrich the initial JSON with contextual details."""
    # This function remains unchanged.
    print("\n--- Phase 2: Gemini Enrichment ---")
    print("... Calling the Gemini API for contextual analysis...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = GenerativeModel(GEMINI_MODEL_NAME)
    prompt = """
    You are an expert document analyst. Your task is to enrich an existing OCR transcription.
    You will be given an image of a diary page and a JSON object representing the text that has already been transcribed.
    Analyze the image carefully and update the provided JSON with the following information:
    1.  **Graphical Elements:** Look for any non-text elements like doodles, drawings, scribbles, or stains. For each one you find, add an object to the `graphical_elements` array. Describe the element and provide an *approximate* bounding box.
    2.  **Insertions:** Look for any words that appear to be written between the main lines of text. If you find one, update the corresponding word in the JSON by setting its `is_insertion` flag to `true`.
    Return **only** the complete, updated JSON object as a single JSON code block. Do not add any commentary or explanation outside of the JSON.
    """
    with open(image_path, "rb") as f:
        image_data = f.read()
    image_part = Part.from_data(data=image_data, mime_type="image/jpeg")
    json_part = Part.from_text(json.dumps(initial_json, indent=2))
    response = model.generate_content(
        [prompt, image_part, json_part],
        generation_config={"response_mime_type": "application/json"},
    )
    try:
        enriched_data = response.candidates[0].content.parts[0].text
        print("✅ Gemini enrichment successful.")
        return json.loads(enriched_data)
    except (json.JSONDecodeError, AttributeError, IndexError) as e:
        print(f"❌ Error parsing Gemini response: {e}")
        print(
            "--- Gemini Raw Response ---\n",
            response.text,
            "\n---------------------------",
        )
        return initial_json


# --- Main Application Logic (No changes needed here) ---
def main():
    """Main function to orchestrate the processing."""
    # This function remains unchanged.
    required_vars = ["PROJECT_ID", "LOCATION", "PROCESSOR_ID"]
    missing_vars = [var for var in required_vars if not globals()[var]]
    if missing_vars:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(
            f"!!! ERROR: Missing required environment variables: {', '.join(missing_vars)}"
        )
        print("!!! Please create a .env file and add these values.       !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        sys.exit(1)
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <path_to_your_image.jpg>")
        sys.exit(1)
    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at '{image_path}'")
        sys.exit(1)
    doc_ai_result = process_with_document_ai(image_path)
    if doc_ai_result is None:
        print("Halting execution due to error in Document AI phase.")
        sys.exit(1)
    final_result = enrich_with_gemini(image_path, doc_ai_result)
    image_basename = os.path.basename(image_path)
    final_filename = f"{image_basename}.final.json"
    print(f"\n✅ All phases complete. Saving final enriched data to: {final_filename}")
    with open(final_filename, "w") as f:
        json.dump(final_result, f, indent=2)
    print("\nFinal Result:")
    print(json.dumps(final_result, indent=2))


if __name__ == "__main__":
    main()
