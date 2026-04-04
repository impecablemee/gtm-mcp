# Reply Classification Skill

Classify email campaign replies using a 3-tier cost-optimized funnel. This skill replaces reply_analysis_service.py and reply_service.py.

## When to Use

- During /replies command
- When syncing SmartLead campaign replies
- When user asks "any warm replies?" or "who responded?"

## 3-Tier Classification Funnel

### Tier 1: Regex Pre-filter (FREE — no LLM cost)

Apply regex patterns FIRST. If matched, classify immediately without LLM.

**Out-of-Office Patterns** (confidence: 0.95):
```regex
out of(?:the)?office|ooo|on vacation|holiday|away|
i(?:'m|am)(?:\s+)(?:out|away|off)|
auto[- ]?reply|will(?:\s+)?(?:be)?(?:\s+)?(?:back|return)|
maternity|paternity|sick leave|limited access|
(?:i'?ll|will)\s*respond\s*(?:when|after)|
thank you for your(?:\s+)(?:email|message|patience)
```

**Unsubscribe Patterns** (confidence: 0.90):
```regex
unsubscribe|opt[- ]?out|remove(?:\s*)?(?:me|my)|
stop(?:\s*)?(?:emailing|sending|contacting)|
don'?t(?:\s*)?(?:email|contact|message)|
take me off|no longer wish
```

**Bounce Patterns** (SKIP entirely — not a real reply):
```regex
delivery(?:failed|failure)|undeliverable|
mailbox(?:full|unavailable)|message not delivered|
recipient rejected|address rejected|user unknown|no such user
```

If Tier 1 matches → classify and STOP. No LLM needed.

### Tier 2: Full Thread Fetch (FREE)

For replies that passed Tier 1 (real conversations):
1. Fetch full message thread from SmartLead
2. Extract the LATEST reply (not our sent emails)
3. Re-check Tier 1 patterns on full text (sometimes OOO is in the full thread)
4. Strip HTML tags and entities
5. If still no Tier 1 match → proceed to Tier 3

### Tier 3: LLM Classification (CHEAP — gpt-4o-mini)

Only for ambiguous replies that passed Tier 1. Use concurrency limit of 10.

## 10 Classification Categories

| Category | Description | Example |
|----------|-------------|---------|
| **interested** | ANY positive signal | "sounds good", "tell me more", "yes", shares contact info |
| **meeting_request** | Wants to schedule | "let's set up a call", shares availability, mentions calendar |
| **not_interested** | EXPLICIT decline | "not interested", "no thanks", "don't need this" |
| **question** | Asks before deciding | "how much does it cost?", "what integrations?" |
| **wrong_person** | Not the right contact | "I left the company", "try reaching John", "not my department" |
| **out_of_office** | Away / auto-reply | "I'm on vacation until...", auto-reply |
| **unsubscribe** | Wants to stop emails | "remove me", "unsubscribe", "stop emailing" |
| **bounce** | Delivery failure | "mailbox full", "user unknown" |
| **referral** | Forwards to someone else | "CC'ing my colleague who handles this" |
| **other** | Doesn't fit above | Irrelevant response, spam |

## Classification Rules (for LLM Tier 3)

### Positive Signal Detection
- Short affirmative ("sure", "sounds good", "yes", "why not") = **interested**
- Person shares contact on different channel (WhatsApp, Telegram) = **interested**
- Person asks about pricing or features = **question** (borderline → interested)
- Person says "send me info" or "tell me more" = **interested**

### Russian Language Support
- "нужно" (need) without negation = **interested**
- "не нужно" / "не интересно" = **not_interested**
- "перезвоните" (call back) = **meeting_request**
- "я ушел" (I left) = **wrong_person**

### Disambiguation Rules
- When in doubt between interested and question → **interested** (more conservative to miss)
- "Let me think about it" = **interested** (not a decline)
- "Not now but maybe later" = **interested** (still open)
- "We use Competitor X" without explicit decline = **question** (potential to compare)

### Keyword Fallback (when LLM unavailable)
| Category | Keywords | Confidence |
|----------|----------|------------|
| meeting | meeting, call, schedule, calendar, demo, zoom, teams, available, slot | 0.7 |
| interested | interested, tell me more, sounds good, like to know, send me, pricing, proposal | 0.7 |
| not_interested | not interested, no thank, don't contact, no need, not looking, pass, decline | 0.7 |
| wrong_person | wrong person, not the right, no longer, left the company, try reaching | 0.6 |
| question | ? in text + len>20 | 0.6 |
| other | default | 0.4 |

## Output Per Reply

```json
{
  "lead_email": "john@company.com",
  "lead_name": "John Smith",
  "lead_company": "Acme Corp",
  "campaign_name": "Fintech PAYMENTS Q1",
  "category": "interested",
  "confidence": 0.92,
  "reasoning": "Replied 'sounds good, send me more info about pricing' — explicit interest signal",
  "reply_text": "sounds good, send me more info about pricing",
  "received_at": "2026-04-01T14:30:00Z",
  "needs_reply": true,
  "tier_classified": 3
}
```

## Triage Report (After Classification)

Sort and present by priority:

### 1. WARM Replies (interested + meeting_request)
- List each with: name, company, reply text, suggested action
- "John Smith at Acme Corp replied: 'sounds good, send me pricing' → Draft response?"

### 2. Questions
- List each with the specific question asked
- Suggest answer based on project context

### 3. Wrong Person (with referrals)
- If they suggested someone else → extract the referral contact
- "Jane Doe left Acme. Suggested reaching Mike Johnson, VP Sales"

### 4. Not Interested
- Count only, don't list individually
- "12 explicit declines — no action needed"

### 5. Auto-Filtered (OOO, unsubscribe, bounce)
- Count by category
- "8 out-of-office, 3 unsubscribes, 2 bounces"

## Dedup Logic

- Message hash: MD5 of first 500 chars, lowercased and stripped
- Same hash = same reply, don't re-classify
- Track by: campaign_id + lead_email + message_hash

## Needs Reply Flag

Set `needs_reply: true` for:
- interested
- meeting_request
- question

These are the replies that need human attention.

## Operator Learning Flow

Track approved/dismissed reply drafts to improve over time:

1. AI classifies reply + generates draft response
2. Operator reviews: approve or dismiss
3. System tracks approval rates per category
4. Golden examples accumulate for future improvement:
   - Approved drafts → "this is what a good response looks like"
   - Dismissed drafts → "avoid this pattern"
5. Over time, classification and drafts get more aligned with operator preferences

Store learning data in project workspace for persistence across sessions.

## Summary Stats

```json
{
  "total_replied": 45,
  "warm_count": 8,
  "needs_reply_count": 12,
  "by_category": {
    "interested": 5,
    "meeting_request": 3,
    "question": 4,
    "not_interested": 12,
    "wrong_person": 3,
    "out_of_office": 8,
    "unsubscribe": 3,
    "bounce": 2,
    "other": 5
  },
  "tier_stats": {
    "tier1_free": 13,
    "tier2_thread": 32,
    "tier3_llm": 20
  }
}
```
