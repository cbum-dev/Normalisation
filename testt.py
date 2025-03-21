import unittest
import json
from normaliser import JSONSchemaNormalizer

class TestJSONSchemaNormalizer(unittest.TestCase):
    def setUp(self):
        self.normalizer = JSONSchemaNormalizer()
        
    def _normalize_enum_to_const(self, schema: dict[str, any]) -> dict[str, any]:
        """Convert enum with a single value to const."""
        if "enum" in schema and isinstance(schema["enum"], list) and len(schema["enum"]) == 1:
            # Store the enum value first
            const_value = schema["enum"][0]
        # Then delete the enum
            del schema["enum"]
        # Finally, set the const value
            schema["const"] = const_value
            
        return schema
    def test_remove_non_validation_keywords(self):
        """Test removal of non-validation keywords."""
        schema = {
            "title": "My Schema",
            "required": ["foo"],
            "description": "A test schema",
            "$comment": "This is a comment"
        }
        expected = {
            "required": ["foo"]
        }
        
        normalized = self.normalizer.normalize(schema)
        self.assertEqual(normalized, expected)
        
    def test_simplify_boolean_logic(self):
        """Test simplification of boolean logic."""
        schema = {
            "allOf": [
                {
                    "type": "object",
                    "properties": {
                        "foo": {"type": "string"}
                    }
                }
            ]
        }
        expected = {
            "type": "object",
            "properties": {
                "foo": {"type": "string"}
            }
        }
        
        normalized = self.normalizer.normalize(schema)
        self.assertEqual(normalized, expected)
        
    def test_enum_to_const_conversion(self):
        """Test conversion of single-value enum to const."""
        # Configure normalizer to enable this conversion
        normalizer = JSONSchemaNormalizer({"normalize_enum_to_const": True})
        
        schema = {
            "enum": ["foo"]
        }
        expected = {
            "const": "foo"
        }
        
        normalized = normalizer.normalize(schema)
        self.assertEqual(normalized, expected)
        
    def test_recursive_normalization(self):
        """Test that normalization is applied recursively."""
        schema = {
            "type": "object",
            "properties": {
                "foo": {
                    "oneOf": [
                        {"const": "a"},
                        {"const": "b"}
                    ]
                },
                "bar": {
                    "title": "Bar Property",
                    "type": "string"
                }
            }
        }
        expected = {
            "type": "object",
            "properties": {
                "foo": {
                    "enum": ["a", "b"]
                },
                "bar": {
                    "type": "string"
                }
            }
        }
        
        normalized = self.normalizer.normalize(schema)
        self.assertEqual(normalized, expected)
        
    def test_config_options(self):
        """Test that configuration options work correctly."""
        # Create normalizer that keeps non-validation keywords
        normalizer = JSONSchemaNormalizer({"remove_non_validation_keywords": False})
        
        schema = {
            "title": "My Schema",
            "required": ["foo"]
        }
        
        normalized = normalizer.normalize(schema)
        self.assertEqual(normalized, schema)  # Should be unchanged
        
    def test_equivalence_checking(self):
        """Test the equivalence checking functionality."""
        schema1 = {
            "oneOf": [
                {"const": "foo"},
                {"const": "bar"}
            ]
        }
        schema2 = {
            "enum": ["foo", "bar"]
        }
        
        self.assertTrue(self.normalizer.is_equivalent(schema1, schema2))
        
        schema3 = {
            "enum": ["foo", "bar", "baz"]
        }
        
        self.assertFalse(self.normalizer.is_equivalent(schema1, schema3))
        
    def test_complex_schema(self):
        """Test normalization of a more complex schema."""
        schema = {
            "title": "Complex Schema",
            "type": "object",
            "properties": {
                "name": {
                    "description": "The person's name",
                    "type": "string"
                },
                "age": {
                    "oneOf": [
                        {"const": 18},
                        {"const": 19},
                        {"const": 20}
                    ]
                },
                "address": {
                    "allOf": [
                        {
                            "type": "object",
                            "properties": {
                                "street": {"type": "string"}
                            }
                        }
                    ]
                }
            }
        }
        
        expected = {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string"
                },
                "age": {
                    "enum": [18, 19, 20]
                },
                "address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"}
                    }
                }
            }
        }
        
        normalized = self.normalizer.normalize(schema)
        self.assertEqual(normalized, expected)

if __name__ == "__main__":
    unittest.main()