# /leadgen — Full Lead Generation Pipeline

Run the complete pipeline: offer extraction → filter generation → Apollo search → scrape → classify → people → SmartLead campaign.

**Required skills**: offer-extraction, apollo-filter-mapping, company-qualification, quality-gate, email-sequence, **pipeline-state**

The pipeline-state skill defines the entity model and round loop. Every company, request, and filter must be tracked in the run file per that skill's schema. Every target company must trace back to which keyword/industry found it, which filter snapshot was active, and which round it was gathered in.

## Prerequisites
- API keys configured: Apollo, SmartLead, OpenAI (for user's LLM), Apify (optional, for proxy)
- Call `get_config` to verify keys are set. If missing, tell user to configure first.

## Arguments
- `--resume`: Skip completed steps, resume from last checkpoint
- `--dry-run`: Preview only, don't spend credits
- `--segment <name>`: Run for specific segment only
- `--location <geo>`: Override location
- `--size <range>`: Override employee size range
- `--target-count <N>`: Override default 100 contacts target
- `--contacts-per-company <N>`: Override default 3

## The 7-Step Pipeline

### Step 1: Offer Extraction
**Skill**: offer-extraction

If user provided a website URL:
1. Call `scrape_website` with the URL
2. Analyze scraped text → extract structured offer (use offer-extraction skill)
3. Call `create_project` with extracted data
4. Call `save_data` to persist project

If user provided a strategy document:
1. Read file from disk
2. Analyze document → extract offer (use offer-extraction skill)
3. Call `create_project` with extracted data

If user just described their offer in chat:
1. Extract offer from conversation context
2. Call `create_project`

**Present to user**: Extracted offer summary. Ask: "Does this look right?"
- If feedback → re-extract with feedback, loop
- If approved → proceed

### Step 2: Apollo Filter Mapping
**Skill**: apollo-filter-mapping

1. Generate filters from offer segments + user query
2. Classify industries (SPECIFIC vs BROAD)
3. Generate 20-30 keywords per segment
4. Extract locations
5. Infer employee size
6. Apply seed data merges
7. Apply document overrides (locations, funding, size)

**Present to user**: Filter preview with:
- Keywords (all 20-30)
- Industries selected (with tag_ids)
- Location
- Size ranges
- Funding filter (if from document)
- Probe results per keyword/industry
- Cost estimate: "Default (100 contacts): ~102 credits ($1.02)"

Ask: "Proceed?" ONE question only.

If user wants changes: "also add management consulting and make size 51-500" → regenerate with adjustments, show updated preview.

### Step 3: Cost Gate
**Skill**: quality-gate

Before spending ANY credits:
1. Show total estimated cost (search credits + people credits)
2. Show Apollo credit balance (call `apollo_estimate_cost`)
3. Wait for explicit "yes" / "proceed" / "go ahead"

**NEVER auto-proceed. NEVER spend credits without confirmation.**

### Step 4: Apollo Search (Autonomous — Round Loop)

**Follow the round loop algorithm from pipeline-state skill exactly.**

Before first gather:
1. Create run file: `save_data(project, "runs/run-{id}.json", initial_state)`
2. Create FilterSnapshot fs-001 from generated filters
3. Probe companies flow in first (reuse from preview, skip page 1)

For each round:
1. GATHER: `apollo_search_companies` — 1 keyword per request, all in parallel. 1 industry per request, all in parallel. If funding: funded AND unfunded variants simultaneously. STOP at 400 unique companies.
2. SCRAPE: starts streaming as companies arrive (100 concurrent)
3. CLASSIFY: starts streaming as scrapes complete (via negativa rules)
4. PEOPLE: starts as targets confirmed (20 concurrent, retry logic)
5. KPI CHECK: current_people >= target? YES → done. NO → next round.

**For every company**: record `found_by_requests` (array of request IDs that found it), `found_in_round`, `funded_stream`. This is how you trace back which filters produced each target.

**For every request**: record `filter_snapshot_id`, `round_id`, `type`, `filter_value`, `funded`, `page`, result counts.

After each round: compute keyword_leaderboard and industry_leaderboard. Save to run file.

If KPI not met and keywords exhausted: create new FilterSnapshot (keyword_regeneration), informed by found targets' Apollo keywords. Never repeat keywords from parent snapshot.

### Step 5: Blacklist + Pre-filter

1. Call `blacklist_check` for each gathered domain
2. Remove: trash domains (social media, payment platforms, wikis)
3. Remove: previous campaign contacts (if user imported)
4. Remove: invalid domains (length < 4 chars)

**Trash domains list**: ya.ru, yandex.ru, google.com, youtube.com, wikipedia.org, facebook.com, instagram.com, linkedin.com, twitter.com, x.com, reddit.com, pinterest.com, tiktok.com, vk.com, ok.ru, mail.ru, t.me, binance, bybit, coinmarketcap, coingecko, coinbase, tradingview, booking, agoda, tripadvisor, airbnb, wise, revolut, stripe, paypal

### Step 6: Company Qualification
**Skill**: company-qualification

1. Call `scrape_website` for each company (100 concurrent)
2. Classify each using via negativa rules (use company-qualification skill)
3. Run quality gate checkpoint 2 (use quality-gate skill)
4. Present results:
   - Targets found
   - Target rate
   - Segment distribution
   - Next steps: approve / explore / re-analyze / feedback

If user provides feedback → incorporate and re-classify (new iteration)
If user approves → proceed to people extraction

### Step 7: People Extraction + Campaign Push

**People search is 2-step:**
- Step A: `apollo_search_people` (FREE, no credits) → returns candidate list (25 per company)
- Step B: `apollo_enrich_person` via bulk_match (1 credit per person) → returns verified email

**Priority order for candidates**: owner/founder > c_suite > vp > head > director

**Retry logic** (CRITICAL for contact quality):
1. Top 3 candidates matching target_roles → bulk_match → keep verified
2. If <3 verified → retry with NEXT candidates matching target_roles
3. Priority: exact role match > same seniority > lower seniority with role match
4. NEVER enrich someone with no role relevance (no random directors)
5. Max 3 retry rounds (max 12 credits per company worst case)

Example (fintech doc target roles: VP Sales, CRO, Head of Growth, CMO, CEO):
```
Round 1: VP Sales ✓, CRO ✗ (no email), CEO ✗ → 1 verified
Round 2: Head of Growth, CMO, Co-founder → bulk_match → 2 verified
Total: 3 verified contacts ✓
```

**Side effect**: bulk_match returns org data including `industry_tag_id` → auto-extends taxonomy

**Process** (20 concurrent):
1. For each target company: search + enrich with retry logic
2. KPI check after EACH person: total_people >= target_count?
   - YES → STOP immediately (don't waste credits)
   - NO → continue
3. Generate email sequence (use email-sequence skill)
4. Present sequence to user for approval
5. Push to SmartLead as DRAFT:
   - Create campaign
   - Upload contacts with: normalized company name + segment as custom fields
   - Set sequence + settings (plain text, no tracking, stop on reply)
   - Send test email to user's email
6. Present ALL 4 items:
   1. SmartLead campaign link
   2. CRM contacts link filtered by campaign
   3. "Check your inbox at {email}"
   4. "Type 'activate' to launch"

## Conversation Rules

- ONE question at a time (never ask 2 things in one message)
- Show costs BEFORE every credit-spending step
- Show links after every state change (pipeline link, CRM link, campaign link)
- No token → respond ONLY with signup link
- Keys not configured → list WHICH keys missing
- User hasn't mentioned offer → ask for website FIRST

## Edge Cases (MUST Handle)

### Multi-segment in one message
User: "gather IT consulting Miami and video production London"
→ Ask: "Separate pipelines or one?" before proceeding

### User changes filters after preview
User sees preview, says "also add management consulting and make size 51-500"
→ Re-generate filters with adjustments, show NEW preview. Don't auto-run.

### User changes roles mid-pipeline
User: "I want VP Marketing and CMO, not technical roles"
→ Update people_filters. "Updated roles. Will apply to next people search."
→ If contacts already gathered: "Re-gather contacts with new roles?"
→ People search is FREE — no credit warning needed.

### User changes contacts per company
User: "5 contacts per company"
→ Update. Show: "34 targets × 5 = 170 contacts. People search is FREE."

### User provides strategy doc
User: "use this file: cases/IGAMING_PROVIDERS_BRIEF.md"
→ Claude Code reads file from disk. Extract offer via offer-extraction skill. Pass to MCP tools.

### User provides sequence from file
User: "use the approach from tasks/easystaff/sequence.md for emails"
→ Read file, extract approach, store as project context for sequence generation.

### User asks about credits
User: "how many Apollo credits have I spent?"
→ Show credits per run + total across all runs.

### User has multiple projects, doesn't specify
User: "gather fashion brands in Italy" (without selecting project)
→ Ask: "Which project?" (list projects with names)

### Classification accuracy too low
User sees 48% target rate → "exclude operators, they're not tech providers"
→ Store feedback → re-classify → new iteration → show improvement.

### User sets high target count
User: "I want 1000 contacts"
→ Calculate: 1000/3 = 334 companies, at 35% = 954 from Apollo, ~16 pages
→ Show cost: "~116 credits ($1.16) + enrichment. Continue?"

### No token
→ Respond ONLY with signup/setup instructions. Nothing else.

### Keys not configured
→ List WHICH keys missing. Don't proceed until all set.

### User hasn't mentioned offer
→ Ask for website FIRST. Before anything else.

## "Find More" After Pipeline

If user says "find more contacts" or "continue":
1. Show current count
2. Calculate incremental cost
3. "Current: 102 contacts. Next 4 pages: 4 credits (~$0.04). Continue?"
4. On confirm → resume from last offset (don't re-fetch)
