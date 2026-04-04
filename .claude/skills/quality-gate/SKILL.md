# Quality Gate Skill

Define checkpoints that must PASS before pipeline advances. Prevents wasting credits on bad data.

## When to Use

- After gathering phase (Checkpoint 1)
- After classification phase (Checkpoint 2)
- After people extraction (Checkpoint 3)
- When user asks "is this enough?" or "should I continue?"

## Checkpoint 1: Post-Gather

**Trigger**: After Apollo search + blacklist filtering

| Metric | Threshold | Action if Failed |
|--------|-----------|------------------|
| Total companies gathered | >= 20 | WARN: "Only {N} companies found. Consider broader filters." |
| Blacklist rejection rate | < 50% | WARN: "High blacklist rate ({N}%). Many duplicates from previous campaigns." |
| Apollo pages returned | >= 1 with results | FAIL: "No results from Apollo. Check filters." |

**Output**: PASS or WARN with details.

**On WARN**: Present to user with options:
1. Continue anyway (accept lower quality)
2. Adjust filters (broader keywords, different location)
3. Stop pipeline

## Checkpoint 2: Post-Classification

**Trigger**: After all companies scraped + classified

| Metric | Threshold | Action if Failed |
|--------|-----------|------------------|
| Targets found | >= 10 | WARN: "Only {N} targets. Need ~34 for 100 contacts." |
| Target rate | > 15% | WARN: "Low target rate ({N}%). Filters may be too broad." |
| Scrape success rate | > 60% | WARN: "Many scrape failures ({N}%). May need proxy." |
| High confidence (>0.7) | > 50% of targets | WARN: "Low confidence scores. Consider exploration." |

**Additional checks**:
- Segment distribution: Are targets spread across segments or concentrated?
- segments_sufficient: Need targets in at least 1 segment
- contacts_estimate: targets * contacts_per_company (default 3)
- suggest_exploration: true if targets exist but rate < 50%

**Output format**:
```json
{
  "gate": "PASS" | "WARN",
  "targets_found": 45,
  "target_rate": 0.36,
  "segment_distribution": {"PAYMENTS": 20, "LENDING": 15, "BAAS": 10},
  "contacts_estimate": 135,
  "targets_sufficient": true,
  "suggest_exploration": false,
  "warnings": ["Target rate below 50%, exploration may improve accuracy"]
}
```

**On WARN**: Present next steps:
1. Approve → proceed to people extraction
2. Explore → enrich top targets, optimize filters (5 credits)
3. Re-analyze → apply user feedback, re-classify
4. Provide feedback → "exclude operators" → improve prompt → re-classify

## Checkpoint 3: Post-People

**Trigger**: After contact extraction

| Metric | Threshold | Action if Failed |
|--------|-----------|------------------|
| Total contacts | >= target_count (default 100) | WARN if not met |
| Contacts per company | Average >= 2 | WARN: "Low contact yield. May need different roles." |
| Verified emails | > 80% of extracted | WARN: "Low email verification rate." |
| Role match | > 70% match target roles | WARN: "Many contacts don't match target roles." |

## Pipeline Constants (CRITICAL)

| Constant | Value | Description |
|----------|-------|-------------|
| DEFAULT_TARGET_COUNT | 100 | People to gather before stopping |
| DEFAULT_CONTACTS_PER_COMPANY | 3 | People extracted per target company |
| MAX_PAGES_PER_KEYWORD | 5 | Max Apollo pages per single keyword stream |
| MAX_KEYWORD_REGENERATIONS | 5 | Max keyword regen cycles before giving up |
| LOW_YIELD_THRESHOLD | 10 | If <10 companies on page 1, stop this keyword |
| MAX_TOTAL_CREDITS | 200 | Safety cap — pipeline stops if exceeded |
| EFFECTIVE_PER_PAGE | 60 | Apollo returns ~60 unique per 100 requested |
| COMPANIES_PER_ROUND | 400 | Stop adding Apollo requests when this many unique companies |

## KPI Targets (User Can Override)

| KPI | Default | Example Override |
|-----|---------|-----------------|
| target_people | 100 | "I need 50 targets" / "I want 1000 contacts" |
| contacts_per_company | 3 | "5 contacts per company" |
| target_rate_expected | 0.35 | Calculated from actual results |
| max_apollo_credits | 200 | Safety cap |

## Typical Results (Benchmarks)

| Segment | Targets | People | Time | Cost |
|---------|---------|--------|------|------|
| Fashion Italy | 102 | 131 | 59s | $0.17 |
| Video London | 81 | 134 | 55s | $0.19 |
| IT Miami | 18 | 39 | 27s | $0.04 |

## Cost Transparency at Every Gate

**ALWAYS show costs before and after:**
- Before: "Estimated: 102 credits ($1.02) for 100 contacts"
- After: "Spent: 45 credits ($0.45). Remaining: 157 credits."
- Continue: "Next 4 pages: 4 credits. Estimated: +105 contacts."

**Never spend credits without user confirmation.**

## Pipeline KPI Loop

The autonomous pipeline checks KPIs continuously:

```
ROUND 1: All keywords + industries in parallel
  → Stop adding requests when 400 unique companies reached
  → Scrape + classify as they arrive
  → People extraction for each target
  
CHECK: total_people >= target_count?
  YES → DONE (push to SmartLead)
  NO  → ROUND 2: next batch of keywords
  
REPEAT until:
  - KPI met (100 people) → SUCCESS
  - All keywords exhausted + 5 regeneration cycles → INSUFFICIENT
  - 200 credits cap hit → STOP with warning
```

## Exhaustion Detection

- 10 consecutive empty Apollo pages = keyword/industry exhausted
- When funded stream (Level 0) exhausts → drop funding filter, continue Level 1
- Geo/size filters NEVER dropped (always mandatory)
- After all initial keywords exhausted → regenerate keywords (up to 5 cycles)

## Keyword Regeneration Angles (10 total, when keywords exhaust)

Each cycle uses a DIFFERENT angle to discover untapped company pools:

1. **PRODUCT/PLATFORM** names — specific tools, software, platforms in the space
2. **TECHNOLOGY STACK** — protocols, standards, certifications (PCI DSS, ISO 20022, SWIFT)
3. **USE CASES** — what problems solved ("reduce fraud", "automate payroll")
4. **BUYER SEARCH LANGUAGE** — procurement, RFP, vendor selection terms
5. **ADJACENT NICHES** — sub-categories, crossover markets
6. **INDUSTRY JARGON** — insider terms, acronyms, regulations
7. **COMPETITOR/ALTERNATIVES** — comparison terms ("alternative to Deel")
8. **JOB POSTING keywords** — skills, team names, roles companies hire for
9. **INVESTOR/FUNDING keywords** — pitch terms, market maps, fund themes
10. **CONFERENCE/EVENT keywords** — industry events, associations, trade shows

Generate 10-15 new keywords per angle. All MUST be different from all previous keywords.

## Per-Keyword / Per-Industry Performance Tracking

Track aggregated stats for each keyword and industry_tag_id:

```json
{
  "keyword_stats": {
    "payment gateway": {
      "pages_fetched": 5,
      "raw_companies": 500,
      "new_unique": 312,
      "targets_found": 89,
      "target_rate": 0.28,
      "credits_used": 5,
      "funded": false
    }
  },
  "industry_stats": {
    "financial services": {
      "pages_fetched": 5,
      "raw_companies": 500,
      "new_unique": 287,
      "targets_found": 112,
      "target_rate": 0.39,
      "credits_used": 5,
      "funded": false
    }
  },
  "pipeline_summary": {
    "rounds_completed": 2,
    "total_credits": 45,
    "keywords_used": 15,
    "keywords_available": 25,
    "total_unique_companies": 892,
    "total_targets": 201,
    "overall_target_rate": 0.22,
    "total_people": 103,
    "kpi_met": true
  }
}
```

## "Find More" / "Continue" Handling

When user says "find more contacts":
1. Show current count
2. Calculate next batch cost
3. "Current: 102 contacts. Next 4 pages: 4 credits. Estimated: +105 contacts."
4. User confirms → continue with page_offset (don't re-fetch existing)
5. Don't re-search already gathered companies
