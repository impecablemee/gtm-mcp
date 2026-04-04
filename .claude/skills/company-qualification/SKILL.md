# Company Qualification Skill

Classify gathered companies as target/not-target using via negativa approach. This skill replaces exploration_service.py, prompt_tuner.py, streaming_pipeline.py classification, and refinement_engine.py.

## When to Use

- After gathering companies from Apollo
- During pipeline's classify phase
- When user runs /qualify command
- When re-analyzing after user feedback

## Via Negativa Classification Method

Instead of defining what a target IS, define what a target is NOT. This approach achieves 97% accuracy.

### 7 Exclusion Rules (check in order)

1. **DIRECT COMPETITOR**: Sells the exact same product/service as our offer. Exclude.
   - Example: If our offer is "payroll platform", exclude other payroll platforms
   - BUT: A company that USES payroll (potential customer) is NOT a competitor

2. **COMPLETELY UNRELATED**: Zero overlap with any segment. Exclude.
   - Example: If targeting fintech, a restaurant chain is unrelated
   - BUT: A restaurant chain with 500+ locations MIGHT need payroll → check context

3. **WRONG GEOGRAPHY/SIZE**: Outside the specified location or employee range. Exclude.
   - This is already handled by Apollo filters, but verify from website content

4. **FREELANCER/SOLO CONSULTANT**: Individual, not a company. Exclude.
   - Clue: personal name as company name, "consultant", "freelance" in title

5. **PLACEHOLDER/PARKED/UNDER CONSTRUCTION**: No real business content. Exclude.
   - Clue: "coming soon", "under construction", single-page with no product info

6. **SHUT DOWN/INACTIVE**: Company no longer operating. Exclude.
   - Clue: "closed", "acquired", no recent activity, dead links

7. **INSUFFICIENT DATA**: Website has too little info to classify. Mark as low confidence.
   - If scrape returned <100 chars of useful text → confidence < 0.3

### Inclusion Signals (what makes a company a TARGET)

- They would BUY our product (they're a CUSTOMER, not a competitor)
- Agency doing work in the segment (they need our tools)
- Platform operating in the space (they need our infrastructure)
- Brand in the target activity (they're the end customer)
- Growing company (funding, hiring, expanding)

### Special Rules

- Recruitment agency ≠ buyer of recruiting tools (unless specifically targeting them)
- General digital marketing agency ≠ buyer of marketing SaaS (unless targeting them)
- "IT services" company could be consulting (target) or product company (competitor) — check website
- Company with multiple business lines → classify based on PRIMARY business

## Classification Output

For EACH company, return:

```json
{
  "is_target": true,
  "confidence": 0.85,
  "segment": "PAYMENTS",
  "reasoning": "Stripe dashboard integration platform. Provides payment analytics for merchants. Would be a customer for our payment infrastructure API."
}
```

### Segment Labels
- For TARGETS: use the segment label from offer extraction (PAYMENTS, LENDING, BAAS, etc.)
- For NON-TARGETS: use what the company ACTUALLY IS (COMPETITOR, CONSULTING_FIRM, RESTAURANT, etc.)
- Always CAPS_SNAKE_CASE, max 30 chars

### Confidence Scoring (0-100 scale)
- 90-100: Clear match/non-match with strong evidence
- 70-89: Good match, some ambiguity
- 40-69: Borderline, needs human review (trigger 2-pass re-evaluation)
- 0-39: Likely non-match or insufficient data

## Dynamic Prompt Generation

The classification prompt is generated FRESH for each project — never hardcoded. It combines:

1. **OUR PRODUCT**: {offer from project}
2. **TARGET SEGMENT**: {ICP description}
3. **EXCLUSION RULES**: from document exclusion_list (if available) + 7 via negativa rules above
4. **INCLUSION SIGNALS**: what makes a company a customer
5. **USER FEEDBACK**: Any corrections from previous iterations (HIGHEST PRIORITY)

### User Feedback Integration

User feedback ALWAYS overrides default rules:
- "Roobet is an operator, not a provider" → add to exclusion: "crypto/iGaming operators"
- "Include agencies, they're our target" → override rule that would exclude agencies
- Format: "[USER OVERRIDE] {feedback text}" stored in iteration history

## Iterative Prompt Tuning Algorithm

If initial accuracy is low:

1. Classify all companies with current prompt
2. Compare vs user/agent verdicts → accuracy, mismatches
3. If accuracy >= 95%: DONE
4. Extract false positive/false negative patterns
5. Improve prompt based on patterns:
   - FP (said target but isn't): add to exclusion rules
   - FN (said not target but is): add to inclusion signals
6. Re-classify with improved prompt
7. Repeat (max 5 iterations)

**Rules for improved prompts:**
- Keep via negativa approach
- No specific company names/domains in rules
- No hardcoded industries/keywords
- More PRECISE based on mismatch patterns
- Must generalize to ANY company in segment

## 2-Pass Re-evaluation

For borderline cases (confidence 0.4-0.7):
- Re-classify with higher-quality model (gpt-4o instead of gpt-4o-mini)
- Include extra context from Apollo enrichment data
- If still borderline → mark for human review

## Exploration (Optional Accuracy Boost)

If initial target rate is low, run exploration:
1. Pick top 5 confirmed targets
2. Enrich each via Apollo (5 credits total)
3. Extract common patterns: industry_tag_ids, keywords, SIC/NAICS codes
4. Use patterns to generate BETTER Apollo filters
5. Re-gather with improved filters → higher target rate

**Common Labels Extraction from enriched targets:**
- industry_tag_ids: most frequent across targets
- keywords: most frequent (top 15 from keyword_tags)
- industries: most frequent (top 10)
- sic_codes: most frequent (top 5)

## Concurrency

- Scrape websites: 100 concurrent (via scrape_website tool)
- Classify companies: 100 concurrent LLM calls
- Each company: scrape → classify (streaming, process as they arrive)

## Website Scraping for Classification

1. Call `scrape_website` tool for each company domain
2. Use the scraped text (NOT Apollo industry label) for classification
3. Max 5000 chars of cleaned text per company
4. If scrape fails → classify with low confidence from Apollo data only

## Per-Company Tracking Fields

Every classified company must track:
- `domain`: normalized domain
- `found_by`: array of keyword/industry values that found this company
- `found_in_round`: which pipeline round discovered it
- `funded_stream`: true if found via funded Apollo call
- `scrape_status`: success/failed/timeout
- `is_target`: bool
- `confidence`: 0-100
- `segment`: CAPS_SNAKE_CASE label
- `reasoning`: 1-2 sentences

## Iteration Lifecycle

Pipeline has ITERATIONS. Each change = new iteration. All visible to user.

```
Iteration 1: Initial search + classify (draft filters, initial prompt)
  → User reviews → provides feedback
Iteration 2: Improved prompt + optimized Apollo filters (from exploration enrichment)
  → Better accuracy, better target rate
Iteration 3+: Scale — same prompt + filters, more pages from Apollo
  → "find more" = increase max_pages, next offset
```

Each iteration records: filters used, prompt used, companies count, target count, target rate. User can compare iterations.

## Batch Processing

For large batches (100+ companies):
1. Process in parallel (100 concurrent)
2. Stream results as they complete
3. Track per-company: all fields above
4. Dedup by domain (if same company appears from multiple keyword streams)
