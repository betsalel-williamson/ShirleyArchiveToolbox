import os
import sys
import json
import time
import argparse
import logging
import functools
import hashlib
import shutil
import asyncio
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
    from tqdm.asyncio import tqdm as asyncio_tqdm
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
        async def wrapper(*args, **kwargs) -> Optional[Any]:
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
            result = (
                await func(*args, **kwargs)
                if asyncio.iscoroutinefunction(func)
                else func(*args, **kwargs)
            )

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
GEMINI_PAGE_ANALYSIS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "page_analysis": FINAL_OUTPUT_SCHEMA["properties"]["page_analysis"],
        "graphical_elements": FINAL_OUTPUT_SCHEMA["properties"]["graphical_elements"],
    },
}
GEMINI_WORD_ALTERNATIVES_SCHEMA = {
    "type": "OBJECT",
    "properties": {"alternatives": {"type": "ARRAY", "items": {"type": "STRING"}}},
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


@cache_to_file(
    ".gemini_page_analysis.cache.json", serializer=json.dumps, deserializer=json.loads
)
async def call_gemini_for_page_analysis(
    *, config: Dict, image_path: str, force_recache: bool = False
) -> Optional[Dict]:
    """Phase 2: Performs a single 'macro' analysis of the full page using asyncio."""
    # ... (Unchanged)
    model = genai.GenerativeModel(config["gemini_model_name"])
    system_prompt = "Analyze the entire page. Identify all non-text graphical elements (doodles, stains) and provide a holistic analysis of the page's ink color and writing style. Respond in JSON using the provided schema."
    with open(image_path, "rb") as f:
        image_data = f.read()
    image_part = genai_protos.Part(
        inline_data=genai_protos.Blob(mime_type="image/jpeg", data=image_data)
    )
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=GEMINI_PAGE_ANALYSIS_SCHEMA,
    )
    try:
        response = await model.generate_content_async(
            [system_prompt, image_part], generation_config=generation_config
        )
        return json.loads(response.text)
    except Exception as e:
        logging.error(f"Page-level analysis with Gemini failed: {e}", exc_info=True)
        return None


async def _process_single_word_snippet(
    config: Dict,
    model: genai.GenerativeModel,
    semaphore: asyncio.Semaphore,
    image_snippet: bytes,
    original_text: str,
    word_id: str,
    max_retries: int = 3,
) -> Optional[Dict]:
    """Async worker function that analyzes one word snippet, with retries and a semaphore."""
    system_prompt = f"This is an image of a single, handwritten word. A previous OCR model transcribed it as '{original_text}' with low confidence. What does this word say? Provide a list of the most likely alternatives."
    image_part = genai_protos.Part(
        inline_data=genai_protos.Blob(mime_type="image/png", data=image_snippet)
    )
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=GEMINI_WORD_ALTERNATIVES_SCHEMA,
    )

    async with semaphore:
        for attempt in range(max_retries):
            try:
                response = await model.generate_content_async(
                    [system_prompt, image_part], generation_config=generation_config
                )
                alternatives = json.loads(response.text).get("alternatives", [])
                return {"id": word_id, "alternatives": alternatives}
            except google_exceptions.ResourceExhausted as e:
                retry_delay = 60
                if e.retry and e.retry.delay:
                    retry_delay = e.retry.delay.total_seconds()
                logging.warning(
                    f"Rate limit hit for word '{original_text}' on attempt {attempt + 1}/{max_retries}. Waiting {retry_delay}s. Error: {e}"
                )
                await asyncio.sleep(retry_delay)
            except Exception as e:
                logging.error(
                    f"Failed to process word snippet for '{original_text}' (ID: {word_id}) on attempt {attempt+1}: {e}"
                )
                return None  # Do not retry on other errors

        logging.error(f"Word '{original_text}' failed after {max_retries} attempts.")
        return None


@cache_to_file(
    ".gemini_word_alternatives.cache.json",
    serializer=json.dumps,
    deserializer=json.loads,
)
async def call_gemini_for_word_alternatives_parallel(
    *,
    config: Dict,
    image_path: str,
    transcription: Dict,
    force_recache: bool = False,
    confidence_threshold: float = 0.9,
    concurrency_limit: int = 20,
) -> Dict[str, List[str]]:
    """Phase 3: Finds low-confidence words, crops them, and gets alternatives in parallel using asyncio and a semaphore."""
    low_conf_words = []
    for line in transcription["lines"]:
        for word in line["words"]:
            if word["confidence"] < confidence_threshold:
                word_id = (
                    f"{line['line_id']}_{word['text']}_{word['bounding_box']['x_min']}"
                )
                low_conf_words.append(
                    {"id": word_id, "box": word["bounding_box"], "text": word["text"]}
                )

    if not low_conf_words:
        logging.info("No low-confidence words found to analyze.")
        return {}

    logging.info(
        f"Found {len(low_conf_words)} low-confidence words. Processing in parallel with a concurrency limit of {concurrency_limit}..."
    )

    original_image = Image.open(image_path)
    semaphore = asyncio.Semaphore(concurrency_limit)
    model = genai.GenerativeModel(
        config["gemini_model_name"]
    )  # Create one model instance to be shared
    tasks = []

    for word_data in low_conf_words:
        box = word_data["box"]
        snippet = original_image.crop(
            (box["x_min"] - 5, box["y_min"] - 5, box["x_max"] + 5, box["y_max"] + 5)
        )
        import io

        with io.BytesIO() as output:
            snippet.save(output, format="PNG")
            image_bytes = output.getvalue()

        task = _process_single_word_snippet(
            config, model, semaphore, image_bytes, word_data["text"], word_data["id"]
        )
        tasks.append(task)

    word_alternatives = {}
    for future in asyncio_tqdm.as_completed(
        tasks, total=len(tasks), desc="Analyzing word snippets"
    ):
        result = await future
        if result and result.get("alternatives"):
            word_alternatives[result["id"]] = result["alternatives"]

    return word_alternatives


def _normalize_text(text: str) -> str:
    """Helper to standardize text for comparison."""
    return text.strip().lower()


def merge_all_results(
    *, transcription: Dict, page_analysis: Dict, word_alternatives: Dict
) -> Dict:
    """Phase 4: Merges results from all previous phases into the final JSON."""
    logging.info("Merging results from all phases into final data structure.")
    final_data = transcription
    final_data["page_analysis"] = page_analysis.get("page_analysis", {})
    final_data["graphical_elements"] = page_analysis.get("graphical_elements", [])

    for line in final_data["lines"]:
        for word in line["words"]:
            word_id = (
                f"{line['line_id']}_{word['text']}_{word['bounding_box']['x_min']}"
            )
            if word_id in word_alternatives:
                suggestions = word_alternatives[word_id]
                normalized_original = _normalize_text(word["text"])
                word["alternatives"] = [
                    s for s in suggestions if _normalize_text(s) != normalized_original
                ]
    return final_data


# ==============================================================================
# --- MAIN COORDINATOR & EXECUTION ---
# ==============================================================================
async def main_coordinator(
    image_path: str, force_recache: bool, debug: bool, concurrency: int
) -> int:
    try:
        config = load_config()
        genai.configure(api_key=config["gemini_api_key"])

        logging.info("--- Phase 1: Document AI Transcription ---")
        loop = asyncio.get_running_loop()
        raw_document = await call_doc_ai_api(
            config=config,
            image_path=image_path,
            force_recache=force_recache,
        )

        if not raw_document:
            raise ValueError("Failed to get Document AI result.")
        initial_transcription = transform_doc_ai_to_custom_json(
            document=raw_document, image_path=image_path
        )

        logging.info("--- Phase 2: Gemini Page-Level 'Macro' Analysis ---")
        page_analysis = await call_gemini_for_page_analysis(
            config=config, image_path=image_path, force_recache=force_recache
        )
        if not page_analysis:
            logging.warning("Failed to get page-level analysis. Continuing without it.")
            page_analysis = {}

        logging.info("--- Phase 3: Gemini Word-Level 'Micro' Analysis (Parallel) ---")
        word_alternatives = await call_gemini_for_word_alternatives_parallel(
            config=config,
            image_path=image_path,
            transcription=initial_transcription,
            force_recache=force_recache,
            concurrency_limit=concurrency,
        )

        logging.info("--- Phase 4: Merging All Results ---")
        final_result = merge_all_results(
            transcription=initial_transcription,
            page_analysis=page_analysis,
            word_alternatives=word_alternatives,
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
        description="A multi-phase tool to transcribe and analyze diary pages using Google AI."
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
        "--concurrency-limit",
        type=int,
        default=20,
        help="Max number of parallel API calls to Gemini for word analysis.",
    )
    args = parser.parse_args()
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="[%(levelname)s] %(message)s")

    exit_code = asyncio.run(
        main_coordinator(
            image_path=args.image,
            force_recache=args.force_recache,
            debug=args.debug,
            concurrency=args.concurrency_limit,
        )
    )
    sys.exit(exit_code)
