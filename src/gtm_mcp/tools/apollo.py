"""Apollo.io API tools — company search, people search, enrichment, taxonomy."""
import time
from typing import Any

import httpx

BASE_URL = "https://api.apollo.io/api/v1"
RATE_LIMIT = 0.3  # 300ms between calls


async def apollo_search_companies(
    api_key: str,
    filters: dict,
    page: int = 1,
    per_page: int = 100,
) -> dict:
    """Search Apollo for companies. 1 credit per page.

    CRITICAL: Pass only 1 keyword OR 1 industry_tag_id per call.
    Never combine multiple — it distorts Apollo's ranking.
    """
    payload = {
        "page": page,
        "per_page": per_page,
    }
    if "q_organization_keyword_tags" in filters:
        payload["q_organization_keyword_tags"] = filters["q_organization_keyword_tags"]
    if "organization_industry_tag_ids" in filters:
        payload["organization_industry_tag_ids"] = filters["organization_industry_tag_ids"]
    if "organization_locations" in filters:
        payload["organization_locations"] = filters["organization_locations"]
    if "organization_num_employees_ranges" in filters:
        payload["organization_num_employees_ranges"] = filters["organization_num_employees_ranges"]
    if "organization_latest_funding_stage_cd" in filters:
        payload["organization_latest_funding_stage_cd"] = filters["organization_latest_funding_stage_cd"]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/mixed_companies/search",
            json=payload,
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    companies = []
    for org in data.get("organizations", []):
        companies.append({
            "domain": (org.get("primary_domain") or "").lower().strip(),
            "name": org.get("name", ""),
            "industry": org.get("industry", ""),
            "industry_tag_id": org.get("industry_tag_id", ""),
            "employee_count": org.get("estimated_num_employees"),
            "country": org.get("country", ""),
            "city": org.get("city", ""),
            "linkedin_url": org.get("linkedin_url", ""),
            "website_url": org.get("website_url", ""),
            "founded_year": org.get("founded_year"),
            "keywords": org.get("keywords", []),
            "apollo_id": org.get("id", ""),
        })

    return {
        "success": True,
        "companies": companies,
        "total_entries": data.get("pagination", {}).get("total_entries", 0),
        "page": page,
        "per_page": per_page,
    }


async def apollo_search_people(
    api_key: str,
    organization_domains: list[str],
    person_titles: list[str] | None = None,
    person_seniorities: list[str] | None = None,
    per_page: int = 25,
) -> dict:
    """Search Apollo for people at given companies. FREE — no credits."""
    payload = {
        "q_organization_domains_list": organization_domains,
        "page": 1,
        "per_page": per_page,
    }
    if person_titles:
        payload["person_titles"] = person_titles
    if person_seniorities:
        payload["person_seniorities"] = person_seniorities

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/mixed_people/search",
            json=payload,
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    people = []
    for p in data.get("people", []):
        people.append({
            "name": p.get("name", ""),
            "title": p.get("title", ""),
            "seniority": p.get("seniority", ""),
            "email": p.get("email", ""),
            "linkedin_url": p.get("linkedin_url", ""),
            "organization_name": p.get("organization", {}).get("name", ""),
            "apollo_id": p.get("id", ""),
        })

    return {"success": True, "people": people, "total": data.get("pagination", {}).get("total_entries", 0)}


async def apollo_enrich_company(api_key: str, domain: str) -> dict:
    """Enrich a single company by domain. 1 credit."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/organizations/enrich",
            json={"domain": domain},
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
    org = data.get("organization", {})
    return {"success": True, "company": org}


async def apollo_bulk_enrich_people(api_key: str, details: list[dict]) -> dict:
    """Enrich people to get verified emails. 1 credit per person.
    details: [{"first_name": "...", "last_name": "...", "organization_name": "...", "domain": "..."}]
    """
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{BASE_URL}/people/bulk_match",
            json={"details": details, "reveal_personal_emails": False},
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    matches = []
    for m in data.get("matches", []):
        if m and m.get("email"):
            matches.append({
                "name": m.get("name", ""),
                "email": m.get("email", ""),
                "title": m.get("title", ""),
                "linkedin_url": m.get("linkedin_url", ""),
                "organization": m.get("organization", {}),
            })
    return {"success": True, "matches": matches}


def apollo_get_taxonomy() -> dict:
    """Return hardcoded Apollo industry taxonomy. No API call."""
    return {
        "success": True,
        "industries": [
            "accounting", "airlines/aviation", "alternative dispute resolution",
            "alternative medicine", "animation", "apparel & fashion",
            "architecture & planning", "arts & crafts", "automotive",
            "aviation & aerospace", "banking", "biotechnology", "broadcast media",
            "building materials", "business supplies & equipment", "capital markets",
            "chemicals", "civic & social organization", "civil engineering",
            "commercial real estate", "computer & network security", "computer games",
            "computer hardware", "computer networking", "computer software",
            "construction", "consumer electronics", "consumer goods",
            "consumer services", "cosmetics", "dairy", "defense & space", "design",
            "e-learning", "education management", "electrical/electronic manufacturing",
            "entertainment", "environmental services", "events services",
            "executive office", "facilities services", "farming", "financial services",
            "food & beverages", "food production", "fund-raising", "furniture",
            "gambling & casinos", "glass ceramics & concrete",
            "government administration", "government relations", "graphic design",
            "health wellness & fitness", "higher education", "hospital & health care",
            "hospitality", "human resources", "import & export",
            "individual & family services", "industrial automation",
            "information services", "information technology & services", "insurance",
            "international affairs", "international trade & development", "internet",
            "investment banking", "investment management",
        ],
        "employee_ranges": [
            "1,10", "11,50", "51,200", "201,500",
            "501,1000", "1001,5000", "5001,10000", "10001,",
        ],
    }


def apollo_estimate_cost(
    target_count: int = 100,
    contacts_per_company: int = 3,
    target_rate: float = 0.35,
) -> dict:
    """Estimate Apollo credits needed. No API call."""
    target_companies = target_count / contacts_per_company
    companies_from_apollo = target_companies / target_rate
    pages = int(companies_from_apollo / 60) + 1  # ~60 unique per 100 requested
    search_credits = pages
    people_credits = target_count
    total = search_credits + people_credits
    return {
        "success": True,
        "search_credits": search_credits,
        "people_credits": people_credits,
        "total_credits": total,
        "total_usd": round(total * 0.01, 2),
        "estimate": f"~{total} credits (${round(total * 0.01, 2)})",
    }
