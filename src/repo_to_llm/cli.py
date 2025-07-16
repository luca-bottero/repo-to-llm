import argparse
import sys
from pathlib import Path
import logging
import re

from repo_to_llm.core import generate_report
from repo_to_llm.utils import parse_size
from repo_to_llm.config import config

logger = logging.getLogger("repo-to-llm")

def main():
    parser = argparse.ArgumentParser(description="Dump directory tree and file contents for LLM input.")
    parser.add_argument('input_dir', type=Path, help="Input directory")
    parser.add_argument('--output', type=Path, help="Output file (if omitted, prints to stdout)")
    parser.add_argument('--print', action='store_true', help="Print to stdout (default behavior)")
    parser.add_argument('--max-bytes', type=parse_size, default=config.max_bytes, 
                        help="Maximum file size to include (e.g. 300kb, 1mb). Default is 500000 bytes.")
    parser.add_argument('--verbose', action='store_true', help="Enable debug output")
    parser.add_argument('--exclude-tree', action='store_true', help="Exclude directory tree structure from report")
    parser.add_argument(
        "--exclude-patterns",
        type=str,
        nargs="*",
        help="Space-separated glob patterns to exclude files or directories, e.g. --exclude-patterns '*.py' 'test/*'"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if not args.input_dir.is_dir():
        logger.error(f"{args.input_dir} is not a directory")
        sys.exit(1)

    exclude_patterns = args.exclude_patterns if args.exclude_patterns else []
    logger.debug(f"Excluding patterns: {exclude_patterns}")

    report = generate_report(
        args.input_dir,
        Path(__file__).resolve(),
        max_bytes=args.max_bytes,
        exclude_tree=args.exclude_tree,
        exclude_patterns=exclude_patterns
    )

    if args.output:
        output_path = args.output.with_suffix(args.output.suffix)
        output_path.write_text(report, encoding='utf-8')
        logger.info(f"Wrote output to {output_path}")
    else:
        print(report)
