import argparse
import sys
from pathlib import Path
import logging

# Import your core functions here
from .core import generate_report

logger = logging.getLogger("repo-to-llm")

def main():
    parser = argparse.ArgumentParser(description="Dump directory tree and file contents for LLM input.")
    parser.add_argument('input_dir', type=Path, help="Input directory")
    parser.add_argument('output_file', type=Path, nargs='?', help="Optional output file")
    parser.add_argument('--print', action='store_true', help="Print to stdout instead of writing to a file")
    parser.add_argument('--max-bytes', type=int, default=500_000, help="Maximum file size to include (defaul 500 KB)")
    parser.add_argument('--verbose', action='store_true', help="Enable debug output")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if not args.input_dir.is_dir():
        logger.error(f"{args.input_dir} is not a directory")
        sys.exit(1)

    report = generate_report(args.input_dir, Path(__file__).resolve(), args.max_bytes)

    if args.print:
        print(report)
    elif args.output_file:
        output_path = args.output_file.with_suffix(args.output_file.suffix + '.repo-to-llm.md')
        output_path.write_text(report, encoding='utf-8')
        logger.info(f"Wrote output to {output_path}")
    else:
        logger.error("Specify either --stdout or an output file path")
        sys.exit(1)
