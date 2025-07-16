import os
import fnmatch
from pathlib import Path
import logging

from repo_to_llm.config import config

logger = logging.getLogger("repo-to-llm")

def is_text_file(path: Path, blocksize: int = 512) -> bool:
    try:
        with open(path, 'rb') as f:
            block = f.read(blocksize)
        if b'\0' in block:
            return False
        return True
    except Exception as e:
        logger.debug(f"Error reading {path}: {e}")
        return False

def should_exclude(path: Path, input_dir: Path, ignore_matcher, script_path: Path, max_bytes: int, exclude_patterns: set | None = None) -> bool:
    if path.resolve() == script_path.resolve():
        return True

    relative_str = str(path.relative_to(input_dir))

    if ignore_matcher(str(path)):
        logger.debug(f"Skipping {path} because of inclusion in .gitignore")
        return True

    for pattern in config.excluded_patterns:
        if fnmatch.fnmatch(relative_str, pattern):
            logger.debug(f"Skipping {path} because in config.excluded_patterns")
            return True

    if exclude_patterns:
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(relative_str, pattern):
                logger.debug(f"Excluding {relative_str} due to user pattern: {pattern}")
                return True

    if path.stat().st_size > max_bytes:
        logger.debug(f"Skipping {path} due to size > {max_bytes} bytes")
        return True

    if not is_text_file(path):
        logger.debug(f"Skipping {path} due to binary type")
        return True

    return False

def collect_files(input_dir: Path, ignore_matcher, script_path: Path, max_bytes: int, exclude_patterns: set | None = None) -> list:
    files = []
    for path in input_dir.rglob('*'):
        try:
            if path.is_file() and not should_exclude(path, input_dir, ignore_matcher, script_path, max_bytes, exclude_patterns):
                files.append(path)
        except Exception as e:
            logger.warning(f"Error processing {path}: {e}")
    return files

def generate_tree(input_dir: Path, ignore_matcher, script_path: Path, max_bytes: int, exclude_patterns: set | None = None) -> str:
    output = []

    def walk_dir(path: Path, prefix: str = '', is_last: bool = True):
        # Print the directory name
        connector = '└── ' if is_last else '├── '
        if prefix == '':
            output.append(f"{path.name}/")
        else:
            output.append(f"{prefix}{connector}{path.name}/")

        # List and filter directories
        try:
            entries = [e for e in path.iterdir() if not e.name.startswith('.') and not ignore_matcher(str(e))]
        except Exception as e:
            # Can't list directory contents
            output.append(f"{prefix}    [Error reading directory: {e}]")
            return

        dirs = sorted([e for e in entries if e.is_dir()])
        files = sorted([e for e in entries if e.is_file() and not should_exclude(e, input_dir, ignore_matcher, script_path, max_bytes, exclude_patterns)])

        total_entries = len(dirs) + len(files)

        for i, d in enumerate(dirs):
            last = (i == total_entries - 1) if len(files) == 0 else False
            # For prefix, add '│   ' if not last directory, else '    '
            new_prefix = prefix + ('    ' if is_last else '│   ')
            walk_dir(d, new_prefix, last)

        for i, f in enumerate(files):
            last = (i == len(files) - 1)
            connector = '└── ' if last else '├── '
            new_prefix = prefix + ('    ' if is_last else '│   ')
            output.append(f"{new_prefix}{connector}{f.name}")

    walk_dir(input_dir)

    return '\n'.join(output)

def guess_language(path: Path) -> str:
    ext = path.suffix.lower()
    return config.extension_mapping.get(ext, 'text')