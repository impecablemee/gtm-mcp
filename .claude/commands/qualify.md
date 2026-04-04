# /qualify — Batch Company Qualification

Classify companies as target/not-target using via negativa rules.

## Arguments
- `--file <path>`: CSV file with domains
- `--project <name>`: Use companies from pipeline
- `--domains <d1,d2,...>`: Direct domain list
- `--requalify`: Re-classify already-qualified companies (creates new version)
- `--dry-run`: Show plan without executing

## Steps

### 1. Load Companies
Based on input source:
- `--file`: Read CSV, extract domain column (auto-detect: domain, website, url, company_url)
- `--project`: Call `load_data` for project's companies
- `--domains`: Parse comma-separated list

### 2. Load Project Context
- Call `load_data` for project offer summary
- Extract: offer description, segments, exclusion rules, target roles
- Load any existing user feedback from previous qualify runs

### 3. Scrape Websites
- Call `scrape_website` for each domain (50 concurrent, 15s timeout)
- Track: success, failure, timeout, empty
- Skip already-scraped domains (if resuming)

### 4. Classify
**Skill**: company-qualification

- Apply via negativa rules from offer context
- User feedback from previous runs = HIGHEST PRIORITY override
- Classify each: is_target, confidence, segment, reasoning

### 5. Quality Gate
**Skill**: quality-gate

- Run checkpoint 2 metrics
- Report: targets, target rate, confidence distribution
- If targets < 10: WARN

### 6. Save Results (Versioned)
- Call `save_data` with mode "versioned"
- Creates: qualified/v1.json, qualified/v2.json, etc.
- `latest.json` points to most recent

### 7. Report
Present:
- Total companies: N
- Targets: N (rate%)
- Segment distribution: {PAYMENTS: 20, LENDING: 15}
- Low confidence (needs review): N
- Scrape failures: N

### Feedback Loop
If user provides corrections:
- "Roobet is an operator, not a provider" → store as override
- Re-qualify with updated rules → new version
- Compare: "v1: 15 targets at 48% → v2: 25 targets at 81%"
