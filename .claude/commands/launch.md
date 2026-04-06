---
description: Launch a SmartLead campaign — from user input to DRAFT campaign with zero interaction during execution
argument-hint: "[website/document/description] — e.g. 'https://acme.com payments in Miami' or 'campaign=3070919 kpi=200'"
---

# /launch $ARGUMENTS

## Step 1: Parse Arguments

Parse `$ARGUMENTS` to extract:

```
Named parameters:
- project=<slug>          → existing project (Mode 2)
- campaign=<id_or_slug>   → existing campaign (Mode 3)
- segment=<name>          → target segment
- geo=<location>          → geography
- kpi=<number>            → target contacts (default 100, "+N" for relative)
- max_cost=<credits>      → credit cap (default 200)

Free text:
- URL (starts with http)  → offer source
- File path (.md/.txt/.pdf) → offer source
- "accounts with Renat"   → email account hint
- "blacklist ES Global"   → blacklist hint
- Everything else          → offer description
```

## Step 2: Detect Mode

```
If campaign= found → MODE 3 (append to existing campaign)
If project= found  → MODE 2 (new campaign on existing project)
Else               → MODE 1 (fresh — new project + campaign)
```

## Step 3: Run Pipeline

Read and follow the **manager-leadgen** skill for the full pipeline orchestration.

The manager-leadgen skill defines:
- Session setup (project resolution, state.yaml init, resume detection)
- 7 phases with exactly 2 human checkpoints
- State tracking at every phase boundary
- Resume from crash/pause

Pass the parsed arguments and detected mode to the skill's Session Setup.

**Skills to read as each phase references them:**

| Phase | Skill to read |
|-------|---------------|
| 1. Offer Extraction | offer-extraction |
| 2. Filter Generation | apollo-filter-mapping |
| 3. Cost Gate (Checkpoint 1) | quality-gate (cost section) |
| 4. Round Loop | pipeline-state (round loop), company-qualification |
| 5. People Extraction | pipeline-state (people section) |
| 6. Sequence Generation | email-sequence |
| 7. Campaign Push (Checkpoint 2) | (direct SmartLead tool calls) |
