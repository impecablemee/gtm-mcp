# Leadgen Pipeline Manager

Orchestrate the /leadgen pipeline as a 7-phase sequence with **exactly 2 human checkpoints** and full autonomous execution between them.

**Read these skills as referenced by each phase**: offer-extraction, apollo-filter-mapping, company-qualification, quality-gate, email-sequence, pipeline-state, io-state-safe, resume-checkpoint

## Two Checkpoints — Nothing Else Blocks

```
CHECKPOINT 1 (Phase 3): Strategy Approval — before spending Apollo credits
CHECKPOINT 2 (Phase 7): Launch Approval — before campaign goes live
```

Everything else is AUTONOMOUS. No "Does this look right?", no "Approve targets?", no "Approve sequence?".

---

## Session Setup

### 1. Detect mode

```
If campaign=<id_or_slug> in args → MODE 3 (append)
If project=<slug> in args        → MODE 2 (new campaign)
Else                              → MODE 1 (fresh)
```

### 2. Resolve project

**Mode 1**: Derive slug from input (website domain, or slugify project name).
```
create_project(name)
```

**Mode 2**: Load existing project.
```
result = load_data(project_slug, "project.yaml")
→ Verify result.data.offer_approved == true
→ Check project.campaigns[] — if segment already exists, error:
  "Segment X already has campaign Y. Use /launch campaign=Y to append."
```

**Mode 3**: Look up campaign across all projects.
```
result = find_campaign(campaign_ref)
→ project_slug = result.data.project
→ campaign_data = result.data.data
→ campaign_id = campaign_data.campaign_id

validation = smartlead_get_campaign(campaign_id)
→ If validation.data.status == "STOPPED" → error: "Campaign is stopped."
```

### 3. Initialize state

```
state = {
  session_id: "leadgen-{project_slug}-{YYYYMMDD}-{HHMMSS}",
  project: project_slug,
  pipeline: "leadgen",
  mode: "fresh" | "new_campaign" | "append",
  status: "running",
  current_phase: "offer_extraction",
  active_campaign_slug: null,  # Mode 3: from campaign_data.slug
  active_campaign_id: null,    # Mode 3: from campaign_data.campaign_id
  active_run_id: "run-001",
  phase_states: {
    offer_extraction: "pending",      # Mode 2/3: "skipped"
    filter_generation: "pending",
    cost_gate: "pending",
    round_loop: "pending",
    people_extraction: "pending",
    sequence_generation: "pending",   # Mode 3: "skipped"
    campaign_push: "pending"
  },
  started_at: "{now}",
  last_updated: "{now}",
  error: null,
  completed_at: null
}

existing = load_data(project_slug, "state.yaml")
if existing.success:
  → Read resume-checkpoint skill and follow its algorithm
  → May skip to a later phase
else:
  save_data(project_slug, "state.yaml", state)
```

---

## Phase 1: Offer Extraction (AUTONOMOUS)

**Human gate**: NONE
**Skip if**: Mode 2 or 3 (offer already approved)

### Update state
```
save_data(project, "state.yaml", {
  ...state, current_phase: "offer_extraction",
  phase_states: {..., offer_extraction: "in_progress"}
})
```

### Execute

Read the **offer-extraction** skill. It defines the extraction schema and rules.

**If input is URL**:
```
scraped = scrape_website(url)
```
Then analyze `scraped.data.text` using the offer-extraction skill's schema to produce `offer_summary` JSON.

**If input is file path**: Read the file from disk, then extract using the same schema.

**If input is text**: Extract directly from the user's description.

Apply the extraction rules from the skill: segments with CAPS_SNAKE_CASE names, 8-10 keywords per segment, target roles by offer type, employee size inference.

```
save_data(project, "project.yaml", {
  name: project_name,
  slug: project_slug,
  offer: extracted_offer_summary,
  offer_approved: false,   # becomes true at Checkpoint 1
  campaigns: []
}, mode="merge")
```

### Update state
```
save_data(project, "state.yaml", {
  ...state, phase_states: {..., offer_extraction: "completed"}
})
```

**Mode 2/3**: Skip. Load `project.yaml`, verify `offer_approved == true`.

---

## Phase 2: Filter Generation (AUTONOMOUS)

**Human gate**: NONE
**Runs in all modes** (but with different intelligence in Mode 3)

### Update state
```
save_data(project, "state.yaml", {
  ...state, current_phase: "filter_generation",
  phase_states: {..., filter_generation: "in_progress"}
})
```

### Execute

Read the **apollo-filter-mapping** skill.

**Step 1**: Get Apollo taxonomy.
```
taxonomy = apollo_get_taxonomy()
→ 84 industries with hex tag_ids
```

**Step 2**: Generate filters from offer + taxonomy.

Using the offer's segments, target_roles, and the apollo-filter-mapping skill's rules:
- Pick 2-3 industry tag_ids (SPECIFIC > BROAD)
- Generate 20-30 keywords per segment (product names, not generic terms)
- Map locations to Apollo format
- Map employee sizes to Apollo ranges

**Step 3** (Mode 3 only): Load keyword intelligence from previous runs.
```
for run_id in campaign_data.run_ids:
  prev_run = load_data(project, f"runs/{run_id}.json")
  → Extract keyword_leaderboard → use top performers as seeds
  → Exclude exhausted keywords
```

**Step 4**: Create FilterSnapshot and run probe (6 credits max).

```
# Probe top 3 industries (1 request each)
for tag_id in industry_tag_ids[:3]:
  apollo_search_companies(filters={
    organization_industry_tag_ids: [tag_id],
    organization_locations: locations,
    organization_num_employees_ranges: employee_ranges
  })

# Probe top 3 keywords (1 request each)  
for keyword in keywords[:3]:
  apollo_search_companies(filters={
    q_organization_keyword_tags: [keyword],
    organization_locations: locations,
    organization_num_employees_ranges: employee_ranges
  })
```

Collect probe results: companies per filter, total_available, unique companies.

**Step 5**: Create run file with probe data.
```
save_data(project, "runs/run-001.json", {
  run_id: "run-001",
  project: project_slug,
  campaign_id: campaign_id or null,
  campaign_slug: campaign_slug or null,
  mode: "fresh" | "append",
  status: "running",
  created_at: "{now}",
  kpi: {target_people: kpi, max_people_per_company: 3, max_credits: max_cost},
  probe: {breakdown: [...], companies_from_probe: N, credits_used: 6},
  filter_snapshots: [fs_001],
  rounds: [], requests: [], companies: {}, contacts: [], iterations: [],
  totals: {rounds_completed:0, total_credits:6, ...}
})
```

**Step 6**: Estimate cost.
```
cost = apollo_estimate_cost(target_count=kpi, contacts_per_company=3)
```

### Update state
```
save_data(project, "state.yaml", {
  ...state, active_run_id: "run-001",
  phase_states: {..., filter_generation: "completed"}
})
```

---

## Phase 3: Cost Gate — CHECKPOINT 1 (Strategy Approval)

**Human gate**: **YES — the ONLY pre-gathering approval**

### Update state
```
save_data(project, "state.yaml", {
  ...state, current_phase: "cost_gate",
  phase_states: {..., cost_gate: "in_progress"}
})
```

### Execute

Also resolve email accounts and blacklist here (before presenting the document):

```
accounts = smartlead_list_accounts()
→ If user provided account hint, filter by name/email substring
→ If not, show available accounts and ask which to use
```

```
# Blacklist
Mode 1: Ask user for blacklist sources (SmartLead campaigns, Google Sheets, or "skip")
Mode 2: Auto-import from all existing project campaigns:
  for campaign in project.campaigns:
    existing = smartlead_export_leads(campaign.campaign_id)
    blacklist_add(existing.data.domains)
Mode 3: Auto-dedup (handled in Phase 4 via Cross-Run Dedup Protocol)
```

Save approval document:
```
save_data(project, "pipeline-config.yaml", {
  project: project_name,
  mode: mode,
  filters: {segments, geo, keywords, industries, size, funding},
  probe: {breakdown, total_available, credits_used},
  cost_estimate: cost.data,
  kpi: {target: kpi, per_company: 3, max_cost: max_cost},
  email_accounts: selected_accounts,
  sequence: "GOD_SEQUENCE" or "from_document",
  blacklist: {domains_count: N},
  status: "awaiting_approval"
})
```

### Present to user (ALL in one view):

```
Strategy Document:

  OFFER:
    Product: {primary_offer}
    Segments: {segments}
    Target Roles: {primary_roles}
    Exclusions: {exclusion_list}

  FILTERS:
    Keywords: {N} generated
    Industries: {names} ({N} tag_ids)
    Geo: {locations}
    Size: {employee_range}

  PROBE (6 credits):
    {keyword_1}: {total} companies
    {keyword_2}: {total} companies
    {keyword_3}: {total} companies
    {industry_1}: {total} companies
    {industry_2}: {total} companies
    → {unique} unique from probe

  COST:
    Estimated: ~{total} credits (${usd})
    Max cap: {max_cost} credits (default 200)

  KPI: {target} contacts, 3/company
  Email Accounts: {N} selected
  Sequence: GOD_SEQUENCE (4-5 steps)
  Blacklist: {N} domains

  Proceed?
```

### Wait for user

- "proceed" → set `offer_approved: true` on project.yaml, continue
- Feedback → re-extract offer / regenerate filters / adjust, re-present

### Update state
```
save_data(project, "project.yaml", {...project, offer_approved: true}, mode="merge")
save_data(project, "state.yaml", {
  ...state, phase_states: {..., cost_gate: "completed"}, status: "running"
})
```

---

## Phase 4: Round Loop (AUTONOMOUS)

**Human gate**: NONE — fully autonomous

### Update state
```
save_data(project, "state.yaml", {
  ...state, current_phase: "round_loop",
  phase_states: {..., round_loop: "in_progress"}
})
```

### Mode 3 dedup setup
```
seen_domains = set()
seen_emails = set()

for run_id in campaign_data.run_ids:
  prev_run = load_data(project, f"runs/{run_id}.json")
  seen_domains.update(prev_run.data.companies.keys())

existing_leads = smartlead_export_leads(campaign_id)
seen_emails = {lead.email for lead in existing_leads.data.leads}
seen_domains.update(existing_leads.data.domains)
```

### Execute round loop

Read the **pipeline-state** skill for the full round loop algorithm. Read the **company-qualification** skill for classification rules.

**For each keyword** (1 per request, all in parallel):
```
apollo_search_companies(filters={
  q_organization_keyword_tags: [keyword],
  organization_locations: [...],
  organization_num_employees_ranges: [...]
})
```

**For each industry tag_id** (1 per request, all in parallel):
```
apollo_search_companies(filters={
  organization_industry_tag_ids: [tag_id],
  ...same location/size filters
})
```

Dedup results by domain. Skip domains in `seen_domains`. Stop at 400 unique companies.

**For each company** (parallel, batches of 10-20):
```
scraped = scrape_website(company.domain)
```

**Classify each scraped company** using company-qualification skill rules (via negativa — Claude does this inline, no tool call). Produce `is_target`, `confidence`, `segment`, `reasoning`.

Update run file after each batch:
```
save_data(project, "runs/run-001.json", updated_run, mode="merge")
```

**If target_rate low** → read quality-gate skill, autonomously regenerate keywords with next angle, run another round. Max 5 regeneration cycles.

### Update state
```
save_data(project, "state.yaml", {
  ...state, phase_states: {..., round_loop: "completed"}
})
```

---

## Phase 5: People Extraction (AUTONOMOUS)

**Human gate**: NONE

### Update state
```
save_data(project, "state.yaml", {
  ...state, current_phase: "people_extraction",
  phase_states: {..., people_extraction: "in_progress"}
})
```

### Execute

For each target company (parallel, batches of 5-10):

**Step 1 (FREE)**:
```
people = apollo_search_people(
  domain=company.domain,
  person_seniorities=["c_suite", "vp", "head", "director"]
)
```

**Step 2 (1 credit per person)**:
```
enriched = apollo_enrich_people(person_ids=[...top matches])
→ Extract verified emails
→ If <3 verified, retry with next candidates (max 3 rounds, 12 credits/company)
```

Build contact objects: email, name, title, seniority, company_domain, company_name_normalized, segment.

**Mode 3**: Skip contacts where email is in `seen_emails`.

**KPI check after each batch**: Stop immediately when `total_verified_contacts >= kpi.target_people`.

Save contacts to run file and project:
```
save_data(project, "runs/run-001.json", {contacts: all_contacts, ...}, mode="merge")
save_data(project, "contacts.json", all_contacts, mode="write")
```

### Update state
```
save_data(project, "state.yaml", {
  ...state, phase_states: {..., people_extraction: "completed"}
})
```

---

## Phase 6: Sequence Generation (AUTONOMOUS)

**Human gate**: NONE — GOD_SEQUENCE applied automatically
**Skip if**: Mode 3 (sequence already on campaign)

### Update state
```
save_data(project, "state.yaml", {
  ...state, current_phase: "sequence_generation",
  phase_states: {..., sequence_generation: "in_progress"}
})
```

### Execute

Read the **email-sequence** skill. It defines the 12-rule GOD_SEQUENCE checklist.

If the user's input document contained sequences → use those (already extracted in Phase 1).

Otherwise, generate 4-5 step sequence following the 12 rules:
- Personalization in every email ({{first_name}}, {{company_name}}, {{city}})
- A/B subjects on Email 1
- ≤120 words per email
- Reply-thread subjects (Emails 2+ have empty subjects)
- `<br>` for line breaks
- SmartLead variables only

```
save_data(project, "sequences.json", {steps: generated_steps})
```

### Update state
```
save_data(project, "state.yaml", {
  ...state, phase_states: {..., sequence_generation: "completed"}
})
```

---

## Phase 7: Campaign Push + Launch Approval — CHECKPOINT 2

**Human gate**: **YES — the ONLY pre-launch approval**

### Update state
```
save_data(project, "state.yaml", {
  ...state, current_phase: "campaign_push",
  phase_states: {..., campaign_push: "in_progress"}
})
```

### Step A: Build campaign (autonomous)

**Mode 1 and 2** — create new campaign:
```
campaign = smartlead_create_campaign(
  project=project_slug,
  name="{Segment} — {Geo}",
  sending_account_ids=selected_account_ids,
  country=geo_country_code,
  segment=segment_name
)
campaign_id = campaign.data.campaign_id
campaign_slug = campaign.data.slug

smartlead_set_sequence(
  project=project_slug,
  campaign_slug=campaign_slug,
  campaign_id=campaign_id,
  steps=sequence_steps
)
```

**Mode 3** — skip creation, campaign already exists.

### Step B: Upload contacts
```
leads = [{
  email: contact.email,
  first_name: contact.name.split(" ")[0],
  last_name: contact.name.split(" ")[1],
  company_name: contact.company_name_normalized,
  custom_fields: {segment: contact.segment, city: contact.city}
} for contact in verified_contacts]

smartlead_add_leads(campaign_id=campaign_id, leads=leads)
```

### Step C: Update tracking
```
# Update campaign.yaml
save_data(project, f"campaigns/{campaign_slug}/campaign.yaml", {
  ...campaign_data, run_ids: [..., run_id], total_leads_pushed: N
})

# Update project.yaml campaigns index (Mode 1/2 only)
save_data(project, "project.yaml", {
  ...project, campaigns: [..., {slug, campaign_id, segment, country, status: "DRAFT"}]
}, mode="merge")

# Update run file
save_data(project, "runs/run-001.json", {
  ...run, campaign_id, campaign_slug,
  campaign: {campaign_id, leads_pushed: N, pushed_at: "{now}"}
}, mode="merge")
```

### Step D: Send test email
```
user_email = get_config().configured.user_email
# If not set, ask user for their email
smartlead_send_test_email(campaign_id=campaign_id, test_email=user_email)
```

### Step E: Export to Google Sheet (if configured)
```
# Only if GOOGLE_SERVICE_ACCOUNT_JSON is set
sheet = sheets_export_contacts(project=project_slug, campaign_slug=campaign_slug)
# Returns sheet_url with target_confidence + target_reasoning columns
```

### Step F: Present for activation (CHECKPOINT 2)

**Mode 1 and 2:**
```
Campaign Ready (DRAFT):
  SmartLead: https://app.smartlead.ai/app/email-campaigns-v2/{campaign_id}/analytics

  Settings: plain text, no tracking, 40% followup, {timezone}
  Accounts: {N} assigned
  Sequence: {N} steps (A/B on Email 1)

  Contacts: {N} verified → uploaded
  Google Sheet: {sheet_url}

  Test email sent to {user_email} — check your inbox.

  Cost: {search} + {enrichment} = {total} credits
  Stats: {companies} → {targets} targets ({rate}%) → {contacts} contacts

  Type "activate" to start sending.
```

**Mode 3** (campaign already ACTIVE):
```
Contacts Added:
  Campaign: {name} (ID: {campaign_id})
  NEW: {N} contacts (deduped against {existing})
  TOTAL: {total} in campaign
  New leads entering sending queue automatically.
```

### Step G: Activation

Wait for "activate":
```
smartlead_activate_campaign(campaign_id=campaign_id, confirm="I confirm")
```

### Update state
```
save_data(project, "state.yaml", {
  ...state,
  phase_states: {..., campaign_push: "completed"},
  status: "completed",
  completed_at: "{now}"
})
```

---

## Phase Skip Matrix

| Phase | Mode 1 | Mode 2 | Mode 3 | Human Gate |
|-------|:------:|:------:|:------:|:----------:|
| 1. Offer Extraction | AUTO | SKIP | SKIP | no |
| 2. Filter Generation | AUTO | AUTO | AUTO (seeded) | no |
| 3. Cost Gate | **CHECKPOINT 1** | **CHECKPOINT 1** | **CHECKPOINT 1** | **YES** |
| 4. Round Loop | AUTO | AUTO | AUTO + dedup | no |
| 5. People Extraction | AUTO | AUTO | AUTO + dedup | no |
| 6. Sequence Generation | AUTO | AUTO | SKIP | no |
| 7. Campaign Push | CREATE → **CP2** | CREATE → **CP2** | ADD → **CP2** | **YES** |

## Resume Logic

On pipeline start, BEFORE Phase 1:

```
existing = load_data(project, "state.yaml")
```

If state exists:
- `status == "completed"` → "Pipeline already completed. Start new run?"
- `status == "failed"` → show error, "Retry {failed_phase} or start fresh?"
- `status == "running"/"paused"` → skip all "completed" and "skipped" phases, resume from first pending/in_progress/failed

## Recovery from Phase Failures

| Phase | On Failure | Recovery |
|-------|-----------|----------|
| offer_extraction | Scrape failed | Retry with different URL or manual input |
| filter_generation | Generation failed | Retry or manual filters |
| cost_gate | User declined | Adjust filters, re-present |
| round_loop | Apollo rate limited | Wait and retry, or reduce scope |
| people_extraction | Enrichment failures | Retry failed, skip permanently failed |
| sequence_generation | Generation failed | Retry with different angle |
| campaign_push | SmartLead API error | Retry (handles "Plan expired!" bug) |
