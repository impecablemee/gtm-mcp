"""Configuration manager — reads API keys from ~/.gtm-mcp/config.yaml and env vars."""
import os
import stat
from pathlib import Path
from typing import Any, Optional

import yaml

DEFAULT_DIR = Path.home() / ".gtm-mcp"
CONFIG_FILE = DEFAULT_DIR / "config.yaml"


class ConfigManager:
    def __init__(self, config_dir: Optional[Path] = None):
        self.dir = config_dir or DEFAULT_DIR
        self.file = self.dir / "config.yaml"
        self._data: dict = {}
        self._load()

    def _load(self):
        if self.file.exists():
            self._data = yaml.safe_load(self.file.read_text()) or {}

    def get(self, key: str) -> Optional[str]:
        """Get config value. Env vars override file values."""
        env_key = f"GTM_MCP_{key.upper()}"
        return os.environ.get(env_key) or self._data.get(key)

    def set(self, key: str, value: Any):
        """Set config value and persist to file."""
        self._data[key] = value
        self._save()

    def delete(self, key: str):
        self._data.pop(key, None)
        self._save()

    def all(self) -> dict:
        """Return all config values (file + env overrides)."""
        result = dict(self._data)
        for key in ["apollo_api_key", "smartlead_api_key", "getsales_api_key",
                     "getsales_team_id", "apify_proxy_password"]:
            env_val = os.environ.get(f"GTM_MCP_{key.upper()}")
            if env_val:
                result[key] = env_val
        return result

    def _save(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        self.file.write_text(yaml.dump(self._data, default_flow_style=False))
        self.file.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
