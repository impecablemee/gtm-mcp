# Pipeline State Skill

Defines the entity model, run file format, round loop algorithm, and cross-run intelligence protocol. This skill tells the agent HOW to structure and track every piece of data throughout the pipeline.

## When to Use

- During /leadgen command (create and maintain run file)
- During /qualify command (create iterations)
- After any pipeline run completes (update filter_intelligence.json)
- When "find more" resumes an existing run

## The Run File

Every pipeline execution produces ONE file: `runs/run-{id}.json`. This is the complete, self-contained record. All 6 entities live inside it.

```
~/.gtm-mcp/projects/{project}/
├── project.yaml
├── runs/
│   ├── run-001.json          ← Everything for this pipeline execution
│   ├── run-002.json          ← "Find more" or new segment
│   └── latest.json
├── feedback.json             ← User corrections (across runs)
├── sequences.json
└── campaigns.json
```

Create the run file with `save_data(project, "runs/run-{id}.json", data)` at pipeline start. Update it with `save_data(project, "runs/run-{id}.json", data, mode="merge")` as phases complete.

Generate run IDs as `run-{NNN}` where NNN is zero-padded sequential (run-001, run-002, ...).

## Entity 1: FilterSnapshot

Immutable record of exact filters at a point in time. NEVER modify — create a new snapshot when filters change.

```json
{
  "id": "fs-001",
  "created_at": "2026-04-04T10:15:00Z",
  "trigger": "initial_generation",
  "parent_id": null,
  "filters": {
    "keywords": ["employer of record", "EOR platform", "...85 total"],
    "industry_tag_ids": ["5567cd82a1e38c..."],
    "industry_names": ["human resources"],
    "locations": ["United States"],
    "employee_ranges": ["11,50", "51,200"],
    "funding_stages": ["series_a", "series_b"]
  },
  "generation_details": {
    "query": "EOR clients in the US",
    "strategy": "keywords_first",
    "keywords_from_seed": 8,
    "keywords_from_generation": 16,
    "keywords_from_expansion": 61,
    "total_keywords": 85,
    "industries_classification": {"human resources": "SPECIFIC"}
  }
}
```

**Create new snapshot when:**

| Trigger | parent_id | What Changed |
|---------|-----------|---|
| `initial_generation` | null | First filter set from query + offer |
| `exploration_improved` | previous | After enriching top 5 targets — new keywords/industries discovered |
| `keyword_regeneration_{N}` | previous | After round exhausted — fresh keywords from specific angle |
| `user_adjustment` | previous | User said "also add management consulting" |

## Entity 2: APIRequest

Every single Apollo API call. One keyword OR one industry_tag_id per request.

```json
{
  "id": "req-017",
  "filter_snapshot_id": "fs-001",
  "round_id": "round-001",
  "created_at": "2026-04-04T10:20:03Z",
  "type": "keyword",
  "filter_value": "employer of record",
  "funded": true,
  "page": 1,
  "result": {
    "raw_returned": 100,
    "new_unique": 72,
    "duplicates": 28,
    "credits_used": 1,
    "apollo_total_entries": 1933
  }
}
```

For industry requests, add `filter_tag_id` field with the hex tag ID.

Generate request IDs as `req-{NNN}` sequential within the run.

## Entity 3: Round

One gather-scrape-classify-people cycle.

```json
{
  "id": "round-001",
  "filter_snapshot_id": "fs-001",
  "started_at": "2026-04-04T10:20:00Z",
  "completed_at": "2026-04-04T10:28:00Z",
  "status": "completed",
  "gather_phase": {
    "started_at": "10:20:00",
    "completed_at": "10:24:00",
    "keywords_used": ["employer of record", "EOR platform", "...10 total"],
    "industries_used": ["human resources"],
    "funded_streams": true,
    "request_ids": ["req-001", "req-002", "..."],
    "total_api_calls": 24,
    "unique_companies_gathered": 387,
    "credits_used": 24,
    "stopped_reason": "reached_400_cap"
  },
  "scrape_phase": {
    "started_at": "10:20:05",
    "completed_at": "10:25:00",
    "total": 375,
    "success": 334,
    "failed": 29,
    "timeout": 12,
    "success_rate": 0.89
  },
  "classify_phase": {
    "started_at": "10:20:30",
    "completed_at": "10:27:00",
    "total_classified": 334,
    "targets": 89,
    "rejected": 245,
    "target_rate": 0.27,
    "segment_distribution": {"EOR_CLIENTS": 62, "CONTRACTOR_PAYROLL": 27},
    "avg_confidence": 78,
    "iteration": 1
  },
  "people_phase": {
    "started_at": "10:27:00",
    "completed_at": "10:28:00",
    "targets_processed": 34,
    "contacts_extracted": 98,
    "contacts_verified": 91,
    "credits_used": 91,
    "avg_per_company": 2.68
  },
  "kpi_check": {
    "target_people": 100,
    "current_people": 91,
    "kpi_met": false,
    "decision": "continue_to_round_2",
    "people_needed": 9
  }
}
```

**Phases overlap (streaming):** Scrape starts the MOMENT first company arrives from Apollo. Classify starts when first scrape finishes. People starts when first target confirmed. All run concurrently. Round completes when ALL phases finish and KPI is checked.

## Entity 4: Company

Keyed by domain. References request IDs that found it.

```json
{
  "domain": "fastgrowthstartup.com",
  "name": "FastGrowth",
  "apollo_id": "abc123",
  "discovery": {
    "first_seen_at": "2026-04-04T10:20:05Z",
    "found_by_requests": ["req-003", "req-017"],
    "found_in_round": "round-001",
    "funded_stream": true,
    "apollo_data": {
      "industry": "computer software",
      "industry_tag_id": "5567cd82a1e4f...",
      "employee_count": 150,
      "country": "United States",
      "city": "Austin",
      "founded_year": 2020,
      "keywords": ["saas", "hr tech", "remote work"],
      "linkedin_url": "https://linkedin.com/company/fastgrowth"
    }
  },
  "timeline": {
    "gathered_at": "2026-04-04T10:20:05Z",
    "scraped_at": "2026-04-04T10:20:42Z",
    "classified_at": "2026-04-04T10:21:01Z",
    "people_extracted_at": "2026-04-04T10:23:15Z"
  },
  "scrape": {
    "status": "success",
    "http_status": 200,
    "text_length": 4823,
    "text": "FastGrowth is a Series B startup..."
  },
  "classification": {
    "is_target": true,
    "confidence": 88,
    "segment": "EOR_CLIENTS",
    "reasoning": "Series B startup, 150 employees across 12 countries. Uses Deel. Would benefit from switching.",
    "classified_from": "scraped_text",
    "iteration": 1
  },
  "people_extraction": {
    "target_roles": ["VP HR", "CHRO", "Head of People"],
    "rounds": [
      {"round": 1, "enriched": ["VP Sales", "CRO", "CEO"], "verified": ["VP Sales"], "credits": 3},
      {"round": 2, "enriched": ["Head of Growth", "CMO"], "verified": ["Head of Growth", "CMO"], "credits": 2}
    ],
    "total_verified": 3,
    "total_credits": 5
  },
  "blacklisted": false
}
```

**Provenance chain**: company.found_by_requests → requests[id] → request.filter_snapshot_id → filter_snapshots[id].filters

**Dedup rule**: If same domain found by multiple requests, add ALL request IDs to `found_by_requests`. Don't create duplicate company entries.

## Entity 5: Contact

```json
{
  "email": "john.smith@fastgrowthstartup.com",
  "email_verified": true,
  "name": "John Smith",
  "title": "VP of People Operations",
  "seniority": "vp",
  "linkedin_url": "https://linkedin.com/in/johnsmith",
  "company_domain": "fastgrowthstartup.com",
  "company_name_normalized": "FastGrowth",
  "segment": "EOR_CLIENTS",
  "extraction": {
    "round_id": "round-001",
    "enrichment_round": 1,
    "credits_used": 1,
    "extracted_at": "2026-04-04T10:27:15Z",
    "role_match": "primary"
  }
}
```

## Entity 6: Iteration

Classification pass. New iteration created on user feedback.

```json
{
  "id": "iter-001",
  "created_at": "2026-04-04T10:25:00Z",
  "trigger": "initial_classification",
  "filter_snapshot_id": "fs-001",
  "parent_iteration": null,
  "feedback_applied": [],
  "results": {
    "total_classified": 334,
    "targets": 89,
    "target_rate": 0.27,
    "segment_distribution": {"EOR_CLIENTS": 62, "CONTRACTOR_PAYROLL": 27}
  }
}
```

After feedback:
```json
{
  "id": "iter-002",
  "trigger": "user_feedback",
  "parent_iteration": "iter-001",
  "feedback_applied": ["Exclude EOR providers (competitors). Only target companies that USE EOR services."],
  "results": {
    "total_classified": 334,
    "targets": 71,
    "target_rate": 0.21,
    "flipped_target_to_rejected": 22,
    "flipped_rejected_to_target": 4
  }
}
```

## Complete Run File Structure

```json
{
  "run_id": "run-001",
  "project": "easystaff-payroll",
  "created_at": "...",
  "status": "running | completed | insufficient | failed",
  "completed_at": "...",

  "kpi": {
    "target_people": 100,
    "max_people_per_company": 3,
    "max_credits": 200
  },

  "probe": {
    "filter_snapshot_id": "fs-001",
    "probe_requests": ["req-probe-001", "req-probe-002"],
    "companies_from_probe": 253,
    "companies_deduped": 201,
    "credits_used": 6,
    "reused_on_confirm": true
  },

  "filter_snapshots": [],
  "rounds": [],
  "requests": [],
  "companies": {},
  "contacts": [],
  "iterations": [],

  "funding_cascade": {
    "level_0_funded": {"requests": 0, "unique_companies": 0, "exhausted_at": null},
    "level_1_unfunded": {"requests": 0, "unique_companies": 0, "exhausted_at": null}
  },

  "taxonomy_extensions": [],

  "keyword_leaderboard": [],
  "industry_leaderboard": [],

  "totals": {
    "rounds_completed": 0,
    "total_api_requests": 0,
    "total_credits_search": 0,
    "total_credits_people": 0,
    "total_credits": 0,
    "total_usd": 0,
    "unique_companies": 0,
    "companies_scraped": 0,
    "companies_classified": 0,
    "targets": 0,
    "contacts_extracted": 0,
    "kpi_met": false,
    "duration_seconds": 0
  },

  "campaign": null
}
```

## The Round Loop Algorithm

```
1. CREATE FilterSnapshot fs-001 (initial generation)
2. PROBE: 1 request per top-3 keywords + top-3 industries (6 credits max)
   → Save probe companies, show preview to user
   → WAIT for user confirmation

3. On confirm → CREATE Round round-001:
   a. GATHER (streaming):
      - 1 keyword per Apollo request, all in parallel
      - 1 industry_tag_id per Apollo request, all in parallel
      - If funding: funded AND unfunded variants of ALL above simultaneously
      - Each company → check global dedup (seen_domains set)
      - STOP adding new requests when 400 unique companies reached
      - Probe companies flow in first (skip page 1 for probed filters)
      - Track: each company gets found_by_requests[], found_in_round

   b. SCRAPE (streaming, starts as companies arrive):
      - 100 concurrent website scrapes
      - Each company → scrape result → flows to classify

   c. CLASSIFY (streaming, starts as scrapes arrive):
      - 100 concurrent classifications
      - Via negativa rules from company-qualification skill
      - Each company → is_target, confidence, segment, reasoning
      - classified_from: always "scraped_text" (NEVER Apollo industry)

   d. PEOPLE (streaming, starts as targets confirmed):
      - 20 concurrent people extractions
      - For each target: search (FREE) → enrich (1 credit/person)
      - Retry: if <3 verified, try next candidates matching target_roles
      - Max 3 retry rounds, max 12 credits per company
      - Seniority priority: owner > founder > c_suite > vp > head > director
      - Side effect: bulk_match may return new industry_tag_ids → save to taxonomy_extensions

   e. KPI CHECK (after all phases complete):
      - current_people >= target_people?
      - YES → DONE, proceed to campaign push
      - NO → decision: continue_to_round_2

4. If KPI not met:
   - Are there unused keywords? → use next batch in Round 2 (same filter snapshot)
   - All keywords exhausted? → REGENERATE keywords:
     - CREATE FilterSnapshot fs-002 (keyword_regeneration_1, parent: fs-001)
     - Angle: pick next from 10 angles (see quality-gate skill)
     - Informed by: which target companies were found (their Apollo keywords)
     - Excluded: ALL keywords from parent snapshot (never repeat)
   - CREATE Round round-002 with new/remaining keywords → go to step 3

5. REPEAT until:
   - KPI met → push to SmartLead (DRAFT)
   - All keywords exhausted + 5 regeneration cycles → status: "insufficient"
   - 200 credits cap hit → status: "insufficient", warn user
```

## Exhaustion Detection

Per keyword/industry stream:
- 10 consecutive empty pages = exhausted
- LOW_YIELD_THRESHOLD: page 1 returns <10 companies = stop immediately
- MAX_PAGES_PER_KEYWORD: 5 pages max per stream

Funding cascade:
- Level 0 (funded): all keyword+industry requests WITH funding → exhausted when 10 empty
- Level 1 (unfunded): same requests WITHOUT funding → often sparse pagination (0 results)
- Level 2+: keyword regeneration cycles

Geo and size filters are NEVER dropped. Funding is dropped when exhausted.

## Leaderboard Computation

After each round completes, compute per-keyword and per-industry stats:

```
For each keyword K:
  requests_for_K = requests.filter(r => r.type == "keyword" && r.filter_value == K)
  all_companies_for_K = companies.filter(c => c.found_by_requests intersects requests_for_K.ids)
  targets_for_K = all_companies_for_K.filter(c => c.classification.is_target)
  
  keyword_leaderboard.push({
    keyword: K,
    requests: requests_for_K.length,
    unique_companies: all_companies_for_K.length,
    targets: targets_for_K.length,
    target_rate: targets_for_K.length / all_companies_for_K.length,
    credits: sum(requests_for_K.result.credits_used),
    funded: requests_for_K[0].funded,
    quality_score: target_rate * log(unique_companies + 1) / credits
  })
```

Sort by `quality_score` DESC. Same for industries.

## Post-Run: Update Filter Intelligence

After run completes, update `~/.gtm-mcp/filter_intelligence.json`:

```
1. Read run file → keyword_leaderboard, industry_leaderboard
2. For each keyword:
   - Exists in keyword_knowledge? → update: avg_target_rate, increment times_used, update best_target_rate
   - New? → create entry with this run's stats
3. Same for industries
4. Update segment_playbooks:
   - Match run's segment to existing playbook (or create new)
   - Update: best_keywords (top 5 by quality_score), avg_target_rate, avg_cost
5. Update funding_knowledge based on funded vs unfunded comparison
6. Save with save_data("_global", "filter_intelligence.json", data, mode="merge")
```

## Consuming Intelligence (New Run)

When generating filters for a new run:

```
1. Read filter_intelligence.json
2. Find closest segment_playbook to current segment
3. best_keywords from playbook → HIGH-PRIORITY seeds for keyword generation
4. funding_essential → always include funding filter
5. industry classification → pick industry_first or keywords_first strategy
6. Show user: "Based on N previous runs, expect ~X% target rate, ~$Y cost"
```

Intelligence is ADVISORY. The agent uses it as seeds and hints, not as hard constraints. New keywords are still generated — intelligence just makes the starting point much better.
