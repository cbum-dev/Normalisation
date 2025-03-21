# setup.py
from setuptools import setup, find_packages

setup(
    name="json-schema-normalizer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        'console_scripts': [
            'normalize-schema=json_schema_normalizer:cli',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool for normalizing JSON Schema to canonical forms",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/json-schema-normalizer",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)

# pyproject.toml
"""
[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"
"""

# README.md
"""
# JSON Schema Normalizer

A Python library for normalizing JSON Schema documents to canonical form.

## Installation

```
pip install json-schema-normalizer
```

## Usage

### Command Line

```
normalize-schema input.json output.json
```

### Python API

```python
from json_schema_normalizer import JSONSchemaNormalizer

# Create a normalizer with default settings
normalizer = JSONSchemaNormalizer()

# Or with custom configuration
normalizer = JSONSchemaNormalizer({
    "remove_non_validation_keywords": True,
    "normalize_const_to_enum": True,
    # ... other options
})

# Normalize a schema
schema = {
    "oneOf": [
        {"const": "foo"},
        {"const": "bar"}
    ]
}
normalized = normalizer.normalize(schema)
# Result: {"enum": ["foo", "bar"]}

# Check if two schemas are equivalent
is_same = normalizer.is_equivalent(schema1, schema2)
```

## Configuration Options

- `remove_non_validation_keywords`: Remove keywords like title, description, etc.
- `simplify_boolean_logic`: Simplify allOf, anyOf, oneOf structures
- `normalize_const_to_enum`: Convert oneOf with const values to enum
- `normalize_enum_to_const`: Convert single-item enum to const
- `simplify_numeric_ranges`: Simplify numeric range constraints
- `simplify_string_constraints`: Simplify string pattern constraints
- `remove_redundant_constraints`: Remove redundant or overlapping constraints

## License

MIT
"""

# json_schema_normalizer/__init__.py
"""
from .normalizer import JSONSchemaNormalizer, cli

__all__ = ["JSONSchemaNormalizer", "cli"]
"""