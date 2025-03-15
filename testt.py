"""
Tests for the JSON Schema Normalizer.
"""

import unittest
import json
from normaliser import normalize_schema, SchemaNormalizer


class TestSchemaRules(unittest.TestCase):
    """Test each individual normalization rule."""
    
    def setUp(self):
        self.normalizer = SchemaNormalizer()
    
    def test_oneOf_to_enum(self):
        """Test converting oneOf with const values to enum."""
        schema = {
            "oneOf": [
                {"const": "foo"},
                {"const": "bar"}
            ]
        }
        expected = {
            "enum": ["foo", "bar"]
        }
        self.assertEqual(self.normalizer.normalize(schema), expected)
    
    def test_remove_non_validation_keywords(self):
        """Test removing non-validation keywords."""
        schema = {
            "title": "My Schema",
            "description": "A schema for testing",
            "required": ["foo"],
            "examples": ["example1", "example2"]
        }
        expected = {
            "required": ["foo"]
        }
        self.assertEqual(self.normalizer.normalize(schema), expected)
    
    def test_simplify_boolean_schema_empty(self):
        """Test simplifying an empty schema to true."""
        schema = {}
        expected = True
        self.assertEqual(self.normalizer.normalize(schema), expected)
    
    def test_simplify_boolean_schema_contradiction(self):
        """Test simplifying a contradictory schema to false."""
        schema = {
            "type": "string",
            "not": {"type": "string"}
        }
        expected = False
        self.assertEqual(self.normalizer.normalize(schema), expected)
    
    def test_simplify_array_items(self):
        """Test simplifying array items with redundant definitions."""
        schema = {
            "type": "array",
            "items": {},
            "additionalItems": {"type": "string"}
        }
        expected = {
            "type": "array",
            "items": {}
        }
        self.assertEqual(self.normalizer.normalize(schema), expected)
    
    def test_merge_allOf_single(self):
        """Test merging allOf with a single schema."""
        schema = {
            "allOf": [
                {"type": "string", "minLength": 1}
            ]
        }
        expected = {
            "type": "string",
            "minLength": 1
        }
        self.assertEqual(self.normalizer.normalize(schema), expected)
    
    def test_simplify_boolean_logic_not_not(self):
        """Test simplifying double negation (not not X)."""
        schema = {
            "not": {
                "not": {"type": "string"}
            }
        }
        expected = {
            "type": "string"
        }
        self.assertEqual(self.normalizer.normalize(schema), expected)
    
    def test_deduplicate_enum(self):
        """Test deduplicating enum values."""
        schema = {
            "enum": ["foo", "bar", "foo", "baz"]
        }
        expected = {
            "enum": ["foo", "bar", "baz"]
        }
        self.assertEqual(self.normalizer.normalize(schema), expected)


class TestComplexCases(unittest.TestCase):
    """Test more complex schema normalization cases."""
    
    def setUp(self):
        self.normalizer = SchemaNormalizer()
    
    def test_nested_boolean_logic(self):
        """Test normalizing nested boolean logic."""
        schema = {
            "allOf": [
                {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "number"},
                        False
                    ]
                },
                {
                    "not": {
                        "type": "number"
                    }
                }
            ]
        }
        expected = {
            "type": "string"
        }
        self.assertEqual(self.normalizer.normalize(schema), expected)
    
    def test_recursive_structures(self):
        """Test normalizing recursively defined structures."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "title": "Name Field"},
                "children": {
                    "type": "array",
                    "items": {
                        "oneOf": [
                            {"const": "child1"},
                            {"const": "child2"}
                        ]
                    }
                }
            }
        }
        expected = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "children": {
                    "type": "array",
                    "items": {
                        "enum": ["child1", "child2"]
                    }
                }
            }
        }
        self.assertEqual(self.normalizer.normalize(schema), expected)
    
    def test_equivalent_schemas(self):
        """Test pairs of schemas that should normalize to the same result."""
        pairs = [
            # Pair 1
            (
                {"oneOf": [{"const": "foo"}, {"const": "bar"}]},
                {"enum": ["foo", "bar"]}
            ),
            # Pair 2
            (
                {"required": ["foo"]},
                {"title": "My Schema", "required": ["foo"]}
            ),
            # Pair 3
            (
                {"type": "string", "minLength": 1},
                {"allOf": [{"type": "string"}, {"minLength": 1}]}
            ),
            # Pair 4
            (
                {"type": ["string", "null"]},
                {"anyOf": [{"type": "string"}, {"type": "null"}]}
            ),
        ]
        
        for schema1, schema2 in pairs:
            normalized1 = self.normalizer.normalize(schema1)
            normalized2 = self.normalizer.normalize(schema2)
            self.assertEqual(normalized1, normalized2, 
                             f"Schemas didn't normalize to same result: {schema1} and {schema2}")


class TestRealWorldExamples(unittest.TestCase):
    """Test normalization of real-world schema examples."""
    
    def setUp(self):
        self.normalizer = SchemaNormalizer()
    
    def test_person_schema(self):
        """Test normalizing a typical person schema."""
        schema = {
            "title": "Person",
            "description": "A person object",
            "type": "object",
            "properties": {
                "firstName": {
                    "type": "string",
                    "description": "The person's first name"
                },
                "lastName": {
                    "type": "string",
                    "description": "The person's last name"
                },
                "age": {
                    "description": "Age in years",
                    "type": "integer",
                    "minimum": 0
                }
            },
            "required": ["firstName", "lastName"]
        }
        
        expected = {
            "type": "object",
            "properties": {
                "firstName": {
                    "type": "string"
                },
                "lastName": {
                    "type": "string"
                },
                "age": {
                    "type": "integer",
                    "minimum": 0
                }
            },
            "required": ["firstName", "lastName"]
        }
        
        self.assertEqual(self.normalizer.normalize(schema), expected)
    
    def test_api_response_schema(self):
        """Test normalizing an API response schema with oneOf."""
        schema = {
            "title": "API Response",
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "status": {"const": "success"},
                        "data": {"type": "object"}
                    },
                    "required": ["status", "data"]
                },
                {
                    "type": "object",
                    "properties": {
                        "status": {"const": "error"},
                        "error": {"type": "string"}
                    },
                    "required": ["status", "error"]
                }
            ]
        }
        
        # This should remain largely unchanged as it can't be simplified further
        expected = {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "status": {"const": "success"},
                        "data": {"type": "object"}
                    },
                    "required": ["status", "data"]
                },
                {
                    "type": "object",
                    "properties": {
                        "status": {"const": "error"},
                        "error": {"type": "string"}
                    },
                    "required": ["status", "error"]
                }
            ]
        }
        
        self.assertEqual(self.normalizer.normalize(schema), expected)


class TestPerformance(unittest.TestCase):
    """Test the performance characteristics of the normalizer."""
    
    def setUp(self):
        self.normalizer = SchemaNormalizer()
    
    def test_deeply_nested_schema(self):
        """Test that deeply nested schemas don't cause stack overflow."""
        # Create a deeply nested schema
        schema = {"type": "string"}
        for _ in range(100):
            schema = {"allOf": [schema]}
        
        # Should normalize without errors
        try:
            normalized = self.normalizer.normalize(schema)
            self.assertEqual(normalized, {"type": "string"})
        except RecursionError:
            self.fail("Normalizer caused recursion error on deeply nested schema")
    
    def test_pathological_case(self):
        """Test a pathological case with many nested oneOfs."""
        # Create a schema with many nested oneOfs that can be simplified
        schema = {"type": "string"}
        for i in range(20):
            schema = {
                "oneOf": [
                    {"const": f"value{i}"},
                    schema
                ]
            }
        
        # Should normalize without timing out
        import time
        start_time = time.time()
        normalized = self.normalizer.normalize(schema)
        duration = time.time() - start_time
        
        # Check that it completes in a reasonable time (adjust threshold as needed)
        self.assertLess(duration, 5.0, "Normalization took too long")


if __name__ == "__main__":
    unittest.main()