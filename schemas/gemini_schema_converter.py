# gemini_schema_converter.py

import json
import copy

def resolve_refs(node, definitions):
    """
    Recursively finds and replaces all "$ref" keys in a schema
    with their corresponding definitions.

    Args:
        node: The current node (dict or list) in the schema to process.
        definitions: A dictionary containing all the definitions from "$defs".

    Returns:
        The processed node with all "$ref"s inlined.
    """
    if isinstance(node, dict):
        if "$ref" in node:
            ref_path = node["$ref"]
            # Assumes path is like "#/$defs/MyDefinition"
            def_name = ref_path.split('/')[-1]
            if def_name in definitions:
                # Use a deep copy to avoid modifying the original definition
                # and to handle multiple references to the same object.
                return resolve_refs(copy.deepcopy(definitions[def_name]), definitions)
            else:
                # If ref is not found, return as is or raise an error
                return node
        else:
            # Recurse into dictionary values
            return {k: resolve_refs(v, definitions) for k, v in node.items()}
    elif isinstance(node, list):
        # Recurse into list items
        return [resolve_refs(item, definitions) for item in node]
    else:
        # Return primitives as is
        return node

def transform_for_gemini(node, is_root=False):
    """
    Recursively transforms an inlined OpenAPI schema to be compliant
    with the Google Gemini Schema format.

    Args:
        node: The current node (dict or list) of the inlined schema.
        is_root: A boolean flag to indicate if the current node is the root
                 of the schema. This is used to preserve the top-level 'example'.

    Returns:
        The transformed, Gemini-compliant schema node.
    """
    if isinstance(node, dict):
        # 1. Handle nullable fields using 'anyOf'
        if "anyOf" in node:
            # Find the 'null' type and the other type definition
            other_schemas = [s for s in node["anyOf"] if s.get("type") != "null"]
            is_nullable = len(other_schemas) < len(node["anyOf"])

            if len(other_schemas) == 1:
                # If there's one other schema, it's a simple nullable type.
                # Replace the 'anyOf' node with the other schema and add 'nullable'.
                node = other_schemas[0]
                if is_nullable:
                    node["nullable"] = True
            # Note: This doesn't handle complex anyOf with more than one non-null type,
            # as it's not present in the source schema.

        # 2. Process the (potentially new) node
        processed_node = {}
        for key, value in node.items():
            # Rule: Remove 'title' field
            if key == "title":
                continue

            # Rule: Remove 'example' field if not at the root
            if key == "example" and not is_root:
                continue

            # Rule: Convert type names to uppercase
            if key == "type" and isinstance(value, str):
                processed_node[key] = value.upper()
            else:
                # Recurse into nested structures
                processed_node[key] = transform_for_gemini(value, is_root=False)

        return processed_node

    elif isinstance(node, list):
        return [transform_for_gemini(item, is_root=False) for item in node]
    else:
        return node


def main():
    """
    Main function to load, convert, and save the schema.
    """
    input_filename = "ocr-schema-v2.openapi.json"
    output_filename = "gemini_transcription_schema.json"

    print(f"Loading OpenAPI schema from '{input_filename}'...")
    try:
        with open(input_filename, 'r') as f:
            openapi_schema = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not parse JSON from '{input_filename}'.")
        return

    # --- Phase 1: Resolve all $refs ---
    print("Phase 1: Inlining all $ref definitions...")
    # The definitions are expected in '$defs' for this schema.
    # For a more general tool, you might also check 'components/schemas'.
    definitions = openapi_schema.get("$defs", {})
    if not definitions:
        print("Warning: No '$defs' section found in the schema.")

    # Create a working copy to avoid modifying the original dict while iterating
    inlined_schema = copy.deepcopy(openapi_schema)
    inlined_schema = resolve_refs(inlined_schema, definitions)
    print("...$refs resolved.")

    # --- Phase 2: Transform for Gemini compliance ---
    print("Phase 2: Transforming schema for Gemini compliance...")
    gemini_schema = transform_for_gemini(inlined_schema, is_root=True)

    # Final cleanup: remove the now-unnecessary $defs section from the root
    if "$defs" in gemini_schema:
        del gemini_schema["$defs"]

    print("...Transformation complete.")

    # --- Save the result ---
    print(f"Saving Gemini-compliant schema to '{output_filename}'...")
    with open(output_filename, 'w') as f:
        json.dump(gemini_schema, f, indent=2)

    print("\nConversion successful!")
    print(f"Output written to {output_filename}")


if __name__ == "__main__":
    main()
