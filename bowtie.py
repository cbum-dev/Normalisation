import bowtie
from jsonschema import validate, ValidationError

def validate_equivalence(original_schema, normalized_schema, test_instances):
    original_valid = all(validate_schema(original_schema, instance) for instance in test_instances)
    normalized_valid = all(validate_schema(normalized_schema, instance) for instance in test_instances)
    
    assert original_valid == normalized_valid, "Validation result mismatch between original and normalized schema"

    return original_valid, normalized_valid

def validate_schema(schema, instance):
    try:
        validate(instance, schema)
        return True
    except ValidationError:
        return False

# Example usage
original_schema = {"oneOf": [{"const": "foo"}, {"const": "bar"}]}
normalized_schema = {"enum": ["foo", "bar"]}
test_instances = ["foo", "bar", "baz", 42]
print(
validate_equivalence(original_schema, normalized_schema, test_instances)
)