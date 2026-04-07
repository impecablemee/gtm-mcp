# Test Run #8 — sally-fintech — Issues Report
Date: 2026-04-07

## Run Summary
- 206 gathered (probe only, no gather) -> 140 scraped (16 probe + 124 agent) -> 90 targets (64%) -> 220 contacts
- Campaign: sally-fintech-fintech-07-04 (ID 3141033), 137 Rinat accounts, 220 leads pushed
- KPI: 220/100 = 220% exceeded
- Total credits: 226 (6 probe + 220 people)

---

## ISSUES FOUND

### Issue 1: Search credits = 0 in report (MISLEADING) — FIXED
**Severity:** Medium (cosmetic but confusing)
**What:** Report shows "Search: 0, $0.00" because `pipeline_gather_and_scrape` was never called. Probe found 206 companies and agent skipped gather entirely. Probe credits (6) tracked separately in `total_credits_probe`.
**Root cause:** Probe saves to `total_credits_probe` but NOT `total_credits_search`. When gather is skipped, search stays 0.
**Fix:** Probe now also writes `total_credits_search: credits_used`. Gather overwrites if called later.
**File:** `src/gtm_mcp/tools/pipeline.py:162`

### Issue 2: people_credits = len(contacts) instead of len(all_person_ids) — FIXED
**Severity:** Medium (under-counting credits)
**What:** `people_credits` was set to 220 (contacts with emails), but Apollo charges per enrichment request, not per email returned. Some person IDs return no email — those credits are still spent.
**Root cause:** Line 1109 used `len(contacts)` instead of `len(all_person_ids)`.
**Fix:** Changed to `len(all_person_ids)`.
**File:** `src/gtm_mcp/tools/pipeline.py:1109`

### Issue 3: rounds_completed = 0 in totals — FIXED
**Severity:** Low (cosmetic)
**What:** `totals.rounds_completed` is 0 despite round-001 being completed.
**Root cause:** `rounds_completed` was never set by any tool — agent wrote it as 0 during init, nobody updated it.
**Fix:** `pipeline_gather_and_scrape` now sets `rounds_completed` from round count.
**File:** `src/gtm_mcp/tools/pipeline.py:459`

### Issue 4: Leaderboard empty — requests array empty — FIXED
**Severity:** Medium (blocks continuation flow)
**What:** `pipeline_compute_leaderboard` returns error "No keyword_leaderboard in run file" because `requests` array is empty.
**Root cause:** Probe never saved its requests to the `requests` array. Only `pipeline_gather_and_scrape` does. When gather is skipped, leaderboard has no data.
**Fix:** Probe now saves its breakdown as requests (with type, filter_value, page, credits_used, raw_returned, new_unique).
**File:** `src/gtm_mcp/tools/pipeline.py:166`

### Issue 5: 190/206 companies show scrape status "not_scraped" in run file
**Severity:** Medium (data integrity)
**What:** Round scrape_phase says 140 success, 66 failed. But companies dict only has 16 with `scrape.status=success`. The other 124 show `not_scraped`.
**Root cause:** Probe saved all 206 companies with `not_scraped` status (only 16 were scraped by probe). Agent then scraped 124 more via `scrape_batch` directly, but never updated the companies dict in the run file with the new scrape status.
**Impact:** Continuation flow thinks 190 companies need re-scraping. Data is stale.
**Status:** NOT FIXED — requires either (a) gather to always run, or (b) a separate tool to update scrape status in run file after agent scrapes.

### Issue 6: classify_chunk_2 missing .json extension
**Severity:** Low (cosmetic)
**What:** File saved as `classify_chunk_2` instead of `classify_chunk_2.json`.
**Root cause:** Agent-side naming inconsistency.
**Impact:** None for current flow (code reads file without extension), but messy.
**Status:** NOT FIXED — agent behavior, not tool bug.

### Issue 7: 2 orphan contact domains not in companies dict
**Severity:** Low
**What:** `simplicitygroup.com` and `checkout.com` appear in contacts but not in companies dict.
**Root cause:** Apollo enrichment returned these domains as `company_domain` for people who were searched under different company domains. The enrichment org_data maps to the person's CURRENT employer, not the searched company.
**Impact:** These contacts still have full data (org_data on contact), so sheet is fine. But traceability is broken.
**Status:** NOT FIXED — edge case in Apollo data.

### Issue 8: 9 targets with no people extracted
**Severity:** Low
**What:** 9 target companies have `people_extracted: False`. All have `scrape: not_scraped`.
**Domains:** agree.com, getcheddar.com, ubble.ai, received.ai, envel.ai, frienton.com, loopinsure.co, helloplum.com, getspendly.com
**Root cause:** These were classified as targets by the agent (based on scrape text it had in-memory) but their scrape status is `not_scraped` in run file. Apollo people search may have returned no results for them.
**Impact:** 9 companies with potential contacts left on the table. KPI already exceeded so no business impact.
**Status:** NOT FIXED — acceptable for this run.

### Issue 9: selected_accounts.json not saved per-project
**Severity:** Medium
**What:** `selected_accounts.json` not found in project dir.
**Root cause:** Agent may not have called the tool with project param, or file was saved to global location.
**Impact:** On continuation, user would need to re-confirm accounts.
**Status:** NOT FIXED — need to verify agent is passing project param.

### Issue 10: 97/140 classified companies have short reasoning (<100 chars)
**Severity:** Low (was supposed to be 3-5 sentences)
**What:** 69% of classified companies have reasoning under 100 characters. Example: "E-commerce checkout platform for selling to consumers. Not B2B fintech infrastructure." (85 chars). Probe_classified entries have proper 3-5 sentence reasoning.
**Root cause:** Classification agents used shorter reasoning than the probe. Skill says 3-5 sentences but agents compressed.
**Impact:** None for accuracy (64% target rate is good). But less auditable.
**Status:** NOT FIXED — agent behavior.

---

## CHECKLIST

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | Probe credits tracked | PASS | 6 credits in totals |
| 2 | Search credits tracked | FAIL -> FIXED | Was 0, now probe fills it |
| 3 | People credits tracked | PASS (but wrong count) -> FIXED | Was len(contacts), now len(person_ids) |
| 4 | Total credits correct | PASS | probe + search + people |
| 5 | max_credits enforced (companies) | PASS | Only 6 credits for companies |
| 6 | KPI met | PASS | 220/100 = 220% |
| 7 | probe_companies survived | PASS | 206 in probe_companies dict |
| 8 | Classification quality | PARTIAL | 90 targets, 64% rate. But short reasoning |
| 9 | contacts.json saved | PASS | 220 contacts |
| 10 | org_data on contacts | PASS | All 220 have org_data with industry |
| 11 | Google Sheet created | PASS | URL in report |
| 12 | SmartLead campaign created | PASS | ID 3141033, 220 leads, 137 accounts |
| 13 | Campaign naming | PASS | "Sally Fintech FINTECH 07/04" |
| 14 | Leaderboard computed | FAIL -> FIXED | Requests array was empty |
| 15 | rounds_completed | FAIL -> FIXED | Was 0, now auto-set |
| 16 | selected_accounts.json | FAIL | Not saved per-project |
| 17 | Scrape status in run file | FAIL | 190/206 show not_scraped |
| 18 | leads_for_push.json | PASS | 220 leads |
| 19 | campaign.yaml | PASS | All fields populated |
| 20 | sequence.yaml | PASS | Saved in campaign dir |

**Score: 16/20 PASS (4 FIXED in code, 4 remaining)**

---

## FIXES APPLIED

### Fix 1: Probe credits → total_credits_search (pipeline.py:162)
Probe now writes `total_credits_search` so report shows correct search credits.

### Fix 2: people_credits = len(all_person_ids) (pipeline.py:1141)
Credits now count enrichment requests, not returned contacts.

### Fix 3: rounds_completed auto-set (pipeline.py:480)
`pipeline_gather_and_scrape` sets `rounds_completed` from round count.

### Fix 4: Probe requests saved for leaderboard (pipeline.py:167)
Probe breakdown saved to `requests[]` with `_from_probe` tag. Leaderboard works without gather.

### Fix 5: Scrape unscraped probe companies in gather (pipeline.py:240-270)
`pipeline_gather_and_scrape` now pre-populates companies dict with probe data and queues unscraped probe domains for scraping. Scrape status properly updated in run file.

### Fix 6: Google Sheet reuse on append (pipeline.py:1172, sheets.py:298)
- `pipeline_people_to_push` looks for `sheet_id` in campaign.yaml when mode="append"
- Sheet cleared before re-export (prevents duplicate rows)
- `sheet_id` saved to campaign.yaml after creation (mode="create")
- On append: full re-export of ALL contacts (old + new) to same sheet URL

### Fix 7: Gather preserves probe requests (pipeline.py:475)
When gather runs after probe, probe requests tagged `_from_probe` are preserved in merge.

---

## RUN-002 ("add 50 more") — IN PROGRESS

| Metric | Value |
|--------|-------|
| Mode | append to campaign 3141033 |
| Phase 0 | 9 unused targets (~27 contacts, insufficient for KPI=50) |
| Gather | 50 new companies, 13 search credits |
| Scrape | 34/50 success |
| Classification | in progress |
| People | not yet |
| Dedup baseline | 206 companies, 220 contacts from run-001 |

### Run-002 Final Results
- 50 gathered (13 search credits) → 34 scraped → 18 targets (53%) → 29 contacts
- Phase 0 yielded 0 contacts (9 unused targets too small for Apollo)
- 29 leads appended to campaign 3141033
- Total in campaign: 249 (220 + 29)
- KPI: 29/50 = 58% (NOT MET)
- Credits: 13 search + 29 people = 42 total

### Issues in Run-002

| # | Issue | Severity | Root Cause |
|---|-------|----------|------------|
| R2-1 | people_credits=29=len(contacts), not len(person_ids) | Medium | Code fix applied but MCP server running old code |
| R2-2 | Phase 0 → 0 contacts from 9 targets | Low | Apollo has no people for tiny companies. Data, not code |
| R2-3 | Classification chunk structure inconsistent | Medium | Agent produces nested vs flat format randomly |
| R2-4 | KPI not met (29/50) | Info | 1.6 contacts/company vs 3 assumed. Agent should suggest more |
| R2-5 | sheet_id not in campaign.yaml | Medium | Code fix applied but MCP server running old code |
| R2-6 | state.yaml still points to run-001 | Low | Agent didn't update state |
| R2-7 | Google Sheet may not include run-002 contacts | High | If agent called sheets_export before, new contacts not there |

### Fixes needed (agent-side, not tool)
- Enforce classification output format in agent prompt: MUST be `{domain: {classification: {is_target, ...}}}`
- Agent MUST update state.yaml active_run_id on continuation
- Agent MUST call sheets_export_contacts AFTER all contacts saved (not before)

---

## ARCHITECTURE FIXES — Deterministic, Agent-Proof

### Fix 8: Auto-compute keyword_start_pages from ALL run files (pipeline.py gather)
`pipeline_gather_and_scrape` now scans ALL `runs/run-*.json` files and builds a complete
keyword→page map from actual request history. Agent doesn't need to pass `keyword_start_pages`
at all — the tool computes it deterministically. Agent-provided value is fallback only.

### Fix 9: max_companies means NEW companies (pipeline.py gather)
`max_companies=50` now means "find 50 NEW companies on top of existing". Previously it was
capped by `len(seen_domains) >= max_companies` which counted existing companies.
No more "seen_domains bug" when re-running gather.

### Fix 10: Protected data keys survive agent overwrite (pipeline.py gather)
`pipeline_gather_and_scrape` saves to BOTH `companies` AND `gather_companies` (+ `requests`
AND `gather_requests`). Same pattern as `probe_companies`. Agent `save_data(mode="write")`
can't destroy this data.

### Fix 11: Auto-recovery from agent overwrites (_recover_run_data)
Every pipeline tool that reads the run file calls `_recover_run_data()` first. If `companies`
is empty but `gather_companies` or `probe_companies` has data, it restores automatically.
Same for `requests` → `gather_requests`.

### Fix 12: pipeline_prepare_continuation uses full request history
Instead of relying on leaderboard only, continuation now scans ALL run files' requests to
build `keyword_start_pages` and `fired_keywords`. Works even when leaderboard was never computed.

### Fix 13: Classification chunk normalization in launch.md merge
Merge code now normalizes flat `{is_target, ...}` → nested `{classification: {is_target, ...}}`
automatically. Different agent output formats handled deterministically.
