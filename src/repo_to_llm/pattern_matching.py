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

def collect_files(input_dir: Path, ignore_matcher, script_path: Path, max_bytes: int,
                  exclude_patterns: set | None = None) -> list:
    files = []

    for root, dirs, filenames in os.walk(input_dir):
        root_path = Path(root)

        # Determine which directories to skip BEFORE descending
        dirs[:] = [
            d for d in dirs
            if not should_exclude(root_path / d, input_dir, ignore_matcher, script_path, max_bytes, exclude_patterns)
        ]

        for filename in filenames:
            file_path = root_path / filename
            try:
                if not should_exclude(file_path, input_dir, ignore_matcher, script_path, max_bytes, exclude_patterns):
                    files.append(file_path)
            except Exception as e:
                logger.warning(f"Error processing {file_path}: {e}")
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

        # List and filter directory entries (hide dotfiles and .gitignore-matched entries)
        try:
            entries = [e for e in path.iterdir() if not e.name.startswith('.') and not ignore_matcher(str(e))]
        except Exception as e:
            output.append(f"{prefix}    [Error reading directory: {e}]")
            return

        # Filter directories using the same exclusion logic used for files so we do not descend into excluded dirs
        dirs = sorted(
            [e for e in entries if e.is_dir() and not should_exclude(e, input_dir, ignore_matcher, script_path, max_bytes, exclude_patterns)]
        )

        # Files: apply should_exclude as before
        files = sorted(
            [e for e in entries if e.is_file() and not should_exclude(e, input_dir, ignore_matcher, script_path, max_bytes, exclude_patterns)]
        )

        # Iterate directories first, then files (compute last correctly)
        for i, d in enumerate(dirs):
            # A directory is "last" only if it's the last directory AND there are no files
            last_dir = (i == len(dirs) - 1) and (len(files) == 0)
            new_prefix = prefix + ('    ' if is_last else '│   ')
            walk_dir(d, new_prefix, last_dir)

        for i, f in enumerate(files):
            last_file = (i == len(files) - 1)
            connector = '└── ' if last_file else '├── '
            new_prefix = prefix + ('    ' if is_last else '│   ')
            output.append(f"{new_prefix}{connector}{f.name}")

    walk_dir(input_dir)
    return '\n'.join(output)

def guess_language(path: Path) -> str:
    ext = path.suffix.lower()
    return config.extension_mapping.get(ext, 'text')