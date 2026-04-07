"""Campaign push — atomic SmartLead campaign setup in one tool call.

Creates campaign, sets sequence, uploads ALL leads, sends test email.
100% deterministic. Zero LLM needed. One tool call replaces 4+ separate calls.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def campaign_push(
    project: str,
    campaign_name: str,
    sending_account_ids: list[int],
    country: str,
    segment: str,
    sequence_steps: list[dict],
    leads_file: str,
    test_email: str = "",
    run_id: str = "",
    *,
    config=None,
    workspace=None,
) -> dict:
    """Atomic campaign push — one tool call does everything.

    1. Create SmartLead campaign (DRAFT) with settings + schedule
    2. Set email sequence (with A/B variants + \\n→<br> conversion)
    3. Upload ALL leads from file (no size limit — reads from disk)
    4. Send test email (if test_email provided)
    5. Save campaign.yaml locally

    Returns: campaign_id, campaign_slug, leads_uploaded, test_email_sent
    """
    import json
    from gtm_mcp.tools.smartlead import (
        smartlead_create_campaign,
        smartlead_set_sequence,
        smartlead_add_leads,
        smartlead_export_leads,
        smartlead_send_test_email,
    )

    config = config or _default_config()
    workspace = workspace or _default_workspace()

    # 1. Create campaign
    logger.info("Creating SmartLead campaign: %s", campaign_name)
    result = await smartlead_create_campaign(
        project, campaign_name, sending_account_ids, country,
        segment=segment, config=config, workspace=workspace,
    )
    if not result.get("success"):
        return {"success": False, "error": f"Campaign creation failed: {result.get('error')}",
                "step": "create_campaign"}

    campaign_data = result["data"]
    campaign_id = campaign_data["campaign_id"]
    campaign_slug = campaign_data["slug"]
    logger.info("Campaign created: %s (ID: %s)", campaign_slug, campaign_id)

    # 2. Set sequence
    logger.info("Setting sequence: %d steps", len(sequence_steps))
    seq_result = await smartlead_set_sequence(
        project, campaign_slug, campaign_id, sequence_steps,
        config=config, workspace=workspace,
    )
    if not seq_result.get("success"):
        return {"success": False, "error": f"Sequence setup failed: {seq_result.get('error')}",
                "step": "set_sequence", "campaign_id": campaign_id}

    # 3. Upload ALL leads from file
    leads_path = workspace.base / "projects" / project.lower().replace(" ", "-") / leads_file
    if not leads_path.exists():
        # Try absolute path
        from pathlib import Path
        leads_path = Path(leads_file)

    if not leads_path.exists():
        return {"success": False, "error": f"Leads file not found: {leads_file}",
                "step": "add_leads", "campaign_id": campaign_id}

    all_leads = json.loads(leads_path.read_text())
    logger.info("Uploading %d leads from %s", len(all_leads), leads_file)

    # Single API call — SmartLead accepts full list. Retry on failure (upload is FREE).
    total_uploaded = 0
    for attempt in range(3):
        add_result = await smartlead_add_leads(campaign_id, all_leads, config=config)
        if add_result.get("success"):
            total_uploaded = len(all_leads)
            break
        logger.warning("Lead upload attempt %d failed: %s", attempt + 1, add_result.get("error"))
        if attempt < 2:
            import asyncio
            await asyncio.sleep(3 * (attempt + 1))

    if total_uploaded == 0:
        logger.error("Lead upload FAILED after 3 attempts — %d leads lost", len(all_leads))

    # Verify actual count from SmartLead (timeout ≠ failure — SmartLead may have processed it)
    try:
        verify_result = await smartlead_export_leads(campaign_id, config=config)
        if verify_result.get("success"):
            actual_count = len(verify_result.get("data", {}).get("leads", []))
            if actual_count > total_uploaded:
                logger.info("SmartLead verification: %d actual vs %d tracked — correcting", actual_count, total_uploaded)
                total_uploaded = actual_count
    except Exception as e:
        logger.warning("SmartLead verification failed: %s — using tracked count", e)

    logger.info("Uploaded %d/%d leads (verified)", total_uploaded, len(all_leads))

    # 4. Send test email
    test_sent = False
    if test_email:
        logger.info("Sending test email to %s", test_email)
        test_result = await smartlead_send_test_email(
            campaign_id, test_email, config=config,
        )
        test_sent = test_result.get("success", False)

    # 5. Update campaign.yaml with lead count + run link
    campaign_data["total_leads_pushed"] = total_uploaded
    campaign_data["run_ids"] = [run_id] if run_id else []
    workspace.save(project, f"campaigns/{campaign_slug}/campaign.yaml", campaign_data)

    # 6. Update run file with campaign data (if run_id provided)
    if run_id:
        run_path = f"runs/{run_id}.json"
        run_data = workspace.load(project, run_path)
        if run_data:
            run_data["campaign_id"] = campaign_id
            run_data["campaign_slug"] = campaign_slug
            run_data["campaign"] = {
                "campaign_id": campaign_id,
                "leads_pushed": total_uploaded,
                "pushed_at": datetime.now(timezone.utc).isoformat(),
            }
            workspace.save(project, run_path, run_data)

    return {
        "success": True,
        "data": {
            "campaign_id": campaign_id,
            "campaign_slug": campaign_slug,
            "campaign_name": campaign_name,
            "leads_uploaded": total_uploaded,
            "leads_total": len(all_leads),
            "sequence_steps": len(sequence_steps),
            "test_email_sent": test_sent,
            "test_email": test_email,
            "status": "DRAFT",
        },
    }


def _default_config():
    from gtm_mcp.config import ConfigManager
    return ConfigManager()

def _default_workspace():
    from gtm_mcp.workspace import WorkspaceManager
    return WorkspaceManager(_default_config().dir)
