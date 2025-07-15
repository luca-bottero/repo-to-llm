import os
import fnmatch
from pathlib import Path
import logging
from gitignore_parser import parse_gitignore

DEFAULT_MAX_BYTES = 500_000
EXCLUDED_PATTERNS = [
    ".git/*",
    ".*",
    "*.log",
    "*.log.*",
    "*.ipynb",
]

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


def should_exclude(path: Path, input_dir: Path, ignore_matcher, script_path: Path, max_bytes: int, exclude_extensions: set | None = None) -> bool:
    if path.resolve() == script_path.resolve():
        return True

    relative_str = str(path.relative_to(input_dir))

    if ignore_matcher(str(path)):
        return True

    for pattern in EXCLUDED_PATTERNS:
        if fnmatch.fnmatch(relative_str, pattern):
            return True

    if exclude_extensions:
        if path.suffix.lower() in exclude_extensions:
            logger.debug(f"Excluding {path} due to extension in exclude list")
            return True

    if path.stat().st_size > max_bytes:
        logger.debug(f"Skipping {path} due to size > {max_bytes} bytes")
        return True

    if not is_text_file(path):
        logger.debug(f"Skipping {path} due to binary type")
        return True

    return False


def collect_files(input_dir: Path, ignore_matcher, script_path: Path, max_bytes: int, exclude_extensions: set | None = None) -> list:
    files = []
    for path in input_dir.rglob('*'):
        try:
            if path.is_file() and not should_exclude(path, input_dir, ignore_matcher, script_path, max_bytes, exclude_extensions):
                files.append(path)
        except Exception as e:
            logger.warning(f"Error processing {path}: {e}")
    return files

def generate_tree(input_dir: Path, ignore_matcher, script_path: Path, max_bytes: int, exclude_extensions: set | None = None) -> str:
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
        files = sorted([e for e in entries if e.is_file() and not should_exclude(e, input_dir, ignore_matcher, script_path, max_bytes, exclude_extensions)])

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
    mapping = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.html': 'html',
        '.css': 'css',
        '.json': 'json',
        '.md': 'markdown',
        '.sh': 'bash',
        '.yml': 'yaml',
        '.yaml': 'yaml',
        '.txt': 'text'
    }
    return mapping.get(ext, 'text')

def generate_report(
    input_dir: Path,
    script_path: Path,
    max_bytes: int,
    exclude_tree: bool = False,
    exclude_extensions: set | None = None
) -> str:
    gitignore_path = input_dir / '.gitignore'
    ignore_matcher = parse_gitignore(gitignore_path) if gitignore_path.exists() else lambda path: False

    output = []

    if not exclude_tree:
        output.append("## Directory Tree\n")
        output.append("```")
        output.append(generate_tree(input_dir, ignore_matcher, script_path, max_bytes, exclude_extensions))
        output.append("```\n\n")

    output.append("## File Contents\n")
    files = collect_files(input_dir, ignore_matcher, script_path, max_bytes, exclude_extensions)

    for file in sorted(files):
        rel_path = file.relative_to(input_dir)
        lang = guess_language(file)
        output.append(f"### {rel_path}\n")
        output.append(f"```{lang}")
        try:
            content = file.read_text(encoding='utf-8')
        except Exception as e:
            content = f"[Error reading file: {e}]"
        output.append(content.rstrip())
        output.append("```")
        output.append("")

    return '\n'.join(output)
