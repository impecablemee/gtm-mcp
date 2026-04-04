"""GetSales API tools — LinkedIn outreach flows."""
from typing import Optional

import httpx

BASE_URL = "https://api.getsales.io/api/v1"


async def _gs_request(method: str, path: str, api_key: str, team_id: str, data: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Team-Id": team_id,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        if method == "GET":
            resp = await client.get(f"{BASE_URL}{path}", headers=headers)
        else:
            resp = await client.post(f"{BASE_URL}{path}", headers=headers, json=data or {})
        resp.raise_for_status()
        return resp.json()


async def getsales_list_profiles(api_key: str, team_id: str) -> dict:
    data = await _gs_request("GET", "/linkedin-profiles", api_key, team_id)
    profiles = []
    for p in (data.get("data", []) if isinstance(data, dict) else []):
        profiles.append({
            "id": p.get("id"),
            "name": p.get("name", ""),
            "linkedin_url": p.get("linkedin_url", ""),
        })
    return {"success": True, "profiles": profiles}


async def getsales_create_flow(api_key: str, team_id: str, name: str, nodes: list[dict]) -> dict:
    data = await _gs_request("POST", "/flows", api_key, team_id, {"name": name, "nodes": nodes})
    return {"success": True, "flow_id": data.get("data", {}).get("id"), "name": name}


async def getsales_add_leads(api_key: str, team_id: str, flow_id: int, leads: list[dict]) -> dict:
    data = await _gs_request("POST", f"/flows/{flow_id}/leads", api_key, team_id, {"leads": leads})
    return {"success": True, "flow_id": flow_id, "leads_added": len(leads)}


async def getsales_activate_flow(api_key: str, team_id: str, flow_id: int, confirm: str) -> dict:
    if confirm != "I confirm":
        return {"success": False, "error": "Must pass confirm='I confirm' to activate"}
    data = await _gs_request("POST", f"/flows/{flow_id}/activate", api_key, team_id)
    return {"success": True, "flow_id": flow_id, "status": "ACTIVE"}
