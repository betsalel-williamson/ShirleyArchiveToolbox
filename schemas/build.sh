#!/bin/bash

# Ensure the script exits if any command fails
set -e

# Define file names
SCHEMA_PY="schema_definition.py"
TEMPLATE_MD="transcription_system_prompt.md"
OUTPUT_MD="system_prompt.md"
SCHEMA_JSON_TMP="ocr-schema-v2.openapi.json"

# echo "Step 1: Generating JSON Schema from Pydantic models..."
# # Run the Python script to generate the schema and save it to a temporary file
# python3 "$SCHEMA_PY" > "$SCHEMA_JSON_TMP"
# echo "✅ JSON Schema generated and saved to $SCHEMA_JSON_TMP"

echo "Step 2: Injecting JSON Schema into the prompt template..."
# Read the template and the schema content
template_content=$(cat "$TEMPLATE_MD")
schema_content=$(cat "$SCHEMA_JSON_TMP")

# Replace the placeholder and save the final output
# Using a different delimiter for sed to avoid issues with slashes in JSON
final_prompt="${template_content//'{{JSON_SCHEMA}}'/$schema_content}"
echo "$final_prompt" > "$OUTPUT_MD"

echo "✅ Final system prompt created at $OUTPUT_MD"

# Clean up the temporary file
rm "$SCHEMA_JSON_TMP"
echo "🧹 Cleaned up temporary files."

echo "Build complete!"
