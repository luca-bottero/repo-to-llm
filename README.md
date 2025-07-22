# repo-to-llm

**Convert a code repository into a clean, LLM-friendly Markdown report.**  
Includes a directory tree and source code contents, with filtering for size, binary files, and `.gitignore`.

## Features

- ✅ CLI interface
- ✅ `.gitignore` and glob-based exclusions
- ✅ File size filtering
- ✅ Language-aware syntax blocks (e.g. `python`, `yaml`, etc.)
- ✅ Directory tree generation (optional)

## Installation

```bash
pip install repo-to-llm
````

## Usage

```bash
repo-to-llm /path/to/repo > output.md
```

### Options

```bash
--output OUTPUT           Write to a file instead of stdout
--print                   Print to stdout (default)
--max-bytes 300kb         Max file size to include (default: 500000 bytes)
--exclude-tree            Skip the directory tree section
--exclude-patterns "*.log" "docs/*"   Glob patterns to exclude
--verbose                 Enable debug output
```

### Example

```bash
repo-to-llm my-project --exclude-patterns "*.log" "tests/*" --max-bytes 300kb > project.md
```

## Configuration

You can override defaults in `~/.repo_to_llm/config.yml`.

```yaml
max_bytes: 1000000
excluded_patterns:
  - ".git/*"
  - "__pycache__/*"
extension_mapping:
  .ext: my_extension
  .ext2: my_second_extension
```

## Contributing

Contributions are welcome. Please open an issue or PR on GitHub.

## License

MIT License. See [LICENSE](./LICENSE).