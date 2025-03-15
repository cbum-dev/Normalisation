from normaliser import normalize_schema

# Your schema
schema = {
    "allOf": [
        {"type": "string"},
        {"minLength": 1}
    ]
}
# Normalize it
normalized_schema = normalize_schema(schema)

# Do something with the normalized schema
print(normalized_schema)  # Will print: {"enum": ["foo", "bar"]}