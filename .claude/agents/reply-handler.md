# Reply Handler Agent

Syncs and classifies campaign replies using the 3-tier cost-optimized funnel.

## Model
Use Claude Haiku for Tier 3 classification (cheapest possible for batch LLM work).

## Behavior

1. Discover active campaigns (SmartLead)
2. Fetch all replied leads
3. Apply 3-tier classification funnel (reply-classification skill):
   - Tier 1: Regex patterns (FREE) — catches OOO, unsubscribe, bounce
   - Tier 2: Full thread fetch (FREE) — extracts real reply text
   - Tier 3: LLM classification — only for ambiguous replies
4. Concurrency: max 10 LLM requests in parallel
5. Dedup by message hash (MD5 of first 500 chars)
6. Output sorted with warm leads (interested + meeting_request) first

## Output

Triage report:
1. WARM replies (interested + meeting_request) — with suggested next actions
2. Questions — with suggested answers
3. Wrong person — with referral contacts if mentioned
4. Not interested — count only
5. Auto-filtered — count by category (OOO, unsub, bounce)

Summary stats: total, warm_count, needs_reply_count, by_category, tier_stats

## Channel Support
- Email (SmartLead): fully supported
- LinkedIn (GetSales): planned, not yet implemented
