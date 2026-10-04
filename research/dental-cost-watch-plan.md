# The plan: Dental Cost Watch (draft 2026-10-03)

## The idea in one line
A monthly cost watch for independent UK dental practices. They send their bills, you send back one page: what is too high, what changed, what renews soon, and what to ask for. AI-native payments and cost work, starting with dental.

## Why this and not a tool
- You sell the finished result (a checked page of findings), not software. Customers never log in. (Sequoia "autopilot".)
- It is ongoing work across many bills, not a one-off report. That is what makes it bigger than a card-fee check.
- Accountants only benchmark once a year; none of the three I checked advertise negotiating prices. (research/dental-procurement-biggest-version.md)

## Where we are today
- Chosen niche and service: dental, card fee check first.
- A working first version of the engine is in `engine/`. It passes 32 of 32 checks on the 7 sample statements.
- One-page website structure decided: no login, no "book a call", sample report plus an upload form. (research/ai-native-service-websites.md)
- Strategy: free and public for now, no selling. Post openly under your own name.

## Phases

### Phase 1: make the card check real (now)
1. Add the AI reader to the engine so real statements work. Needs an API key from you.
2. Replace the assumed price table with real, dated numbers.
3. Confirm the expected answers for the Willow Court and Brightwater samples.
4. Add the AI report writer (it may only use numbers from the check code). You read every report before it goes out.

### Phase 2: one-page site and public posting
1. Domain plus one page: headline, sample report, 3 steps, upload form, why trust it, FAQ.
2. Short privacy note (statements are business data).
3. Post what you find under your own name, framed as payments insights ("what I found in 10 UK card statements").
4. Track one number: minutes you spend per report. Post it weekly.

### Phase 3: first free jobs
1. Do the first 3-5 reports by hand with the engine, for practices that find you.
2. Keep a log of what each one taught you, with names removed.

### Phase 4: add lab invoices
1. Lab work is the largest and least served cost line (about 6.6% of income in private practices).
2. Test with 3-5 real lab invoices before promising anything. UK lab price evidence is thin, so measure it.
3. Then consumables, energy, service contracts.

### Phase 5: the monthly watch
1. Practices who liked the first report send bills every month.
2. Each month you send the one-page summary: changes, renewals, what to ask for.
3. Only now think about pricing and about whether to act on their behalf.

## Safety checks (brief, not blockers)
- Your work contract: outside work, IP, conflict of interest. (Noted as checked and fine.)
- Statements and invoices are business data. Keep files local, delete after the agreed time, say so on the site.
- Do not take commission from anyone you recommend.
- Do not take fees for compensation claims against suppliers or processors.
- Before charging for anything: short check of HMRC money-laundering registration scope, and FCA scope for anything about finance or claims.

## Not now
Customer logins or dashboards, pricing and selling, payments, automatic sending of reports, billing and revenue-cycle work (parked, see below), reconciliation and associate pay.

## Open questions
1. Is billing and revenue cycle work worth a proper look? First impression: mostly US, sensitive health data, well-funded rivals. Not researched yet.
2. Does a monthly cost watch light you up more than the card check alone? You said the card check alone did not.
3. Which of the first 3-5 practices will find you without you contacting anyone? The public posts decide this.

## Next three steps
1. Say yes to the AI reader and give me the API key location you want to use.
2. Confirm the two sample answers I wrote (Willow Court, Brightwater).
3. Pick the domain name for the one-page site.
