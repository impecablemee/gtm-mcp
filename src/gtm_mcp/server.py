"""GTM-MCP Server — 39 thin tools, zero LLM calls. stdio transport via FastMCP."""
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


@mcp.tool()
async def find_campaign(campaign_ref: str) -> dict:
    """Find a campaign by SmartLead ID or slug across all projects.

    Use when the user provides a campaign= parameter and you need to
    resolve which project it belongs to.
    """
    result = _workspace.find_campaign(campaign_ref)
    if result is None:
        return {"success": False, "error": f"Campaign '{campaign_ref}' not found in any project"}
    return {"success": True, "data": result}


@mcp.tool()
async def get_project_costs(project: str) -> dict:
    """Get cost breakdown for a project — totals, per-campaign, and per-run.

    Scans all run files and aggregates: credits (search + people), USD,
    companies gathered, contacts extracted. Grouped by campaign.
    """
    return {"success": True, "data": _workspace.get_project_costs(project)}


# ─── Google Sheets Tools ─────────────────────────────────────────────────────

@mcp.tool()
async def sheets_create(title: str, share_with: str = "") -> dict:
    """Create a Google Sheet on Shared Drive with standard contact headers.

    Returns sheet_id and sheet_url. Optionally shares with an email (editor).
    Requires GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_SHARED_DRIVE_ID in .env.
    """
    from gtm_mcp.tools.sheets import sheets_create as _impl
    return await _impl(title, share_with, config=_config)


@mcp.tool()
async def sheets_export_contacts(
    project: str, campaign_slug: str = "", sheet_id: str = "",
) -> dict:
    """Export project contacts to a Google Sheet.

    If sheet_id provided → appends to existing sheet.
    If not → creates new sheet, returns URL.
    If campaign_slug → filters contacts by that campaign's segment.
    """
    from gtm_mcp.tools.sheets import sheets_export_contacts as _impl
    return await _impl(project, campaign_slug, sheet_id,
                       config=_config, workspace=_workspace)


@mcp.tool()
async def sheets_read(sheet_id: str, tab: str = "Sheet1") -> dict:
    """Read all data from a Google Sheet tab as list of dicts.

    Use for: importing blacklist domains from a sheet, reading company lists,
    or any structured data the user has in Google Sheets.
    """
    from gtm_mcp.tools.sheets import sheets_read as _impl
    return await _impl(sheet_id, tab, config=_config)


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
    """Search Apollo for companies. 1 credit/page. Rate limited (300ms + 429 retry).

    CRITICAL: Pass EITHER q_organization_keyword_tags OR organization_industry_tag_ids.
    NEVER both — Apollo ANDs them, kills results. Use separate parallel calls.
    Locations, employee_ranges, funding_stages CAN be combined with either.
    """
    api_key = _config.get("apollo_api_key")
    if not api_key:
        return {"success": False, "error": "Apollo API key not configured. Run set_config."}
    from gtm_mcp.tools.apollo import apollo_search_companies as _impl
    return await _impl(api_key, filters, page, per_page)


@mcp.tool()
async def apollo_search_people(
    domain: str,
    person_seniorities: list[str] | None = None,
    per_page: int = 25,
) -> dict:
    """Search Apollo for people at a company. FREE — no credits.

    Returns candidates with person IDs for enrichment. Filters has_email=true.
    Default seniorities: owner, founder, c_suite, vp, head, director.
    """
    api_key = _config.get("apollo_api_key")
    if not api_key:
        return {"success": False, "error": "Apollo API key not configured."}
    from gtm_mcp.tools.apollo import apollo_search_people as _impl
    return await _impl(api_key, domain, person_seniorities, per_page)


@mcp.tool()
async def apollo_enrich_people(person_ids: list[str]) -> dict:
    """Enrich people by Apollo person IDs. 1 credit per verified email.

    Returns ONLY verified emails. Also returns org data (industry_tag_id)
    which auto-extends the industry taxonomy.
    """
    api_key = _config.get("apollo_api_key")
    if not api_key:
        return {"success": False, "error": "Apollo API key not configured."}
    from gtm_mcp.tools.apollo import apollo_enrich_people as _impl
    return await _impl(api_key, person_ids)


@mcp.tool()
async def apollo_enrich_companies(domains: list[str]) -> dict:
    """Bulk enrich companies by domain. Max 10 per call, 1 credit per company.

    Returns full company data including industry_tag_id.
    Auto-extends industry taxonomy with discovered tag_ids.
    """
    api_key = _config.get("apollo_api_key")
    if not api_key:
        return {"success": False, "error": "Apollo API key not configured."}
    from gtm_mcp.tools.apollo import apollo_enrich_companies as _impl
    return await _impl(api_key, domains)


@mcp.tool()
async def apollo_get_taxonomy() -> dict:
    """Get Apollo industry taxonomy with hex tag_ids + employee ranges.

    Returns 84 industry name → tag_id mappings from production data.
    For organization_industry_tag_ids filter, use the hex tag_ids, NOT name strings.
    Keywords are free-text — generate any with LLM, no validation needed.
    """
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
    """Scrape a website and return cleaned text. No credits.

    3-layer fallback: Apify proxy → direct fetch → HTTP fallback.
    Retries 429/5xx with exponential backoff.
    """
    proxy = _config.get("apify_proxy_password")
    from gtm_mcp.tools.scraping import scrape_website as _impl
    return await _impl(url, apify_proxy_password=proxy)


@mcp.tool()
async def scrape_batch(urls: list[str], max_concurrent: int = 50) -> dict:
    """Scrape many URLs in parallel with concurrency pool. No credits.

    50 concurrent by default (Apify residential proxy).
    MUCH faster than calling scrape_website one by one.
    Use this for batch scraping in the pipeline — pass all domains at once.
    """
    proxy = _config.get("apify_proxy_password")
    from gtm_mcp.tools.scraping import scrape_batch as _impl
    return await _impl(urls, apify_proxy_password=proxy, max_concurrent=max_concurrent)


# ─── SmartLead Tools ──────────────────────────────────────────────────────────

@mcp.tool()
async def smartlead_list_campaigns() -> dict:
    """List all SmartLead campaigns."""
    from gtm_mcp.tools.smartlead import smartlead_list_campaigns as _impl
    return await _impl(config=_config)


@mcp.tool()
async def smartlead_create_campaign(
    project: str, name: str, sending_account_ids: list[int],
    country: str = "US", segment: str = "",
) -> dict:
    """Create a SmartLead campaign with schedule, settings, and email accounts.

    Chains 5 API calls: create → schedule (timezone from country, 09-18 Mon-Fri) →
    settings (plain text, no tracking, stop on reply, 40% follow-up, AI ESP matching) →
    assign accounts → save locally.
    Campaign is always DRAFT — use smartlead_activate_campaign to start sending.
    """
    from gtm_mcp.tools.smartlead import smartlead_create_campaign as _impl
    return await _impl(project, name, sending_account_ids, country,
                       segment=segment, config=_config, workspace=_workspace)


@mcp.tool()
async def smartlead_set_sequence(
    project: str, campaign_slug: str, campaign_id: int, steps: list[dict],
) -> dict:
    """Set email sequence steps for a SmartLead campaign.

    Saves sequence.yaml locally first, then pushes to SmartLead.
    Each step: {step, day, subject, body, subject_b?}
    """
    from gtm_mcp.tools.smartlead import smartlead_set_sequence as _impl
    return await _impl(project, campaign_slug, campaign_id, steps,
                       config=_config, workspace=_workspace)


@mcp.tool()
async def smartlead_add_leads(campaign_id: int, leads: list[dict]) -> dict:
    """Add leads to a SmartLead campaign.

    Each lead: {email, first_name, last_name, company_name, custom_fields?}
    custom_fields is a dict: {"segment": "PAYMENTS", "city": "Miami"}
    """
    from gtm_mcp.tools.smartlead import smartlead_add_leads as _impl
    return await _impl(campaign_id, leads, config=_config)


@mcp.tool()
async def smartlead_list_accounts() -> dict:
    """Load ALL SmartLead email accounts, cache locally, return SUMMARY.

    With 2000+ accounts, the full list is too large for tool results.
    This caches all accounts to ~/.gtm-mcp/email_accounts.json and returns:
    total count, unique domains, top 20 domains by account count.
    Use smartlead_search_accounts(query) to filter by name/email/domain.
    """
    from gtm_mcp.tools.smartlead import smartlead_list_accounts as _impl
    return await _impl(config=_config, workspace=_workspace)


@mcp.tool()
async def smartlead_search_accounts(query: str) -> dict:
    """Search cached email accounts by name, email, or domain.

    Call smartlead_list_accounts() first to populate the cache.
    Example queries: "sally", "danila", "renat@", "getsally.io"
    Returns matching accounts with IDs ready for campaign creation.
    """
    from gtm_mcp.tools.smartlead import smartlead_search_accounts as _impl
    return await _impl(query, config=_config, workspace=_workspace)


@mcp.tool()
async def smartlead_sync_replies(
    project: str, campaign_slug: str, campaign_id: int,
) -> dict:
    """Sync replied leads from a SmartLead campaign. Saves replies.json to workspace."""
    from gtm_mcp.tools.smartlead import smartlead_sync_replies as _impl
    return await _impl(project, campaign_slug, campaign_id,
                       config=_config, workspace=_workspace)


@mcp.tool()
async def smartlead_send_reply(campaign_id: int, lead_id: int, body: str) -> dict:
    """Send a reply to a lead in SmartLead."""
    from gtm_mcp.tools.smartlead import smartlead_send_reply as _impl
    return await _impl(campaign_id, lead_id, body, config=_config)


@mcp.tool()
async def smartlead_activate_campaign(campaign_id: int, confirm: str) -> dict:
    """Activate a SmartLead campaign. confirm must be exactly 'I confirm'.

    This starts REAL email sending — use with care.
    """
    from gtm_mcp.tools.smartlead import smartlead_activate_campaign as _impl
    return await _impl(campaign_id, confirm, config=_config)


@mcp.tool()
async def smartlead_pause_campaign(campaign_id: int, confirm: str) -> dict:
    """Pause an active SmartLead campaign. confirm must be exactly 'I confirm'.

    Pauses all email sending. Use smartlead_activate_campaign to resume.
    """
    from gtm_mcp.tools.smartlead import smartlead_pause_campaign as _impl
    return await _impl(campaign_id, confirm, config=_config)


@mcp.tool()
async def smartlead_send_test_email(
    campaign_id: int, test_email: str, sequence_number: int = 1,
) -> dict:
    """Send a test email from a campaign to verify the sequence.

    Requires at least one lead and one email account on the campaign.
    Auto-resolves the sending account and lead for variable substitution.
    """
    from gtm_mcp.tools.smartlead import smartlead_send_test_email as _impl
    return await _impl(campaign_id, test_email, sequence_number, config=_config)


@mcp.tool()
async def smartlead_get_campaign(campaign_id: int) -> dict:
    """Get campaign details by ID — name, status, assigned accounts, sequences.

    Use to validate an existing campaign before appending new leads.
    """
    from gtm_mcp.tools.smartlead import smartlead_get_campaign as _impl
    return await _impl(campaign_id, config=_config)


@mcp.tool()
async def smartlead_export_leads(campaign_id: int) -> dict:
    """Export all leads from a SmartLead campaign.

    Returns every lead with email, name, company, domain.
    Use for dedup when appending new contacts to an existing campaign.
    """
    from gtm_mcp.tools.smartlead import smartlead_export_leads as _impl
    return await _impl(campaign_id, config=_config)


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
