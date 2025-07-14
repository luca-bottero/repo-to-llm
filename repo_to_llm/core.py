import os
import fnmatch
from pathlib import Path
import mimetypes
import logging
from gitignore_parser import parse_gitignore

EXCLUDED_PATTERNS = [
    ".git/*",
    ".*",
    "*.log",
    "*.log.*",
    "*repo-to-llm.md",
]
DEFAULT_MAX_BYTES = 500_000  # ~500 KB per file

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


def should_exclude(path: Path, input_dir: Path, ignore_matcher, script_path: Path, max_bytes: int) -> bool:
    if path.resolve() == script_path.resolve():
        return True

    relative_str = str(path.relative_to(input_dir))

    if ignore_matcher(str(path)):
        return True

    for pattern in EXCLUDED_PATTERNS:
        if fnmatch.fnmatch(relative_str, pattern):
            return True

    if path.stat().st_size > max_bytes:
        logger.debug(f"Skipping {path} due to size > {max_bytes} bytes")
        return True

    if not is_text_file(path):
        logger.debug(f"Skipping {path} due to binary type")
        return True

    return False

def collect_files(input_dir: Path, ignore_matcher, script_path: Path, max_bytes: int) -> list:
    files = []
    for path in input_dir.rglob('*'):
        try:
            if path.is_file() and not should_exclude(path, input_dir, ignore_matcher, script_path, max_bytes):
                files.append(path)
        except Exception as e:
            logger.warning(f"Error processing {path}: {e}")
    return files

def generate_tree(input_dir: Path, ignore_matcher, script_path: Path, max_bytes: int) -> str:
    output = []

    for root, dirs, files in os.walk(input_dir):
        root_path = Path(root)

        dirs[:] = [
            d for d in dirs
            if not d.startswith('.') and not ignore_matcher(str(root_path / d))
        ]

        relative_root = root_path.relative_to(input_dir)
        indent = '    ' * len(relative_root.parts)
        output.append(f"{indent}{root_path.name}/")

        filtered_files = []
        for f in sorted(files):
            full_path = root_path / f
            try:
                if not should_exclude(full_path, input_dir, ignore_matcher, Path(__file__), DEFAULT_MAX_BYTES):
                    filtered_files.append(f)
            except Exception as e:
                logger.warning(f"Error processing {full_path}: {e}")

        for file in filtered_files:
            output.append(f"{indent}    {file}")

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

def generate_report(input_dir: Path, script_path: Path, max_bytes: int) -> str:
    gitignore_path = input_dir / '.gitignore'
    ignore_matcher = parse_gitignore(gitignore_path) if gitignore_path.exists() else lambda path: False

    output = []
    output.append("## Directory Tree\n")
    output.append("```")
    output.append(generate_tree(input_dir, ignore_matcher, script_path, max_bytes))
    output.append("```\n\n")

    output.append("## File Contents\n")
    files = collect_files(input_dir, ignore_matcher, script_path, max_bytes)

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
