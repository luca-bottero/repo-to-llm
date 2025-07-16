import yaml
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(__file__).parent / "defaults.yml"
USER_CONFIG_PATH = Path.home() / ".repo_to_llm" / "config.yml"

class Config:
    def __init__(self):
        self._default = self._load_yaml(DEFAULT_CONFIG_PATH)
        self._user = self._load_yaml(USER_CONFIG_PATH)

    def _load_yaml(self, path):
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _get(self, key, default=None):
        return self._user.get(key, self._default.get(key, default))

    @property
    def max_bytes(self) -> int:
        return self._get("max_bytes", 500_000)

    @property
    def extension_mapping(self) -> dict:
        return self._get("extension_mapping", {})

    @property
    def excluded_patterns(self) -> list:
        return self._get("excluded_patterns", [])


config = Config()
