import json
from jsonschema import validate, ValidationError

with open('schema.json') as schema_file:
    schema = json.load(schema_file)
with open('instance.json') as instance_file:
    instance = json.load(instance_file)

try:
    validate(instance=instance, schema=schema)
    print("Validation successful!")
except ValidationError as e:
    print("Validation failed:", e)
