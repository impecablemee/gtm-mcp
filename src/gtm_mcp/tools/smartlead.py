"""SmartLead API tools — campaign CRUD, sequences, leads, replies."""
import asyncio
from typing import Any, Optional

import httpx

BASE_URL = "https://server.smartlead.ai/api/v1"


async def _sl_get(api_key: str, path: str, params: dict | None = None) -> dict:
    params = params or {}
    params["api_key"] = api_key
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()


async def _sl_post(api_key: str, path: str, data: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}{path}",
            params={"api_key": api_key},
            json=data,
        )
        resp.raise_for_status()
        return resp.json()


async def smartlead_list_campaigns(api_key: str) -> dict:
    data = await _sl_get(api_key, "/campaigns")
    campaigns = []
    for c in (data if isinstance(data, list) else []):
        campaigns.append({
            "id": c.get("id"),
            "name": c.get("name", ""),
            "status": c.get("status", ""),
            "created_at": c.get("created_at", ""),
        })
    return {"success": True, "campaigns": campaigns}


async def smartlead_create_campaign(api_key: str, name: str) -> dict:
    data = await _sl_post(api_key, "/campaigns/create", {"name": name})
    return {"success": True, "campaign_id": data.get("id"), "name": name}


async def smartlead_set_sequence(api_key: str, campaign_id: int, sequences: list[dict]) -> dict:
    data = await _sl_post(api_key, f"/campaigns/{campaign_id}/sequences", {"sequences": sequences})
    return {"success": True, "campaign_id": campaign_id}


async def smartlead_add_leads(api_key: str, campaign_id: int, leads: list[dict]) -> dict:
    data = await _sl_post(api_key, f"/campaigns/{campaign_id}/leads", {"lead_list": leads})
    return {"success": True, "campaign_id": campaign_id, "leads_added": len(leads)}


async def smartlead_list_accounts(api_key: str) -> dict:
    data = await _sl_get(api_key, "/email-accounts")
    accounts = []
    for a in (data if isinstance(data, list) else []):
        accounts.append({
            "id": a.get("id"),
            "from_email": a.get("from_email", ""),
            "from_name": a.get("from_name", ""),
        })
    return {"success": True, "accounts": accounts, "count": len(accounts)}


async def smartlead_sync_replies(api_key: str, campaign_id: int) -> dict:
    data = await _sl_get(api_key, f"/campaigns/{campaign_id}/statistics")
    replied = [
        lead for lead in (data if isinstance(data, list) else [])
        if lead.get("lead_status") == "REPLIED"
    ]
    return {"success": True, "campaign_id": campaign_id, "replied_count": len(replied), "leads": replied}


async def smartlead_send_reply(api_key: str, campaign_id: int, lead_id: int, body: str) -> dict:
    data = await _sl_post(api_key, f"/campaigns/{campaign_id}/leads/{lead_id}/reply", {"body": body})
    return {"success": True}


async def smartlead_activate_campaign(api_key: str, campaign_id: int, confirm: str) -> dict:
    if confirm != "I confirm":
        return {"success": False, "error": "Must pass confirm='I confirm' to activate"}
    data = await _sl_post(api_key, f"/campaigns/{campaign_id}/status", {"status": "START"})
    return {"success": True, "campaign_id": campaign_id, "status": "ACTIVE"}
