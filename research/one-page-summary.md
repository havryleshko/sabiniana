# Dental Cost Watch: the one-page summary (2026-10-03, verified against sources the same day)

## 1. The problem
**Independent UK dental practices pay many bills every month, and nobody checks whether those bills are fair, whether they crept up, or when they renew.** Costs are rising faster than income, so every unchecked bill eats margin.

## 2. Main points
1. **Costs are rising faster than income.** Lab fees are up 16.5%, staff up 15% and utilities up 10%, against a 4% NHS contract uplift. NHS dental funding is down about 16% in real terms since 2014/15.
2. **The non-staff bills are large.** In private practices, lab is about 6.6% of income and materials about 7.5%. On a typical mixed practice (about £926k a year, 2023 benchmarking survey), that is roughly £61k on lab and £69k on materials.
3. **Prices vary a lot.** UK labs' public price lists show e.max crowns at £85, £90 and £145, and zirconia implant crowns at £125 versus £330. These are not like-for-like, but the gap is worth checking.
4. **Nobody checks monthly.** Accountants benchmark costs once a year, and none of the three checked advertise negotiating prices. Buying groups are free but are paid by the suppliers they recommend. Free card fee reviews we found are run by firms paid when the practice switches provider (for example BoonPay).
5. **Small businesses don't shop around.** The payments regulator found card acquiring services "do not work well for small and medium-sized merchants", and many "do not regularly (if ever) search for providers".
6. **Renewals cost money.** Out-of-contract business electricity averages 38p/kWh against 26p on a fixed deal (vendor figure). There is no price cap on business energy.
7. **The market is real and moving private.** England has 10,160 dental practices. The share offering NHS general dentistry fell from 64.6% to 55.6% between 2017 and 2026, and over 1,000 more practices now run without a general NHS contract. About 80% of UK practices do private work, and 86% are single-site.

## 3. Evidence strength (be honest)
| Claim | Strength |
|---|---|
| Practice count, NHS-to-private shift | Strong: Nuffield Trust analysis of CQC and NHSBSA data, 2026 |
| Cost lines as % of income | Strong: NHS Digital / NASDAL (2019/20, older) |
| Costs rising faster than income | Medium: BDA figures quoted in an article (July 2025) |
| UK lab price spread | Medium: real public price lists, but not like-for-like |
| Small merchants don't shop for card deals | Strong: payments regulator |
| £ saved per practice | **Weak:** only vendor claims and our sizing (a few £k to maybe £15k a year) |
| Owners care enough to send their bills | **Unknown:** no survey; the public free offer will test it |
| Your 3,300-3,800 private-only figure | Unverified source; plausible for England alone |

## 4. What we focus on (our territory)
**Make sure a practice never overpays for what it buys, and never gets caught by a renewal.**

Each month the practice sends its bills, and we send back one page that answers four questions:
1. What changed since last month?
2. Which bills are too high, and by how much a year? (always "illustrative, not a quote")
3. What renews in the next 90 days?
4. What exactly should they ask each supplier for?

Bills we watch, in this order: card fees, then lab, then consumables, energy, service contracts, software.

**Not ours:** bookkeeping and associate pay (accountants, likely money-laundering registration), patient payments (patient data), staff costs, NHS contract rules, tax, compensation claims, and US-style billing and claims work.

## 5. What we build
**An internal engine, not an app.** Customers never log in. They send documents and get a finished page.

| Step | What it does | Status |
|---|---|---|
| Read | AI turns a bill (PDF) into numbers | Claude Sonnet 5.5 copies the printed fields from the PDF. It does not calculate. On the 30 sample PDFs, the checker then returns the same finding codes as the hand-typed answer key. |
| Check | Plain code does all the maths: effective rate, charged vs agreed, duplicates, extra fees, renewals, fair price | Hand-typed card statements: effective rate, line total, repeated small fees, PCI non-compliance, charged vs agreed, and a comparison with the PSR's 2015–2018 observed average merchant service charge. That average is not a fair price. Hand-typed lab, energy, supplies, and service bills use the figures printed on the document: invoice maths, a duplicated lab case, a remake inside the lab's own free window, VAT on lab work (Value Added Tax Act 1994, Schedule 9, Group 7, item 2A), courier and surcharge lines, a printed percentage rise, out-of-contract and rollover energy, a fixed contract ending within 90 days, an estimated meter reading, small-order extras, a service-plan renewal rise, and a charge for decommissioned equipment. The yearly gap and the verdict stay incomplete. |
| Write | AI writes the plain-English page, using only the checked numbers | v0 is a template |
| Approve | You read every page before it goes out | Manual, by design |

Checks still blocked on a source and a date: a lab price list, an energy unit-rate comparison, and service-plan prices. The ranges in the sample answer key point at a deleted research note, MoneySuperMarket, and The Probe.

**Also build:** a one-page website on its own domain (headline, sample report, 3 steps, upload form, why trust it, FAQ). No login, no "book a call".

## 6. How we test it (without asking anyone)
1. Post the free offer publicly under your own name, framed as payments insights.
2. Measure how many practices send a statement, and how many come back with a second bill.
3. Track one number every week: minutes you spend per report.

## 7. Next three steps
1. Add the AI reader to the engine (you provide an API key).
2. Replace the assumed price table with real, dated numbers.
3. Pick a domain and put up the one-page site.

## Sources (all in the project folder)
research/card-fee-check-engine-spec.md, engine/README.md
