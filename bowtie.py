import json

# Define the schema and instances
schema = {"type": "integer"}
valid_instance = 37
invalid_instance = "foo"

# Function to write JSON to a file
def write_json(data, filename):
    with open(filename, 'w') as file:
        json.dump(data, file)

# Create the files
write_json(schema, 'schema.json')
write_json(valid_instance, 'instance.json')
write_json(invalid_instance, 'invalid_instance.json')
