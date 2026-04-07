# Inxy Affiliates — Full Validation Checklist

**Date**: 2026-04-07
**Project**: inxy-affiliate
**Run**: run-001
**Mode**: append (campaign 3137079)

---

## Checklist Summary

| # | Check | Status | Detail |
|---|-------|--------|--------|
| 1 | Credits math: probe + search + people = total | PASS | 6 + 17 + 28 = 51 (matches reported total) |
| 2 | contacts.json count matches run file | PASS | Both report 28 contacts |
| 3 | leads_for_push.json count matches contacts | PASS | 28 leads in push file, 28 in contacts.json |
| 4 | SmartLead push count matches | PASS | campaign.leads_pushed = 28, campaign.yaml total_leads_pushed = 480 |
| 5 | Dedup baseline math | PASS | 452 existing emails + 28 new = 480 total (matches campaign.yaml) |
| 6 | Blacklist: 307 domains imported | PASS | blacklist.json has 307 domain keys |
| 7 | Blacklist: no blacklisted domains in contacts | PASS | Zero contact email domains match blacklist |
| 8 | Keywords: affiliate-themed, not fintech | PASS | 19 keywords used in gather, all affiliate/CPA/ad-network themed. Zero fintech keywords |
| 9 | 9 example companies: which appeared | FAIL | 0 of 9 appear in gathered companies (see Issue 4 in log) |
| 10 | 9 example companies: blacklisted ones excluded | PASS | 5 blacklisted (adsterra, propellerads, clickadu, trafficstars, sundesiremedia) correctly excluded |
| 11 | Classification: nested format | PASS | All 296 classified companies use `{is_target, confidence, segment, reasoning}` dict |
| 12 | Classification: segments correct theme | PASS | Primary target segment is AFFILIATE_NETWORKS (27 targets) |
| 13 | Campaign 3137079: leads appended (not new) | PASS | mode=append, existing campaign_id=3137079, leads added to existing campaign |
| 14 | Protected keys: gather_companies present | PASS | gather_companies: 424 entries in run file |
| 15 | Protected keys: gather_requests present | PASS | gather_requests: 23 entries in run file |
| 16 | File hygiene: chunks in project root | FAIL | 10 chunk files (4 classify + 2 extra classify + 4 scrape) in project root, not tmp/ |
| 17 | Missing: pipeline-config.yaml | FAIL | Not present in project directory |
| 18 | Missing: selected_accounts.json | FAIL | Not present (using campaign 3137079's existing 46 accounts) |
| 19 | Duplicate emails in contacts.json | FAIL | vlad.b@referon.com appears 2x (Vlad vs Vladyslav Bondarenko, same person) |
| 20 | Duplicate emails in leads_for_push.json | FAIL | Same vlad.b@referon.com duplicate pushed to SmartLead |
| 21 | Empty company_domain in contacts | FAIL | adriana@algorand.foundation has empty company_domain and company_name |
| 22 | state.yaml reflects actual progress | FAIL | Shows round_loop=in_progress, people_extraction=pending, campaign_push=pending — but all are completed |
| 23 | project.yaml: all 9 example companies listed | FAIL | Only 7 of 9: missing sundesiremedia.com and excellerate.com |
| 24 | classify_chunk_2 missing .json extension | FAIL | Saved as `classify_chunk_2` instead of `classify_chunk_2.json` (recurring issue) |
| 25 | Probe breakdown: duplicate entries | FAIL | 3 duplicate entries in probe.breakdown (CPA network, affiliate network, performance marketing network each appear 2x) |
| 26 | Keyword leaderboard populated | PASS | 22 entries with quality scores, target rates, exhaustion flags |
| 27 | Redundant chunk files | FAIL | classify_chunk_3_output.json and classify_chunk_4_temp.json are duplicates of chunk_3 and chunk_4 |
| 28 | False positive targets in classification | FAIL | At least 3-4 misclassified companies (see NEW ISSUES below) |
| 29 | 17 of 27 targets got zero contacts | WARN | 63% of targets yielded no people from Apollo enrichment |

**Score: 14 PASS / 12 FAIL / 1 WARN out of 29 checks**

---

## Issues Already Logged (confirmed)

| Issue | Confirmed | Notes |
|-------|-----------|-------|
| ISSUE 1: apollo_enrich_companies NoneType crash | YES | Fix committed (13b706e). 9 examples not enriched. |
| ISSUE 2: Only 6 of 9 domains in enrichment call | YES | project.yaml lists only 7 (missing sundesiremedia.com, excellerate.com) |
| ISSUE 3: TrafficStps typo in user input | YES | Parsing error from user prompt |
| ISSUE 4: 9 example companies NOT in companies dict | YES | 5 blacklisted, 4 not in Apollo index |
| ISSUE 5: Chunks in project root, not tmp/ | YES | 10 chunk files confirmed in root |
| ISSUE 6: Missing pipeline-config.yaml + selected_accounts.json | YES | Both absent |
| ISSUE 7: Leaderboard empty | FIXED | Now has 22 entries (was empty at time of logging, populated later) |
| ISSUE 8: 9.5% target rate | YES | 27/296 = 9.1% — niche vertical, expected |

---

## NEW Issues (not in issues log)

### NEW ISSUE 9: Duplicate email pushed to SmartLead
**Severity: MEDIUM**
`vlad.b@referon.com` appears twice in both contacts.json and leads_for_push.json. Two Apollo records (Vlad Bondarenko / Vladyslav Bondarenko) share the same email. The dedup logic checks against baseline emails from the existing campaign but does NOT dedup within the current batch. SmartLead received the same email twice.

### NEW ISSUE 10: Empty company_domain contact
**Severity: LOW**
`adriana@algorand.foundation` has empty `company_domain` and `company_name_normalized`. The email domain is `algorand.foundation` but the company was enriched under `algorand.co`. The people enrichment returned this contact without mapping back to the parent domain.

### NEW ISSUE 11: False positive classifications — non-affiliate companies marked as targets
**Severity: HIGH**
At least 4 companies are misclassified as AFFILIATE_NETWORKS:

| Domain | Actual Business | Confidence | Why Wrong |
|--------|----------------|------------|-----------|
| staderlabs.com | DeFi staking platform (Stader Labs) | 65 | Blockchain staking, not affiliate/CPA |
| transfi.com | Crypto payment infrastructure (TransFi) | 83 | Payment gateway, not affiliate network |
| algorand.co | Blockchain L1 protocol (Algorand Foundation) | 50 | Layer-1 blockchain, not affiliate |
| thecirqle.com | Influencer marketing platform (Meta/TikTok partner) | 93 | Influencer platform, not CPA network |

The classifier appears to trigger on generic keywords like "payout", "offer", "network" without distinguishing affiliate networks from crypto/fintech/influencer platforms. These 4 companies account for 12 of the 28 contacts (43% of pushed leads are false positives).

### NEW ISSUE 12: Probe breakdown has duplicate entries
**Severity: LOW**
`probe.breakdown` contains 12 entries but 3 keywords appear twice each (CPA network, affiliate network, performance marketing network). Likely the breakdown was appended twice — once with industry_tag_ids and once with industry names. Not a data corruption issue but indicates a probe reporting bug.

### NEW ISSUE 13: state.yaml not updated after completion
**Severity: MEDIUM**
state.yaml shows:
- `current_phase: round_loop`
- `people_extraction: pending`
- `campaign_push: pending`
- `status: running`

But the run file shows contacts extracted (28), leads pushed to campaign, and `campaign.pushed_at` timestamp exists. The pipeline completed people extraction and campaign push but never updated state.yaml. This would break resume functionality.

### NEW ISSUE 14: Redundant classify chunk files
**Severity: LOW**
Two extra classification files exist that are duplicates:
- `classify_chunk_3_output.json` (identical to `classify_chunk_3.json`)
- `classify_chunk_4_temp.json` (identical to `classify_chunk_4.json`)

These are agent artifacts that should be cleaned up or written to tmp/.

### NEW ISSUE 15: 63% of targets yielded zero contacts
**Severity: MEDIUM**
17 out of 27 target companies produced no contacts from Apollo people enrichment. This could mean:
- Small affiliate networks not indexed in Apollo's people database
- People search exhausted the 3-per-company limit with unverified emails (filtered out)
- `total_credits_people = 28` suggests only 28 credits spent, meaning only ~10 companies returned results

Combined with 4 false positives among the remaining 10 companies that DID return contacts, the effective yield is approximately 6 legitimate affiliate network contacts out of 27 targets.

---

## 9 Example Companies — Detailed Status

| Domain | Blacklisted | In Gathered | In Contacts | Status |
|--------|:-----------:|:-----------:|:-----------:|--------|
| adsterra.com | YES | NO | NO | Correctly excluded (in campaign 3137079) |
| propellerads.com | YES | NO | NO | Correctly excluded |
| clickadu.com | YES | NO | NO | Correctly excluded |
| trafficstars.com | YES | NO | NO | Correctly excluded |
| sundesiremedia.com | YES | NO | NO | Correctly excluded; missing from project.yaml example list |
| imonetize.com | NO | NO | NO | Not in Apollo index (small network) |
| adverticals.com | NO | NO | NO | Not in Apollo index |
| trafficinmedia.com | NO | NO | NO | Not in Apollo index |
| excellerate.com | NO | NO | NO | Not in Apollo index; missing from project.yaml example list |

**Result**: 5/9 blacklisted (correct), 4/9 not found in Apollo. Zero examples appear as gathered targets.

---

## Credits Breakdown

| Category | Credits | Notes |
|----------|---------|-------|
| Probe | 6 | 3 keywords + 3 industries tested |
| Search (gather) | 17 | 19 unique keywords + 3 industries, 23 total requests |
| People enrichment | 28 | 28 contacts extracted from 10 companies |
| **Total** | **51** | Matches run file. Well under 200 credit cap |

---

## File Inventory

| File | Expected | Present | Issue |
|------|----------|---------|-------|
| project.yaml | YES | YES | Missing 2 of 9 example domains |
| state.yaml | YES | YES | Stale — not updated after people+push |
| blacklist.json | YES | YES | 307 domains, correct |
| contacts.json | YES | YES | 28 entries, 1 duplicate email, 1 empty domain |
| leads_for_push.json | YES | YES | 28 entries, same duplicate |
| runs/run-001.json | YES | YES | 1MB, complete run data |
| campaigns/inxy-affiliate-network/campaign.yaml | YES | YES | 480 total leads |
| pipeline-config.yaml | YES | NO | Not saved |
| selected_accounts.json | YES | NO | Not saved (using campaign's existing accounts) |
| tmp/ directory | YES | NO | Chunks written to project root instead |
| classify_chunk_1.json | NO (should be in tmp/) | YES | In root |
| classify_chunk_2 | NO (should be .json) | YES | Missing extension |
| classify_chunk_3.json | NO (should be in tmp/) | YES | In root |
| classify_chunk_3_output.json | NO | YES | Redundant duplicate |
| classify_chunk_4.json | NO (should be in tmp/) | YES | In root |
| classify_chunk_4_temp.json | NO | YES | Redundant duplicate |
| scrape_chunk_{1-4}.json | NO (should be in tmp/) | YES | In root |
