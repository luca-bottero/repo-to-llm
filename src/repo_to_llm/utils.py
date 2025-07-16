import argparse
import re

def parse_size(size_str: str) -> int:
    """Parse size strings like '300kb', '2mb' into bytes."""
    size_str = size_str.strip().lower()
    match = re.match(r'^(\d+(?:\.\d+)?)([kmgt]?b)?$', size_str)
    if not match:
        raise argparse.ArgumentTypeError(f"Invalid size format: {size_str}")
    number, unit = match.groups()
    number = float(number)
    unit_multipliers = {
        None: 1,
        'b': 1,
        'kb': 10**3,
        'mb': 10**6,
        'gb': 10**9,
        'tb': 10**12,
    }
    multiplier = unit_multipliers.get(unit, None)
    if multiplier is None:
        raise argparse.ArgumentTypeError(f"Unknown size unit: {unit}")
    return int(number * multiplier)