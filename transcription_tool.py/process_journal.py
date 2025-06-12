import os
import sys
import json
import time
import argparse
import logging
import functools
import hashlib
import shutil
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
            cache_dir = ".cache"
            image_basename = os.path.basename(image_path)
            cache_path = os.path.join(cache_dir, f"{image_basename}{cache_suffix}")
            if kwargs.get("force_recache"):
                if os.path.exists(cache_path):
                    logging.warning(f"Force recache requested. Deleting {cache_path}")
                    os.remove(cache_path)
            if os.path.exists(cache_path):
                logging.info(f"Found cache: {cache_path}. Loading.")
                with open(cache_path, "r") as f:
                    return deserializer(f.read())
            logging.info(
                f"No cache found at {cache_path}. Executing '{func.__name__}'."
            )
            result = func(*args, **kwargs)
            if result:
                os.makedirs(cache_dir, exist_ok=True)
                logging.info(f"Caching result to: {cache_path}")
                with open(cache_path, "w") as f:
                    f.write(serializer(result))
            return result

        return wrapper

    return decorator


# ... (Schemas are unchanged)
FINAL_OUTPUT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "page_number": {"type": "INTEGER"},
        "image_source": {"type": "STRING"},
        "page_analysis": {
            "type": "OBJECT",
            "description": "Holistic analysis of the page by the LLM.",
            "properties": {
                "primary_ink_color": {"type": "STRING"},
                "overall_writing_style": {
                    "type": "STRING",
                    "description": "e.g., 'neat and deliberate', 'rushed', 'emotional'",
                },
            },
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
                    "element_type": {"type": "STRING"},
                    "bounding_box": {
                        "type": "OBJECT",
                        "properties": {
                            "x_min": {"type": "INTEGER"},
                            "y_min": {"type": "INTEGER"},
                            "x_max": {"type": "INTEGER"},
                            "y_max": {"type": "INTEGER"},
                        },
                    },
                    "description": {"type": "STRING"},
                },
            },
        },
    },
}
GEMINI_AUGMENTATION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "page_analysis": FINAL_OUTPUT_SCHEMA["properties"]["page_analysis"],
        "low_confidence_alternatives": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "line_id": {"type": "STRING"},
                    "word_alternatives": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "original_text": {"type": "STRING"},
                                "suggestions": {
                                    "type": "ARRAY",
                                    "items": {"type": "STRING"},
                                },
                            },
                        },
                    },
                },
            },
        },
        "graphical_elements": FINAL_OUTPUT_SCHEMA["properties"]["graphical_elements"],
    },
}


# ==============================================================================
# --- PIPELINE FUNCTIONS ---
# ==============================================================================


@cache_to_file(
    ".docai_cache.json", serializer=json.dumps, deserializer=Document.from_json
)
def call_doc_ai_api(
    *, config: Dict, image_path: str, force_recache: bool = False
) -> Optional[Document]:
    # ... (Unchanged)
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
    # ... (Unchanged)
    logging.info("Transforming raw Document AI data into custom JSON schema.")
    with Image.open(image_path) as img:
        width, height = img.size
    output_data = {
        "page_number": 1,
        "image_source": image_path,
        "page_analysis": {},
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
                }
                line_data["words"].append(word_data)
            output_data["lines"].append(line_data)
    return output_data


def create_minimized_contextual_chunks(
    transcription: Dict, threshold: float = 0.90
) -> List[Dict]:
    """Step 2a: Finds lines with low-confidence words and packages them into a token-efficient format."""
    # ... (Unchanged)
    contextual_chunks = []
    for line in transcription.get("lines", []):
        low_conf_words = [
            word["text"]
            for word in line.get("words", [])
            if word.get("confidence", 1.0) < threshold
        ]
        if low_conf_words:
            all_line_boxes = [w["bounding_box"] for w in line.get("words", [])]
            line_box = [
                min(b["x_min"] for b in all_line_boxes),
                min(b["y_min"] for b in all_line_boxes),
                max(b["x_max"] for b in all_line_boxes),
                max(b["y_max"] for b in all_line_boxes),
            ]
            contextual_chunks.append(
                {
                    "i": line["line_id"],
                    "t": " ".join(word["text"] for word in line.get("words", [])),
                    "b": line_box,
                    "w": low_conf_words,
                }
            )
    logging.info(
        f"Found {len(contextual_chunks)} lines with low-confidence words to analyze."
    )
    return contextual_chunks


def _process_batch_with_autosplit(
    *,
    model: genai.GenerativeModel,
    image_part: genai_protos.Part,
    batch: List[Dict],
    schema: Dict,
    generation_config: genai.GenerationConfig,
    debug: bool,
    max_retries: int = 3,
) -> List[Dict]:
    """
    The recursive worker. Tries to process a batch, and if it fails due to size,
    splits the batch in half and calls itself on the two halves. Returns a LIST of results.
    """
    # ... (Unchanged)
    system_prompt = f"Analyze the image. For the provided list of text lines (minimized format: i=id, t=text, b=box, w=words to check), suggest alternatives for the words in 'w'. Also, provide a page-level analysis and find graphical elements. Respond in JSON using the provided schema.\nBatch:\n{json.dumps(batch)}"
    if debug:
        debug_dir = "debug"
        os.makedirs(debug_dir, exist_ok=True)
        batch_hash = hashlib.sha1(str(batch).encode()).hexdigest()[:10]
        debug_path = os.path.join(debug_dir, f"gemini_prompt_batch_{batch_hash}.log")
        logging.info(f"Saving Gemini prompt for batch to: {debug_path}")
        with open(debug_path, "w") as f:
            f.write(system_prompt)
    FINISH_REASON_EXPLANATIONS = {
        1: "OK",
        2: "MAX_TOKENS",
        3: "SAFETY",
        4: "RECITATION",
        5: "OTHER",
    }
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                [system_prompt, image_part], generation_config=generation_config
            )
            if not response.parts:
                finish_reason = getattr(response.candidates[0], "finish_reason", 0)
                if finish_reason != 2:
                    logging.error(
                        f"Gemini response for batch contained no valid parts. Finish Reason: {FINISH_REASON_EXPLANATIONS.get(finish_reason, 'UNKNOWN')}"
                    )
                    return []
            return [json.loads(response.text)]
        except google_exceptions.ResourceExhausted as e:
            retry_delay = 60
            logging.warning(
                f"Rate limit hit on attempt {attempt + 1}/{max_retries}. Waiting {retry_delay}s. Error: {e}"
            )
            time.sleep(retry_delay)
        except ValueError as e:
            logging.warning(
                f"Batch failed, likely with MAX_TOKENS. len(batch)={len(batch)}. Error: {e}"
            )
            if len(batch) > 1:
                logging.info("Splitting batch and retrying recursively.")
                midpoint = len(batch) // 2
                first_half_results = _process_batch_with_autosplit(
                    model=model,
                    image_part=image_part,
                    batch=batch[:midpoint],
                    schema=schema,
                    generation_config=generation_config,
                    debug=debug,
                    max_retries=max_retries,
                )
                second_half_results = _process_batch_with_autosplit(
                    model=model,
                    image_part=image_part,
                    batch=batch[midpoint:],
                    schema=schema,
                    generation_config=generation_config,
                    debug=debug,
                    max_retries=max_retries,
                )
                return first_half_results + second_half_results
            else:
                logging.error(
                    "A batch of size 1 still failed. This line is too complex to process. Skipping."
                )
                return []
        except Exception as e:
            logging.error(
                f"An unexpected error occurred during Gemini batch API call: {e}",
                exc_info=True,
            )
            return []
    logging.error(
        f"Failed to get a valid response from Gemini for batch after {max_retries} attempts."
    )
    return []


def augment_transcription_with_gemini(
    *,
    config: Dict,
    image_path: str,
    contextual_chunks: List[Dict],
    schema: Dict,
    force_recache: bool = False,
    debug: bool = False,
    batch_size: int = 5,
) -> Optional[Dict]:
    """Orchestrates batch processing with per-batch caching and recursive splitting."""
    genai.configure(api_key=config["gemini_api_key"])
    model = genai.GenerativeModel(config["gemini_model_name"])
    with open(image_path, "rb") as f:
        image_data = f.read()
    image_part = genai_protos.Part(
        inline_data=genai_protos.Blob(mime_type="image/jpeg", data=image_data)
    )
    gemini_schema = genai_protos.Schema(**_convert_json_schema_to_gemini_schema(schema))
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=gemini_schema,
        max_output_tokens=8192,
    )
    batches = [
        contextual_chunks[i : i + batch_size]
        for i in range(0, len(contextual_chunks), batch_size)
    ]
    logging.info(
        f"Processing {len(contextual_chunks)} lines in {len(batches)} initial batches of up to {batch_size} lines each."
    )
    batch_cache_dir = os.path.join(
        ".cache", "gemini_batches", os.path.basename(image_path)
    )
    if force_recache and os.path.exists(batch_cache_dir):
        logging.warning(
            f"Force recache requested. Deleting Gemini batch cache directory: {batch_cache_dir}"
        )
        shutil.rmtree(batch_cache_dir)
    os.makedirs(batch_cache_dir, exist_ok=True)
    all_augmentations = {
        "page_analysis": {},
        "low_confidence_alternatives": [],
        "graphical_elements": [],
    }

    for i, batch in enumerate(batches):
        logging.info(f"Processing initial batch {i+1}/{len(batches)}...")
        batch_hash = hashlib.sha1(
            json.dumps(batch, sort_keys=True).encode()
        ).hexdigest()
        batch_cache_path = os.path.join(batch_cache_dir, f"batch_{batch_hash}.json")
        batch_results = None
        if os.path.exists(batch_cache_path):
            logging.info(f"Found cache for batch {i+1}. Loading.")
            with open(batch_cache_path, "r") as f:
                batch_results = json.load(f)
        if not batch_results:
            batch_results = _process_batch_with_autosplit(
                model=model,
                image_part=image_part,
                batch=batch,
                schema=schema,
                generation_config=generation_config,
                debug=debug,
            )
            if batch_results:
                logging.info(
                    f"Caching result for initial batch {i+1} to {batch_cache_path}"
                )
                with open(batch_cache_path, "w") as f:
                    json.dump(batch_results, f, indent=2)

        if batch_results:
            # --- HARDENING FIX IS HERE ---
            for res in batch_results:
                if not isinstance(res, dict):
                    logging.warning(
                        f"Skipping malformed item in cached batch results: {res}"
                    )
                    continue
                if not all_augmentations["page_analysis"] and "page_analysis" in res:
                    all_augmentations["page_analysis"] = res["page_analysis"]
                all_augmentations["low_confidence_alternatives"].extend(
                    res.get("low_confidence_alternatives", [])
                )
                all_augmentations["graphical_elements"].extend(
                    res.get("graphical_elements", [])
                )
        else:
            logging.error(
                f"Initial batch {i+1} failed after all attempts. The final result may be incomplete."
            )
        if i < len(batches) - 1:
            time.sleep(1)

    unique_elements = {
        json.dumps(d, sort_keys=True): d
        for d in all_augmentations["graphical_elements"]
    }.values()
    all_augmentations["graphical_elements"] = list(unique_elements)
    return all_augmentations


def _normalize_text(text: str) -> str:
    """Helper to standardize text for comparison."""
    return text.strip().lower()


def merge_gemini_augmentations(*, transcription: Dict, augmentations: Dict) -> Dict:
    """Step 3: Merges the batched augmentation data back into the main transcription object."""
    # ... (Unchanged)
    logging.info("Merging Gemini augmentations into the final data structure.")
    transcription["page_analysis"] = augmentations.get("page_analysis", {})
    transcription["graphical_elements"] = augmentations.get("graphical_elements", [])
    alt_map = {}
    for aug in augmentations.get("low_confidence_alternatives", []):
        for word_alt in aug.get("word_alternatives", []):
            original_text = word_alt.get("original_text")
            suggestions = word_alt.get("suggestions", [])
            if not original_text or not suggestions:
                continue
            key = (aug["line_id"], _normalize_text(original_text))
            normalized_original = _normalize_text(original_text)
            filtered_suggestions = [
                s for s in suggestions if _normalize_text(s) != normalized_original
            ]
            if key not in alt_map and filtered_suggestions:
                alt_map[key] = filtered_suggestions
    for line in transcription["lines"]:
        for word in line["words"]:
            key = (line["line_id"], _normalize_text(word["text"]))
            if key in alt_map:
                word["alternatives"] = alt_map.pop(key)
    return transcription


# ==============================================================================
# --- MAIN COORDINATOR & EXECUTION ---
# ==============================================================================
def main_coordinator(
    image_path: str, force_recache: bool, debug: bool, batch_size: int
) -> int:
    try:
        config = load_config()
        logging.info("--- Phase 1: Document AI Transcription ---")
        raw_document = call_doc_ai_api(
            config=config, image_path=image_path, force_recache=force_recache
        )
        if not raw_document:
            raise ValueError("Failed to get Document AI result.")
        initial_transcription = transform_doc_ai_to_custom_json(
            document=raw_document, image_path=image_path
        )

        logging.info("--- Phase 2: Gemini Qualitative Analysis (in Batches) ---")
        contextual_chunks = create_minimized_contextual_chunks(initial_transcription)
        if not contextual_chunks:
            logging.warning("No low-confidence words found. Skipping Gemini analysis.")
            final_result = initial_transcription
        else:
            gemini_augmentations = augment_transcription_with_gemini(
                config=config,
                image_path=image_path,
                contextual_chunks=contextual_chunks,
                schema=GEMINI_AUGMENTATION_SCHEMA,
                force_recache=force_recache,
                debug=debug,
                batch_size=batch_size,
            )
            if not gemini_augmentations or not (
                gemini_augmentations.get("low_confidence_alternatives")
                or gemini_augmentations.get("graphical_elements")
            ):
                logging.error(
                    "Failed to get any valid Gemini analysis results after batch processing. The final JSON will be incomplete."
                )
                final_result = initial_transcription
            else:
                logging.info("--- Phase 3: Merging AI Results ---")
                final_result = merge_gemini_augmentations(
                    transcription=initial_transcription,
                    augmentations=gemini_augmentations,
                )

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


def _convert_json_schema_to_gemini_schema(json_dict: dict) -> Dict:
    # ... (Unchanged)
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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable saving of intermediate debug files (e.g., Gemini prompts).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of lines to process in each initial Gemini API call.",
    )
    args = parser.parse_args()
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="[%(levelname)s] %(message)s")
    exit_code = main_coordinator(
        image_path=args.image,
        force_recache=args.force_recache,
        debug=args.debug,
        batch_size=args.batch_size,
    )
    sys.exit(exit_code)
