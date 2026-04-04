# /outreach — Generate & Launch Outreach Sequences

Generate email and/or LinkedIn sequences and push to campaign platforms.

## Arguments
- `--channel email|linkedin|both`: Channel selection (default: email)
- `--project <name>`: Project to use
- `--sequence-file <path>`: Use sequence from file instead of generating

## Email Path

### 1. Load Context
- Project offer, segments, target roles
- Qualified companies + extracted contacts
- Any user feedback on sequences

### 2. Generate Sequence
**Skill**: email-sequence

- Generate 4-5 step sequence following 12-rule checklist
- Apply user feedback (highest priority)
- If `--sequence-file`: read file, normalize variables, validate against checklist

### 3. User Approval
Present each email: subject, subject_b, body, day
Ask: "Approve this sequence?"
- If feedback → regenerate with adjustments
- If approved → proceed

### 4. Email Account Selection
Ask: "Which email accounts?" 
- "all with rinat" → search local data, find matching accounts
- "use account 17062361" → use specific ID
- Present: "14 accounts matched. Confirm?"

### 5. Push to SmartLead
- Call `smartlead_create_campaign` (DRAFT)
- Call `smartlead_set_sequence` with generated steps
- Call `smartlead_add_leads` with contacts:
  - Verified emails only
  - Dedup against blacklist
  - Include custom fields: company_name, segment, city
- Send test email to user's email

### 6. Present Results
ALL 4 items:
1. SmartLead campaign link
2. CRM contacts link (filtered by campaign)
3. "Check your inbox at {email}"
4. "Type 'activate' to launch"

### 7. Activation
On "activate" / "launch" / "go live":
- Require exact confirmation
- Set campaign status → ACTIVE
- Enable reply monitoring
- Mention: "Reply monitoring is ON. I'll classify incoming replies."

## LinkedIn Path

### 1. Load Context
Same as email path

### 2. Filter Contacts for LinkedIn
- Must have LinkedIn URL
- Not in active GetSales flow
- Not in blacklist
- Separate from email contacts

### 3. Generate Flow
**Skill**: linkedin-sequence

- Select flow type based on context
- Generate messages + timing

### 4. User Approval + Push to GetSales
- Call `getsales_create_flow`
- Call `getsales_add_leads`
- Require "I confirm" before activation

## Both Channels
- Split contacts: email-verified → email, LinkedIn URL → LinkedIn
- Don't contact same person on both channels simultaneously
- Generate both sequences, present together for approval
