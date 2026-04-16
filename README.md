# GTM-MCP — B2B Cold Outreach Toolkit for Claude Code

A set of skills and API wrappers that turn Claude Code into a full B2B cold email pipeline. Describe what you sell and who you're targeting — it finds companies, verifies fit, extracts contacts, writes sequences, and launches campaigns. All from your terminal, all on your machine.

Built by [GetSally](https://getsally.io), a B2B lead gen agency. The classification rules, filtering logic, and email patterns in this toolkit come from running thousands of outreach campaigns for 100+ B2B companies across the US, EU, and other markets – from early-stage startups to large enterprises. Our campaigns deliver 10–50 qualified leads per month. Used daily by our 20-person sales team. Now open source.

For updates, follow [Rinat Khatipov on LinkedIn](https://www.linkedin.com/in/rinat-khatipov/).

---

## Requirements & flexibility

The full `/launch` pipeline runs on three tools: [Apollo](https://apollo.io) for company and people data, [SmartLead](https://smartlead.ai) for email campaigns, and [Apify](https://apify.com) for web scraping. If you already use Apollo + SmartLead, you can plug in your API keys and run the whole pipeline end-to-end.

**Don't use these tools?** You can still grab individual skills and use them in your own setup — the AI classification skill, the ICP filtering logic, the email sequence patterns. They're just markdown files in `.claude/skills/`, portable to any Claude Code project.

We're actively working on more integrations (Instantly, Lemlist, ZoomInfo, Hunter, and others) to give you more flexibility on the stack. If your setup needs something we don't cover yet — [open an issue](https://github.com/impecablemee/gtm-mcp/issues) or drop a comment. Feedback shapes what we build next.

---

## Getting Started

Open your terminal and copy-paste each block below, one at a time. That's the entire install.

<sub>On Mac: press `Cmd + Space`, type "Terminal", hit Enter. On Windows: open "Windows Terminal" or "PowerShell".</sub>

### Step 1 — Clone the repo

```bash
git clone https://github.com/impecablemee/gtm-mcp.git
cd gtm-mcp
```

### Step 2 — Add your API keys

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in:

| Key | Where to get it | Required? |
|-----|----------------|-----------|
| `GTM_MCP_APOLLO_API_KEY` | [Apollo](https://apollo.io) → Settings → API Keys | Yes |
| `GTM_MCP_SMARTLEAD_API_KEY` | [SmartLead](https://smartlead.ai) → Settings → API | Yes |
| `GTM_MCP_USER_EMAIL` | Your email — test emails land here before activation | Yes |
| `GTM_MCP_APIFY_PROXY_PASSWORD` | [Apify](https://apify.com) → Proxy → Password | Optional, improves scraping |
| `GTM_MCP_GETSALES_API_KEY` | [GetSales](https://getsales.io) → Settings | Optional, for LinkedIn outreach |
| `GTM_MCP_GETSALES_TEAM_ID` | GetSales → Team settings | Optional, for LinkedIn outreach |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Google Cloud Console | Optional, for Sheets export |
| `GOOGLE_SHARED_DRIVE_ID` | Google Drive | Optional, for Sheets export |

Save and close the file.

### Step 3 — Open in Claude Code

```bash
claude
```

This opens Claude Code inside the `gtm-mcp` directory. It automatically discovers `.mcp.json` and loads all tools. No `pip install`, no virtualenv — `uv run` handles everything.

> If `claude` is not recognized, install Claude Code first: https://docs.anthropic.com/en/docs/claude-code/overview

---

## How to Use

### Step 1: Create an outreach strategy

Before launching a campaign, you need a strategy — an md file describing what you sell, who you're targeting, which segments, and what case studies you have. Two ways to create one:

**Option A — Let Claude generate it for you.**

Inside Claude Code in the gtm-mcp directory:

```
Generate an outreach strategy for [yourwebsite.com].
Use all case studies from the website — focus on segments
where we have proven results and success stories.
```

You can also feed Claude additional materials: pitch decks, product descriptions, offers. More context = more accurate strategy.

Claude scrapes your website, studies case studies and product pages, and generates a structured md file with segments, Apollo keywords, and draft email sequences. Saves as `outreach-plan-[segment].md`.

Review the document, adjust if needed, then move to Step 2.

**Option B — Create the strategy file manually.**

If you already know your ICP and want full control, create an md file yourself and place it in the project directory.

---

### Step 2: Launch the campaign

When your strategy is ready, launch the campaign. Type `/launch`, provide your website and describe your ICP in detail. **The more detailed the ICP description, the better** — it directly determines filtering quality and how many target companies end up in the campaign.

**From a strategy file:**

```
/launch outreach-plan-fintech.md
```

**Or directly from a URL + ICP description:**

```
/launch https://yourcompany.com fintech payments companies in US, 50-500 employees, Series A+
```

**What happens after `/launch`:**

1. **Offer extraction** — Claude reads your strategy (or scrapes the website) and builds a structured profile: what you sell, who needs it, what problems you solve.
2. **Filter generation** — based on the offer, picks Apollo keywords and filters. Runs a probe search (6 credits) to estimate volume and cost.
3. **⏸️ Strategy approval** — shows the full plan: keywords, geography, cost estimate, draft email sequence. **Nothing runs until you say "yes".** You can adjust: remove a keyword, add a geography, change email copy.
4. **Search and classification** — searches Apollo for companies, scrapes each website, uses AI to determine: is this company actually your target? Filters out 60-70% of irrelevant results.
5. **Contact extraction** — finds decision-makers at each verified company. Free people search first, then paid enrichment (1 Apollo credit per contact).
6. **Campaign creation** — creates a SmartLead campaign in DRAFT mode (not sending!). Uploads contacts, sets up the sequence. Sends a test email to your inbox.
7. **⏸️ Activation** — you check the test email. If it looks good, type `activate`. Only then does SmartLead start sending.

**Two moments where you decide:** strategy approval (step 3) and campaign activation (step 7). Everything in between is autonomous.

---

### After launch

- **Add more contacts** to a running campaign: `gather 50 more`
- **New segment** within an existing project: `/launch project=easystaff segment=LENDING geo=UK`
- **Append to any SmartLead campaign** (even manually created ones): `/launch campaign=3070919 kpi=+100` — paste the campaign URL and describe what you want. The system deduplicates against existing leads automatically.

---

## Architecture

```
Claude Code ──stdio──> gtm-mcp (49 tools, 0 LLM calls)
                            |
                  +---------+---------+
                  v         v         v
              Apollo    SmartLead   GetSales
              (search)  (campaigns) (LinkedIn)
```

Zero LLM calls inside the toolkit. Claude Code does all the reasoning using domain knowledge encoded as skills.

**Tools** (`src/gtm_mcp/`): Thin API wrappers. Only data access.

**Skills** (`.claude/skills/`): Domain knowledge in markdown — classification rules, email writing rules, filter strategies. Claude reads these and reasons.

**Commands** (`.claude/commands/`): The `/launch` command — orchestrates the full pipeline.

### Pipeline Steps

| Step | What Happens | Human Input |
|------|-------------|:-----------:|
| 1. Extract Offer | Scrape URL / read file / parse text -> structured ICP | - |
| 2. Generate Filters | Apollo taxonomy + keywords + probe (6 credits) | - |
| 3. Strategy Approval | Show offer + filters + cost estimate | **Approve?** |
| 4. Gather + Classify | Apollo search -> scrape websites -> AI classifies | - |
| 5. Extract People | FREE search -> PAID enrichment (1 credit/person) | - |
| 6. Generate Sequence | Email sequence from 12-rule template or reference | - |
| 7. Campaign Push | SmartLead DRAFT + test email + Google Sheet | **Activate?** |

### Key Rules

- **1 keyword per Apollo request** — 7x more unique companies vs combined
- **Via negativa classification** — exclude non-targets, don't define targets (97% accuracy)
- **Max 200 Apollo credits** per run (default, overridable)
- **100 verified contacts** KPI target (default, overridable)
- **Plain text emails**, no tracking, Mon-Fri 9-18 target timezone

---

## Tools (49)

### Config & Projects (8)
| Tool | Description |
|------|-------------|
| `get_config` | Get configuration status (which keys are set) |
| `set_config` | Set a configuration value |
| `create_project` | Create a new project |
| `list_projects` | List all projects |
| `save_data` | Save data to project workspace (write/merge/append/versioned) |
| `load_data` | Load data from project workspace |
| `find_campaign` | Find campaign by SmartLead ID or slug across projects |
| `get_project_costs` | Cost breakdown per project — totals, per-campaign, per-run |

### Blacklist (3)
| Tool | Description |
|------|-------------|
| `blacklist_check` | Check if a domain is blacklisted (supports time-windowed checks) |
| `blacklist_add` | Add domains with metadata (source, campaign, contact date) |
| `blacklist_import` | Import blacklist from a file |

### Apollo (6)
| Tool | Description |
|------|-------------|
| `apollo_search_companies` | Search by keywords, industries, location, size, funding |
| `apollo_search_people` | Search people at a company (FREE — no credits) |
| `apollo_enrich_people` | Enrich with verified emails (1 credit/person) |
| `apollo_enrich_companies` | Bulk enrich companies by domain |
| `apollo_get_taxonomy` | Get all 84 Apollo industries with tag_ids |
| `apollo_estimate_cost` | Estimate credits needed for a pipeline run |

### Scraping (2)
| Tool | Description |
|------|-------------|
| `scrape_website` | Scrape website text via Apify proxy with fallback |
| `scrape_batch` | Batch scrape many URLs in parallel (50 concurrent) |

### SmartLead (13)
| Tool | Description |
|------|-------------|
| `smartlead_list_campaigns` | List all campaigns |
| `smartlead_list_accounts` | List all email accounts (paginated, handles 2000+) |
| `smartlead_search_accounts` | Filter cached accounts by name/domain |
| `smartlead_create_campaign` | Create campaign with schedule and settings (DRAFT) |
| `smartlead_set_sequence` | Set email sequence steps with A/B variant support |
| `smartlead_add_leads` | Add leads to campaign with company name normalization |
| `smartlead_get_campaign` | Get campaign details (accounts, sequences, status) |
| `smartlead_get_lead_messages` | Fetch full message thread for reply classification |
| `smartlead_export_leads` | Export all leads from a campaign (for dedup/blacklist) |
| `smartlead_sync_replies` | Sync replied leads from a campaign |
| `smartlead_send_reply` | Send a reply to a lead |
| `smartlead_send_test_email` | Send test email to verify before activation |
| `smartlead_activate_campaign` | Activate campaign — start sending (requires confirmation) |

### GetSales — LinkedIn (4)
| Tool | Description |
|------|-------------|
| `getsales_list_profiles` | List LinkedIn profiles |
| `getsales_create_flow` | Create LinkedIn outreach flow |
| `getsales_add_leads` | Add leads to a GetSales flow (validates LinkedIn URLs) |
| `getsales_activate_flow` | Activate flow — start LinkedIn outreach |

### Google Sheets (3)
| Tool | Description |
|------|-------------|
| `sheets_create` | Create Google Sheet on Shared Drive with contact headers |
| `sheets_export_contacts` | Export contacts with classification reasoning |
| `sheets_read` | Read sheet data (for blacklist import, company lists) |

### Pipeline (7)
| Tool | Description |
|------|-------------|
| `pipeline_probe` | Probe search — 6 Apollo calls + batch scrape in ONE call |
| `pipeline_gather_and_scrape` | Full gather — all Apollo searches + all scraping, streaming |
| `pipeline_import_blacklist` | Export SmartLead campaign leads as project blacklist |
| `pipeline_save_contacts` | Save contacts to project + run file atomically |
| `pipeline_compute_leaderboard` | Compute keyword quality scores from run data |
| `pipeline_save_intelligence` | Save cross-run keyword intelligence for future runs |
| `campaign_push` | Atomic campaign setup — create + sequence + leads + test email |

### Assignment (2)
| Tool | Description |
|------|-------------|
| `assign_campaigns_to_projects` | Auto-assign SmartLead campaigns to projects |
| `learn_assignment_correction` | Learn from user correction for future auto-assignment |

### Utility (1)
| Tool | Description |
|------|-------------|
| `normalize_company_name` | Strip legal suffixes (Inc, LLC, Ltd, GmbH, etc.) |

---

## Data Storage

All project data in `~/.gtm-mcp/projects/<slug>/`:

```
~/.gtm-mcp/
├── config.yaml                  # API keys
├── blacklist.json               # global domain blacklist (structured, temporal)
├── filter_intelligence.json     # cross-run keyword quality scores
└── projects/
    └── sally-fintech/
        ├── project.yaml         # offer, segments, ICP
        ├── state.yaml           # pipeline phase progress
        ├── contacts.json        # extracted contacts
        ├── runs/
        │   └── run-001.json     # complete execution record
        └── campaigns/
            └── payments-us/
                ├── campaign.yaml
                ├── sequence.yaml
                └── replies.json
```

---

## Email Infrastructure

Before sending cold emails, you need separate sending domains and inboxes — **never send cold outreach from your primary domain** (Google/Microsoft will flag it as spam and you'll stop receiving normal business emails).

What you need:
- **5+ lookalike domains** (e.g., `acme-team.com`, `getacme.com`) — ~$10/domain/year on [Namecheap](https://namecheap.com)
- **2 inboxes per domain** via [Google Workspace](https://workspace.google.com)
- **Connect all inboxes to [SmartLead](https://smartlead.ai)** and run warmup (~2 weeks before you can start sending)
- **Capacity:** ~100 emails/day per domain. 5 domains = ~500 emails/day
- **Rotate every 4-6 weeks** — domains degrade over time as recipients mark emails as spam. Buy new ones, warm up, retire old ones.

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Inspired By

[claude-pipe](https://github.com/bluzir/claude-pipe) — file-first agent orchestration framework. Core ideas adopted: state persists to YAML files, quality gates between phases, predictable costs through deterministic tool code.

## License

MIT
