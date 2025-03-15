from json_schema_canonicalizer import canonicalish
import json
# Example testing script
schemas = [
    True,  # Example 1
    {"enum": ["singleValue"]},  # Example 2
    False  # Example 3
]

for schema in schemas:
    print("Input:", schema)
    result = canonicalish(schema)
    print("Canonical Form:", json.dumps(result, indent=2))
    print()
