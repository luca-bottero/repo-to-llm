import argparse
import sys
from pathlib import Path
import logging
import re

# Import your core functions here
from .core import generate_report, DEFAULT_MAX_BYTES
from .utils import parse_size

logger = logging.getLogger("repo-to-llm")

def main():
    parser = argparse.ArgumentParser(description="Dump directory tree and file contents for LLM input.")
    parser.add_argument('input_dir', type=Path, help="Input directory")
    parser.add_argument('--output', type=Path, help="Output file (if omitted, prints to stdout)")
    parser.add_argument('--print', action='store_true', help="Print to stdout (default behavior)")
    parser.add_argument('--max-bytes', type=parse_size, default=DEFAULT_MAX_BYTES, 
                        help="Maximum file size to include (e.g. 300kb, 1mb). Default is 500000 bytes.")
    parser.add_argument('--verbose', action='store_true', help="Enable debug output")
    parser.add_argument('--exclude-tree', action='store_true', help="Exclude directory tree structure from report")
    parser.add_argument('--exclude-extensions', type=str,
                        help="Comma-separated list of file extensions to exclude, e.g. '.py, .js'")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if not args.input_dir.is_dir():
        logger.error(f"{args.input_dir} is not a directory")
        sys.exit(1)

    exclude_exts = None
    if args.exclude_extensions:
        exclude_exts = {ext.strip().lower() for ext in args.exclude_extensions.split(',') if ext.strip()}
        logger.debug(f"Excluding extensions: {exclude_exts}")

    report = generate_report(
        args.input_dir,
        Path(__file__).resolve(),
        max_bytes=args.max_bytes,
        exclude_tree=args.exclude_tree,
        exclude_extensions=exclude_exts
    )

    if args.output:
        output_path = args.output.with_suffix(args.output.suffix)
        output_path.write_text(report, encoding='utf-8')
        logger.info(f"Wrote output to {output_path}")
    else:
        print(report)
