# How AI-native services present themselves on the web (researched 2026-10-01)

Question: SaaS = landing page, sign up, log in, use the tool. Agency = landing page, book a call, onboarding. What should a business that sells the *finished outcome* (Sequoia "autopilot") look like on the web? Is there an established playbook?

## Short answer
- **No established playbook yet.** The written guidance (Sequoia, EMCap's "AI-native services" guide, YC's talk) is about the business model, not the website. The closest thing to a rule is EMCap's "It's the demo, stupid": show the finished result. (EMCap: https://www.emcap.com/ai-native-services)
- Looking at real sites, AI-native services do **not** look like SaaS. They look like a **modern professional firm with a very short intake**: headline = outcome, button = "get started / get a quote / upload", humans + AI do the work, result comes back finished.
- **Login appears only later**, once there is an ongoing relationship (a dashboard to track recurring work). It is never the first step.

## The sites (checked 2026-10-01, homepages only)

| Company | What they sell | Main button | How work comes in | How the result comes back | Login? |
|---|---|---|---|---|---|
| Crosby (AI law firm, US) | Contract review, "under an hour" | Get started | Sign-up, then send contracts | Reviewed contract, by real lawyers | Not on homepage |
| Garfield.law (AI law firm, UK) | Debt recovery for SMEs | Get started for free | Upload invoices or link accounting software | Letters sent for you, money recovered, status dashboard | Yes, for tracking claims |
| Lawhive (UK) | Legal work via solicitors + AI | Get a quote | Short question form, then call or callback | Solicitor handles the matter | No |
| Harper (US insurance broker) | Business insurance | Get a quote now | Multi-step form or phone | Quotes explained in plain words, they do enrolment | No |
| Pilot (US) | Bookkeeping, "50/50 people and software" | Talk to our team | Consultation or trial | Monthly books done for you | Yes, existing clients |
| Hanover Park (US) | Fund admin | Request demo | Demo request | Accountants review AI-prepared work, dashboards | Yes |
| EvenUp (US) | Injury-law demand letters | Schedule demo | Plugs into firm's case system | Drafted documents | Yes (has drifted toward a platform) |
| Merchant Cost Consulting (US) | Card fee cutting, paid from savings | Book consultation + free audit form | Form with optional statement upload | Audit in 1-2 days, then they negotiate | No |
| BoonPay (UK) | Free card statement review | Form | Upload statement (PDF/photo), can redact | Plain-English report by email in 48h | No |
| Unique Payments (US) | Free statement "report card" | Drag-and-drop | Upload PDF, no account, no call | PDF report in ~60 seconds, optional call | No |
| Property firm test (from side-launch-playbooks.md) | Free rental analysis | One-field form | One field | Personalised analysis | No, leads went 1-3/month to 10+ |

## Three shapes that keep showing up
1. **"Talk to us"** (Pilot, Hanover Park, EvenUp). Big-ticket B2B. Looks like an agency with a client portal. Fits large, ongoing contracts. Not right for a free Stage 0 offer.
2. **"Get a quote" form** (Lawhive, Harper, Crosby). Short intake form, then a human + AI do the job. Fits work that varies case by case.
3. **"Send us the thing, get the finished result"** (Garfield, BoonPay, Merchant Cost Consulting, Unique Payments, the property test). One form, one upload, result back by email. **Best fit for small businesses and for a free outcome.**

## What they all share
1. Headline names the outcome, not the technology ("Stop chasing, start recovering").
2. Heavy trust signals: real experts check the work, regulated status, numbers of clients, testimonials, data security.
3. Clear "what you get" and "how fast".
4. Fixed or outcome-based price, or free.
5. AI is mentioned as *how* it is fast, never as the thing being sold.

## Direct competition found (worth knowing)
- **BoonPay (UK)**: free statement review, 48h, by email. Paid by introduction fees when you switch provider. Not dental-specific.
- **Unique Payments (US)**: instant AI report card, no account. Has a dental testimonial. US processors only.
- **Your edge**: dental-only, fully independent (no introduction fees, says so plainly), a person reads every report, and public write-ups of what you find. Warning: an instant self-serve analyser like Unique Payments is a *tool*. Don't copy that part.

## Recommended page for the dental card fee check (Stage 0)
One page on its own domain. No login, no sign-up, no "book a call".

1. **Headline**: "Find out what your practice really pays to take card payments. Free plain-English report in 48 hours."
2. **The sample report**: show the Riverside sample (samples/riverside-dental-card-statement-SAMPLE.pdf turned into a report). This is the "demo".
3. **How it works, 3 steps**: upload last month's card statement, Alex checks it (AI does the reading, a person checks every number), report lands in your inbox.
4. **The form**: name, practice name, email, statement upload. Note that they can black out bank details.
5. **Why trust it**: dental only, independent, no commission from any provider, who Alex is (fintech engineer, own name), what happens to the file (deleted after X days).
6. **What we keep finding**: short anonymised findings, links to the X posts and blog. This is the public build log.
7. **FAQ**: is it really free, why, what you need, what happens next (nothing unless you reply).

Later (not now): one blog page per common question for search; monthly re-check by email for practices who come back; a login only if there is ever ongoing work that needs one.

Safety items (brief): add a short privacy note since statements are business data (UK GDPR); keep the "no commission" claim true.

## Update 2026-10-01: EMCap playbook (Alex's pick, "tremendously helpful")
Sources: https://www.emcap.com/thoughts/the-ai-native-services-playbook and https://www.emcap.com/thoughts/why-ai-native-services-and-why-now
EMCap says it outright: "the true playbook is being written in real-time" (the model "wasn't really possible until 2023"). Their 9 rules are team, product-market fit, delivery, roadmap, go-to-market, pricing, defensibility, metrics and M&A. These apply to us now:
1. **Customers buy you.** Domain expertise is non-negotiable (Harper's founders came from insurance families). For us: Alex's own name and his payments know-how go near the top of the page, not hidden in the footer.
2. **"It's the demo, stupid."** Show the work happening, not a pitch (Mechanical Orchard cut sales cycles by more than half this way). For us: the sample report, plus a short screen recording of a real (anonymised) statement turning into a report. Show the finished report, not a tool to play with.
3. **One number for how much the AI does.** Crosby tracks human review time per document. For us: minutes Alex spends per report. Post it every week. It is ready-made build-in-public content.
4. **Learn from every job.** Each report should make the next one faster and better. For us: one line in the privacy note asking permission to keep anonymised fee data and use it to improve future reports.
5. **Partners for reach, but own the customer.** Later, dental accountants or practice-manager groups could send practices our way, while the report and the relationship stay with us.
Not now (Stage 0): pricing models, "fake product-market fit" warnings, margins, M&A.
