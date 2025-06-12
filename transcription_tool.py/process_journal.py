import os
import sys
import json
import time
import argparse
import logging
import functools
from typing import Dict, Optional, Callable, Any, List
from dotenv import load_dotenv

# --- Dependencies ---
try:
    from google.api_core.client_options import ClientOptions
    from google.cloud import documentai
    from google.cloud.documentai_v1.types import Document
    from PIL import Image
    import google.generativeai as genai
    from google.generativeai import protos as genai_protos
    from google.api_core import exceptions as google_exceptions
except ImportError:
    logging.critical(
        "Error: Required libraries not found. Please run: pip install -r requirements.txt"
    )
    sys.exit(1)


# ==============================================================================
# --- CACHING DECORATOR & SCHEMA DEFINITIONS ---
# ==============================================================================


def cache_to_file(
    cache_suffix: str, serializer: Callable, deserializer: Callable
) -> Callable:
    """A generic decorator to cache the output of a function to a file."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Optional[Any]:
            image_path = kwargs.get("image_path")
            if not image_path:
                raise ValueError("Cached function must have 'image_path' kwarg.")
            image_basename = os.path.basename(image_path)
            cache_dir = ".cache"
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, f"{image_basename}{cache_suffix}")
            if os.path.exists(cache_path):
                logging.info(f"Found cache: {cache_path}. Loading.")
                with open(cache_path, "r") as f:
                    return deserializer(f.read())
            logging.info(
                f"No cache found at {cache_path}. Executing '{func.__name__}'."
            )
            result = func(*args, **kwargs)
            if result:
                logging.info(f"Caching result to: {cache_path}")
                with open(cache_path, "w") as f:
                    f.write(serializer(result))
            return result

        return wrapper

    return decorator


# This is the final, complete schema our script will produce
FINAL_OUTPUT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "page_number": {"type": "INTEGER"},
        "image_source": {"type": "STRING"},
        "image_dimensions": {
            "type": "OBJECT",
            "properties": {"width": {"type": "INTEGER"}, "height": {"type": "INTEGER"}},
        },
        "lines": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "line_id": {"type": "STRING"},
                    "words": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "text": {"type": "STRING"},
                                "bounding_box": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "x_min": {"type": "INTEGER"},
                                        "y_min": {"type": "INTEGER"},
                                        "x_max": {"type": "INTEGER"},
                                        "y_max": {"type": "INTEGER"},
                                    },
                                },
                                "confidence": {"type": "NUMBER"},
                                "writing_style": {"type": "STRING"},
                                "decoration": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "is_struckthrough": {"type": "BOOLEAN"},
                                        "is_underlined": {"type": "BOOLEAN"},
                                        "is_insertion": {"type": "BOOLEAN"},
                                    },
                                },
                                "alternatives": {
                                    "type": "ARRAY",
                                    "items": {"type": "STRING"},
                                    "description": "Alternative transcriptions suggested by the LLM for low-confidence words.",
                                },
                                "ink_color": {
                                    "type": "STRING",
                                    "description": "e.g., 'blue', 'black', 'faded black'",
                                },
                                "style_notes": {
                                    "type": "STRING",
                                    "description": "Qualitative observations like 'heavy pressure', 'written quickly', 'shaky'.",
                                },
                            },
                        },
                    },
                },
            },
        },
        "graphical_elements": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "element_type": {
                        "type": "STRING",
                        "description": "e.g., 'doodle', 'stain', 'scribble'",
                    },
                    "bounding_box": {
                        "type": "OBJECT",
                        "properties": {
                            "x_min": {"type": "INTEGER"},
                            "y_min": {"type": "INTEGER"},
                            "x_max": {"type": "INTEGER"},
                            "y_max": {"type": "INTEGER"},
                        },
                    },
                    "description": {
                        "type": "STRING",
                        "description": "A brief text description of the element.",
                    },
                },
            },
        },
    },
}

# This is the smaller, targeted schema we ask GEMINI to return.
GEMINI_AUGMENTATION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "word_augmentations": {
            "type": "ARRAY",
            "description": "An array of augmentations for specific words on the page.",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "line_id": {
                        "type": "STRING",
                        "description": "The ID of the line containing the word.",
                    },
                    "original_text": {
                        "type": "STRING",
                        "description": "The original text of the word being augmented.",
                    },
                    "alternatives": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Suggested alternative transcriptions if the original was low-confidence.",
                    },
                    "ink_color": {
                        "type": "STRING",
                        "description": "The color of the ink used for this word.",
                    },
                    "style_notes": {
                        "type": "STRING",
                        "description": "Qualitative observations like 'heavy pressure', 'written quickly', 'shaky'.",
                    },
                },
            },
        },
        "graphical_elements": {
            "type": "ARRAY",
            "description": "An array of non-textual graphical elements found on the page.",
            "items": FINAL_OUTPUT_SCHEMA["properties"]["graphical_elements"][
                "items"
            ],  # Reuse from the final schema
        },
    },
}


# ==============================================================================
# --- PIPELINE FUNCTIONS ---
# ==============================================================================


@cache_to_file(
    ".docai_cache.json", serializer=Document.to_json, deserializer=Document.from_json
)
def call_doc_ai_api(*, config: Dict, image_path: str) -> Optional[Document]:
    """Step 1a: Calls the Document AI API. This function is decorated for caching."""
    # ... (code is unchanged)
    try:
        opts = ClientOptions(
            api_endpoint=f"{config['location']}-documentai.googleapis.com"
        )
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
        name = client.processor_path(
            config["project_id"], config["location"], config["processor_id"]
        )
        with open(image_path, "rb") as f:
            image_content = f.read()
        raw_document = documentai.RawDocument(
            content=image_content, mime_type="image/jpeg"
        )
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)
        result = client.process_document(request=request)
        logging.info("Document AI API call successful.")
        return result.document
    except Exception as e:
        logging.error(
            f"An error occurred during Document AI API call: {e}", exc_info=True
        )
        return None


def transform_doc_ai_to_custom_json(*, document: Document, image_path: str) -> Dict:
    """Step 1b: Transforms a raw Document AI object into the project's custom JSON schema."""
    # ... (code has minor changes to add new empty fields)
    logging.info("Transforming raw Document AI data into custom JSON schema.")
    with Image.open(image_path) as img:
        width, height = img.size
    output_data = {
        "page_number": 1,
        "image_source": image_path,
        "image_dimensions": {"width": width, "height": height},
        "lines": [],
        "graphical_elements": [],
    }
    text = document.text
    for page_index, page in enumerate(document.pages):
        page_tokens = page.tokens
        for line_index, line in enumerate(page.lines):
            line_data = {"line_id": f"p{page_index+1}-l{line_index+1}", "words": []}
            line_start = line.layout.text_anchor.text_segments[0].start_index
            line_end = line.layout.text_anchor.text_segments[0].end_index
            current_line_tokens = [
                token
                for token in page_tokens
                if line_start
                <= token.layout.text_anchor.text_segments[0].start_index
                < line_end
            ]
            for token in current_line_tokens:
                style_info = token.style_info
                decorations = (
                    getattr(style_info, "text_decoration", []) if style_info else []
                )
                word_data = {
                    "text": "".join(
                        text[int(s.start_index) : int(s.end_index)]
                        for s in token.layout.text_anchor.text_segments
                    ),
                    "bounding_box": {
                        "x_min": min(v.x for v in token.layout.bounding_poly.vertices),
                        "y_min": min(v.y for v in token.layout.bounding_poly.vertices),
                        "x_max": max(v.x for v in token.layout.bounding_poly.vertices),
                        "y_max": max(v.y for v in token.layout.bounding_poly.vertices),
                    },
                    "confidence": (
                        round(token.provenance.confidence, 4)
                        if token.provenance
                        else 0.0
                    ),
                    "writing_style": (
                        "cursive"
                        if style_info and style_info.handwritten
                        else "pre-printed_sans-serif"
                    ),
                    "decoration": {
                        "is_struckthrough": any(
                            d.type_ == "STRIKETHROUGH" for d in decorations
                        ),
                        "is_underlined": any(
                            d.type_ == "UNDERLINE" for d in decorations
                        ),
                        "is_insertion": False,
                    },
                    "alternatives": [],
                    "ink_color": None,
                    "style_notes": None,
                }
                line_data["words"].append(word_data)
            output_data["lines"].append(line_data)
    return output_data


def find_low_confidence_words(
    transcription: Dict, threshold: float = 0.90
) -> List[Dict]:
    """Step 2a: Finds words with confidence below a threshold to ask Gemini about."""
    low_conf_words = []
    for line in transcription.get("lines", []):
        for word in line.get("words", []):
            if word.get("confidence", 1.0) < threshold:
                low_conf_words.append(
                    {"line_id": line["line_id"], "text": word["text"]}
                )
    logging.info(
        f"Found {len(low_conf_words)} words with confidence below {threshold}."
    )
    return low_conf_words


@cache_to_file(".gemini_cache.json", serializer=json.dumps, deserializer=json.loads)
def call_gemini_api(
    *, config: Dict, image_path: str, low_confidence_words: List[Dict], schema: Dict
) -> Optional[Dict]:
    """Step 2b: Calls Gemini with a targeted request for augmentations."""
    genai.configure(api_key=config["gemini_api_key"])
    model = genai.GenerativeModel(config["gemini_model_name"])

    system_prompt = f"""
    You are a document analysis expert. Analyze the provided image to augment a previous OCR pass.
    1.  For the entire page, identify all non-text graphical elements (doodles, stains).
    2.  For each word on the page, determine its ink color and provide qualitative style notes (e.g., 'heavy pressure', 'rushed').
    3.  I have identified a list of low-confidence words. For these specific words, please suggest likely alternative transcriptions.

    Return ONLY this new information in a JSON object adhering to the requested schema. Do not return the full transcription.

    Low-confidence words to get alternatives for:
    {json.dumps(low_confidence_words, indent=2)}
    """

    gemini_schema = genai_protos.Schema(**_convert_json_schema_to_gemini_schema(schema))
    with open(image_path, "rb") as f:
        image_data = f.read()
    image_part = genai_protos.Part(
        inline_data=genai_protos.Blob(mime_type="image/jpeg", data=image_data)
    )
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=gemini_schema,
        max_output_tokens=8192,
    )

    FINISH_REASON_EXPLANATIONS = {
        1: "OK - The model successfully completed its generation.",
        2: "MAX_TOKENS - The model stopped because it reached the maximum number of output tokens. The response is likely truncated.",
        3: "SAFETY - The model stopped because its response was flagged by the safety filter.",
        4: "RECITATION - The model stopped because its response was flagged for containing recited content from the web.",
        5: "OTHER - The model stopped for an unspecified reason.",
    }

    try:
        response = model.generate_content(
            [system_prompt, image_part], generation_config=generation_config
        )

        if not response.parts:
            finish_reason_code = (
                response.candidates[0].finish_reason if response.candidates else 0
            )
            reason_str = FINISH_REASON_EXPLANATIONS.get(finish_reason_code, "UNKNOWN")
            logging.error(
                f"Gemini response contained no valid parts. Finish Reason: {reason_str} (Code: {finish_reason_code})."
            )
            return None

        logging.info("Gemini API call successful.")
        return json.loads(response.text)
    except Exception as e:
        logging.error(
            f"An unexpected error occurred during Gemini API call: {e}", exc_info=True
        )
        return None


def merge_gemini_augmentations(*, transcription: Dict, augmentations: Dict) -> Dict:
    """Step 3: Merges the augmentation data from Gemini back into the main transcription object."""
    logging.info("Merging Gemini augmentations into the final data structure.")

    # Create a fast lookup map for words: (line_id, original_text) -> word_object
    word_map = {}
    for line in transcription["lines"]:
        for word in line["words"]:
            # To handle duplicate words on the same line, we make the key more unique
            word_key = (line["line_id"], word["text"], word["bounding_box"]["x_min"])
            word_map[word_key] = word

    # Merge word-specific augmentations
    for aug in augmentations.get("word_augmentations", []):
        # Find the word to update. We need to iterate as we don't have the x_min in the augmentation data.
        # This is a trade-off for a smaller prompt.
        for line in transcription["lines"]:
            if line["line_id"] == aug["line_id"]:
                for word in line["words"]:
                    if word["text"] == aug["original_text"]:
                        word["alternatives"] = aug.get("alternatives", [])
                        word["ink_color"] = aug.get("ink_color")
                        word["style_notes"] = aug.get("style_notes")
                        # Break after finding the first match on the line to avoid overwriting duplicates incorrectly
                        break

    # Add graphical elements
    transcription["graphical_elements"] = augmentations.get("graphical_elements", [])

    return transcription


# ==============================================================================
# --- MAIN COORDINATOR & EXECUTION ---
# ==============================================================================


def main_coordinator(image_path: str, force_recache: bool) -> int:
    """Main pipeline coordinator that calls processing functions and returns an exit code."""
    try:
        config = load_config()
        if force_recache:
            logging.warning("User requested --force-recache. Deleting cache files.")
            # ... (cache deletion logic)
            image_basename = os.path.basename(image_path)
            docai_cache_path = os.path.join(
                ".cache", f"{image_basename}.docai_cache.json"
            )
            gemini_cache_path = os.path.join(
                ".cache", f"{image_basename}.gemini_cache.json"
            )
            if os.path.exists(docai_cache_path):
                os.remove(docai_cache_path)
            if os.path.exists(gemini_cache_path):
                os.remove(gemini_cache_path)

        # --- Phase 1: High-Precision OCR ---
        logging.info("--- Phase 1: Document AI Transcription ---")
        raw_document = call_doc_ai_api(config=config, image_path=image_path)
        if not raw_document:
            raise ValueError("Failed to get Document AI result.")
        initial_transcription = transform_doc_ai_to_custom_json(
            document=raw_document, image_path=image_path
        )

        # --- Phase 2: Qualitative Analysis ---
        logging.info("--- Phase 2: Gemini Qualitative Analysis ---")
        low_conf_words = find_low_confidence_words(initial_transcription)
        gemini_augmentations = call_gemini_api(
            config=config,
            image_path=image_path,
            low_confidence_words=low_conf_words,
            schema=GEMINI_AUGMENTATION_SCHEMA,
        )
        if not gemini_augmentations:
            raise ValueError("Failed to get Gemini analysis result.")

        # --- Phase 3: Intelligent Merging ---
        logging.info("--- Phase 3: Merging AI Results ---")
        final_result = merge_gemini_augmentations(
            transcription=initial_transcription, augmentations=gemini_augmentations
        )

        # --- Save Final Result ---
        image_basename = os.path.basename(image_path)
        final_filename = f"{image_basename}.final.json"
        logging.info(
            f"All phases complete. Saving final enriched data to: {final_filename}"
        )
        with open(final_filename, "w") as f:
            json.dump(final_result, f, indent=2)
        return 0

    except Exception as e:
        logging.error(
            f"An unexpected error occurred in the main coordinator: {e}", exc_info=True
        )
        return 1


# --- Helper for schema conversion (unchanged but necessary) ---
def _convert_json_schema_to_gemini_schema(json_dict: dict) -> Dict:
    if not json_dict:
        return None
    type_map = {
        "STRING": "STRING",
        "NUMBER": "NUMBER",
        "INTEGER": "INTEGER",
        "BOOLEAN": "BOOLEAN",
        "ARRAY": "ARRAY",
        "OBJECT": "OBJECT",
    }
    json_type_str = json_dict.get("type", "").upper()
    gemini_type = type_map.get(json_type_str)
    if not gemini_type:
        raise ValueError(f"Unsupported JSON schema type: {json_dict.get('type')}")
    kwargs = {
        "type": gemini_type,
        "description": json_dict.get("description"),
        "format": json_dict.get("format"),
    }
    if gemini_type == "OBJECT" and "properties" in json_dict:
        kwargs["properties"] = {
            k: _convert_json_schema_to_gemini_schema(v)
            for k, v in json_dict["properties"].items()
        }
    if gemini_type == "ARRAY" and "items" in json_dict:
        kwargs["items"] = _convert_json_schema_to_gemini_schema(json_dict["items"])
    return {k: v for k, v in kwargs.items() if v is not None}


if __name__ == "__main__":

    def load_config() -> Dict:
        load_dotenv()
        config = {
            "project_id": os.getenv("PROJECT_ID"),
            "location": os.getenv("LOCATION"),
            "processor_id": os.getenv("PROCESSOR_ID"),
            "gemini_api_key": os.getenv("GEMINI_API_KEY"),
            "gemini_model_name": os.getenv(
                "GEMINI_MODEL_NAME", "gemini-1.5-pro-preview-0409"
            ),
        }
        if not config["gemini_api_key"]:
            logging.critical("!!! ERROR: GEMINI_API_KEY not found in .env file.")
            sys.exit(1)
        return config

    parser = argparse.ArgumentParser(
        description="A three-phase tool to transcribe and analyze diary pages using Google AI."
    )
    parser.add_argument(
        "-i", "--image", required=True, help="Path to the input image file."
    )
    parser.add_argument(
        "--force-recache",
        action="store_true",
        help="Delete existing cache files for this image.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose INFO-level logging."
    )
    args = parser.parse_args()
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="[%(levelname)s] %(message)s")
    exit_code = main_coordinator(
        image_path=args.image, force_recache=args.force_recache
    )
    sys.exit(exit_code)
