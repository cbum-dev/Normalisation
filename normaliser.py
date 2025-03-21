import json
import copy
from typing import Any, Dict, List, Union, Set, Optional, Tuple

class JSONSchemaNormalizer:
    """
    A normalizer for JSON Schema that transforms schemas into a canonical form
    while preserving validation behavior.
    
    This implementation includes normalizations from:
    https://gist.github.com/cbum-dev/7ebfcd47d8448b8291371746cc06b66d
    """
    
    def normalize(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a JSON Schema by applying a series of transformations.
        
        Args:
            schema: The JSON Schema to normalize
            
        Returns:
            A normalized version of the schema
        """
        if not isinstance(schema, dict):
            return schema
            
        # Make a deep copy to avoid modifying the original
        result = copy.deepcopy(schema)
        
        # Apply normalizations in order
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
        """Normalize boolean schemas to their canonical form."""
        # Empty schema is equivalent to {"type": "any"}
        if schema == {}:
            return {}
            
        return schema
    
    def _remove_redundant_metadata(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Remove metadata keywords that don't affect validation."""
        metadata_keywords = {
            "title", "description", "$comment", "examples", 
            "readOnly", "writeOnly", "deprecated", "$id", "$schema"
        }
        
        return {k: v for k, v in schema.items() if k not in metadata_keywords}
    
    def _normalize_type_constraints(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize type constraints."""
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
            
            # Add minimum and multipleOf constraints if needed
            if "multipleOf" not in result:
                result["multipleOf"] = 1.0
                
        # Convert back to string if only one type
        if "type" in result and len(result["type"]) == 1:
            result["type"] = result["type"][0]
            
        return result
    
    def _normalize_number_constraints(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize constraints for numeric types."""
        result = schema.copy()
        
        # Skip if not a numeric type
        if "type" in result and result["type"] not in ["number", "integer"] and \
           not (isinstance(result["type"], list) and any(t in ["number", "integer"] for t in result["type"])):
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
        if "multipleOf" in result and result["multipleOf"] == 1 and "type" in result:
            if result["type"] == "integer" or \
               (isinstance(result["type"], list) and "integer" in result["type"] and "number" not in result["type"]):
                del result["multipleOf"]
                
        return result
    
    def _normalize_string_constraints(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize constraints for string types."""
        result = schema.copy()
        
        # Skip if not a string type
        if "type" in result and result["type"] != "string" and \
           not (isinstance(result["type"], list) and "string" in result["type"]):
            return result
            
        # Remove redundant maxLength: 0 if minLength >= 0
        if "minLength" in result and "maxLength" in result:
            if result["minLength"] >= result["maxLength"]:
                del result["maxLength"]
                
        # Replace pattern with enum if it's a simple enumeration pattern
        if "pattern" in result and result["pattern"].startswith("^(") and result["pattern"].endswith(")$"):
            # Check if pattern is a simple alternation
            pattern = result["pattern"][2:-2]  # Remove ^( and )$
            if "|" in pattern and not any(c in pattern for c in "[]{}()?*.+"):
                # Simple enumeration pattern
                values = [val for val in pattern.split("|") if val]
                result["enum"] = values
                del result["pattern"]
                
        return result
    
    def _normalize_array_constraints(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize constraints for array types."""
        result = schema.copy()
        
        # Skip if not an array type
        if "type" in result and result["type"] != "array" and \
           not (isinstance(result["type"], list) and "array" in result["type"]):
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
        """Normalize constraints for object types."""
        result = schema.copy()
        
        # Skip if not an object type
        if "type" in result and result["type"] != "object" and \
           not (isinstance(result["type"], list) and "object" in result["type"]):
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
                required = [prop for prop in required if prop in result["properties"]]
                
            if required:
                result["required"] = required
            else:
                del result["required"]
                
        # Remove default minProperties: 0
        if "minProperties" in result and result["minProperties"] == 0:
            del result["minProperties"]
            
        # Normalize property dependencies
        if "dependencies" in result:
            deps = {}
            for prop, dep in result["dependencies"].items():
                if isinstance(dep, list):
                    # Property dependency
                    if dep:  # Non-empty list
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
    
    def _normalize_enum_and_const(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize enum and const keywords."""
        result = schema.copy()
        
        # Deduplicate enum values
        if "enum" in result:
            # For simple types, we can deduplicate and sort
            try:
                # Try to convert to hashable types for deduplication
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
        """Normalize allOf constructs."""
        result = schema.copy()
        
        if "allOf" not in result:
            return result
            
        # Recursively normalize subschemas
        subschemas = []
        for subschema in result["allOf"]:
            normalized = self.normalize(subschema)
            if normalized != {}:  # Skip empty schemas
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
        """Normalize anyOf and oneOf constructs."""
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
        """Normalize not constructs."""
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
        """Normalize if-then-else constructs."""
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
        """Normalize dependencies constructs."""
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
        """Remove empty arrays and objects from keywords."""
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
    # Handle boolean schemas
    if schema is True:
        return {}
    elif schema is False:
        return {"not": {}}
        
    normalizer = JSONSchemaNormalizer()
    return normalizer.normalize(schema)


# Example usage
if __name__ == "__main__":
    # Example schemas from the description
    examples = [
        # Example 1: oneOf with consts vs enum
        {
            "oneOf": [
                {"const": "foo"},
                {"const": "bar"}
            ]
        },
        
        # Example 2: enum equivalent to example 1
        {"enum": ["foo", "bar"]},
        
        # Example 3: simple required
        {"required": ["foo"]},
        
        # Example 4: schema with title
        {
            "title": "My Schema",
            "required": ["foo"]
        },
        
        # Example 5: redundant type array
        {"type": ["string", "string", "number"]},
        
        # Example 6: allOf that can be simplified
        {
            "allOf": [
                {"minimum": 0},
                {"type": "integer"}
            ]
        },
        
        # Example 7: if-then that can be simplified
        {
            "if": {},
            "then": {"minimum": 0}
        },
        
        # Example 8: empty schema
        {},
        
        # Example 9: complex schema
        {
            "title": "Complex Schema",
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {
                    "type": "integer",
                    "minimum": 0,
                    "exclusiveMinimum": True
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 0
                },
                "status": {
                    "oneOf": [
                        {"const": "active"},
                        {"const": "inactive"}
                    ]
                }
            },
            "required": ["name", "name", "age"],
            "additionalProperties": True
        }
    ]
    
    # Normalize and print results
    for i, schema in enumerate(examples):
        print(f"Example {i+1}:")
        print("Original:", json.dumps(schema, indent=2))
        print("Normalized:", json.dumps(normalize_schema(schema), indent=2))
        print()