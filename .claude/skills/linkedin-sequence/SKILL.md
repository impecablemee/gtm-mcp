# LinkedIn Sequence Generation Skill

Generate GetSales LinkedIn outreach flows. This skill replaces getsales_automation.py domain knowledge.

## When to Use

- User wants LinkedIn outreach (not just email)
- During /outreach command with `--channel linkedin` or `--channel both`
- When building multi-channel campaigns

## 5 Flow Types

### 1. Standard Flow (default)
- Best for: general B2B outreach, 50-200 leads
- Timing: conservative, professional
```
Trigger → Connection Request (note)
  → Wait 3 days
  → [Accepted?]
    YES → Message 1 (value prop) → Wait 2 days → Message 2 (case study) → Wait 3 days → Message 3 (CTA)
    NO  → Profile View → Wait 2 days → Withdraw
```

### 2. Networking Flow
- Best for: relationship building, founder-to-founder
- Timing: slower, more personal
```
Trigger → Profile View → Wait 1 day → Connection Request (personal note, no pitch)
  → Wait 5 days
  → [Accepted?]
    YES → Message 1 (genuine interest) → Wait 4 days → Message 2 (value exchange) → Wait 5 days → Message 3 (soft ask)
    NO  → Like recent post → Wait 3 days → Withdraw
```

### 3. Product Launch Flow
- Best for: announcements, new features, time-sensitive
- Timing: aggressive, urgency-driven
```
Trigger → Connection Request (announcement hook)
  → Wait 2 days
  → [Accepted?]
    YES → Message 1 (launch details) → Wait 1 day → Message 2 (demo offer) → Wait 2 days → Message 3 (urgency)
    NO  → Withdraw immediately
```

### 4. Volume Flow
- Best for: high-volume prospecting, 500+ leads
- Timing: minimal, efficient
```
Trigger → Connection Request (short note)
  → Wait 2 days
  → [Accepted?]
    YES → Message 1 (pitch) → Wait 3 days → Message 2 (follow-up)
    NO  → Withdraw
```

### 5. Event Flow
- Best for: conference attendees, webinar leads
- Timing: context-dependent
```
Trigger → Connection Request ("Great meeting you at {event}")
  → Wait 1 day
  → [Accepted?]
    YES → Message 1 (reference talk/booth) → Wait 2 days → Message 2 (offer) → Wait 3 days → Message 3 (follow-up)
    NO  → Profile View → Wait 2 days → Withdraw
```

## Timing Presets (Derived from 414 Live Flows)

| Flow Type | Connection Wait | Message Spacing | Total Duration |
|-----------|----------------|-----------------|----------------|
| Standard | 3 days | 2-3 days | 14 days |
| Networking | 5 days | 4-5 days | 25 days |
| Product Launch | 2 days | 1-2 days | 8 days |
| Volume | 2 days | 3 days | 10 days |
| Event | 1 day | 2-3 days | 10 days |

## Branching Node Tree

Every GetSales flow has the same structure:

```
Trigger (profile filter)
  └→ Connection Request (with/without note)
      └→ Wait {N} days
          └→ Branch: Connection Accepted?
              ├→ YES path:
              │   └→ Message 1 → Wait → Message 2 → Wait → Message 3
              │       └→ Engagement actions between messages (like post, endorse)
              └→ NO path:
                  └→ Engagement action (profile view / like post)
                      └→ Wait
                          └→ Withdraw connection request
```

## Lead Validation

- Every lead MUST have a valid LinkedIn URL
- Format: `https://www.linkedin.com/in/{slug}`
- Validate before adding to flow
- Dedup by LinkedIn URL across all active flows
- Check against blacklist

## Rate Limits

| Action | Daily Limit | Why |
|--------|-------------|-----|
| Connection requests | 20-25 | LinkedIn's unwritten limit |
| Messages | 50-75 | Avoid restrictions |
| Profile views | 100-150 | Engagement warming |
| Post likes | 30-50 | Natural-looking activity |

## Activation Safety Gate

Before activating any flow, require exact confirmation: `"I confirm"`
This prevents accidental mass outreach.

## Contact Filtering for LinkedIn

From gathered contacts, filter for LinkedIn channel:
1. Must have LinkedIn URL (from Apollo data)
2. Must NOT already be in an active GetSales flow
3. Must NOT be in domain blacklist
4. Separate from email contacts (don't contact same person on both channels simultaneously)

## Output Format

```json
{
  "flow_type": "standard",
  "name": "Fintech PAYMENTS — LinkedIn Standard",
  "nodes": [
    {"type": "trigger", "filter": {"segment": "PAYMENTS"}},
    {"type": "connection_request", "note": "Hi {{first_name}}, noticed {{company_name}} is growing fast in {{city}}. Would love to connect.", "delay_days": 0},
    {"type": "wait", "days": 3},
    {"type": "branch", "condition": "accepted"},
    {"type": "message", "path": "accepted", "text": "Thanks for connecting...", "delay_days": 0},
    {"type": "wait", "path": "accepted", "days": 2},
    {"type": "message", "path": "accepted", "text": "By the way...", "delay_days": 0},
    {"type": "profile_view", "path": "not_accepted", "delay_days": 0},
    {"type": "wait", "path": "not_accepted", "days": 2},
    {"type": "withdraw", "path": "not_accepted", "delay_days": 0}
  ],
  "timing_preset": "standard",
  "max_leads_per_day": 25
}
```
