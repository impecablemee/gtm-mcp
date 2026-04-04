"""Workspace manager — file-based project storage in ~/.gtm-mcp/projects/."""
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

import yaml


class WorkspaceManager:
    def __init__(self, base_dir: Path):
        self.base = base_dir
        self.projects_dir = base_dir / "projects"
        self.blacklist_file = base_dir / "blacklist.json"

    def _project_dir(self, project: str) -> Path:
        slug = project.lower().replace(" ", "-").replace("/", "-")
        d = self.projects_dir / slug
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save(self, project: str, name: str, data: Any, mode: str = "write") -> Path:
        """Save data to project workspace.
        Modes: write (overwrite), merge (deep-merge dicts), append (add to list), versioned (numbered snapshot).
        """
        d = self._project_dir(project)

        if mode == "versioned":
            return self._save_versioned(d, name, data)

        path = d / name
        ext = path.suffix.lower()

        if mode == "merge" and path.exists():
            existing = self._read_file(path)
            if isinstance(existing, dict) and isinstance(data, dict):
                data = self._deep_merge(existing, data)

        if mode == "append" and path.exists():
            existing = self._read_file(path)
            if isinstance(existing, list):
                existing.extend(data if isinstance(data, list) else [data])
                data = existing

        self._write_file(path, data)
        return path

    def load(self, project: str, name: str) -> Optional[Any]:
        """Load data from project workspace."""
        path = self._project_dir(project) / name
        if not path.exists():
            return None
        return self._read_file(path)

    def list_projects(self) -> list:
        if not self.projects_dir.exists():
            return []
        return [d.name for d in self.projects_dir.iterdir() if d.is_dir()]

    # --- Blacklist ---

    def blacklist_check(self, domain: str) -> bool:
        bl = self._load_blacklist()
        return domain.lower().strip() in bl

    def blacklist_add(self, domains: list):
        bl = self._load_blacklist()
        bl.update(d.lower().strip() for d in domains)
        self._save_blacklist(bl)

    def blacklist_import(self, path: str) -> int:
        p = Path(path)
        if not p.exists():
            return 0
        domains = [line.strip() for line in p.read_text().splitlines() if line.strip()]
        self.blacklist_add(domains)
        return len(domains)

    def _load_blacklist(self) -> set:
        if not self.blacklist_file.exists():
            return set()
        data = json.loads(self.blacklist_file.read_text())
        return set(data) if isinstance(data, list) else set()

    def _save_blacklist(self, bl: set):
        self.blacklist_file.write_text(json.dumps(sorted(bl), indent=2))

    # --- Versioned saves ---

    def _save_versioned(self, d: Path, name: str, data: Any) -> Path:
        stem = Path(name).stem
        ext = Path(name).suffix or ".json"
        vdir = d / stem
        vdir.mkdir(exist_ok=True)

        existing = sorted(vdir.glob(f"v*{ext}"))
        next_num = len(existing) + 1
        vpath = vdir / f"v{next_num}{ext}"
        self._write_file(vpath, data)

        latest = vdir / f"latest{ext}"
        self._write_file(latest, data)
        return vpath

    # --- File I/O ---

    def _read_file(self, path: Path) -> Any:
        ext = path.suffix.lower()
        text = path.read_text()
        if ext in (".yaml", ".yml"):
            return yaml.safe_load(text)
        return json.loads(text)

    def _write_file(self, path: Path, data: Any):
        ext = path.suffix.lower()
        if ext in (".yaml", ".yml"):
            path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))
        else:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))

    def _deep_merge(self, base: dict, override: dict) -> dict:
        result = deepcopy(base)
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._deep_merge(result[k], v)
            else:
                result[k] = deepcopy(v)
        return result
