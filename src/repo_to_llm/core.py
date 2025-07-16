from pathlib import Path
from gitignore_parser import parse_gitignore

from repo_to_llm.pattern_matching import generate_tree, collect_files, guess_language

def generate_report(
    input_dir: Path,
    script_path: Path,
    max_bytes: int,
    exclude_tree: bool = False,
    exclude_patterns: set | None = None
) -> str:
    gitignore_path = input_dir / '.gitignore'
    ignore_matcher = parse_gitignore(gitignore_path) if gitignore_path.exists() else lambda path: False

    output = []

    if not exclude_tree:
        output.append("## Directory Tree\n")
        output.append("```")
        output.append(generate_tree(input_dir, ignore_matcher, script_path, max_bytes, exclude_patterns))
        output.append("```\n\n")

    output.append("## File Contents\n")
    files = collect_files(input_dir, ignore_matcher, script_path, max_bytes, exclude_patterns)

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
