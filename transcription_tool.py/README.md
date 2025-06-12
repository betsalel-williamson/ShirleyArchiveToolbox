# AI-Powered Document Enrichment Pipeline

This project provides a resilient, multi-phase pipeline to perform high-accuracy OCR on documents and enrich the transcription with qualitative analysis from a large language model. It is built to be idempotent and cost-effective by leveraging a hybrid AI approach and an intelligent, file-based work queue.

## Core Concepts & Architecture

The pipeline is designed around a key principle: use the best tool for each job.

1. **Phase 1: Precision OCR**: **Google Cloud Document AI** is used for its state-of-the-art optical character recognition. It extracts text, confidence scores, and precise bounding boxes, forming a reliable "ground truth" transcription. This result is cached to avoid redundant API calls.

2. **Phase 2: Qualitative Enrichment**: The **Google Gemini API** augments the ground truth. To achieve high accuracy for specific elements and manage API costs/limits, this phase uses a **resilient work queue**:
    * **Targeted Snippet Analysis**: The system identifies low-confidence words from Document AI and extracts corresponding image snippets. These snippets are then sent to Gemini for precise re-transcription or alternative suggestions.
    * **File-Based Queue**: Each snippet analysis request becomes a job, seeded into a `pending/` directory, making the process stateless and resumable.
    * **Rate Limit Handling**: The worker process consumes the queue, automatically retrying and introducing delays for rate-limiting errors. This ensures all jobs eventually complete.
    * **Idempotency & Failure Handling**: Successfully processed jobs are removed from the queue. Un-processable "poison pill" jobs are moved to a `failed/` directory for later inspection, ensuring the pipeline always runs to completion.

3. **Phase 3: Data Fusion**: A local Python process intelligently merges the qualitative enrichments from Gemini (such as alternative word suggestions and graphical element descriptions) back into the high-precision transcription from Document AI.

This "Analyze, Augment, Merge" pattern ensures maximum data quality while maintaining efficiency and resilience.

## Setup

### Prerequisites

* Python 3.11 or 3.12
* A Google Cloud Project with billing enabled
* The `gcloud` command-line tool

### Installation

1. **Clone & Setup Environment**:

    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    python3.12 -m venv .venv
    source .venv/bin/activate
    ```

2. **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

3. **Configure Services**:
    * Enable the **Document AI API** and **Vertex AI API** in your GCP project.
    * Authenticate your local environment for Document AI: `gcloud auth application-default login`.
    * Create a **Document OCR** processor in the Document AI console.
    * Get a **Gemini API Key** from [Google AI Studio](https://makersuite.google.com/app/apikey).
4. **Create `.env` File**:
    Copy `.env.example` to `.env` and populate it with your GCP Project ID, Document AI Processor ID, and Gemini API Key.

## Usage

The script is run from the command line, pointing to an image file.

```bash
# Basic usage
python process_journal.py -i path/to/image.jpg

# Common usage with detailed logs
python process_journal.py -i path/to/image.jpg --verbose

# Force all API calls to re-run, ignoring any cached data
python process_journal.py -i path/to/image.jpg --force-recache
```

### Command-Line Arguments

The script's behavior can be controlled via command-line arguments. For a full list of options and their descriptions, run:

```bash
python process_journal.py --help
```

## Troubleshooting

* **Errors after a code change?** Your cache may be stale. Run with `--force-recache`.

* **Gemini calls failing?** Run with `--debug` to inspect the prompts being sent to the API, which are saved in the `debug/` directory. Check the `.cache/gemini_work_queue/.../failed/` directory for any jobs that could not be processed.
* **Installation fails?** Ensure you are using a supported, stable version of Python (e.g., 3.11, 3.12).

## Tasks and Bugs
