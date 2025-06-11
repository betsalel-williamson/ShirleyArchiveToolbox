import os
import sys
import json
import time
import argparse
import logging
import functools
from typing import Dict, Optional, Callable, Any
from dotenv import load_dotenv

# --- Dependencies (with error handling) ---
try:
    from google.api_core.client_options import ClientOptions
    from google.cloud import documentai
    from google.cloud.documentai_v1.types import Document
    from PIL import Image
    import google.generativeai as genai
    from google.generativeai import protos as genai_protos
    from google.api_core import exceptions as google_exceptions
except ImportError:
    logging.critical("Error: Required libraries not found.")
    logging.critical(
        "Please run: pip install python-dotenv google-cloud-documentai Pillow google-generativeai"
    )
    sys.exit(1)


# ==============================================================================
# --- CACHING DECORATOR ---
# ==============================================================================


def cache_to_file(
    cache_suffix: str, serializer: Callable, deserializer: Callable
) -> Callable:
    """
    A generic decorator to cache the output of a function to a file.
    The wrapped function must accept 'image_path' as a keyword argument.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Optional[Any]:
            image_path = kwargs.get("image_path")
            if not image_path:
                raise ValueError(
                    "Cached function must be called with 'image_path' keyword argument."
                )

            image_basename = os.path.basename(image_path)
            cache_dir = ".cache"
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, f"{image_basename}{cache_suffix}")

            # Check for and load from cache
            if os.path.exists(cache_path):
                logging.info(f"Found cache: {cache_path}. Loading.")
                with open(cache_path, "r") as f:
                    return deserializer(f.read())

            # If no cache, execute the function
            logging.info(
                f"No cache found at {cache_path}. Executing function '{func.__name__}'."
            )
            result = func(*args, **kwargs)

            # Save the result to cache if it's not None
            if result:
                logging.info(f"Caching result to: {cache_path}")
                with open(cache_path, "w") as f:
                    f.write(serializer(result))

            return result

        return wrapper

    return decorator


# ==============================================================================
# --- PROCESSING PIPELINE FUNCTIONS ---
# ==============================================================================


@cache_to_file(
    ".docai_cache.json", serializer=Document.to_json, deserializer=Document.from_json
)
def call_doc_ai_api(*, config: Dict, image_path: str) -> Optional[Document]:
    """
    Step 1a: Calls the Document AI API. This function is decorated for caching.
    """
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
    """
    Step 1b: Transforms a raw Document AI object into the project's custom JSON schema.
    """
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
                }
                line_data["words"].append(word_data)
            output_data["lines"].append(line_data)
    return output_data


@cache_to_file(".gemini_cache.json", serializer=json.dumps, deserializer=json.loads)
def call_gemini_api(
    *, config: Dict, image_path: str, initial_json: Dict, schema: Dict
) -> Optional[Dict]:
    """
    Step 2: Calls the Gemini API for enrichment. This function is decorated for caching.
    """
    genai.configure(api_key=config["gemini_api_key"])
    model = genai.GenerativeModel(config["gemini_model_name"])
    system_prompt = "You are an expert document analyst. Your task is to enrich an existing OCR transcription. Analyze the provided image and JSON, then update the JSON with graphical elements and insertions you find. Adhere strictly to the provided schema and return the complete, updated JSON."
    gemini_schema = genai_protos.Schema(**_convert_json_schema_to_gemini_schema(schema))
    with open(image_path, "rb") as f:
        image_data = f.read()
    image_part = genai_protos.Part(
        inline_data=genai_protos.Blob(mime_type="image/jpeg", data=image_data)
    )
    prompt_parts = [system_prompt, json.dumps(initial_json, indent=2), image_part]
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=gemini_schema,
        max_output_tokens=8192,
    )

    try:
        response = model.generate_content(
            prompt_parts, generation_config=generation_config
        )
        logging.info("Gemini API call successful.")
        return json.loads(response.text)
    except google_exceptions.ResourceExhausted as e:
        logging.warning(f"Rate limit exceeded. Waiting 60s. Error: {e}")
        time.sleep(60)
        return None
    except (json.JSONDecodeError, AttributeError, ValueError) as e:
        logging.error(f"Failed to decode Gemini JSON response: {e}", exc_info=True)
        try:
            logging.error(f"Problematic API Response Text:\n---\n{response.text}\n---")
        except NameError:
            pass
        return None


def _convert_json_schema_to_gemini_schema(json_dict: dict) -> Dict:
    """Helper to recursively convert a JSON Schema dict to a Gemini-compatible dict."""
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


# ==============================================================================
# --- MAIN COORDINATOR ---
# ==============================================================================


def main_coordinator(image_path: str, force_recache: bool) -> int:
    """
    Main pipeline coordinator that calls processing functions and returns an exit code.
    Returns 0 on success, and a non-zero integer on failure.
    """
    try:
        config = load_config()

        if force_recache:
            logging.warning(
                "User requested --force-recache. Deleting existing cache files."
            )
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

        # --- Phase 1 ---
        logging.info("--- Phase 1: Document AI Transcription ---")
        raw_document = call_doc_ai_api(config=config, image_path=image_path)
        if not raw_document:
            raise ValueError("Failed to get Document AI result (from API or cache).")

        initial_transcription = transform_doc_ai_to_custom_json(
            document=raw_document, image_path=image_path
        )

        # --- Phase 2 ---
        logging.info("--- Phase 2: Gemini Enrichment ---")
        final_result = call_gemini_api(
            config=config,
            image_path=image_path,
            initial_json=initial_transcription,
            schema=FINAL_OUTPUT_SCHEMA,
        )
        if not final_result:
            raise ValueError("Failed to get Gemini result (from API or cache).")

        # --- Save Final Result ---
        image_basename = os.path.basename(image_path)
        final_filename = f"{image_basename}.final.json"
        logging.info(
            f"All phases complete. Saving final enriched data to: {final_filename}"
        )
        with open(final_filename, "w") as f:
            json.dump(final_result, f, indent=2)

        return 0  # Success

    except FileNotFoundError as e:
        logging.error(f"Input file not found: {e}")
        return 2
    except ValueError as e:
        logging.error(f"Processing error: {e}")
        return 3
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return 1


# ==============================================================================
# --- ARGUMENT PARSING AND EXECUTION ---
# ==============================================================================

if __name__ == "__main__":
    # --- Load Configuration ---
    # This must be defined before the parser to use it for defaults
    # For now, we will just hardcode the schema
    FINAL_OUTPUT_SCHEMA = {
        "description": "Represents the complete, structured transcription of a single journal page, enhanced to capture writing styles, decorations, and graphical elements.",
        "type": "OBJECT",
        "required": [
            "page_number",
            "image_source",
            "image_dimensions",
            "lines",
            "graphical_elements",
        ],
        "properties": {
            "page_number": {
                "description": "The sequential number of the page in the journal. Use 0 for the cover/front matter.",
                "type": "INTEGER",
            },
            "image_source": {
                "description": "The filename or URL of the source page image.",
                "type": "STRING",
            },
            "image_dimensions": {
                "type": "OBJECT",
                "required": ["width", "height"],
                "properties": {
                    "width": {"type": "INTEGER"},
                    "height": {"type": "INTEGER"},
                },
            },
            "lines": {
                "description": "An ordered array of transcribed text lines found on the page.",
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "required": ["line_id", "words"],
                    "properties": {
                        "line_id": {
                            "description": "A unique identifier for the line within the page (e.g., 'line-1', 'line-2').",
                            "type": "STRING",
                        },
                        "words": {
                            "description": "An ordered array of the words transcribed on this line.",
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "required": [
                                    "text",
                                    "bounding_box",
                                    "confidence",
                                    "status",
                                    "writing_style",
                                ],
                                "properties": {
                                    "text": {
                                        "description": "The transcribed text of the word. For illegible words, this should be '[illegible]'.",
                                        "type": "STRING",
                                    },
                                    "bounding_box": {
                                        "description": "The coordinates of a rectangular box, with the origin (0,0) at the top-left corner of the page.",
                                        "type": "OBJECT",
                                        "required": [
                                            "x_min",
                                            "y_min",
                                            "x_max",
                                            "y_max",
                                        ],
                                        "properties": {
                                            "x_min": {"type": "INTEGER"},
                                            "y_min": {"type": "INTEGER"},
                                            "x_max": {"type": "INTEGER"},
                                            "y_max": {"type": "INTEGER"},
                                        },
                                    },
                                    "confidence": {
                                        "description": "The model's confidence in the accuracy of the transcription, from 0.0 (uncertain) to 1.0 (certain).",
                                        "type": "NUMBER",
                                        "format": "float",
                                    },
                                    "status": {
                                        "description": "The confidence status of the transcription for a single word.",
                                        "type": "STRING",
                                        "enum": [
                                            "Transcribed",
                                            "Hypothesized",
                                            "Illegible",
                                        ],
                                    },
                                    "writing_style": {
                                        "description": "The style of writing for a given word.",
                                        "type": "STRING",
                                        "enum": [
                                            "cursive",
                                            "print",
                                            "pre-printed_serif",
                                            "pre-printed_sans-serif",
                                            "pre-printed_script",
                                            "shorthand",
                                            "unknown",
                                        ],
                                    },
                                    "decoration": {
                                        "description": "Describes visual decorations applied to a word.",
                                        "type": "OBJECT",
                                        "properties": {
                                            "is_struckthrough": {"type": "BOOLEAN"},
                                            "is_underlined": {"type": "BOOLEAN"},
                                            "is_insertion": {
                                                "type": "BOOLEAN",
                                                "description": "True if this word was inserted above or below the main line of text.",
                                            },
                                            "ink_color": {"type": "STRING"},
                                            "notes": {
                                                "type": "STRING",
                                                "description": "Note for complex decorations, e.g., 'Scribble underline.' or 'Inserted above ''FIVE'''.",
                                            },
                                        },
                                    },
                                    "alternatives": {
                                        "description": "An optional list of alternative transcriptions, used for hypothesized or low-confidence words.",
                                        "type": "ARRAY",
                                        "items": {"type": "STRING"},
                                    },
                                },
                            },
                        },
                    },
                },
            },
            "graphical_elements": {
                "description": "An array of non-textual graphical elements on the page.",
                "type": "ARRAY",
                "items": {
                    "description": "A non-textual element on the page.",
                    "type": "OBJECT",
                    "required": ["element_type", "bounding_box"],
                    "properties": {
                        "element_type": {
                            "type": "STRING",
                            "enum": ["stamp", "doodle", "scribble", "drawing", "stain"],
                        },
                        "bounding_box": {
                            "description": "The coordinates of a rectangular box, with the origin (0,0) at the top-left corner of the page.",
                            "type": "OBJECT",
                            "required": ["x_min", "y_min", "x_max", "y_max"],
                            "properties": {
                                "x_min": {"type": "INTEGER"},
                                "y_min": {"type": "INTEGER"},
                                "x_max": {"type": "INTEGER"},
                                "y_max": {"type": "INTEGER"},
                            },
                        },
                        "description": {
                            "type": "STRING",
                            "description": "A brief description of the element.",
                        },
                    },
                },
            },
        },
    }

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
            logging.critical(
                "!!! ERROR: GEMINI_API_KEY not found in .env file. Please get a key from Google AI Studio."
            )
            sys.exit(1)
        return config

    parser = argparse.ArgumentParser(
        description="A two-phase tool to transcribe and analyze diary pages using Google AI."
    )
    parser.add_argument(
        "-i", "--image", required=True, help="Path to the input image file."
    )
    parser.add_argument(
        "--force-recache",
        action="store_true",
        help="Delete existing cache files for this image before processing.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose INFO-level logging to the console.",
    )
    args = parser.parse_args()

    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="[%(levelname)s] %(message)s")

    exit_code = main_coordinator(
        image_path=args.image, force_recache=args.force_recache
    )

    sys.exit(exit_code)
