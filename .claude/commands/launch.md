---
description: Run the full lead generation pipeline — from offer extraction through Apollo search to SmartLead campaign
argument-hint: "[website/file/text] — e.g. 'https://acme.com payments in US' or 'outreach-plan.md' or 'campaign=3070919 kpi=+100'"
---

# /launch $ARGUMENTS

Full pipeline: input → gather → qualify → SmartLead campaign. **Two human checkpoints, everything else autonomous.**

## Parse Arguments

```
Named params:
  project=<slug>        → Mode 2 (new campaign on existing project)
  campaign=<id_or_slug> → Mode 3 (append to existing campaign)
  segment=<name>        → target segment
  geo=<location>        → geography
  kpi=<number>          → target contacts (default 100, "+N" for relative)
  max_cost=<credits>    → Apollo credit cap (default 200)

Free text:
  URL (starts with http)     → scrape for offer
  File path (.md/.txt/.pdf)  → read for offer
  "accounts with Renat"      → email account hint
  Everything else            → offer description
```

**Mode detection:**
- `campaign=` → MODE 3. Call `find_campaign(campaign_ref)` → get project + campaign data. Call `smartlead_get_campaign(campaign_id)` → verify not STOPPED.
- `project=` → MODE 2. Call `load_data(project, "project.yaml")` → verify `offer_approved == true`. Check segment not already used in `project.campaigns[]`.
- Neither → MODE 1. Fresh project.

## Resume Check

```
existing_state = load_data(project, "state.yaml")
If exists and status != "completed":
  → Show progress, ask "Resume from {current_phase}?"
  → If yes: skip completed/skipped steps, pick up from first pending
  → If no: archive old state, start fresh
```

---

## Step 1: Extract Offer (AUTONOMOUS)

**Mode 2/3**: SKIP — offer already approved. Show: "Using offer from {project}."

**Mode 1**:

If URL: `scrape_website(url)` → analyze scraped text.
If file: read file from disk → analyze text.
If text: analyze directly.

Use the **offer-extraction** skill rules to produce structured JSON:
- `primary_offer`, `segments[]` (name + 8-10 keywords each), `target_roles`, `apollo_filters`, `exclusion_list`

```
save_data(project, "project.yaml", {name, slug, offer: extracted, offer_approved: false, campaigns: []}, mode="merge")
```

Update state: `save_data(project, "state.yaml", {..., phase_states: {offer_extraction: "completed"}})`

---

## Step 2: Generate Filters + Probe (AUTONOMOUS)

Use the **apollo-filter-mapping** skill rules.

**Get taxonomy:**
```
taxonomy = apollo_get_taxonomy()
```

**Generate filters** from offer + taxonomy:
- Pick 2-3 industry tag_ids (SPECIFIC > BROAD)
- Generate 20-30 keywords (product names, not generic terms)
- Map locations and employee sizes

**Mode 3 extra**: Load `keyword_leaderboard` from previous runs → seed with top performers, exclude exhausted.

**Probe (6 credits max):**
```
For tag_id in industry_tag_ids[:3]:
  apollo_search_companies({organization_industry_tag_ids: [tag_id], organization_locations: [...], organization_num_employees_ranges: [...]})

For keyword in keywords[:3]:
  apollo_search_companies({q_organization_keyword_tags: [keyword], organization_locations: [...], organization_num_employees_ranges: [...]})
```

Collect probe_breakdown: companies per filter, total available.

**Estimate cost:**
```
apollo_estimate_cost(target_count=kpi, contacts_per_company=3)
```

**Resolve email accounts:**
```
accounts = smartlead_list_accounts()
→ Filter by user hint or ask which to use
```

**Create run file:**
```
save_data(project, "runs/run-001.json", {
  run_id: "run-001", project, campaign_id, campaign_slug, mode,
  status: "running", kpi: {target_people: kpi, max_people_per_company: 3, max_credits: max_cost},
  probe: {breakdown, credits_used}, filter_snapshots: [fs_001],
  rounds: [], requests: [], companies: {}, contacts: [], totals: {...}
})
```

Update state: `save_data(project, "state.yaml", {..., phase_states: {filter_generation: "completed"}})`

---

## Step 3: Strategy Approval — CHECKPOINT 1

**This is the ONLY approval before spending Apollo credits.**

Present everything in ONE document:

```
Strategy Document:

  OFFER: {primary_offer}
  Segments: {segments}
  Target Roles: {roles}
  Exclusions: {exclusions}

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

  COST: ~{total} credits (${usd}), max cap: {max_cost}
  KPI: {target} contacts, 3/company
  Accounts: {N} selected
  Sequence: GOD_SEQUENCE (4-5 steps)

  Proceed?
```

- "proceed" → set `offer_approved: true`, continue to autonomous gathering
- Feedback → adjust offer/filters, re-present

```
save_data(project, "project.yaml", {..., offer_approved: true}, mode="merge")
save_data(project, "state.yaml", {..., phase_states: {cost_gate: "completed"}})
```

---

## Step 4: Gather + Scrape + Classify (AUTONOMOUS)

**After user says "proceed", this runs with ZERO interaction.**

Update state: `save_data(project, "state.yaml", {..., current_phase: "round_loop", phase_states: {round_loop: "in_progress"}})`

### Mode 3 dedup setup
```
For run_id in campaign.run_ids:
  prev = load_data(project, f"runs/{run_id}.json")
  seen_domains.add(prev.companies.keys())
existing = smartlead_export_leads(campaign_id)
seen_emails = {lead.email for lead in existing.leads}
```

### Round loop

**CRITICAL: 1 keyword per request, 1 tag_id per request. NEVER combine.**

For each keyword (parallel):
```
apollo_search_companies({q_organization_keyword_tags: [keyword], organization_locations: [...], organization_num_employees_ranges: [...]})
```

For each tag_id (parallel):
```
apollo_search_companies({organization_industry_tag_ids: [tag_id], ...})
```

Dedup by domain. Skip `seen_domains`. Stop at 400 unique companies per round.

**Scrape** each company (parallel, batches of 10-20):
```
scrape_website(company.primary_domain)
```

**Classify** each scraped company using **company-qualification** skill rules (via negativa — you do this inline, no tool call):
- Is this a target? → `is_target`, `confidence`, `segment`, `reasoning`
- Focus on EXCLUDING non-matches, not defining matches

**If target_rate < 15% after round**: autonomously regenerate keywords using **quality-gate** skill's 10 angles. Create new round. Max 5 regeneration cycles.

Update run file after each batch: `save_data(project, "runs/run-001.json", updated_run, mode="merge")`

Update state: `save_data(project, "state.yaml", {..., phase_states: {round_loop: "completed"}})`

---

## Step 5: Extract People (AUTONOMOUS)

Update state: `save_data(project, "state.yaml", {..., current_phase: "people_extraction", phase_states: {people_extraction: "in_progress"}})`

For each target company (parallel, batches of 5-10):

```
# FREE — no credits
people = apollo_search_people(domain=company.domain, person_seniorities=["c_suite","vp","head","director"])

# 1 credit per person
enriched = apollo_enrich_people(person_ids=[top_matches])
```

Priority: owner > founder > c_suite > vp > head > director.
Retry: if <3 verified, try next candidates (max 3 rounds, 12 credits/company).
Mode 3: skip contacts where email in `seen_emails`.
**Stop immediately when total_verified >= kpi target.**

```
save_data(project, "contacts.json", all_contacts, mode="write")
save_data(project, "runs/run-001.json", {..., contacts: all_contacts, totals: {kpi_met: true}}, mode="merge")
save_data(project, "state.yaml", {..., phase_states: {people_extraction: "completed"}})
```

---

## Step 6: Generate Sequence (AUTONOMOUS)

**Mode 3**: SKIP — sequence already on campaign.

Use **email-sequence** skill rules (12-rule GOD_SEQUENCE):
- 4-5 steps, Day 0/3/7/14
- ≤120 words per email
- A/B subjects on Email 1
- SmartLead variables: `{{first_name}}`, `{{company_name}}`, `{{city}}`, `{{signature}}`
- `<br>` for line breaks

If user's input document had sequences → use those instead.

```
save_data(project, "sequences.json", {steps: sequence_steps})
save_data(project, "state.yaml", {..., phase_states: {sequence_generation: "completed"}})
```

---

## Step 7: Campaign Push — CHECKPOINT 2

Update state: `save_data(project, "state.yaml", {..., current_phase: "campaign_push", phase_states: {campaign_push: "in_progress"}})`

### Create campaign (Mode 1/2)

```
campaign = smartlead_create_campaign(project, "{Segment} — {Geo}", account_ids, country_code, segment)
smartlead_set_sequence(project, campaign.slug, campaign.campaign_id, sequence_steps)
```

### Upload contacts (all modes)

```
smartlead_add_leads(campaign_id, [{email, first_name, last_name, company_name, custom_fields: {segment, city}}])
```

### Update tracking

```
save_data(project, f"campaigns/{slug}/campaign.yaml", {..., run_ids: [run_id], total_leads_pushed: N})
save_data(project, "project.yaml", {..., campaigns: [..., {slug, campaign_id, segment, country, status}]}, mode="merge")
save_data(project, "runs/run-001.json", {..., campaign: {campaign_id, leads_pushed: N, pushed_at: now}}, mode="merge")
```

### Test email

```
user_email from get_config() → user_email field. If not set, ask.
smartlead_send_test_email(campaign_id, user_email)
```

### Google Sheet (if configured)

```
sheets_export_contacts(project, campaign_slug)
→ Creates sheet with target_confidence + target_reasoning columns
```

### Present for activation

```
Campaign Ready (DRAFT):
  SmartLead: https://app.smartlead.ai/app/email-campaigns-v2/{id}/analytics
  Settings: plain text ✓, no tracking ✓, 40% followup ✓
  Accounts: {N} assigned
  Sequence: {N} steps set
  Contacts: {N} verified → uploaded
  Google Sheet: {url}
  Test email sent to {user_email} — check your inbox.
  Cost: {total} credits
  Stats: {companies} → {targets} targets → {contacts} contacts

  Type "activate" to start sending.
```

### Activate

```
smartlead_activate_campaign(campaign_id, "I confirm")
save_data(project, "state.yaml", {..., phase_states: {campaign_push: "completed"}, status: "completed"})
```

---

## Mode 3 Output (append to active campaign)

```
Contacts Added:
  Campaign: {name} (ID: {id})
  NEW: {N} contacts (deduped against {existing})
  TOTAL: {total} in campaign
  New leads entering sending queue automatically.
```
