# Card Fee Check engine: what it should be (draft 2026-10-03)

Status: draft for Alex. Picks used where he said "you know the answers": runs on his laptop, statements dropped into a folder by hand, Python.

## What it is
A small internal program that turns one UK card-processing statement into one finished plain-English report. Only Alex uses it. Customers never log in or see it. The service Alex sells is the finished report. The engine is just how he makes it quickly.

**Guard rail (standing rule):** no customer screens, accounts or dashboards. If a step needs one, stop and re-check against the Sequoia autopilot rule.

## The flow
```
statement PDF -> 1 READ -> 2 CHECK -> 3 WRITE -> 4 ALEX APPROVES -> report PDF sent by Alex
```

1. **READ (AI).** The AI extracts a fixed list of fields from the PDF into a simple data file (JSON). It does no maths and no judging.
   - Total card sales and number of transactions
   - Each fee line: name, amount, rate or unit
   - Plan type if stated (flat, tiered, cost-plus)
   - Terminals and monthly fees
   - Statement month, provider name, contract end date if shown
   - Anything it could not read (flagged, never guessed)
2. **CHECK (plain code, no AI).** Same input always gives the same output. It produces:
   - Effective rate: total charges / total sales
   - Charged rate vs agreed rate where both appear
   - Duplicate or repeated small fees (statement, gateway, admin, terminal rental)
   - Penalty fees (for example PCI non-compliance) and whether they can be avoided
   - Lines that do not add up to the stated total
   - Plan-type flags: one flat rate on all cards, provider-chosen bands
   - Fair-price estimate from the price table (below), with the yearly gap = monthly x 12
   - A verdict: "overpaying", "fine", or "mostly fine, small room"
3. **WRITE (AI).** The AI turns the CHECK results into the report text. It may only use numbers from step 2 and must not recalculate. Required parts:
   - One-line answer at the top ("You pay about X a year more than a fair deal" or "You're mostly fine")
   - The numbers in a small table
   - What each finding means in plain words
   - What to ask the provider for, with yearly savings marked **illustrative, not a quote**
   - What happens next (nothing unless the practice replies)
   - Honesty rule: if the practice is fine, the report says so.
4. **ALEX APPROVES.** Alex reads every report, compares it with the statement, fixes anything, and sends it. Nothing goes out automatically. He records the minutes spent per report (the one number from the EMCap playbook).

## Reference price table (a file, not an agent)
A small file Alex builds once and updates occasionally:
- UK card interchange caps (0.2% consumer debit, 0.3% consumer credit)
- Typical fair all-in rates by plan type and monthly sales band
- Typical provider margins and common extra fees
- Source and date for every value, so reports can say "assumed rate, not a quote"

## Folder layout
```
engine/
  inbox/        statements dropped here
  working/      extracted data and check results per statement
  reports/      finished reports for Alex to review
  reference/    price table
  tests/        the sample statements and answer key
```

## How we know it works
- The 7 fake statements in /mnt/project-files/samples are the test set. Pass = all key numbers match the answer key exactly (effective rate, yearly cost, flagged fees) and the verdict is right.
- Note: answer-key-SAMPLE.md covers only 5 of the 7 PDFs (Riverside, Oakfield, Elm Street, Hollybush, Maple Smiles). Willow Court and Brightwater need answers written before they count as tests.
- Before any real practice: also test one messy case (photographed statement, redacted lines) and confirm unreadable fields are flagged, not guessed.

## Build order (small, time-boxed)
1. Price table file and the answer key for all 7 samples.
2. CHECK code, tested on hand-typed data (no AI yet).
3. READ step, tested on the 7 PDFs.
4. WRITE step and report template.
5. Run all 7 end to end, then one real statement.

## Safety items (brief, not blockers)
- Statements are business data: keep files local, delete after the agreed period, say so on the website (UK GDPR).
- Keep "no commission from any provider" true.
- Before charging for anything later, get the short AML-scope check noted in research/dental-services.md.

## Out of scope for Stage 0
Customer logins, dashboards, payments, automatic sending, supplier/lab bill check (second service), reconciliation, associate pay.
