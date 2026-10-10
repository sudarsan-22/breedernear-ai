# BreederNear AI — Documentation

This folder is the single source of truth for **what** we are building, **why**, **how**, and **how it gets submitted** to the Google Cloud AI Builder Cup 2026 (JAPAC).

> Prototype submission deadline: **Sunday 18 Oct 2026, 11:59 PM IST**. Target: submit by **18 Oct, 12:00 PM IST**.

## Read in this order

| # | Document | Read it when |
|---|---|---|
| 1 | [event/01-event-overview.md](event/01-event-overview.md) | First. What the event is, dates, eligibility, prizes |
| 2 | [event/02-rules-dos-and-donts.md](event/02-rules-dos-and-donts.md) | **Before writing any code.** Everything that can get us rejected |
| 2b | [event/06-terms-compliance-matrix.md](event/06-terms-compliance-matrix.md) | Every T&C clause → what we do → status. Re-check schedule and team agreement. |
| 3 | [event/03-judging-strategy.md](event/03-judging-strategy.md) | Before deciding scope. How each judging criterion maps to BreederNear |
| 4 | [product/01-problem-and-vision.md](product/01-problem-and-vision.md) | The real-world problem and theme alignment |
| 5 | [product/02-requirements.md](product/02-requirements.md) | MVP scope, user stories, acceptance criteria |
| 6 | [product/03-responsible-ai-and-safety.md](product/03-responsible-ai-and-safety.md) | Before writing any prompt or tool |
| 7 | [implementation/01-architecture.md](implementation/01-architecture.md) | System design, Google Cloud services, repo layout |
| 8 | [implementation/02-agent-design.md](implementation/02-agent-design.md) | ADK agents, tools, schemas, guardrails |
| 9 | [implementation/03-data-model.md](implementation/03-data-model.md) | Firestore collections, Cloud Storage, seed data |
| 10 | [implementation/04-api-and-frontend.md](implementation/04-api-and-frontend.md) | HTTP endpoints and the web UI |
| 11 | [implementation/05-gcp-setup-and-deployment.md](implementation/05-gcp-setup-and-deployment.md) | Setting up Google Cloud and deploying to Cloud Run |
| 12 | [implementation/06-testing-and-evaluation.md](implementation/06-testing-and-evaluation.md) | Unit tests, ADK evals, pre-submission smoke test |
| 13 | [implementation/07-build-plan.md](implementation/07-build-plan.md) | Day-by-day plan to 18 Oct, owners, risks |
| 14 | [event/04-submission-checklist.md](event/04-submission-checklist.md) | Every day from 16 Oct onward, and before pressing Submit |
| 15 | [submission/01-pitch-deck-outline.md](submission/01-pitch-deck-outline.md) | When building the PDF deck |
| 16 | [submission/02-demo-video-script.md](submission/02-demo-video-script.md) | When recording the demo video |
| — | [event/05-kickoff-session-notes.md](event/05-kickoff-session-notes.md) | Reference: notes from the official explainer session |

## One-paragraph summary

*"The breeder is 50 metres away. The customer never finds them."* That's the founder's 5 years as a bird breeder and broker in Coimbatore, in one line.

BreederNear AI is an **agentic, trusted breeder-to-buyer pet commerce system** for India, entered under the **Retail & Commerce** theme. Five **Google ADK** agents on **Gemini** do the work:
- **Listing copilot:** a breeder's photos plus a WhatsApp-style Tamil/English message become a structured, fairly priced listing in under a minute.
- **Trust & compliance:** every listing is screened. Protected native species are blocked in code. Dyed birds, health signs, reused photos, price anomalies, scam language and missing dog-breeder registration are flagged. The result is an explainable trust score.
- **Buyer matching:** suitable pets, then trusted breeders nearby at fair prices.
- **Starter kit & care:** what to buy and a first-14-days care plan.
- **"Is this listing safe?":** buyers can check posts they saw in WhatsApp or Instagram groups.

It runs on **Cloud Run** with **Firestore** and **Cloud Storage**. The idea comes from the founder's earlier PetZonic startup work, but **all code here is new** (see rule R25).

## Status

| Area | Status |
|---|---|
| Registration | Done |
| Team formation (closes 11 Oct) | Done: 2 members (Sudarsan N, lead; Shreya Azad), both working professionals; final |
| "Prompt your jersey" activity | Done |
| Documentation | ✅ This folder |
| Prototype | Live: listing copilot (photos + English/Tamil text → screened listing), trust check for external posts, code-enforced BLOCKED for protected species (10 Oct). Buyer matching live (species shortlist by rules, nearby trusted listings, demo enquiries; 40 sample listings in Firestore). Starter kit with welfare-sized cages, 14-day care plan and demo cart live. Web app live: home, three modes, demo buttons, streaming chat, cards for every tool, photo upload, activity panel, cart and inbox; tested in a headless browser at 375 px and 1280 px (10 Oct). Next (decided 10 Oct): three-tab UI (Pets · Local Breeders + My farm · BreederNear AI) so new users can buy and sell by tapping, with AI on every screen; then rate limiting, evals, listing images |
| Deployment | ✅ Live on Cloud Run: https://breedernear-655711985039.asia-south1.run.app (10 Oct) |
| Deck / video | Not started |
| Submission | Not started |

Update this table as work progresses.
