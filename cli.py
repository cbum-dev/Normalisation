#!/usr/bin/env python3
"""
JSON Schema Normalizer CLI

A command-line tool for normalizing JSON Schema documents.
"""

import argparse
import json
import sys
from pathlib import Path
from normaliser import normalize_schema, SchemaNormalizer


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Normalize JSON Schema documents to a canonical form"
    )
    
    parser.add_argument(
        "input",
        nargs="?",
        type=str,
        help="Input JSON Schema file (or use stdin if not specified)"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file (default is stdout)"
    )
    
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the output JSON"
    )
    
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Explain the transformations applied"
    )
    
    parser.add_argument(
        "--no-strip-meta",
        action="store_true",
        help="Don't strip non-validation metadata like title and description"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Read input schema
    if args.input:
        with open(args.input, 'r') as f:
            try:
                schema = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        # Read from stdin
        try:
            schema = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from stdin: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Create normalizer with customized rules if needed
    normalizer = SchemaNormalizer()
    
    # Apply normalization