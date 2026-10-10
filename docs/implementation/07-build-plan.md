# Build Plan: 9 Oct to 18 Oct 2026

**Team:** Sudarsan N (lead: agents, backend, deployment, domain expert for species, prices and trust rules) and Shreya Azad (seed data, UI and design, deck, video, testing). Adjust as you agree.

**Daily rule:** each day ends with (1) commits pushed, (2) a Cloud Run redeploy if code changed, (3) the status table in [../README.md](../README.md) updated.

**Owner actions from the [risk tracker](../event/02-rules-dos-and-donts.md#risk-tracker), not code, but they can disqualify us:**

| By | Who | Action |
|---|---|---|
| 10 Oct | Sudarsan | R25 clarification email to the organisers · R39 paste the submission-form fields · R10 join Discord |
| 11 Oct | Both | R8 no part-time course · R9 ID + employment proof ready · R29 check employment contracts for IP/moonlighting clauses · R28 re-read T&C |
| 12 Oct | Both / Sudarsan | R30 sign the team agreement · R32 make the public `petZonic` org profile private or neutral · R37 trademark quick-check |
| 15 Oct | Both | R41 passport validity · R28 re-read T&C |
| 17–18 Oct | Both | R38 consents for anyone or any animals filmed · R28 re-read T&C before submitting |

**Fresh-code rule:** nothing is copied from the earlier PetZonic platform repos: no code, UI designs, images, data or brand files. Ideas only. See [rules R25](../event/02-rules-dos-and-donts.md#risk-tracker).

## Day by day

| Date | Sudarsan | Shreya | End-of-day proof |
|---|---|---|---|
| **Fri 9 Oct** | GCP project, billing, APIs, Firestore, bucket, service account ([05](05-gcp-setup-and-deployment.md) §1–5). Repo skeleton, `requirements.txt` (pin `google-adk`), Dockerfile. **Deploy hello-world** with one Gemini call. Send the organiser clarification email (R25). | Confirm R8/R9 (eligibility). Join Discord. Start `districts.json`, `species.json`, `price_ranges.json` (with Sudarsan's numbers). | Live URL returns a Gemini reply |
| **Sat 10 Oct** | `breedernear_core`: config, schemas, services (Firestore, Storage, Gemini, images, geo), `safety/*` + unit tests. Seed script. | `protected_species.json` + `cites_species.json` with sources; `breeders.json`; `sawb_registry_sample.json`; first 20 listings. | `pytest` green; Firestore seeded |
| **Sun 11 Oct** | `listing_agent`: `extract_listing`, `update_draft`, `publish_listing` with screening + trust score. Works in `adk web`. | **Roster final (no action needed: 2 members).** Generate listing and product images; `products.json` (~50); remaining listings incl. demo cases. | Photo + text → draft → publish → trust result in `adk web` |
| **Mon 12 Oct** | `trust_agent` + `check_external_listing`; uploads API; root agent routing. | UI shell: home, mode switch, chat streaming via `/run_sse`, uploads with preview, draft card, trust card. | Breeder flow works on the live URL |
| **Tue 13 Oct** | `match_agent`: `recommend_species`, `search_listings`, `create_enquiry`. `/api/listings`, `/api/enquiries`. | UI: species cards, listing cards (badge, fair-price bar, distance), breeder inbox. | Buyer flow works on the live URL |
| **Wed 14 Oct** | `care_agent`: `build_starter_kit`, `care_plan`, cart. Callbacks; rate limiting; activity-panel data. | UI: product cards, care plan card, cart drawer, "Is this listing safe?" page, activity panel, mobile and accessibility pass. | **MVP feature freeze.** Full smoke test passes |
| **Thu 15 Oct** | Evals E01–E14 + golden images; fix failures. CI workflow. Stretch (F8 auto-reply / F10 Tamil replies) only if all green. | Manual smoke test on phone and laptop; log bugs. Make the sample scam screenshot and demo photos. Collect deck sources. Start deck. | Eval pass rate recorded |
| **Fri 16 Oct** | Bug fixes. **Final README pass** (live URL, real setup, eval results, simulated-vs-real). `ATTRIBUTIONS.md` complete. Secrets audit. | Deck draft complete ([outline](../submission/01-pitch-deck-outline.md)). Rehearse the video script. | README and deck reviewed by both |
| **Sat 17 Oct** | Final deploy (`min-instances=1`); record the revision; freeze `main`. | **Record and edit the video** (≤ 2:55); upload to YouTube (Unlisted). Export the deck PDF. | Checklist sections B–E all ticked |
| **Sun 18 Oct** | Final smoke test, 9–10 AM. | Fill in the submission form with Sudarsan. | **Submitted by 12:00 PM IST**; screenshot saved |

## Definition of done (per feature)

- [ ] Works on the **deployed** URL
- [ ] Unit tests for every rule it touches
- [ ] At least one ADK eval case covers it
- [ ] Works on a phone-width screen
- [ ] Simulated or sample data is labelled in the UI
- [ ] Committed with a clear message

## Cut list (if behind, cut in this order)

1. Stretch F8–F11
2. Breeder inbox (keep enquiry creation + confirmation only)
3. Cart (keep starter-kit cards + total)
4. Activity panel styling (plain list)

**Never cut:** deployment, listing copilot, trust screening with BLOCKED species, buyer matching with trust badges, "Is this listing safe?", README accuracy, video, deck.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Organisers consider the entry part of the earlier PetZonic project | Low (organisers confirmed startups are allowed, 10 Oct) | **Disqualification** | Fresh code only; written clarification from the organisers received (R25); deck presents the founder's experience, not the old platform |
| Billing/credits not ready | Medium | Blocks deploy | Do it first on day 1 |
| Model ID wrong or unavailable | Medium | Blocks AI | Day-1 hello-world; `GOOGLE_CLOUD_LOCATION=global`; model in an env var |
| ADK API differs from docs | Medium | Slows dev | Pin the version; check `adk --help` and the installed source |
| Gemini species ID unreliable for similar birds | Medium | Wrong trust result | Combine vision with text; protected decision on text **or** vision; demo with clear photos; golden-image tests |
| Getting realistic bird/dog photos legally | Medium | Weak demo | Own photos (Sudarsan's aviary contacts, with permission) or Gemini-generated images; log in ATTRIBUTIONS |
| In-memory sessions lost on restart | Low | Chat resets | `min-instances=1`, `max-instances=1`; business data in Firestore |
| Portal trouble near the deadline | Medium | Missed deadline | Submit by 12:00 PM on 18 Oct |
| Credits expire during evaluation | Low | App down | Check expiry; budget alert; weekly check |
| One person unavailable | Medium | Delay | Daily push; docs; cut list |
