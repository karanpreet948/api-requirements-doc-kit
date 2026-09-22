"""
apidoc.cli
==========

Command line interface for the API Requirements Documentation Kit.

Example:
    python -m apidoc generate \\
        --spec examples/customer_profile_api.yaml \\
        --output out/customer_profile_api_requirements.md
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from apidoc.generator import generate_markdown
from apidoc.parser import ApiSpecError, parse_spec

logger = logging.getLogger("apidoc")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apidoc",
        description=(
            "Generates a Business-Analyst-style API integration "
            "requirements document (Markdown) from an OpenAPI 3.0 YAML "
            "specification."
        ),
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser(
        "generate",
        help="Generate a requirements document from an OpenAPI spec.",
    )
    generate.add_argument(
        "--spec",
        required=True,
        type=Path,
        help="Path to the OpenAPI 3.0 YAML specification file.",
    )
    generate.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to write the generated Markdown requirements document to.",
    )

    return parser


def run_generate(spec_path: Path, output_path: Path) -> int:
    """Runs the 'generate' subcommand. Returns a process exit code."""
    try:
        parsed_spec = parse_spec(spec_path)
        document = generate_markdown(parsed_spec)
    except ApiSpecError as exc:
        logger.error("Could not generate requirements document: %s", exc)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    logger.info(
        "Wrote requirements document for '%s' (%d endpoint(s)) to %s",
        parsed_spec.info.title,
        len(parsed_spec.operations),
        output_path,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    argument_parser = _build_parser()
    args = argument_parser.parse_args(argv)
    _configure_logging(args.verbose)

    if args.command == "generate":
        return run_generate(args.spec, args.output)

    argument_parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
