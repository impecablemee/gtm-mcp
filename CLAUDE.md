# GTM-MCP Open Source

## Architecture

Thin MCP server (tools) + domain knowledge (skills). Zero LLM calls inside the server.

### How It Works
- **Tools** (`src/gtm_mcp/`): Thin API wrappers. Return raw data only.
- **Skills** (`.claude/skills/`): Domain knowledge the calling agent reads and applies.
- **Commands** (`.claude/commands/`): Multi-step workflow orchestrators.
- **Agents** (`.claude/agents/`): Batch-processing agent definitions.

## Skills (8 total)

| Skill | Purpose |
|-------|---------|
| offer-extraction | Extract ICP from website/document/text |
| apollo-filter-mapping | NL query → Apollo API filters (67 industries, keyword expansion, funding) |
| company-qualification | Via negativa target/not-target classification (97% accuracy) |
| quality-gate | Pipeline checkpoints, KPI logic, 10 keyword regen angles |
| email-sequence | 12-rule GOD_SEQUENCE cold email generation |
| linkedin-sequence | GetSales flow generation (5 types from 414 live flows) |
| reply-classification | 3-tier reply funnel (regex FREE → keywords FREE → LLM cheap) |
| **pipeline-state** | **Entity model, run file format, round loop, filter tracking, cross-run intelligence** |

## Commands

| Command | What It Does |
|---------|---|
| /leadgen | Full pipeline: offer → filters → round loop (gather→scrape→classify→people) → campaign |
| /qualify | Batch company qualification with versioned snapshots |
| /outreach | Generate email/LinkedIn sequences + push to platforms |
| /replies | Sync + classify + triage campaign replies |

## Pipeline Tracking (pipeline-state skill)

Every pipeline run produces `runs/run-{id}.json` — a single file containing 6 linked entities:

| Entity | Purpose |
|--------|---------|
| FilterSnapshot | Immutable filter record with parent chain (evolution history) |
| Round | One gather→scrape→classify→people cycle with streaming phase timelines |
| APIRequest | Every Apollo API call (1 keyword per request, page, funded flag) |
| Company | Keyed by domain, references request IDs that found it |
| Contact | Extracted people with enrichment retry tracking |
| Iteration | Classification pass with feedback applied |

**Every target company traces back to**: company → found_by_requests → request → filter_snapshot → generation_details

**Cross-run learning**: `~/.gtm-mcp/filter_intelligence.json` accumulates keyword/industry quality scores across all projects. Future runs start with proven keywords as seeds.

## Critical Rules

- **1 keyword per Apollo request** — 7x more unique companies vs combined
- **Funding filter fixes sparse pagination** — essential for funded segments
- **Classify from scraped text ONLY** — never use Apollo industry label
- **KPI = 100 verified contacts** (not companies). Stop immediately when reached.
- **400 companies per round max** — then wait for scrape+classify before deciding next round
- **Never spend credits without user confirmation**
- **ONE question per response**

## Install & Run

```bash
cd mcp-open-source
pip install -e ".[dev]"
gtm-mcp                    # stdio MCP server
```

## Config

```yaml
# ~/.gtm-mcp/config.yaml
apollo_api_key: ""
smartlead_api_key: ""
getsales_api_key: ""
getsales_team_id: ""
apify_proxy_password: ""    # optional
```

## Project Structure

```
.claude/
  skills/           # 8 domain knowledge skills
  commands/          # 4 orchestrator commands
  agents/            # 2 batch agents
  settings.json
.mcp.json
src/gtm_mcp/
  server.py          # 27 tools via FastMCP (stdio)
  config.py          # ~/.gtm-mcp/config.yaml
  workspace.py       # File-based storage (write/merge/append/versioned)
  tools/             # apollo.py, smartlead.py, getsales.py, scraping.py
pyproject.toml       # pip install → gtm-mcp binary
```
