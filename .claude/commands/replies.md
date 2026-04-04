# /replies — Sync, Classify & Triage Campaign Replies

Sync replies from SmartLead campaigns, classify them, and present a triage report.

## Arguments
- `--campaign <name>`: Specific campaign (default: all active campaigns)
- `--project <name>`: All campaigns for a project
- `--warm-only`: Show only warm replies (interested + meeting_request)

## Phase 1: Sync + Classify

### 1. Discover Campaigns
- Call `smartlead_list_campaigns`
- Filter by project if specified
- Get campaigns with status ACTIVE or COMPLETED

### 2. Fetch Replied Leads
For each campaign:
- Call `smartlead_sync_replies`
- Get all leads with reply status

### 3. Classify (3-Tier Funnel)
**Skill**: reply-classification

For each reply:

**Tier 1 (FREE)**: Check regex patterns
- OOO → classify as out_of_office (0.95 confidence)
- Unsubscribe → classify as unsubscribe (0.90 confidence)
- Bounce → skip entirely
- If matched → DONE for this reply

**Tier 2 (FREE)**: Fetch full thread
- Call SmartLead API for full message history
- Extract latest REPLY (not our sent messages)
- Re-check Tier 1 on full text
- Strip HTML

**Tier 3 (LLM)**: Classify ambiguous replies
- Use classification rules from reply-classification skill
- Max 10 concurrent LLM calls
- Return: category, confidence, reasoning

### 4. Dedup
- Hash: MD5 of first 500 chars (lowercased, stripped)
- Skip already-classified replies

## Phase 2: Triage Report

Present results sorted by priority:

### WARM REPLIES (interested + meeting_request)
```
1. John Smith, VP Sales at Acme Corp
   "Sounds good, send me pricing info"
   → Suggested action: Send pricing sheet, offer 15-min call

2. Jane Doe, CTO at TechCo
   "Can we schedule a demo next week?"
   → Suggested action: Share calendar link
```

### QUESTIONS (need response)
```
3. Mike Johnson, Head of Growth at StartupX
   "How does your integration with Salesforce work?"
   → Suggested answer: [based on project offer context]
```

### WRONG PERSON (with referrals)
```
4. Sarah Lee at BigCorp
   "I left BigCorp last month. Try reaching Tom Wilson, he's the new VP."
   → Action: Add Tom Wilson to pipeline
```

### NOT INTERESTED
- 12 explicit declines — no action needed

### AUTO-FILTERED
- 8 out-of-office (will return by various dates)
- 3 unsubscribes (removed from campaigns)
- 2 bounces (invalid emails)

## Summary Stats

```
Campaign: Fintech PAYMENTS Q1
Total replies: 45
Warm: 8 (18%)
Needs response: 12
Auto-filtered: 13
Classification: Tier 1 FREE: 13 | Tier 2 FREE: 12 | Tier 3 LLM: 20
```

## Draft Response (Optional)

For warm replies, offer to draft a response:
- "Want me to draft responses for the 8 warm replies?"
- If yes → generate personalized response for each based on:
  - Their reply content
  - Project offer context
  - Their company/role
- Present drafts for approval
- On approve → call `smartlead_send_reply` for each

## Ongoing Monitoring

After initial sync:
- "Reply monitoring is active. Run /replies again anytime for updates."
- For Telegram notifications: configure via project settings
