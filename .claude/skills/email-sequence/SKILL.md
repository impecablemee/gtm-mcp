# Email Sequence Generation Skill

Generate 4-5 step cold email sequences optimized for reply rate. This skill replaces campaign_intelligence.py and its GOD_SEQUENCE system.

## When to Use

- After pipeline gathers enough contacts (KPI met)
- User says "generate sequence" or "create emails"
- During /outreach command
- When reviewing/improving existing sequences

## THE 12-RULE SEQUENCE CHECKLIST

Every generated sequence MUST pass ALL 12 rules. If any rule fails, regenerate.

### Rule 1: Personalization in EVERY Email
`{{first_name}}` must appear in subject OR body of EVERY email. No exceptions.

### Rule 2: Geo Case Study
`{{city}}` used in at least 1 email for social proof.
Example: "We helped a {{city}}-based fintech save $4,000/month"

### Rule 3: Specific Numbers
At least 2 emails must contain quantified metrics: dollar amounts, percentages, time savings.
BAD: "We save companies money"
GOOD: "We cut payroll costs by 40% — $4,000/month for a 50-person team"

### Rule 4: Competitor Positioning
Mention alternatives (Deel, Upwork, etc.) in at least 1 email.
Shows you know the market. Positions against known options.

### Rule 5: Distinct Intent Per Email
No 2 emails can have the same purpose:

| Email | Intent | Length |
|-------|--------|--------|
| 1 | Hook + value prop + geo case study with numbers | ~100 words |
| 2 | Competitor comparison + bullet-point benefits (3-5) | ~100 words |
| 3 | Transparent pricing + social proof numbers | ~80 words |
| 4 | Ultra-short, channel switch (LinkedIn/Telegram), casual | 2-3 lines |
| 5 (optional) | Breakup — brief, respectful, no pressure | 2-3 lines |

### Rule 6: Subject Lines
- At least 2 subjects must include `{{first_name}}`
- Email 1 subject: uses `{{first_name}}`
- Email 3 subject: uses `{{company_name}}`
- A/B testing: each email gets subject + subject_b (alternate personalization)

### Rule 7: Reply-Thread Subjects
Emails 2-4 have EMPTY subject ("") to maintain reply thread in inbox. Only Email 1 has a real subject.

### Rule 8: Banned Phrases
NEVER use:
- "I hope this message finds you well"
- "I hope this email finds you well"
- "Just following up"
- "Just checking in"
- "Touching base"
- Any variant of the above

### Rule 9: No Identical Closings
Each email must have a different closing/CTA. Examples:
- "Worth a 15-min call?" (Email 1)
- "Shall I send a comparison sheet?" (Email 2)
- "Want me to run the numbers for {{company_name}}?" (Email 3)
- "Open to connecting on LinkedIn?" (Email 4)

### Rule 10: HTML Formatting
Use `<br><br>` between paragraphs (SmartLead renders HTML).
No `\n` — use `<br>` tags only.

### Rule 11: Max 120 Words Per Email
Each email must be under 120 words. Shorter emails get higher reply rates.
Email 4 should be 2-3 lines max.

### Rule 12: SmartLead Merge Tags Only
Valid variables: `{{first_name}}`, `{{last_name}}`, `{{company_name}}`, `{{city}}`, `{{signature}}`
Double curly braces. No other variable formats.

## Reference Sequence (4% Reply Rate)

This is the benchmark — Petr's EasyStaff Australia campaign (ID 3070919):

**Email 1 (Day 0)**: Hook + geo case study
- Subject: "{{first_name}}, quick question about {{company_name}}"
- Body: Hook about contractor payments in {{city}}, specific savings ($4,000/month for 50 contractors), soft CTA
- Subject_b: "Growth challenge at {{company_name}}"

**Email 2 (Day 3)**: Competitor comparison
- Subject: "" (reply thread)
- Body: "Unlike Deel or Upwork..." + 3-5 bullet benefits with specific numbers
- Subject_b: ""

**Email 3 (Day 4)**: Transparent pricing
- Subject: "" (reply thread)
- Body: Exact pricing ($39/contractor, 3% fee, custom rates for 50+), social proof
- Subject_b: ""

**Email 4 (Day 7)**: Ultra-short channel switch
- Subject: "" (reply thread)
- Body: 2-3 lines max, casual tone, "Sent from my iPhone" vibe, suggest LinkedIn/Telegram
- Subject_b: ""

**Default Timing**: [0, 3, 4, 7, 7] days between emails

## Sequence Output Format

```json
{
  "name": "Pipeline Pain — {segment}",
  "steps": [
    {
      "step": 1,
      "day": 0,
      "subject": "{{first_name}}, quick question about {{company_name}}",
      "subject_b": "Growth challenge at {{company_name}}",
      "body": "Hi {{first_name}},<br><br>I noticed {{company_name}} is scaling in {{city}}...<br><br>We helped a similar team cut costs by 40%...<br><br>Worth a 15-min call?<br><br>{{signature}}"
    },
    {
      "step": 2,
      "day": 3,
      "subject": "",
      "subject_b": "",
      "body": "Unlike Deel or Upwork, we...<br><br>- Benefit 1 with number<br>- Benefit 2 with number<br>- Benefit 3 with number<br><br>Shall I send a comparison?<br><br>{{signature}}"
    }
  ],
  "cadence_days": [0, 3, 4, 7, 7],
  "settings": {
    "tracking": false,
    "stop_on_reply": true,
    "plain_text": true,
    "daily_limit_per_mailbox": 35
  }
}
```

## User Feedback Integration

User feedback on sequences has HIGHEST PRIORITY:
- "Make it more casual" → adjust tone
- "Don't mention competitors" → remove Rule 4 for this sequence
- "Add a LinkedIn step" → add channel switch email
- "Use this approach from my file" → read file, adapt style

Store feedback and apply to ALL future sequence generations for this project.

## Campaign Settings (SmartLead Defaults)

| Setting | Value | Why |
|---------|-------|-----|
| tracking | false | Improves deliverability |
| stop_on_reply | true | Don't spam responders |
| plain_text | true | Higher inbox rate |
| daily_limit_per_mailbox | 35 | Safe sending volume |
| schedule | Mon-Fri 9:00-18:00 | Target's local timezone |
| timezone | Auto-detect from contacts' location | Per-country mapping |

## 23-Country Timezone Mapping

| Country | Timezone |
|---------|----------|
| United States | America/New_York |
| United Kingdom | Europe/London |
| Germany | Europe/Berlin |
| France | Europe/Paris |
| Australia | Australia/Sydney |
| Canada | America/Toronto |
| India | Asia/Kolkata |
| Singapore | Asia/Singapore |
| UAE | Asia/Dubai |
| Israel | Asia/Jerusalem |
| Japan | Asia/Tokyo |
| Brazil | America/Sao_Paulo |
| Mexico | America/Mexico_City |
| Netherlands | Europe/Amsterdam |
| Sweden | Europe/Stockholm |
| Switzerland | Europe/Zurich |
| Italy | Europe/Rome |
| Spain | Europe/Madrid |
| Poland | Europe/Warsaw |
| Turkey | Europe/Istanbul |
| South Korea | Asia/Seoul |
| Thailand | Asia/Bangkok |
| Nigeria | Africa/Lagos |

## Document-Provided Sequences

If the strategy document includes email sequences:
1. Preserve EXACT text from document
2. Normalize variables to SmartLead format
3. Validate against 12-rule checklist
4. Present to user: "Document includes a sequence. Use as-is or generate new?"
