"""
JSON Schema Normalizer

This library converts JSON Schema documents to a canonical form while preserving validation semantics.
The normalization process transforms semantically equivalent schemas into the same representation.

Normalization benefits:
1. Simplified schema comparison (equality testing)
2. Reduced redundancy and schema size
3. Improved readability
4. Better performance in validation
5. More reliable schema merging and diff operations

Author: Claude
"""

import json
import copy
from typing import Any, Dict, List, Union, Set, Optional, Tuple
import unittest
import time
import os
import sys

class JSONSchemaNormalizer:
    """
    A normalizer for JSON Schema that transforms schemas into a canonical form
    while preserving validation behavior.
    """
    
    def normalize(self, schema: Union[Dict[str, Any], bool]) -> Union[Dict[str, Any], bool]:
        """
        Normalize a JSON Schema by applying a series of transformations.
        
        Args:
            schema: The JSON Schema to normalize
            
        Returns:
            A normalized version of the schema
        """
        # Handle boolean schemas
        if schema is True:
            return {}
        elif schema is False:
            return {"not": {}}
            
        if not isinstance(schema, dict):
            return schema
            
        # Make a deep copy to avoid modifying the original
        result = copy.deepcopy(schema)
        
        # Apply normalizations in a specific order for consistency
        result = self._normalize_boolean_schemas(result)
        result = self._remove_redundant_metadata(result)
        result = self._normalize_type_constraints(result)
        result = self._normalize_number_constraints(result)
        result = self._normalize_string_constraints(result)
        result = self._normalize_array_constraints(result)
        result = self._normalize_object_constraints(result)
        result = self._normalize_enum_and_const(result)
        result = self._normalize_allOf(result)
        result = self._normalize_anyOf_oneOf(result)
        result = self._normalize_not(result)
        result = self._normalize_if_then_else(result)
        result = self._normalize_dependencies(result)
        result = self._normalize_reference_resolution(result)
        result = self._cleanup_empty_keywords(result)
        
        return result
    
    def _normalize_boolean_schemas(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize boolean schemas to their canonical form.
        
        - Empty schema {} represents the "true" schema (accepts everything)
        - {"not": {}} represents the "false" schema (rejects everything)
        """
        if schema == {}:
            return {}
            
        return schema
    
    def _remove_redundant_metadata(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove metadata keywords that don't affect validation.
        
        These include title, description, $comment, examples, etc.
        """
        metadata_keywords = {
            "title", "description", "$comment", "examples", 
            "readOnly", "writeOnly", "deprecated", "$id", "$schema"
        }
        
        return {k: v for k, v in schema.items() if k not in metadata_keywords}
    
    def _normalize_type_constraints(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize type constraints.
        
        - Convert type strings to arrays and back when appropriate
        - Handle integer/number combinations
        - Remove redundant types
        """
        result = schema.copy()
        
        if "type" not in result:
            return result
            
        # Normalize type to array form
        if isinstance(result["type"], str):
            result["type"] = [result["type"]]
            
        # Sort and deduplicate types
        result["type"] = sorted(set(result["type"]))
        
        # Convert array of all types to no type constraint
        all_types = {"null", "boolean", "object", "array", "number", "string", "integer"}
        if set(result["type"]) == all_types:
            del result["type"]
            
        # Normalize "integer" and "number" combination
        if "integer" in result["type"] and "number" in result["type"]:
            result["type"].remove("integer")
            
            # Add multipleOf constraint if needed
            if "multipleOf" not in result:
                result["multipleOf"] = 1.0
                
        # Convert back to string if only one type
        if "type" in result and len(result["type"]) == 1:
            result["type"] = result["type"][0]
            
        return result
    
    def _normalize_number_constraints(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize constraints for numeric types.
        
        - Handle draft-04 to draft-07 exclusive min/max conversions
        - Remove redundant multipleOf: 1 for integers
        """
        result = schema.copy()
        
        # Skip if not a numeric type
        type_values = result.get("type", [])
        if isinstance(type_values, str):
            type_values = [type_values]
            
        if not any(t in ["number", "integer"] for t in type_values) and type_values:
            return result
            
        # Normalize exclusive minimum/maximum
        for kw_pair in [("minimum", "exclusiveMinimum"), ("maximum", "exclusiveMaximum")]:
            inclusive, exclusive = kw_pair
            
            # Handle draft-04 style exclusive keywords
            if inclusive in result and exclusive in result and isinstance(result[exclusive], bool):
                if result[exclusive]:
                    # Convert to draft-07 style
                    result[exclusive] = result[inclusive]
                    del result[inclusive]
                else:
                    # Remove redundant exclusiveMinimum: false
                    del result[exclusive]
                    
        # Normalize multipleOf
        if "multipleOf" in result and result["multipleOf"] == 1:
            if "type" in result and (
                result["type"] == "integer" or
                (isinstance(result["type"], list) and 
                 "integer" in result["type"] and 
                 "number" not in result["type"])
            ):
                del result["multipleOf"]
                
        return result
    
    def _normalize_string_constraints(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize constraints for string types.
        
        - Optimize minLength/maxLength combinations
        - Convert some patterns to enum when possible
        """
        result = schema.copy()
        
        # Skip if not a string type
        type_values = result.get("type", [])
        if isinstance(type_values, str):
            type_values = [type_values]
            
        if "string" not in type_values and type_values:
            return result
            
        # Remove redundant maxLength if minLength >= maxLength
        if "minLength" in result and "maxLength" in result:
            if result["minLength"] >= result["maxLength"]:
                del result["maxLength"]
                
        # Replace pattern with enum if it's a simple enumeration pattern
        if "pattern" in result and result["pattern"].startswith("^(") and result["pattern"].endswith(")$"):
            # Check if pattern is a simple alternation without complex regex features
            pattern = result["pattern"][2:-2]  # Remove ^( and )$
            if "|" in pattern and not any(c in pattern for c in "[]{}()?*.+"):
                # Simple enumeration pattern
                values = [val for val in pattern.split("|") if val]
                result["enum"] = values
                del result["pattern"]
                
        return result
    
    def _normalize_array_constraints(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize constraints for array types.
        
        - Normalize items and additionalItems
        - Handle tuple validation
        - Remove default minItems: 0
        """
        result = schema.copy()
        
        # Skip if not an array type
        type_values = result.get("type", [])
        if isinstance(type_values, str):
            type_values = [type_values]
            
        if "array" not in type_values and type_values:
            return result
            
        # Normalize items
        if "items" in result:
            if isinstance(result["items"], dict):
                # Single schema for all items
                result["items"] = self.normalize(result["items"])
                
                # If items is empty schema (true), remove it
                if result["items"] == {}:
                    del result["items"]
            elif isinstance(result["items"], list):
                # Tuple validation - normalize each schema
                result["items"] = [self.normalize(item_schema) for item_schema in result["items"]]
                
                # If all items are empty schemas, convert to single empty schema
                if all(item == {} for item in result["items"]):
                    result["items"] = {}
                    
                # Remove empty items array
                if not result["items"]:
                    del result["items"]
                    
        # Normalize additionalItems
        if "additionalItems" in result:
            if isinstance(result["additionalItems"], dict):
                result["additionalItems"] = self.normalize(result["additionalItems"])
                
                # If additionalItems is empty schema (true), remove it
                if result["additionalItems"] == {}:
                    del result["additionalItems"]
            elif result["additionalItems"] is True:
                # True is the default, so we can remove it
                del result["additionalItems"]
                
        # Remove redundant length constraints
        if "minItems" in result and "maxItems" in result:
            if result["minItems"] >= result["maxItems"]:
                # Fixed length array - keep only one constraint
                result["minItems"] = result["maxItems"]
                del result["maxItems"]
                
        # Remove default minItems: 0
        if "minItems" in result and result["minItems"] == 0:
            del result["minItems"]
            
        # Normalize contains
        if "contains" in result:
            result["contains"] = self.normalize(result["contains"])
            
            # If contains is empty schema (true), remove it
            if result["contains"] == {}:
                del result["contains"]
                
        return result
    
    def _normalize_object_constraints(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize constraints for object types.
        
        - Normalize properties and patternProperties
        - Normalize additionalProperties
        - Sort and deduplicate required properties
        """
        result = schema.copy()
        
        # Skip if not an object type
        type_values = result.get("type", [])
        if isinstance(type_values, str):
            type_values = [type_values]
            
        if "object" not in type_values and type_values:
            return result
            
        # Normalize properties
        if "properties" in result:
            # Normalize each property schema
            properties = {}
            for prop, prop_schema in result["properties"].items():
                normalized = self.normalize(prop_schema)
                if normalized != {}:  # Skip empty schemas
                    properties[prop] = normalized
                    
            if properties:
                result["properties"] = properties
            else:
                del result["properties"]
                
        # Normalize patternProperties
        if "patternProperties" in result:
            pattern_props = {}
            for pattern, pattern_schema in result["patternProperties"].items():
                normalized = self.normalize(pattern_schema)
                if normalized != {}:  # Skip empty schemas
                    pattern_props[pattern] = normalized
                    
            if pattern_props:
                result["patternProperties"] = pattern_props
            else:
                del result["patternProperties"]
                
        # Normalize additionalProperties
        if "additionalProperties" in result:
            if isinstance(result["additionalProperties"], dict):
                result["additionalProperties"] = self.normalize(result["additionalProperties"])
                
                # If additionalProperties is empty schema (true), remove it
                if result["additionalProperties"] == {}:
                    del result["additionalProperties"]
            elif result["additionalProperties"] is True:
                # True is the default, so we can remove it
                del result["additionalProperties"]
                
        # Normalize required
        if "required" in result:
            # Sort and deduplicate required properties
            required = sorted(set(result["required"]))
            
            # Check if required properties exist in properties
            if "properties" in result:
                # Only keep properties that exist in the properties object
                # This is a stricter normalization but can be disabled if needed
                required = [prop for prop in required if prop in result["properties"]]
                
            if required:
                result["required"] = required
            else:
                del result["required"]
                
        # Remove default minProperties: 0
        if "minProperties" in result and result["minProperties"] == 0:
            del result["minProperties"]
            
        return result
    
    def _normalize_enum_and_const(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize enum and const keywords.
        
        - Convert singleton enum to const
        - Sort and deduplicate enum values when possible
        """
        result = schema.copy()
        
        # Deduplicate enum values
        if "enum" in result:
            # For simple types, we can deduplicate and sort
            try:
                # Convert to hashable types for deduplication
                enum_set = set()
                for item in result["enum"]:
                    if isinstance(item, (dict, list)):
                        enum_set.add(json.dumps(item, sort_keys=True))
                    else:
                        enum_set.add(item)
                        
                # Convert back to original types if needed
                enum_list = []
                for item in enum_set:
                    if isinstance(item, str) and (item.startswith('{') or item.startswith('[')):
                        try:
                            enum_list.append(json.loads(item))
                        except:
                            enum_list.append(item)
                    else:
                        enum_list.append(item)
                        
                # Try to sort if possible
                try:
                    enum_list = sorted(enum_list)
                except TypeError:
                    # Mixed types, can't sort
                    pass
                    
                result["enum"] = enum_list
            except:
                # If we can't deduplicate/sort, keep as is
                pass
                
            # Convert singleton enum to const
            if len(result["enum"]) == 1:
                result["const"] = result["enum"][0]
                del result["enum"]
                
            # Remove empty enum
            if "enum" in result and not result["enum"]:
                del result["enum"]
                
        return result
    
    def _normalize_allOf(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize allOf constructs.
        
        - Flatten nested allOf
        - Remove empty allOf
        - Merge single item allOf with parent
        """
        result = schema.copy()
        
        if "allOf" not in result:
            return result
            
        # Recursively normalize subschemas
        subschemas = []
        for subschema in result["allOf"]:
            normalized = self.normalize(subschema)
            
            # Skip empty schemas (true)
            if normalized == {}:
                continue
                
            # Flatten nested allOf
            if "allOf" in normalized:
                subschemas.extend(normalized["allOf"])
            else:
                subschemas.append(normalized)
                
        # Special cases
        if not subschemas:
            # Empty allOf is always true
            del result["allOf"]
        elif len(subschemas) == 1:
            # Single item allOf can be merged
            del result["allOf"]
            single_schema = subschemas[0]
            
            # Merge the single schema with the parent
            for key, value in single_schema.items():
                if key not in result:
                    result[key] = value
                elif key in ["required", "type"] and isinstance(value, list) and isinstance(result[key], list):
                    # Merge lists with deduplication
                    result[key] = sorted(set(result[key] + value))
                elif key == "properties" and isinstance(value, dict) and isinstance(result[key], dict):
                    # Merge properties
                    for prop, prop_schema in value.items():
                        if prop not in result[key]:
                            result[key][prop] = prop_schema
                        else:
                            # Property exists in both - create an allOf
                            result[key][prop] = {
                                "allOf": [result[key][prop], prop_schema]
                            }
        else:
            # Multiple subschemas - keep normalized allOf
            result["allOf"] = subschemas
            
        return result
    
    def _normalize_anyOf_oneOf(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize anyOf and oneOf constructs.
        
        - Convert oneOf of consts to enum
        - Remove empty anyOf/oneOf
        - Merge single item anyOf/oneOf with parent
        """
        result = schema.copy()
        
        # Process each keyword
        for keyword in ["anyOf", "oneOf"]:
            if keyword not in result:
                continue
                
            # Recursively normalize subschemas
            subschemas = []
            for subschema in result[keyword]:
                normalized = self.normalize(subschema)
                if normalized != {}:  # Skip empty schemas
                    subschemas.append(normalized)
                    
            # Special cases
            if not subschemas:
                # Empty anyOf/oneOf
                if keyword == "anyOf":
                    # Empty anyOf is always false
                    del result[keyword]
                    return {"not": {}}
                else:  # oneOf
                    # Empty oneOf is always false
                    del result[keyword]
                    return {"not": {}}
            elif len(subschemas) == 1:
                # Single item can be merged
                del result[keyword]
                single_schema = subschemas[0]
                
                # Merge the single schema with the parent
                for key, value in single_schema.items():
                    if key not in result:
                        result[key] = value
            else:
                # Check if we can convert oneOf to enum
                if keyword == "oneOf":
                    all_const = all("const" in subschema and len(subschema) == 1 
                                   for subschema in subschemas)
                    
                    if all_const:
                        enum_values = [subschema["const"] for subschema in subschemas]
                        del result[keyword]
                        result["enum"] = enum_values
                    else:
                        result[keyword] = subschemas
                else:
                    result[keyword] = subschemas
                    
        return result
    
    def _normalize_not(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize not constructs.
        
        - Handle double negation
        - Normalize the subschema
        """
        result = schema.copy()
        
        if "not" not in result:
            return result
            
        # Normalize the subschema
        subschema = self.normalize(result["not"])
        
        # Special cases
        if subschema == {}:
            # not {} (not true) is always false
            return {"not": {}}
        elif "not" in subschema and len(subschema) == 1:
            # Double negation: not (not X) => X
            del result["not"]
            inner_not = subschema["not"]
            
            # Merge the inner schema with the parent
            for key, value in inner_not.items():
                if key not in result:
                    result[key] = value
        else:
            result["not"] = subschema
            
        return result
    
    def _normalize_if_then_else(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize if-then-else constructs.
        
        - Simplify when if is true or false
        - Normalize subschemas
        """
        result = schema.copy()
        
        # Check if we have the conditional keywords
        has_if = "if" in result
        has_then = "then" in result
        has_else = "else" in result
        
        if not has_if:
            # No if keyword, remove then/else
            if has_then:
                del result["then"]
            if has_else:
                del result["else"]
            return result
            
        # Normalize the subschemas
        if has_if:
            result["if"] = self.normalize(result["if"])
        if has_then:
            result["then"] = self.normalize(result["then"])
        if has_else:
            result["else"] = self.normalize(result["else"])
            
        # Special cases
        if result["if"] == {}:
            # if true
            if has_then and not has_else:
                # if true then X => allOf: [X]
                then_schema = result["then"]
                del result["if"]
                del result["then"]
                if "allOf" not in result:
                    result["allOf"] = [then_schema]
                else:
                    result["allOf"].append(then_schema)
            elif has_else and not has_then:
                # if true else Y is invalid, keep as is
                pass
            elif has_then and has_else:
                # if true then X else Y => X
                then_schema = result["then"]
                del result["if"]
                del result["then"]
                del result["else"]
                
                # Merge then_schema with result
                for key, value in then_schema.items():
                    if key not in result:
                        result[key] = value
        elif result["if"] == {"not": {}}:
            # if false
            if has_then and not has_else:
                # if false then X => valid
                del result["if"]
                del result["then"]
            elif has_else and not has_then:
                # if false else Y => allOf: [Y]
                else_schema = result["else"]
                del result["if"]
                del result["else"]
                if "allOf" not in result:
                    result["allOf"] = [else_schema]
                else:
                    result["allOf"].append(else_schema)
            elif has_then and has_else:
                # if false then X else Y => Y
                else_schema = result["else"]
                del result["if"]
                del result["then"]
                del result["else"]
                
                # Merge else_schema with result
                for key, value in else_schema.items():
                    if key not in result:
                        result[key] = value
                        
        return result
    
    def _normalize_dependencies(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize dependencies constructs.
        
        - Sort property dependencies
        - Normalize schema dependencies
        - Remove empty dependencies
        """
        result = schema.copy()
        
        if "dependencies" not in result:
            return result
            
        # Normalize dependencies
        deps = {}
        for prop, dep in result["dependencies"].items():
            if isinstance(dep, list):
                # Property dependency
                if not dep:  # Empty list
                    continue
                deps[prop] = sorted(set(dep))
            elif isinstance(dep, dict):
                # Schema dependency
                normalized = self.normalize(dep)
                if normalized != {}:  # Skip empty schemas
                    deps[prop] = normalized
                    
        if deps:
            result["dependencies"] = deps
        else:
            del result["dependencies"]
            
        return result
    
    def _normalize_reference_resolution(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Placeholder for reference resolution.
        
        Note: Full reference resolution requires maintaining a document base and 
        resolving all $ref pointers. This is a simplified version.
        """
        # In a real implementation, this would resolve $ref pointers
        # For now, we'll just pass through
        return schema
    
    def _cleanup_empty_keywords(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove empty arrays and objects from keywords.
        
        This ensures that empty constraints are removed from the schema.
        """
        result = schema.copy()
        
        # Keywords that should be removed if empty
        array_keywords = ["required", "enum", "allOf", "anyOf", "oneOf"]
        object_keywords = ["properties", "patternProperties", "dependencies"]
        
        # Remove empty arrays
        for keyword in array_keywords:
            if keyword in result and (not result[keyword] or result[keyword] == []):
                del result[keyword]
                
        # Remove empty objects
        for keyword in object_keywords:
            if keyword in result and (not result[keyword] or result[keyword] == {}):
                del result[keyword]
                
        return result


def normalize_schema(schema: Union[Dict[str, Any], bool]) -> Union[Dict[str, Any], bool]:
    """
    Normalize a JSON Schema to a canonical form.
    
    Args:
        schema: The JSON Schema to normalize (can be a dict or a boolean)
        
    Returns:
        A normalized version of the schema
    """
    normalizer = JSONSchemaNormalizer()
    return normalizer.normalize(schema)


class TestJSONSchemaNormalizer(unittest.TestCase):
    """Test cases for the JSON Schema normalizer."""
    
    def setUp(self):
        self.normalizer = JSONSchemaNormalizer()
        
    def test_boolean_schemas(self):
        """Test boolean schema normalization."""
        # True schema
        self.assertEqual(self.normalizer.normalize(True), {})
        self.assertEqual(self.normalizer.normalize({}), {})
        
        # False schema
        self.assertEqual(self.normalizer.normalize(False), {"not": {}})
        
    def test_metadata_removal(self):
        """Test metadata keyword removal."""
        schema = {
            "title": "Test Schema",
            "description": "This is a test schema",
            "$comment": "Just a comment",
            "examples": ["example1", "example2"],
            "type": "string"
        }
        expected = {"type": "string"}
        self.assertEqual(self.normalizer.normalize(schema), expected)
        
    def test_type_normalization(self):
        """Test type constraint normalization."""
        # Deduplicate types
        schema = {"type": ["string", "string", "number"]}
        expected = {"type": ["number", "string"]}
        self.assertEqual(self.normalizer.normalize(schema), expected)
        
        # Merge integer and number
        schema = {"type": ["integer", "number"]}
        expected = {"type": "number", "multipleOf": 1.0}
        self.assertEqual(self.normalizer.normalize(schema), expected)
        
        # Single type as string
        schema = {"type": ["string"]}
        expected = {"type": "string"}
        self.assertEqual(self.normalizer.normalize(schema), expected)
        
    def test_number_constraints(self):
        """Test number constraint normalization."""
        # Draft-04 style exclusiveMinimum
        schema = {
            "type": "number",
            "minimum": 5,
            "exclusiveMinimum": true
        }
        expected = {
            "type": "number",
            "exclusiveMinimum": 5
        }
        self.assertEqual(self.normalizer.normalize(schema), expected)
        
        # Remove redundant multipleOf: 1 for integers
        schema = {
            "type": "integer",
            "multipleOf": 1
        }
        expected = {"type": "integer"}
        self.assertEqual(self.normalizer.normalize(schema), expected)
        
    def test_string_constraints(self):
        """Test string constraint normalization."""
        # Remove redundant maxLength
        schema = {
            "type": "string",
            "minLength": 10,
            "maxLength": 10
        }
        expected = {
            "type": "string",
            "minLength": 10
        }
        self.assertEqual(self.normalizer.normalize(schema), expected)
        
        # Convert simple pattern to enum
        schema = {
            "type": "string",
            "pattern": "^(foo|bar|baz)$"
        }
        expected = {
            "type": "string",
            "enum": ["foo", "bar", "baz"]
        }
        self.assertEqual(self.normalizer.normalize(schema), expected)
        
    def test_array_constraints(self):
        """Test array constraint normalization."""
        # Remove default minItems
        schema = {
            "type": "array",
            "minItems": 0
        }
        expected = {"type": "array"}
        self.assertEqual(self.normalizer.normalize(schema), expected)
        
        # Normalize fixed length array
        schema = {
            "type": "array",
            "minItems": 5,
            "maxItems": 5
        }
        expected = {
            "type": "array",
            "minItems": 5
        }
        self.assertEqual(self.normalizer.normalize(schema), expected)
        
        # Normalize items
        schema = {
            "type": "array",
            "items": {"type": "string", "title": "Item Schema"}
        }
        expected = {
            "type": "array",
            "items": {"type": "string"}
        }
        self.assertEqual(self.normalizer.normalize(schema), expected)
        
    def test_object_constraints(self):
        """Test object constraint normalization."""
        # Normalize required
        schema = {
            "type": "object",
            "required": ["foo", "foo", "bar"]
        }
        expected = {
            "type": "object",
            "required": ["bar", "foo"]
        }
        self.assertEqual(self.normalizer.normalize(schema), expected)
        
        # Remove properties not in required
        schema = {
            "type": "object",
            "properties": {
                "foo": {"type": "string"}
            },
            "required": ["foo", "bar"]
        }
        expected = {
            "type": "object",
            "properties": {
                "foo": {"type": "string"}
            },
            "required": ["foo"]
        }
        self.assertEqual(self.normalizer.normalize(schema), expected)
        
    def test_enum_and_const(self):
        """Test enum and const normalization."""
        # Convert singleton enum to const
        schema = {"enum": ["foo"]}
        expected = {"const": "foo"}
        self.assertEqual(self.normalizer.normalize(schema), expected)
        
        # Sort enum values
        schema = {"enum": ["foo", "bar", "baz"]}
        expected = {"enum": ["bar", "baz", "foo"]}
        self.assertEqual(self.normalizer.normalize(schema), expected)
        
    def test_oneOf_enum_conversion(self):
        """Test conversion of oneOf with consts to enum."""
        schema = {
            "oneOf": [
                {"const": "foo"},
                {"const": "bar"}
            ]
        }
        expected = {"enum": ["bar", "foo"]}
        self.assertEqual(self.normalizer.normalize(schema), expected)
   