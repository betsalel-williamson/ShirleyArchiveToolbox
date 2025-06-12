# AI-Powered Document Enrichment Pipeline

This project provides a resilient, multi-phase pipeline to perform high-accuracy OCR on documents and enrich the transcription with qualitative analysis from a large language model. It is built to be idempotent and cost-effective by leveraging a hybrid AI approach and an intelligent, file-based work queue.

## Core Concepts & Architecture

The pipeline is designed around a key principle: use the best tool for each job.

1. **Phase 1: Precision OCR**: **Google Cloud Document AI** is used for its state-of-the-art optical character recognition. It extracts text, confidence scores, and precise bounding boxes, forming a reliable "ground truth" transcription. This result is cached to avoid redundant API calls.

2. **Phase 2: Qualitative Enrichment**: The **Google Gemini API** augments the ground truth. To handle documents of any size and complexity without hitting API limits, this phase is architected as a **resilient work queue**:
    * **Token-Efficient Jobs**: The system identifies low-confidence words and packages them into minimized, context-rich "chunks" for analysis.
    * **File-Based Queue**: These chunks are seeded into a `pending/` directory, making the process stateless and resumable.
    * **Recursive Auto-Splitting**: A worker process consumes the queue. If an API call fails because a batch is too large, the worker automatically splits the job into smaller batches and re-queues them. This allows the system to gracefully find the optimal processing size for any given document.
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

* [fixed] final output doesn't properly copy the confidence levels from the source information -- I think that this means that we should go back to localized requests that is, taking snippets of the image and sending that up one at a time to gemini, this would increase the total number of requests but provide us with a better gurantee that the system is only looking at the input that we provided