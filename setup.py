import unittest
from json_schema_canonicalizer import canonicalish, merged

class TestCanonicalisation(unittest.TestCase):
    def test_boolean_schema(self):
        # True should become an empty schema and False should become a negated schema.
        self.assertEqual(canonicalish(True), {})
        self.assertIn("not", canonicalish(False))

    def test_enum_normalization(self):
        # Test that an enum with one element becomes a const.
        schema = {"enum": ["foo"]}
        result = canonicalish(schema)
        self.assertEqual(result, {"const": "foo"})

    # More tests for merged(), handling oneOf, allOf, etc.
    
if __name__ == "__main__":
    unittest.main()
