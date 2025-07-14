import os
import stat
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock

import repo_to_llm.core as core


@pytest.fixture
def temp_repo(tmp_path):
    # Setup a sample repo structure
    (tmp_path / ".gitignore").write_text("ignored_dir/\nignored_file.log\n")
    (tmp_path / "file1.py").write_text("print('hello')")
    (tmp_path / "file2.log").write_text("log contents")
    ignored_dir = tmp_path / "ignored_dir"
    ignored_dir.mkdir()
    (ignored_dir / "file3.py").write_text("print('ignore me')")
    binary_file = tmp_path / "binary.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03\x00")  # Contains null byte, treated as binary
    large_file = tmp_path / "large.txt"
    large_file.write_text("a" * (core.DEFAULT_MAX_BYTES + 1))
    yield tmp_path


def test_is_text_file(tmp_path):
    text_file = tmp_path / "text.txt"
    text_file.write_text("normal text")
    binary_file = tmp_path / "binary.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x00")

    assert core.is_text_file(text_file) is True
    assert core.is_text_file(binary_file) is False

def test_should_exclude(temp_repo):
    ignore_matcher = core.parse_gitignore(temp_repo / ".gitignore")
    script_path = Path("/some/script/path.py")  # assume unrelated script path
    max_bytes = core.DEFAULT_MAX_BYTES

    # Exclude script file itself
    assert core.should_exclude(script_path, temp_repo, ignore_matcher, script_path, max_bytes)

    # Exclude files matched by gitignore
    ignored_file = temp_repo / "ignored_file.log"
    assert core.should_exclude(ignored_file, temp_repo, ignore_matcher, script_path, max_bytes)

    # Exclude files matched by EXCLUDED_PATTERNS (e.g. *.log)
    log_file = temp_repo / "file2.log"
    assert core.should_exclude(log_file, temp_repo, ignore_matcher, script_path, max_bytes)

    # Exclude large files
    large_file = temp_repo / "large.txt"
    assert core.should_exclude(large_file, temp_repo, ignore_matcher, script_path, max_bytes)

    # Exclude binary files
    binary_file = temp_repo / "binary.bin"
    assert core.should_exclude(binary_file, temp_repo, ignore_matcher, script_path, max_bytes)

    # Include normal python file
    py_file = temp_repo / "file1.py"
    assert not core.should_exclude(py_file, temp_repo, ignore_matcher, script_path, max_bytes)

def test_collect_files(temp_repo):
    ignore_matcher = core.parse_gitignore(temp_repo / ".gitignore")
    script_path = Path("/unrelated/script.py")
    max_bytes = core.DEFAULT_MAX_BYTES

    files = core.collect_files(temp_repo, ignore_matcher, script_path, max_bytes)
    # Should include file1.py, exclude others per should_exclude
    rel_paths = [f.relative_to(temp_repo) for f in files]
    assert Path("file1.py") in rel_paths
    assert Path("file2.log") not in rel_paths
    assert Path("ignored_dir/file3.py") not in rel_paths

def test_generate_tree(temp_repo):
    ignore_matcher = core.parse_gitignore(temp_repo / ".gitignore")
    script_path = Path("/unrelated/script.py")  # dummy path for exclusion check
    max_bytes = core.DEFAULT_MAX_BYTES
    tree_str = core.generate_tree(temp_repo, ignore_matcher, script_path, max_bytes)

    # Should include top-level files except ignored ones
    assert "file1.py" in tree_str
    assert "file2.log" not in tree_str  # ignored by pattern
    assert "ignored_dir" not in tree_str  # ignored directory
    # Directory names end with /
    assert f"{temp_repo.name}/" in tree_str or "./" in tree_str

def test_guess_language():
    assert core.guess_language(Path("foo.py")) == "python"
    assert core.guess_language(Path("bar.ts")) == "typescript"
    assert core.guess_language(Path("README.md")) == "markdown"
    assert core.guess_language(Path("unknown.ext")) == "text"
    assert core.guess_language(Path("script.sh")) == "bash"

def test_generate_report(temp_repo, monkeypatch):
    # Patch parse_gitignore to control ignored files
    monkeypatch.setattr(core, "parse_gitignore", lambda p: lambda path: "ignored_file.log" in path)

    script_path = Path("/some/script.py")
    report = core.generate_report(temp_repo, script_path, core.DEFAULT_MAX_BYTES)

    # Report must contain Directory Tree and File Contents sections
    assert "## Directory Tree" in report
    assert "## File Contents" in report

    # Must contain file1.py contents, but not ignored_file.log or binary or large files
    assert "file1.py" in report
    assert "print('hello')" in report
    assert "ignored_file.log" not in report
    assert "binary.bin" not in report
    assert "large.txt" not in report

    # Syntax highlighting tags must be present
    assert "```python" in report

    # Check error reading handled gracefully
    unreadable = temp_repo / "unreadable.py"
    unreadable.write_text("some content")
    unreadable.chmod(0)  # no permission

    try:
        report = core.generate_report(temp_repo, script_path, core.DEFAULT_MAX_BYTES)
        assert "[Error reading file:" in report
    finally:
        unreadable.chmod(stat.S_IWRITE)  # restore permissions to allow cleanup
