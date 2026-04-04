"""GTM-MCP Server — 27 thin tools, zero LLM calls. stdio transport via FastMCP."""
from pathlib import Path

from fastmcp import FastMCP

from gtm_mcp.config import ConfigManager
from gtm_mcp.workspace import WorkspaceManager

mcp = FastMCP(
    name="gtm-mcp",
    instructions=(
        "GTM-MCP: B2B lead generation tools. "
        "Use /leadgen for full pipeline, /qualify for batch classification, "
        "/outreach for sequence generation, /replies for reply triage. "
        "All AI reasoning is done by YOU (the calling agent) using the skills in .claude/skills/. "
        "These tools only handle data access — API calls, storage, blacklist."
    ),
)

_config = ConfigManager()
_workspace = WorkspaceManager(_config.dir)


# ─── Config Tools ─────────────────────────────────────────────────────────────

@mcp.tool()
async def get_config() -> dict:
    """Get current configuration (API keys status, not values)."""
    cfg = _config.all()
    return {
        "success": True,
        "configured": {k: bool(v) for k, v in cfg.items()},
        "workspace": str(_config.dir),
    }


@mcp.tool()
async def set_config(key: str, value: str) -> dict:
    """Set a configuration value (e.g. apollo_api_key)."""
    _config.set(key, value)
    return {"success": True, "key": key}


# ─── Project Tools ────────────────────────────────────────────────────────────

@mcp.tool()
async def create_project(name: str, data: dict | None = None) -> dict:
    """Create a new project in workspace."""
    project_data = data or {}
    project_data["name"] = name
    path = _workspace.save(name, "project.yaml", project_data)
    return {"success": True, "project": name, "path": str(path)}


@mcp.tool()
async def list_projects() -> dict:
    """List all projects in workspace."""
    return {"success": True, "projects": _workspace.list_projects()}


@mcp.tool()
async def save_data(project: str, name: str, data: dict | list, mode: str = "write") -> dict:
    """Save data to project workspace. Modes: write, merge, append, versioned."""
    path = _workspace.save(project, name, data, mode=mode)
    return {"success": True, "path": str(path)}


@mcp.tool()
async def load_data(project: str, name: str) -> dict:
    """Load data from project workspace."""
    data = _workspace.load(project, name)
    if data is None:
        return {"success": False, "error": f"File {name} not found in project {project}"}
    return {"success": True, "data": data}


# ─── Blacklist Tools ──────────────────────────────────────────────────────────

@mcp.tool()
async def blacklist_check(domain: str) -> dict:
    """Check if a domain is blacklisted."""
    return {"success": True, "domain": domain, "blacklisted": _workspace.blacklist_check(domain)}


@mcp.tool()
async def blacklist_add(domains: list[str]) -> dict:
    """Add domains to the global blacklist."""
    _workspace.blacklist_add(domains)
    return {"success": True, "added": len(domains)}


@mcp.tool()
async def blacklist_import(file_path: str) -> dict:
    """Import domains from a file into the blacklist."""
    count = _workspace.blacklist_import(file_path)
    return {"success": True, "imported": count}


# ─── Apollo Tools ─────────────────────────────────────────────────────────────

@mcp.tool()
async def apollo_search_companies(filters: dict, page: int = 1, per_page: int = 100) -> dict:
    """Search Apollo for companies. 1 credit/page. MUST use 1 keyword OR 1 industry per call."""
    api_key = _config.get("apollo_api_key")
    if not api_key:
        return {"success": False, "error": "Apollo API key not configured. Run set_config."}
    from gtm_mcp.tools.apollo import apollo_search_companies as _impl
    return await _impl(api_key, filters, page, per_page)


@mcp.tool()
async def apollo_search_people(
    domains: list[str],
    person_titles: list[str] | None = None,
    person_seniorities: list[str] | None = None,
) -> dict:
    """Search Apollo for people at given companies. FREE — no credits."""
    api_key = _config.get("apollo_api_key")
    if not api_key:
        return {"success": False, "error": "Apollo API key not configured."}
    from gtm_mcp.tools.apollo import apollo_search_people as _impl
    return await _impl(api_key, domains, person_titles, person_seniorities)


@mcp.tool()
async def apollo_enrich_company(domain: str) -> dict:
    """Enrich a company by domain. 1 credit."""
    api_key = _config.get("apollo_api_key")
    if not api_key:
        return {"success": False, "error": "Apollo API key not configured."}
    from gtm_mcp.tools.apollo import apollo_enrich_company as _impl
    return await _impl(api_key, domain)


@mcp.tool()
async def apollo_bulk_enrich_people(details: list[dict]) -> dict:
    """Enrich people to get verified emails. 1 credit per person."""
    api_key = _config.get("apollo_api_key")
    if not api_key:
        return {"success": False, "error": "Apollo API key not configured."}
    from gtm_mcp.tools.apollo import apollo_bulk_enrich_people as _impl
    return await _impl(api_key, details)


@mcp.tool()
async def apollo_get_taxonomy() -> dict:
    """Get Apollo industry taxonomy (67 industries + 8 employee ranges). No API call."""
    from gtm_mcp.tools.apollo import apollo_get_taxonomy as _impl
    return _impl()


@mcp.tool()
async def apollo_estimate_cost(
    target_count: int = 100,
    contacts_per_company: int = 3,
    target_rate: float = 0.35,
) -> dict:
    """Estimate Apollo credits needed for a pipeline run. No API call."""
    from gtm_mcp.tools.apollo import apollo_estimate_cost as _impl
    return _impl(target_count, contacts_per_company, target_rate)


# ─── Scraping Tool ────────────────────────────────────────────────────────────

@mcp.tool()
async def scrape_website(url: str) -> dict:
    """Scrape a website and return cleaned text. No credits."""
    proxy = _config.get("apify_proxy_password")
    from gtm_mcp.tools.scraping import scrape_website as _impl
    return await _impl(url, apify_proxy_password=proxy)


# ─── SmartLead Tools ──────────────────────────────────────────────────────────

@mcp.tool()
async def smartlead_list_campaigns() -> dict:
    """List all SmartLead campaigns."""
    api_key = _config.get("smartlead_api_key")
    if not api_key:
        return {"success": False, "error": "SmartLead API key not configured."}
    from gtm_mcp.tools.smartlead import smartlead_list_campaigns as _impl
    return await _impl(api_key)


@mcp.tool()
async def smartlead_create_campaign(name: str) -> dict:
    """Create a SmartLead campaign (DRAFT)."""
    api_key = _config.get("smartlead_api_key")
    if not api_key:
        return {"success": False, "error": "SmartLead API key not configured."}
    from gtm_mcp.tools.smartlead import smartlead_create_campaign as _impl
    return await _impl(api_key, name)


@mcp.tool()
async def smartlead_set_sequence(campaign_id: int, sequences: list[dict]) -> dict:
    """Set email sequence on a SmartLead campaign."""
    api_key = _config.get("smartlead_api_key")
    if not api_key:
        return {"success": False, "error": "SmartLead API key not configured."}
    from gtm_mcp.tools.smartlead import smartlead_set_sequence as _impl
    return await _impl(api_key, campaign_id, sequences)


@mcp.tool()
async def smartlead_add_leads(campaign_id: int, leads: list[dict]) -> dict:
    """Add leads to a SmartLead campaign."""
    api_key = _config.get("smartlead_api_key")
    if not api_key:
        return {"success": False, "error": "SmartLead API key not configured."}
    from gtm_mcp.tools.smartlead import smartlead_add_leads as _impl
    return await _impl(api_key, campaign_id, leads)


@mcp.tool()
async def smartlead_list_accounts() -> dict:
    """List SmartLead email accounts."""
    api_key = _config.get("smartlead_api_key")
    if not api_key:
        return {"success": False, "error": "SmartLead API key not configured."}
    from gtm_mcp.tools.smartlead import smartlead_list_accounts as _impl
    return await _impl(api_key)


@mcp.tool()
async def smartlead_sync_replies(campaign_id: int) -> dict:
    """Sync replied leads from a SmartLead campaign."""
    api_key = _config.get("smartlead_api_key")
    if not api_key:
        return {"success": False, "error": "SmartLead API key not configured."}
    from gtm_mcp.tools.smartlead import smartlead_sync_replies as _impl
    return await _impl(api_key, campaign_id)


@mcp.tool()
async def smartlead_send_reply(campaign_id: int, lead_id: int, body: str) -> dict:
    """Send a reply to a lead in SmartLead."""
    api_key = _config.get("smartlead_api_key")
    if not api_key:
        return {"success": False, "error": "SmartLead API key not configured."}
    from gtm_mcp.tools.smartlead import smartlead_send_reply as _impl
    return await _impl(api_key, campaign_id, lead_id, body)


@mcp.tool()
async def smartlead_activate_campaign(campaign_id: int, confirm: str) -> dict:
    """Activate a SmartLead campaign. Must pass confirm='I confirm'."""
    api_key = _config.get("smartlead_api_key")
    if not api_key:
        return {"success": False, "error": "SmartLead API key not configured."}
    from gtm_mcp.tools.smartlead import smartlead_activate_campaign as _impl
    return await _impl(api_key, campaign_id, confirm)


# ─── GetSales Tools ───────────────────────────────────────────────────────────

@mcp.tool()
async def getsales_list_profiles() -> dict:
    """List GetSales LinkedIn profiles."""
    api_key = _config.get("getsales_api_key")
    team_id = _config.get("getsales_team_id")
    if not api_key or not team_id:
        return {"success": False, "error": "GetSales API key or team_id not configured."}
    from gtm_mcp.tools.getsales import getsales_list_profiles as _impl
    return await _impl(api_key, team_id)


@mcp.tool()
async def getsales_create_flow(name: str, nodes: list[dict]) -> dict:
    """Create a GetSales LinkedIn outreach flow."""
    api_key = _config.get("getsales_api_key")
    team_id = _config.get("getsales_team_id")
    if not api_key or not team_id:
        return {"success": False, "error": "GetSales not configured."}
    from gtm_mcp.tools.getsales import getsales_create_flow as _impl
    return await _impl(api_key, team_id, name, nodes)


@mcp.tool()
async def getsales_add_leads(flow_id: int, leads: list[dict]) -> dict:
    """Add leads to a GetSales flow."""
    api_key = _config.get("getsales_api_key")
    team_id = _config.get("getsales_team_id")
    if not api_key or not team_id:
        return {"success": False, "error": "GetSales not configured."}
    from gtm_mcp.tools.getsales import getsales_add_leads as _impl
    return await _impl(api_key, team_id, flow_id, leads)


@mcp.tool()
async def getsales_activate_flow(flow_id: int, confirm: str) -> dict:
    """Activate a GetSales flow. Must pass confirm='I confirm'."""
    api_key = _config.get("getsales_api_key")
    team_id = _config.get("getsales_team_id")
    if not api_key or not team_id:
        return {"success": False, "error": "GetSales not configured."}
    from gtm_mcp.tools.getsales import getsales_activate_flow as _impl
    return await _impl(api_key, team_id, flow_id, confirm)


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
