"""Workspace manager — file-based project storage in ~/.gtm-mcp/projects/."""
import json
from copy import deepcopy
from datetime import datetime, timezone
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

    def _safe_path(self, base: Path, name: str) -> Path:
        """Resolve name under base, reject path traversal."""
        resolved = (base / name).resolve()
        if not str(resolved).startswith(str(base.resolve())):
            raise ValueError(f"Path traversal blocked: '{name}' escapes project directory")
        return resolved

    def save(self, project: str, name: str, data: Any, mode: str = "write") -> Path:
        """Save data to project workspace.
        Modes: write (overwrite), merge (deep-merge dicts), append (add to list), versioned (numbered snapshot).
        """
        d = self._project_dir(project)

        if mode == "versioned":
            return self._save_versioned(d, name, data)

        path = self._safe_path(d, name)
        path.parent.mkdir(parents=True, exist_ok=True)  # create nested dirs (campaigns/slug/)
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
        path = self._safe_path(self._project_dir(project), name)
        if not path.exists():
            return None
        return self._read_file(path)

    def list_projects(self) -> list:
        if not self.projects_dir.exists():
            return []
        return [d.name for d in self.projects_dir.iterdir() if d.is_dir()]

    # --- Campaign lookup ---

    def find_campaign(self, campaign_ref: str) -> dict | None:
        """Find a campaign by SmartLead ID or slug across all projects.

        Returns {project, slug, data} or None if not found.
        """
        for project in self.list_projects():
            d = self._project_dir(project)
            campaigns_dir = d / "campaigns"
            if not campaigns_dir.exists():
                continue
            for campaign_dir in campaigns_dir.iterdir():
                if not campaign_dir.is_dir():
                    continue
                yaml_path = campaign_dir / "campaign.yaml"
                if not yaml_path.exists():
                    continue
                try:
                    data = self._read_file(yaml_path)
                except Exception:
                    continue
                # Match by slug or by campaign_id (as string or int)
                if (campaign_dir.name == campaign_ref
                        or str(data.get("campaign_id", "")) == str(campaign_ref)):
                    return {"project": project, "slug": campaign_dir.name, "data": data}
        return None

    # --- Cost reporting ---

    def get_project_costs(self, project: str) -> dict:
        """Aggregate costs across all runs in a project, grouped by campaign."""
        d = self._project_dir(project)
        runs_dir = d / "runs"
        if not runs_dir.exists():
            return {"runs": [], "campaigns": {}, "totals": {
                "total_credits": 0, "total_credits_search": 0,
                "total_credits_people": 0, "total_usd": 0,
                "total_contacts": 0, "total_companies": 0,
            }}

        runs = []
        campaign_costs: dict[str, dict] = {}
        grand = {"total_credits": 0, "total_credits_search": 0,
                 "total_credits_people": 0, "total_usd": 0,
                 "total_contacts": 0, "total_companies": 0}

        for run_file in sorted(runs_dir.glob("run-*.json")):
            try:
                run = self._read_file(run_file)
            except Exception:
                continue
            totals = run.get("totals", {})
            run_id = run.get("run_id", run_file.stem)
            campaign_slug = run.get("campaign_slug", "unlinked")
            campaign_id = run.get("campaign_id")

            entry = {
                "run_id": run_id,
                "campaign_slug": campaign_slug,
                "campaign_id": campaign_id,
                "status": run.get("status", "unknown"),
                "credits_search": totals.get("total_credits_search", 0),
                "credits_people": totals.get("total_credits_people", 0),
                "credits_total": totals.get("total_credits", 0),
                "usd": totals.get("total_usd", 0),
                "companies": totals.get("unique_companies", 0),
                "targets": totals.get("targets", 0),
                "contacts": totals.get("contacts_extracted", 0),
            }
            runs.append(entry)

            # Aggregate by campaign
            if campaign_slug not in campaign_costs:
                campaign_costs[campaign_slug] = {
                    "campaign_id": campaign_id,
                    "runs": [],
                    "credits_search": 0, "credits_people": 0,
                    "credits_total": 0, "usd": 0,
                    "companies": 0, "contacts": 0,
                }
            c = campaign_costs[campaign_slug]
            c["runs"].append(run_id)
            c["credits_search"] += entry["credits_search"]
            c["credits_people"] += entry["credits_people"]
            c["credits_total"] += entry["credits_total"]
            c["usd"] += entry["usd"]
            c["companies"] += entry["companies"]
            c["contacts"] += entry["contacts"]

            # Grand totals
            grand["total_credits"] += entry["credits_total"]
            grand["total_credits_search"] += entry["credits_search"]
            grand["total_credits_people"] += entry["credits_people"]
            grand["total_usd"] += entry["usd"]
            grand["total_contacts"] += entry["contacts"]
            grand["total_companies"] += entry["companies"]

        grand["total_usd"] = round(grand["total_usd"], 2)
        return {"runs": runs, "campaigns": campaign_costs, "totals": grand}

    # --- Blacklist (temporal, with structured metadata) ---

    def blacklist_check(self, domain: str, max_age_days: int | None = None) -> bool:
        """Check if domain is blacklisted. If max_age_days set, only considers
        entries with last_contact_date within that window."""
        bl = self._load_blacklist()
        d = domain.lower().strip()
        if d not in bl:
            return False
        if max_age_days is None:
            return True
        entry = bl[d]
        if isinstance(entry, dict) and entry.get("last_contact_date"):
            try:
                contact_date = datetime.fromisoformat(entry["last_contact_date"])
                age = (datetime.now(timezone.utc) - contact_date).days
                return age <= max_age_days
            except (ValueError, TypeError):
                pass
        return True  # no date info → treat as blacklisted

    def blacklist_add(self, domains: list, source: str = "", campaign_name: str = "",
                      last_contact_date: str = ""):
        """Add domains to blacklist with optional temporal metadata."""
        bl = self._load_blacklist()
        now = datetime.now(timezone.utc).isoformat()
        for d in domains:
            key = d.lower().strip()
            if not key:
                continue
            entry = bl.get(key, {})
            if not isinstance(entry, dict):
                entry = {"blacklisted_at": now}
            if source:
                entry["source"] = source
            if campaign_name:
                entry["campaign_name"] = campaign_name
            if last_contact_date:
                entry["last_contact_date"] = last_contact_date
            entry.setdefault("blacklisted_at", now)
            entry["domain"] = key
            bl[key] = entry
        self._save_blacklist(bl)

    def blacklist_import(self, path: str, source: str = "") -> int:
        p = Path(path)
        if not p.exists():
            return 0
        domains = [line.strip() for line in p.read_text().splitlines() if line.strip()]
        self.blacklist_add(domains, source=source or p.name)
        return len(domains)

    def _load_blacklist(self) -> dict:
        """Load blacklist as dict keyed by domain.
        Backward-compatible: migrates old list format to structured dict."""
        if not self.blacklist_file.exists():
            return {}
        data = json.loads(self.blacklist_file.read_text())
        # Migrate from old flat list format
        if isinstance(data, list):
            now = datetime.now(timezone.utc).isoformat()
            return {d: {"domain": d, "blacklisted_at": now} for d in data}
        if isinstance(data, dict):
            return data
        return {}

    def _save_blacklist(self, bl: dict):
        self.blacklist_file.write_text(json.dumps(bl, indent=2, ensure_ascii=False, default=str))

    # --- Company Name Normalization ---

    @staticmethod
    def normalize_company_name(name: str) -> str:
        """Normalize company name by stripping legal suffixes.

        Rules (from pipeline-state skill):
        1. Strip comma-prefixed legal suffixes: , Inc., , LLC, , Ltd., , Corp., etc.
        2. Strip trailing punctuation (. or ,)
        3. Trim whitespace
        4. Keep original casing (don't force title case)
        """
        import re
        if not name:
            return name
        # Strip comma-prefixed legal suffixes (case-insensitive)
        suffixes = (
            r",?\s*Inc\.?", r",?\s*LLC\.?", r",?\s*Ltd\.?", r",?\s*Corp\.?",
            r",?\s*GmbH", r",?\s*S\.A\.?", r",?\s*B\.V\.?", r",?\s*Pty\.?\s*Ltd\.?",
            r",?\s*PLC\.?", r",?\s*AG", r",?\s*S\.r\.l\.?", r",?\s*S\.L\.?",
            r",?\s*Co\.?", r",?\s*Limited",
        )
        pattern = r"(?:" + "|".join(suffixes) + r")\s*$"
        result = re.sub(pattern, "", name, flags=re.IGNORECASE).strip()
        # Strip trailing punctuation
        result = result.rstrip(".,").strip()
        return result

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
            elif k in result and isinstance(result[k], list) and isinstance(v, list):
                result[k] = deepcopy(result[k]) + deepcopy(v)
            else:
                result[k] = deepcopy(v)
        return result
