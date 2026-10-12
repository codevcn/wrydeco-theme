"""Versioned AEO module. Core functions are pure; Shopify writes use an adapter."""
from .core import build_input, validate_and_render, normalize_draft, schema

VERSION = 1

__all__ = ["VERSION", "build_input", "validate_and_render", "normalize_draft", "schema"]
