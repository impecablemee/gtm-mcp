"""Campaign-to-project assignment — deterministic grouping from SmartLead data.

Ported from magnum-opus CRM sync service. Three-tier matching:
1. Saved rules (project_rules.json) — tag, prefix, contains
2. Sender domain grouping — campaigns sharing email account domains
3. Campaign name prefix grouping — common prefixes before " - " or " — "

Zero LLM calls. Returns groups with features for the agent to name/validate.
"""
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_project_rules(workspace_base: Path) -> dict:
    """Load saved assignment rules from project_rules.json."""
    rules_path = workspace_base / "project_rules.json"
    if not rules_path.exists():
        return {"projects": {}}
    try:
        return json.loads(rules_path.read_text())
    except Exception:
        return {"projects": {}}


def save_project_rules(workspace_base: Path, rules: dict):
    """Persist assignment rules (learned from user corrections)."""
    rules_path = workspace_base / "project_rules.json"
    rules_path.write_text(json.dumps(rules, indent=2, ensure_ascii=False))


def _extract_sender_domains(campaign: dict, accounts_by_id: dict) -> set[str]:
    """Extract unique sender domains from campaign's assigned email accounts."""
    domains = set()
    for aid in campaign.get("email_account_ids", []):
        acc = accounts_by_id.get(aid) or accounts_by_id.get(str(aid))
        if acc:
            email = acc.get("from_email", "")
            if "@" in email:
                domains.add(email.split("@")[1].lower())
    return domains


def _extract_sender_names(campaign: dict, accounts_by_id: dict) -> set[str]:
    """Extract unique sender display names."""
    names = set()
    for aid in campaign.get("email_account_ids", []):
        acc = accounts_by_id.get(aid) or accounts_by_id.get(str(aid))
        if acc and acc.get("from_name"):
            names.add(acc["from_name"].strip())
    return names


def _normalize_prefix(prefix: str) -> str:
    """Normalize a prefix: strip punctuation from word boundaries, collapse whitespace."""
    # Strip trailing/leading punctuation from EACH word ("Mifort." → "Mifort")
    words = prefix.split()
    cleaned = [re.sub(r"^[.\-_,;:]+|[.\-_,;:]+$", "", w) for w in words]
    cleaned = [w for w in cleaned if w]
    result = " ".join(cleaned)
    result = re.sub(r"\s+", " ", result)
    return result.lower().strip()


def _extract_name_prefix(campaign_name: str) -> str:
    """Extract the most meaningful prefix from a campaign name.

    "Inxy - Affiliate Network Q1" → "inxy"
    "Sally Fintech PAYMENTS 07/04" → "sally fintech"
    "EasyStaff Global - IT Consulting" → "easystaff global"
    "Mifort. iGaming" → "mifort"
    "Deliryo_Florida_24/11" → "deliryo"
    """
    name = campaign_name.strip()
    # Split on common delimiters
    for delim in [" — ", " - ", " – ", " | "]:
        if delim in name:
            prefix = name.split(delim)[0].strip()
            if len(prefix) >= 3:
                return _normalize_prefix(prefix)

    # Try underscore delimiter (Deliryo_Florida_24/11)
    if "_" in name:
        prefix = name.split("_")[0].strip()
        if len(prefix) >= 3:
            return _normalize_prefix(prefix)

    # No delimiter: take first 1-2 words (stop at date patterns, ALL_CAPS segments, numbers)
    words = name.split()
    prefix_words = []
    for w in words:
        # Stop at date patterns (07/04, Q1, 2026, 24/11)
        if re.match(r"^\d{2}/\d{2}$|^Q\d$|^20\d{2}$|\d{2}\.\d{2}$", w):
            break
        # Stop at ALL_CAPS segment labels (PAYMENTS, LENDING, BAAS)
        if w.isupper() and len(w) > 2:
            break
        prefix_words.append(w)
        if len(prefix_words) >= 3:
            break

    raw = " ".join(prefix_words).strip() if prefix_words else name
    return _normalize_prefix(raw)


def _match_by_rules(
    campaign: dict, rules: dict
) -> tuple[str | None, str | None]:
    """Try to match campaign against saved project rules.

    Returns (project_slug, match_method) or (None, None).
    Evaluation order: tags → prefixes (longest first) → contains.
    """
    name_lower = campaign.get("name", "").lower()
    tags_lower = {t.lower() for t in campaign.get("tags", [])}

    # Build match candidates sorted by prefix length (longest first)
    prefix_candidates = []
    contains_candidates = []
    tag_candidates = []

    for slug, project in rules.get("projects", {}).items():
        project_rules = project.get("rules", {})

        for tag in project_rules.get("tags", []):
            tag_candidates.append((tag.lower(), slug))

        for prefix in project_rules.get("campaign_prefixes", []):
            prefix_candidates.append((prefix.lower(), slug))

        # Also use project name as implicit prefix
        pname = project.get("name", "")
        if len(pname) >= 3:
            prefix_candidates.append((pname.lower(), slug))

        for kw in project_rules.get("campaign_contains", []):
            contains_candidates.append((kw.lower(), slug))

    # 1. Tag match
    for tag, slug in tag_candidates:
        if tag in tags_lower:
            return slug, "tag_match"

    # 2. Prefix match (longest first)
    prefix_candidates.sort(key=lambda x: len(x[0]), reverse=True)
    for prefix, slug in prefix_candidates:
        if name_lower.startswith(prefix):
            return slug, "prefix_match"

    # 3. Contains match
    for kw, slug in contains_candidates:
        if kw in name_lower:
            return slug, "contains_match"

    return None, None


def assign_campaigns(
    campaigns: list[dict],
    accounts: list[dict],
    workspace_base: Path,
) -> dict:
    """Auto-assign campaigns to projects. Deterministic — zero LLM.

    Returns:
    {
        "projects": {
            "slug": {
                "name": "suggested name (from prefix)",
                "campaigns": [...],
                "sender_domains": [...],
                "sender_names": [...],
                "match_methods": {"rule_match": 2, "domain_group": 1},
                "metrics": {"total_leads": N, "total_replies": N}
            }
        },
        "unassigned": [...campaigns that couldn't be grouped],
        "rules_applied": N,
        "pattern_grouped": N
    }
    """
    # Build account lookup by ID
    accounts_by_id = {}
    for acc in accounts:
        aid = acc.get("id")
        if aid is not None:
            accounts_by_id[aid] = acc
            accounts_by_id[str(aid)] = acc

    # Load saved rules
    rules = load_project_rules(workspace_base)

    # Phase 1: Apply saved rules
    assigned: dict[str, list] = defaultdict(list)  # slug → campaigns
    unmatched: list[dict] = []
    rules_applied = 0

    for c in campaigns:
        slug, method = _match_by_rules(c, rules)
        if slug:
            c["_match_method"] = method
            assigned[slug].append(c)
            rules_applied += 1
        else:
            unmatched.append(c)

    # Phase 2: Group unmatched by sender domain OVERLAP (connected components)
    # If campaign A uses domains {getsally.io, sally-leads.com} and campaign B uses
    # {getsally.io}, they share getsally.io → same group. Union-find approach.
    still_unmatched: list[dict] = []
    campaigns_with_domains: list[tuple[dict, set]] = []

    for c in unmatched:
        domains = _extract_sender_domains(c, accounts_by_id)
        if domains:
            campaigns_with_domains.append((c, domains))
        else:
            still_unmatched.append(c)

    # Union-find: merge campaigns sharing any domain
    parent: dict[int, int] = {}  # campaign index → root index

    def find(x: int) -> int:
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    def union(a: int, b: int):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Build domain → campaign index mapping
    domain_to_indices: dict[str, list[int]] = defaultdict(list)
    for i, (c, domains) in enumerate(campaigns_with_domains):
        for d in domains:
            domain_to_indices[d].append(i)

    # Union campaigns sharing any domain
    for domain, indices in domain_to_indices.items():
        for j in range(1, len(indices)):
            union(indices[0], indices[j])

    # Collect connected components
    components: dict[int, list[int]] = defaultdict(list)
    for i in range(len(campaigns_with_domains)):
        components[find(i)].append(i)

    # Phase 3: For each component, sub-split by prefix to avoid over-merging
    # Domain overlap groups EasyStaff + Deliryo if they share a mailbox domain.
    # Sub-splitting by prefix separates them back out.
    pattern_grouped = 0
    for root, indices in components.items():
        group_campaigns = [campaigns_with_domains[i][0] for i in indices]

        # Sub-group by prefix within this domain component
        prefix_subgroups: dict[str, list] = defaultdict(list)
        for c in group_campaigns:
            prefix = _extract_name_prefix(c.get("name", ""))
            prefix_subgroups[prefix].append(c)

        if len(prefix_subgroups) == 1:
            # All campaigns share the same prefix — clean group
            prefix = next(iter(prefix_subgroups))
            slug = prefix.replace(" ", "-").replace("/", "-")
            method = "domain_group" if len(group_campaigns) > 1 else "domain_singleton"
            for c in group_campaigns:
                c["_match_method"] = method
                assigned[slug].append(c)
                pattern_grouped += len(group_campaigns)
        else:
            # Mixed prefixes — split into sub-groups
            # First pass: collect all slugs in this component
            component_slugs: dict[str, list] = {}
            for prefix, sub_campaigns in prefix_subgroups.items():
                slug = prefix.replace(" ", "-").replace("/", "-")
                component_slugs[slug] = sub_campaigns

            # Second pass: merge child slugs into parent slugs within this component
            # "petr es us-east" merges into "petr es" if "petr es" exists
            sorted_slugs = sorted(component_slugs.keys(), key=len)  # shortest first
            merged: dict[str, list] = {}
            for slug in sorted_slugs:
                parent = None
                for existing in merged:
                    if slug.startswith(existing + "-") or slug.startswith(existing + " "):
                        parent = existing
                        break
                if parent:
                    merged[parent].extend(component_slugs[slug])
                else:
                    merged[slug] = list(component_slugs[slug])

            for slug, sub_campaigns in merged.items():
                method = "domain_and_prefix" if len(sub_campaigns) > 1 else "domain_singleton"
                for c in sub_campaigns:
                    c["_match_method"] = method
                    assigned[slug].append(c)
                    pattern_grouped += 1

    # Phase 4: Group remaining (no domains) by prefix — merge singletons into existing projects
    final_unassigned = []
    prefix_groups: dict[str, list] = defaultdict(list)
    for c in still_unmatched:
        prefix = _extract_name_prefix(c.get("name", ""))
        prefix_groups[prefix].append(c)

    # Build lookup of existing project slugs for prefix-starts-with matching
    existing_slugs = sorted(assigned.keys(), key=len, reverse=True)  # longest first

    def _find_parent_slug(slug: str) -> str | None:
        """Find existing project whose slug is a prefix of this one."""
        if slug in assigned:
            return slug
        for existing in existing_slugs:
            if slug.startswith(existing + "-") or slug.startswith(existing):
                return existing
        return None

    for prefix, prefix_campaigns in prefix_groups.items():
        slug = prefix.replace(" ", "-").replace("/", "-")
        if len(prefix_campaigns) >= 2:
            for c in prefix_campaigns:
                c["_match_method"] = "prefix_only"
                assigned[slug].append(c)
                pattern_grouped += 1
        else:
            # Singleton — try to merge into existing project by prefix-starts-with
            parent = _find_parent_slug(slug)
            if parent:
                for c in prefix_campaigns:
                    c["_match_method"] = "prefix_merged"
                    assigned[parent].append(c)
                    pattern_grouped += 1
            else:
                final_unassigned.extend(prefix_campaigns)

    # Build result
    projects = {}
    for slug, group_campaigns in assigned.items():
        # Get project name from rules or from the prefix
        rule_project = rules.get("projects", {}).get(slug, {})
        project_name = rule_project.get("name", slug.replace("-", " ").title())

        # Aggregate sender info
        all_domains = set()
        all_names = set()
        all_account_ids = set()
        match_methods = defaultdict(int)
        total_leads = 0
        total_replies = 0

        for c in group_campaigns:
            all_domains |= _extract_sender_domains(c, accounts_by_id)
            all_names |= _extract_sender_names(c, accounts_by_id)
            all_account_ids |= set(c.get("email_account_ids", []))
            match_methods[c.get("_match_method", "unknown")] += 1
            total_leads += c.get("leads_count", 0)
            total_replies += c.get("reply_count", 0)

        projects[slug] = {
            "name": project_name,
            "campaigns": [{
                "id": c.get("id"),
                "name": c.get("name", ""),
                "status": c.get("status", ""),
                "leads_count": c.get("leads_count", 0),
                "reply_count": c.get("reply_count", 0),
                "match_method": c.get("_match_method", "unknown"),
            } for c in group_campaigns],
            "sender_domains": sorted(all_domains),
            "sender_names": sorted(all_names),
            "account_count": len(all_account_ids),
            "match_methods": dict(match_methods),
            "metrics": {
                "total_leads": total_leads,
                "total_replies": total_replies,
                "campaign_count": len(group_campaigns),
            },
        }

    return {
        "projects": projects,
        "unassigned": [{
            "id": c.get("id"),
            "name": c.get("name", ""),
            "status": c.get("status", ""),
            "leads_count": c.get("leads_count", 0),
            "reply_count": c.get("reply_count", 0),
        } for c in final_unassigned],
        "rules_applied": rules_applied,
        "pattern_grouped": pattern_grouped,
        "total_projects": len(projects),
        "total_unassigned": len(final_unassigned),
    }


def learn_correction(
    workspace_base: Path,
    project_slug: str,
    project_name: str,
    campaign_name: str,
    sender_domains: list[str] | None = None,
    sender_names: list[str] | None = None,
) -> dict:
    """Learn from user correction — update project_rules.json.

    Called when user says "move campaign X to project Y" or confirms assignment.
    Extracts patterns from the campaign name and adds to project rules.
    """
    rules = load_project_rules(workspace_base)

    if "projects" not in rules:
        rules["projects"] = {}

    if project_slug not in rules["projects"]:
        rules["projects"][project_slug] = {
            "name": project_name,
            "rules": {
                "campaign_prefixes": [],
                "campaign_contains": [],
                "sender_domains": [],
                "sender_names": [],
                "tags": [],
            },
        }

    project = rules["projects"][project_slug]
    project["name"] = project_name
    project_rules = project["rules"]

    # Extract prefix from campaign name
    prefix = _extract_name_prefix(campaign_name)
    if prefix and prefix not in [p.lower() for p in project_rules.get("campaign_prefixes", [])]:
        project_rules.setdefault("campaign_prefixes", []).append(prefix)

    # Add sender domains
    if sender_domains:
        existing = set(d.lower() for d in project_rules.get("sender_domains", []))
        for d in sender_domains:
            if d.lower() not in existing:
                project_rules.setdefault("sender_domains", []).append(d.lower())

    # Add sender names
    if sender_names:
        existing = set(n.lower() for n in project_rules.get("sender_names", []))
        for n in sender_names:
            if n.lower() not in existing:
                project_rules.setdefault("sender_names", []).append(n)

    save_project_rules(workspace_base, rules)
    return {"success": True, "project": project_slug, "rules": project_rules}
