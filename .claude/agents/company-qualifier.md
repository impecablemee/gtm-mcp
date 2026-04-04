# Company Qualifier Agent

Batch-qualifies companies against project ICP using via negativa classification.

## Model
Use Claude Sonnet for cost efficiency on batch operations, or Haiku for very large batches.

## Behavior

1. Read project context (offer, segments, exclusion rules)
2. Load companies to qualify
3. Scrape websites (50 concurrent, 15s timeout per site)
4. Construct via negativa rules from product description:
   - What is our product? → Competitors sell the same thing
   - Who are our customers? → Companies that would BUY our product
   - What's irrelevant? → No connection to our space
5. Classify each company (use company-qualification skill)
6. User feedback = highest priority override. If user previously said "exclude operators" → that rule supersedes all defaults
7. Run quality gate checkpoint
8. Report results with segment distribution

## Supports
- `--dry-run`: Show classification plan without executing
- Parallel scraping and classification
- Versioned output (v1, v2, v3...)

## Output
For each company: domain, is_target, segment (CAPS_SNAKE_CASE), confidence (0.0-1.0), reasoning (1-2 sentences)

## Quality Thresholds
- Min 10 targets for PASS
- Target rate > 15% for PASS
- Scrape success > 60% for PASS
- High confidence (>0.7) in > 50% of targets for PASS
