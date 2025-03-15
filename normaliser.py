"""
JSON Schema Normalizer

A Python library for normalizing JSON Schema documents by applying
transformation rules that maintain validation equivalence.
"""

import json
from typing import Dict, List, Any, Union, Optional, Set, Tuple, Callable
import copy


class SchemaRule:
    """Base class for schema normalization rules"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def applies_to(self, schema: Dict[str, Any]) -> bool:
        """Check if this rule applies to the given schema."""
        raise NotImplementedError
    
    def apply(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Apply the rule to the schema and return the transformed schema."""
        raise NotImplementedError


class OneOfToEnumRule(SchemaRule):
    """Convert oneOf with const values to an enum."""
    
    def __init__(self):
        super().__init__(
            name="oneOf-to-enum",
            description="Convert oneOf with const values to an enum"
        )
    
    def applies_to(self, schema: Dict[str, Any]) -> bool:
        if "oneOf" not in schema:
            return False
        
        if not isinstance(schema["oneOf"], list):
            return False
        
        # Check if all items in oneOf are const schemas
        return all(
            isinstance(item, dict) and "const" in item and len(item) == 1
            for item in schema["oneOf"]
        )
    
    def apply(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        result = copy.deepcopy(schema)
        const_values = [item["const"] for item in result["oneOf"]]
        del result["oneOf"]
        result["enum"] = const_values
        return result


class RemoveNonValidationKeywordsRule(SchemaRule):
    """Remove keywords that don't affect validation."""
    
    NON_VALIDATION_KEYWORDS = {
        "title", "description", "$comment", "examples", "default",
        "readOnly", "writeOnly", "deprecated"
    }
    
    def __init__(self):
        super().__init__(
            name="remove-non-validation-keywords",
            description="Remove keywords that don't affect validation"
        )
    
    def applies_to(self, schema: Dict[str, Any]) -> bool:
        if not isinstance(schema, dict):
            return False
        
        # Check if any non-validation keywords are present
        return any(keyword in schema for keyword in self.NON_VALIDATION_KEYWORDS)
    
    def apply(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        result = copy.deepcopy(schema)
        for keyword in self.NON_VALIDATION_KEYWORDS:
            if keyword in result:
                del result[keyword]
        return result


class SimplifyBooleanSchemaRule(SchemaRule):
    """Simplify schemas that are equivalent to true or false."""
    
    def __init__(self):
        super().__init__(
            name="simplify-boolean-schema",
            description="Simplify schemas that are equivalent to true or false"
        )
    
    def applies_to(self, schema: Dict[str, Any]) -> bool:
        # Empty schema is equivalent to true
        if isinstance(schema, dict) and len(schema) == 0:
            return True
        
        # Schema with only non-validation keywords is equivalent to true
        if isinstance(schema, dict) and all(k in RemoveNonValidationKeywordsRule.NON_VALIDATION_KEYWORDS for k in schema):
            return True
        
        # Schema with impossible "type" requirements is equivalent to false
        if isinstance(schema, dict) and "type" in schema and "not" in schema and "type" in schema["not"]:
            if schema["type"] == schema["not"]["type"]:
                return True
            
            # Multiple types that are mutually exclusive
            if (isinstance(schema["type"], list) and 
                isinstance(schema["not"]["type"], list) and
                set(schema["type"]).issubset(set(schema["not"]["type"]))):
                return True
        
        return False
    
    def apply(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        # Determine if the schema is equivalent to true or false
        if isinstance(schema, dict):
            # Empty schema or schema with only non-validation keywords -> true
            if len(schema) == 0 or all(k in RemoveNonValidationKeywordsRule.NON_VALIDATION_KEYWORDS for k in schema):
                return True
            
            # Schema with impossible type requirements -> false
            if "type" in schema and "not" in schema and "type" in schema["not"]:
                if schema["type"] == schema["not"]["type"]:
                    return False
                if (isinstance(schema["type"], list) and 
                    isinstance(schema["not"]["type"], list) and
                    set(schema["type"]).issubset(set(schema["not"]["type"]))):
                    return False
                
        return schema


class SimplifyArrayItemsRule(SchemaRule):
    """Simplify array schemas with redundant items definitions."""
    
    def __init__(self):
        super().__init__(
            name="simplify-array-items",
            description="Simplify array schemas with redundant items definitions"
        )
    
    def applies_to(self, schema: Dict[str, Any]) -> bool:
        if not isinstance(schema, dict):
            return False
        
        if "type" not in schema or schema["type"] != "array":
            return False
        
        # Check if both items and additionalItems are present
        if "items" in schema and "additionalItems" in schema:
            # If items is an object, additionalItems is redundant
            if isinstance(schema["items"], dict):
                return True
            
            # If items is an empty array, additionalItems defines all items
            if isinstance(schema["items"], list) and len(schema["items"]) == 0:
                return True
        
        return False
    
    def apply(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        result = copy.deepcopy(schema)
        
        # If items is an object, additionalItems is redundant
        if isinstance(result["items"], dict):
            del result["additionalItems"]
        
        # If items is an empty array, additionalItems defines all items
        elif isinstance(result["items"], list) and len(result["items"]) == 0:
            result["items"] = result["additionalItems"]
            del result["additionalItems"]
        
        return result


class MergeAllOfRule(SchemaRule):
    """Merge allOf schemas where possible."""
    
    def __init__(self):
        super().__init__(
            name="merge-allOf",
            description="Merge allOf schemas into a single schema where possible"
        )
    
    def applies_to(self, schema: Dict[str, Any]) -> bool:
        return isinstance(schema, dict) and "allOf" in schema and isinstance(schema["allOf"], list)
    
    def apply(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        result = copy.deepcopy(schema)
        all_of = result["allOf"]
        
        # If allOf has only one schema, replace with that schema
        if len(all_of) == 1:
            single_schema = all_of[0]
            del result["allOf"]
            
            # Merge the single schema with the parent
            if isinstance(single_schema, dict):
                for key, value in single_schema.items():
                    result[key] = value
            else:
                # If single_schema is a boolean, handle appropriately
                return single_schema
        
        # For now, we'll only handle simple cases
        # A more complete implementation would handle complex merging
        
        return result


class SimplifyBooleanLogicRule(SchemaRule):
    """Simplify boolean logic in anyOf, oneOf, allOf, not."""
    
    def __init__(self):
        super().__init__(
            name="simplify-boolean-logic",
            description="Simplify boolean logic expressions in schemas"
        )
    
    def applies_to(self, schema: Dict[str, Any]) -> bool:
        if not isinstance(schema, dict):
            return False
        
        # Check for boolean logic keywords
        boolean_keywords = {"anyOf", "oneOf", "allOf", "not"}
        return any(keyword in schema for keyword in boolean_keywords)
    
    def apply(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        result = copy.deepcopy(schema)
        
        # Handle allOf
        if "allOf" in result:
            all_of = result["allOf"]
            
            # Remove any true values as they don't add constraints
            all_of = [s for s in all_of if s is not True]
            
            # If any value is false, the entire allOf is false
            if any(s is False for s in all_of):
                return False
            
            # If empty after filtering, it's equivalent to true
            if len(all_of) == 0:
                del result["allOf"]
            elif len(all_of) == 1:
                # Replace allOf with single schema
                single_schema = all_of[0]
                del result["allOf"]
                if isinstance(single_schema, dict):
                    for key, value in single_schema.items():
                        result[key] = value
                else:
                    # Handle boolean case
                    return single_schema
            else:
                result["allOf"] = all_of
        
        # Handle anyOf
        if "anyOf" in result:
            any_of = result["anyOf"]
            
            # If any value is true, the entire anyOf is true
            if any(s is True for s in any_of):
                return True
            
            # Remove any false values as they don't add possibilities
            any_of = [s for s in any_of if s is not False]
            
            # If empty after filtering, it's equivalent to false
            if len(any_of) == 0:
                return False
            elif len(any_of) == 1:
                # Replace anyOf with single schema
                single_schema = any_of[0]
                del result["anyOf"]
                if isinstance(single_schema, dict):
                    for key, value in single_schema.items():
                        result[key] = value
                else:
                    return single_schema
            else:
                result["anyOf"] = any_of
        
        # Handle oneOf
        if "oneOf" in result:
            one_of = result["oneOf"]
            
            # Remove any false values as they don't add possibilities
            one_of = [s for s in one_of if s is not False]
            
            # If only one schema remains, replace oneOf with it
            if len(one_of) == 1:
                single_schema = one_of[0]
                del result["oneOf"]
                if isinstance(single_schema, dict):
                    for key, value in single_schema.items():
                        result[key] = value
                else:
                    return single_schema
            else:
                result["oneOf"] = one_of
        
        # Handle not
        if "not" in result:
            not_schema = result["not"]
            
            # not true -> false
            if not_schema is True:
                return False
            
            # not false -> true
            if not_schema is False:
                return True
            
            # not (not X) -> X
            if isinstance(not_schema, dict) and len(not_schema) == 1 and "not" in not_schema:
                del result["not"]
                inner_schema = not_schema["not"]
                if isinstance(inner_schema, dict):
                    for key, value in inner_schema.items():
                        result[key] = value
                else:
                    return inner_schema
        
        return result


class DeDuplicateEnumRule(SchemaRule):
    """Remove duplicate values from enum arrays."""
    
    def __init__(self):
        super().__init__(
            name="deduplicate-enum",
            description="Remove duplicate values from enum arrays"
        )
    
    def applies_to(self, schema: Dict[str, Any]) -> bool:
        if not isinstance(schema, dict) or "enum" not in schema:
            return False
        
        # Check if enum has duplicate values
        enum_values = schema["enum"]
        return len(enum_values) != len(set(map(self._make_hashable, enum_values)))
    
    def _make_hashable(self, value):
        """Convert a value to a hashable type for deduplication."""
        if isinstance(value, dict):
            return tuple(sorted((k, self._make_hashable(v)) for k, v in value.items()))
        elif isinstance(value, list):
            return tuple(self._make_hashable(v) for v in value)
        return value
    
    def apply(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        result = copy.deepcopy(schema)
        
        # Use a set to track seen values, preserving original order
        seen = set()
        unique_values = []
        
        for value in result["enum"]:
            hashable_value = self._make_hashable(value)
            if hashable_value not in seen:
                seen.add(hashable_value)
                unique_values.append(value)
        
        result["enum"] = unique_values
        return result


class SchemaNormalizer:
    """
    JSON Schema normalizer that applies a series of transformation rules
    to convert schemas into a canonical form.
    """
    
    def __init__(self, rules: Optional[List[SchemaRule]] = None):
        self.rules = rules or self._default_rules()
    
    @staticmethod
    def _default_rules() -> List[SchemaRule]:
        """Create the default set of normalization rules."""
        return [
            OneOfToEnumRule(),
            RemoveNonValidationKeywordsRule(),
            SimplifyBooleanSchemaRule(),
            SimplifyArrayItemsRule(),
            MergeAllOfRule(),
            SimplifyBooleanLogicRule(),
            DeDuplicateEnumRule(),
        ]
    
    def normalize(self, schema: Union[Dict[str, Any], bool]) -> Union[Dict[str, Any], bool]:
        """
        Normalize a JSON Schema by applying transformation rules until no more rules apply.
        
        Args:
            schema: The JSON Schema to normalize
            
        Returns:
            The normalized schema
        """
        if not isinstance(schema, (dict, bool)):
            raise TypeError("Schema must be a dict or boolean value")
        
        # If schema is a boolean, it's already in canonical form
        if isinstance(schema, bool):
            return schema
        
        current_schema = copy.deepcopy(schema)
        
        # Apply rules recursively to subschemas
        current_schema = self._normalize_subschemas(current_schema)
        
        # Apply rules to the current schema until no more changes
        while True:
            changed = False
            
            for rule in self.rules:
                if rule.applies_to(current_schema):
                    new_schema = rule.apply(current_schema)
                    if new_schema != current_schema:
                        current_schema = new_schema
                        changed = True
                        
                        # If schema was reduced to a boolean, we're done
                        if isinstance(current_schema, bool):
                            return current_schema
                        
                        # Reapply recursive normalization since structure changed
                        current_schema = self._normalize_subschemas(current_schema)
                        break
            
            if not changed:
                break
        
        return current_schema
    
    def _normalize_subschemas(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively normalize all subschemas within the given schema."""
        if not isinstance(schema, dict):
            return schema
        
        result = copy.deepcopy(schema)
        
        # Process schema keywords that contain subschemas
        for keyword in self._get_subschema_keywords():
            if keyword in result:
                result[keyword] = self._normalize_keyword(result[keyword], keyword)
        
        return result
    
    def _normalize_keyword(self, value: Any, keyword: str) -> Any:
        """Normalize a keyword value based on its type."""
        if keyword in {"allOf", "anyOf", "oneOf", "prefixItems"}:
            # Array of schemas
            if isinstance(value, list):
                return [self.normalize(item) for item in value]
        
        elif keyword in {"not", "additionalItems", "items", "contains", "propertyNames", 
                         "additionalProperties", "unevaluatedItems", "unevaluatedProperties"}:
            # Single schema
            return self.normalize(value)
        
        elif keyword == "properties" and isinstance(value, dict):
            # Object with property schemas
            return {prop: self.normalize(schema) for prop, schema in value.items()}
        
        elif keyword == "patternProperties" and isinstance(value, dict):
            # Object with pattern property schemas
            return {pattern: self.normalize(schema) for pattern, schema in value.items()}
        
        elif keyword == "dependentSchemas" and isinstance(value, dict):
            # Object with dependent schemas
            return {prop: self.normalize(schema) for prop, schema in value.items()}
        
        elif keyword == "if":
            # if/then/else - normalize each part
            return self.normalize(value)
        
        return value
    
    def _get_subschema_keywords(self) -> List[str]:
        """Get all keywords that can contain subschemas."""
        return [
            "allOf", "anyOf", "oneOf", "not", 
            "items", "prefixItems", "additionalItems", "contains", 
            "properties", "patternProperties", "additionalProperties",
            "propertyNames", "if", "then", "else",
            "dependentSchemas", "unevaluatedItems", "unevaluatedProperties"
        ]


def normalize_schema(schema: Union[Dict[str, Any], bool]) -> Union[Dict[str, Any], bool]:
    """
    Normalize a JSON Schema using the default normalizer configuration.
    
    Args:
        schema: The JSON Schema to normalize
        
    Returns:
        The normalized schema
    """
    normalizer = SchemaNormalizer()
    return normalizer.normalize(schema)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        with open(input_file, 'r') as f:
            schema = json.load(f)
        
        normalizer = SchemaNormalizer()
        normalized = normalizer.normalize(schema)
        
        if len(sys.argv) > 2:
            output_file = sys.argv[2]
            with open(output_file, 'w') as f:
                json.dump(normalized, f, indent=2)
        else:
            print(json.dumps(normalized, indent=2))
    else:
        print("Usage: python normalizer.py input.json [output.json]")