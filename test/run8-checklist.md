# Test Run #8 + Continuation — FULL CHECKLIST
Date: 2026-04-07

## Report Claims vs File Reality

| Metric | Report | Files | Match? |
|--------|--------|-------|--------|
| **run-001** | | | |
| Targets | 90 | 90 | YES |
| Contacts | 220 | 220 | YES |
| Search credits | 0 | 0 | YES |
| People credits | 220 | 220 | YES |
| Total credits | 226 | 226 | YES |
| **run-002** | | | |
| Targets | 18 | 18 | YES |
| Contacts | 29 | 29 | YES |
| Search credits | 13 | **0** | **NO — DATA WIPED** |
| People credits | 29 | 29 | YES |
| Total credits | 42 | **0** | **NO — DATA WIPED** |
| **run-003** | | | |
| Targets | 8 | 8 | YES |
| Contacts | 22 | 22 | YES |
| Search credits | 9 | 9 | YES |
| People credits | 22 | 22 | YES |
| Total credits | 31 | 31 | YES |
| **TOTALS** | | | |
| Total contacts | 271 | 271 | YES |
| Total credits | 299 | **257** | **NO — run-002 credits lost** |
| contacts.json | 271 | 271 | YES |
| Unique emails | 271 | 271 | YES (0 duplicates) |

## Checklist

| # | Check | Status | Details |
|---|-------|--------|---------|
| 1 | Run-001 probe credits tracked | PASS | 6 credits in totals |
| 2 | Run-001 search credits tracked | **FAIL** | Shows 0, should be 6 (probe IS search). Fix deployed but MCP not restarted |
| 3 | Run-001 people credits tracked | PASS | 220 |
| 4 | Run-001 total credits correct | PASS | 226 (6+220) |
| 5 | Run-001 requests saved | **FAIL** | 0 requests (pre-fix). Fix deployed but MCP not restarted |
| 6 | Run-001 probe_companies survived | PASS | 206 in probe_companies |
| 7 | Run-001 classification quality | PARTIAL | 90 targets, 64% rate. 97/140 short reasoning |
| 8 | Run-001 contacts org_data | PASS | All 220 have org_data with industry |
| 9 | Run-001 campaign created | PASS | ID 3141033, 137 Rinat accounts |
| 10 | Run-001 campaign naming | PASS | "Sally Fintech FINTECH 07/04" |
| 11 | Run-002 companies preserved | **FAIL** | 0 companies — agent save_data(mode=write) wiped 50 companies |
| 12 | Run-002 requests preserved | **FAIL** | 0 requests — 13 search requests wiped |
| 13 | Run-002 credits tracked | **FAIL** | total=0, should be 42 (13 search + 29 people) |
| 14 | Run-002 contacts saved | PASS | 29 contacts in run file |
| 15 | Run-002 contacts merged to contacts.json | PASS | 249 total (220+29) |
| 16 | Run-003 gather new companies | PASS | 40 companies, 9 credits |
| 17 | Run-003 classification | PASS | 19 classified, 8 targets, ALL nested format |
| 18 | Run-003 contacts saved | PASS | 22 contacts, all have org_data |
| 19 | Run-003 contacts merged | PASS | 271 total (249+22) |
| 20 | Run-003 campaign appended | PASS | 22 leads pushed to 3141033 |
| 21 | contacts.json no duplicates | PASS | 271 unique emails |
| 22 | campaign.yaml updated | PASS | total_leads=271, run_ids=[001,002,003] |
| 23 | Google Sheet created/updated | **FAIL** | No sheet — create_sheet=false in run-003 |
| 24 | Google Sheet URL in report | **FAIL** | Not shown in final report |
| 25 | sheet_id saved to campaign.yaml | **FAIL** | NOT SET |
| 26 | SmartLead link in report | PASS | https://app.smartlead.ai/app/email-campaigns-v2/3141033/analytics |
| 27 | state.yaml updated | PARTIAL | last_updated updated, but active_run_id still run-001 |
| 28 | keyword_start_pages used | **FAIL** | All run-003 keywords at page=1 (pre-fix, MCP not restarted) |
| 29 | max_companies offset | **FAIL** | Agent hit "50 existing >= max 50" bug (pre-fix) |
| 30 | people_credits = len(person_ids) | **FAIL** | Still len(contacts)=22, not len(person_ids). Pre-fix |
| 31 | Duplicate keyword requests | **FAIL** | 3/9 duplicate keyword+page combinations in run-003 |

## Score: 18/31 PASS, 10 FAIL, 3 PARTIAL

## Root Causes

### 1. Run-002 data wiped (Issues 11-13)
Agent called `save_data(mode="write")` AFTER `pipeline_gather_and_scrape` saved data.
**Fix deployed:** `gather_companies` + `gather_requests` protected keys + `_recover_run_data()`.
**Not yet active:** MCP server running old code.

### 2. No Google Sheet (Issues 23-25)
Agent called `pipeline_people_to_push(create_sheet=false)` for run-003.
**Fix deployed:** Sheet reuse via `sheet_id` in campaign.yaml. But agent must pass `create_sheet=true`.

### 3. keyword_start_pages not used (Issues 28, 31)
Run-001 had 0 requests (probe never saved them pre-fix). So continuation had no page history.
**Fix deployed:** Gather now auto-computes start pages from ALL run files. Agent param is fallback.
**Not yet active:** MCP server running old code.

### 4. people_credits wrong (Issue 30)
Still counting `len(contacts)` not `len(all_person_ids)`.
**Fix deployed** in pipeline.py. **Not yet active.**

## What Needs MCP Restart

ALL 13 fixes are in the code but the MCP server process is running the OLD version.
After restart, the following will be active:
- Probe saves requests + search credits
- Gather auto-computes keyword_start_pages
- max_companies means NEW companies
- Protected keys (gather_companies, gather_requests)
- Auto-recovery from agent overwrites
- Sheet reuse on append
- people_credits = len(person_ids)
- Classification chunk normalization
