"""
apidoc
======

API Requirements Documentation Kit.

A small toolkit that reads a machine-readable OpenAPI 3.0 specification
(YAML) and produces a human-readable, Business-Analyst-style "API
Integration Requirements Document" in Markdown.

The package is intentionally dependency-light: the parser reads the
OpenAPI document structure directly with PyYAML rather than depending on
a full OpenAPI object model library, since the goal is to extract a
handful of well-known sections (paths, parameters, request/response
schemas, and documented responses) rather than to fully validate or
execute the spec.

Public entry points:

* :mod:`apidoc.parser` -- parses an OpenAPI YAML file into plain
  dataclasses that are easy to render from.
* :mod:`apidoc.generator` -- renders those dataclasses into a Markdown
  requirements document.
* :mod:`apidoc.cli` -- the command line interface (``python -m apidoc``).
"""

__version__ = "1.0.0"
