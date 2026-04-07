# Expected Behavior: Inxy Affiliates Campaign Extension

## Prompt
```
/launch add more contacts to this campaign https://app.smartlead.ai/app/email-campaign/3137079/analytics
I want to add more Affiliate networks to the given campaign and offer them inxy.io
[9 example companies with URLs listed]
```

## What This Means
- **Project**: NEW project (inxy or inxy-affiliates) — new offer, new ICP
- **Offer**: inxy.io — proxy service for affiliate marketers
- **Target campaign**: 3137079 — append new contacts here
- **Blacklist**: AUTOMATIC from campaign 3137079 — don't re-contact existing leads. NOT ASKED.
- **9 example companies**: reference material for ICP + filter seeding, NOT the final target list

## Expected Flow

### Phase 0: Project Setup
1. Create project "inxy-affiliates" (or similar slug)
2. Scrape inxy.io to extract offer
3. `pipeline_import_blacklist(project, campaign_id=3137079)` → saves blacklist.json
   - Exports all leads from 3137079
   - Saves their domains to blacklist.json
   - These domains will be EXCLUDED from gather results

### Phase 1: ICP Extraction (from offer + 9 examples)
The 9 companies are REFERENCE MATERIAL for the agent:
- Agent reads inxy.io offer → "proxy/residential IP service for affiliate marketers"
- Agent reads the 9 companies → understands the ICP:
  - Affiliate networks (iMonetizeIt, Adverticals, SunDesire Media)
  - CPA/CPL/RevShare networks (PropellerAds, TrafficInMedia)
  - Ad networks with affiliate format (Adsterra, Clickadu, TrafficStars)
  - Performance marketing (Excellerate)
- **ICP = companies that connect advertisers with affiliates, run CPA/CPL/RevShare offers**
- Segments: AFFILIATE_NETWORK, CPA_NETWORK, AD_NETWORK, PERFORMANCE_MARKETING

### Phase 2: Apollo Enrichment of 9 Example Companies
**CRITICAL: The 9 companies should be enriched FIRST via Apollo.**
Why:
- Apollo returns their `industry`, `industry_tag_id`, `keywords`, `employee_count`
- These real Apollo fields become the SEED for filter generation
- Example: if Adsterra has Apollo keywords ["affiliate marketing", "CPA network", "ad monetization"]
  → those become the basis for keyword generation
- Example: if their industry_tag_id = "5567cd..." → that industry filter gets used
- This is the PROBE phase — deterministic, ~9 credits (1 per company enrichment)

### Phase 3: Filter Generation (BOTH sources combined)
**Source A — Apollo enrichment data from the 9 examples:**
- Real `keywords` from Apollo (e.g., "affiliate marketing", "CPA", "ad monetization")
- Real `industry_tag_ids` (whatever Apollo assigns to these companies)
- Real `employee_count` ranges → employee_ranges filter
- These are FACTS — deterministic, no hallucination

**Source B — LLM reasoning from company names + user description:**
- User said "CPA / CPL / RevShare, connects advertisers with affiliates"
- LLM generates keyword variations Apollo wouldn't have:
  "traffic monetization platform", "media buying network", "offer wall", etc.
- LLM understands the BUSINESS MODEL, Apollo just has tags

**Combined filter = Apollo facts + LLM intelligence = maximum coverage**

- **Keywords**: Apollo keywords from 9 companies UNION LLM-generated variations (150+)
- **Industry tag IDs**: from the 9 companies' actual Apollo data
- **Locations**: from user (or extracted from offer) — likely global
- **Employee ranges**: derived from the 9 companies' actual sizes

### Phase 4: Mandatory Questions (Checkpoint 1)
1. **Email accounts** — which SmartLead accounts to use?
2. **Geography** — confirm target locations

**Blacklist: NOT ASKED.** User said "add more to THIS campaign" — obviously don't re-contact
existing leads. Agent auto-imports blacklist from 3137079. Zero questions about it.

### Phase 5: Probe
- `pipeline_probe` with generated filters
- Tests keyword quality: which keywords find companies similar to the 9 examples?
- Returns target_rate, breakdown per keyword/industry
- The 9 example companies themselves should appear in probe results (validation)

### Phase 6: Cost Gate (Checkpoint 2)
- Show estimated credits, target_rate, keyword breakdown
- User approves

### Phase 7: Gather + Scrape
- `pipeline_gather_and_scrape` with approved filters
- **blacklist.json loaded automatically** — 3137079's domains excluded
- The 9 example domains included (they're valid targets too)
- Discover NEW affiliate networks beyond the 9 examples

### Phase 8: Classify
- Via negativa: exclude non-affiliate companies
- The 9 example companies = instant targets (already validated by user)
- New companies classified against the ICP

### Phase 9: People Extraction + Push
- `pipeline_people_to_push(mode="append", existing_campaign_id=3137079)`
- Deterministic dedup: fetch existing emails from 3137079, exclude before push
- Enrich all targets → extract contacts
- Append to campaign 3137079
- Export to Google Sheet (all contacts)

## Key Metrics to Verify

| Metric | Expected |
|--------|----------|
| Blacklist loaded | domains from campaign 3137079 excluded from gather |
| 9 example companies enriched | Apollo data extracted for filter seeding |
| Keywords generated | affiliate/CPA/performance marketing themed |
| Probe target rate | >50% (niche ICP, should be precise) |
| 9 examples in results | All 9 should appear as targets (if not blacklisted) |
| Push target | Campaign 3137079 (append, not new campaign) |
| Dedup | Existing 3137079 emails excluded before push |
| Blacklist vs dedup | Blacklist = domain-level (gather). Dedup = email-level (push) |

## What Can Go Wrong

| Risk | Mitigation |
|------|-----------|
| Agent treats 3137079 as Mode 3 target without blacklist | launch.md says: blacklist = import leads from campaign |
| Agent skips enrichment of 9 examples | Should use probe or direct enrichment |
| Apollo doesn't know these niche companies | Small affiliate networks may not be in Apollo |
| Agent creates new campaign instead of appending | Must use mode="append", existing_campaign_id=3137079 |
| 9 example companies already in 3137079 | Blacklist should catch them at domain level |
| Agent generates fintech keywords (context pollution from sally-fintech) | New project, clean context |
| pipeline_people_to_push needs sequence_steps | Pass placeholder — 3137079 already has sequence |

## How to Validate Results

After run completes, check:
1. `blacklist.json` exists in project dir with 3137079 domains
2. Run file has the 9 example domains in companies dict (as targets)
3. Keywords are affiliate/CPA themed (not fintech)
4. No blacklisted domains in contacts
5. Campaign 3137079 has MORE leads than before
6. Google Sheet has all contacts
7. Credits tracked correctly
