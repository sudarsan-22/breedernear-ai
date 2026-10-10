# Build Plan: 9 Oct to 18 Oct 2026

**Team:** Sudarsan N (lead: agents, backend, deployment, domain expert for species, prices and trust rules) and Shreya Azad (seed data, UI and design, deck, video, testing). Adjust as you agree.

**Daily rule:** each day ends with (1) commits pushed, (2) a Cloud Run redeploy if code changed, (3) the status table in [../README.md](../README.md) updated.

**Owner actions from the [risk tracker](../event/02-rules-dos-and-donts.md#risk-tracker), not code, but they can disqualify us:**

| By | Who | Action |
|---|---|---|
| 10 Oct | Sudarsan | ✅ R25 clarification email (organisers replied: startups allowed) · R39 paste the submission-form fields · R10 join Discord (✅ Sudarsan; Shreya pending) |
| 11 Oct | Both | ✅ R8 no course · ✅ R9 ID + employment proof ready · ✅ R29 employment contracts checked (all confirmed 10 Oct) · R28 re-read T&C |
| 12 Oct | Both | R30 sign the team agreement · ✅ R32 old org profile private (9 Oct) · ✅ R37 name check (10 Oct) |
| 15 Oct | Both | R41 passport validity · R28 re-read T&C |
| 17–18 Oct | Both | R38 consents for anyone or any animals filmed · R28 re-read T&C before submitting |

**Fresh-code rule:** nothing is copied from the earlier PetZonic platform repos: no code, UI designs, images, data or brand files. Ideas only. See [rules R25](../event/02-rules-dos-and-donts.md#risk-tracker).

## Day by day

**Progress note (10 Oct):** the backend, all five agents, the sample data and a chat-based web app were finished on 9–10 Oct, ahead of the original plan. On 10 Oct the UI was redesigned to **three tabs** (Pets · Local Breeders + My farm · BreederNear AI) so new users can buy and sell by tapping, with AI built into each screen ([04](04-api-and-frontend.md#frontend-web)). The plan below reflects that.

**Progress note (10 Oct, evening):** Sudarsan's engineering items for 11–14 Oct are already done and live: the three tabs, the sell form, "Is this post safe?", the quiz, listing photos, separate customer and seller accounts with two preloaded demo accounts, the agent evals run 3×, the photo-accuracy test ([06 §2b](06-testing-and-evaluation.md#2b-photo-screening-accuracy-gemini-vision-real-model)) and the accessibility audit ([06 §2c](06-testing-and-evaluation.md#2c-accessibility-axe-core-headless-chromium)). Still to do: fixes from Shreya's first-time-user test (13 Oct), doc cleanup, the final README pass with screenshots, deck support, and the 17 Oct freeze. Shreya's column is unchanged.

| Date | Sudarsan | Shreya | End-of-day proof |
|---|---|---|---|
| **Fri 9 Oct** ✅ | GCP project, billing, APIs, Firestore, bucket, service account; repo skeleton; Cloud Run deploy; organiser email | Eligibility checks; Discord | Live URL returns a Gemini reply |
| **Sat 10 Oct** ✅ | Core services, safety rules and trust score; all five agents (listing, trust, match, care, concierge); 40 sample listings, 16 breeders, 45 products; chat web app with cards, uploads, cart, inbox; 158 unit tests; CI | Review price ranges, cage sizes and care facts with Sudarsan | Every agent flow works on the live URL |
| **Sun 11 Oct** | Three-tab shell, district picker, first-visit welcome card. **Pets** tab: grid + filters, listing page, Contact form, starter kit + care plan on the page. APIs: `/api/pets`, `/api/starter-kit`, `/api/care-plan`. **Rate limiting** on all AI routes. | Eligibility owner actions (R8, R9, R29). Try the Pets tab on a phone; log confusing spots. Collect demo photos (own birds, with consent). | Buyer can find, inspect and contact without chat on the live URL |
| **Mon 12 Oct** | **Local Breeders** directory + breeder page. **My farm**: sell form with "✨ Fill with AI", per-field validation, Publish with trust check, My listings, Enquiries. APIs: `/api/breeders`, `/api/sell/*`. | Team agreement (R30). Listing and product images (generated or own photos) + attributions. Sample scam screenshot. | Seller can list by tapping in ≤ 60 s on the live URL |
| **Tue 13 Oct** | "Is this post safe?" form (`/api/check`), "Which pet suits me?" quiz (`/api/recommend`), "Ask AI about this pet" deep link into the AI tab. Wire listing images (turns on the reused-photo demo case). | **First-time-user test:** someone who hasn't seen the app tries all three tabs; note where they get stuck. | All three tabs complete |
| **Wed 14 Oct** | Fixes from the user test. Evals E01–E14 + `scripts/smoke_test.py` + headless-browser UI test in the repo. Accessibility pass. | Phone + laptop smoke test; log bugs. Start the deck. | **MVP feature freeze.** Full smoke test passes |
| **Thu 15 Oct** | Eval failures; callbacks; stretch only if all green. | Deck sources and screenshots; rehearse the video script. | Eval pass rate recorded |
| **Fri 16 Oct** | Bug fixes. **Final README pass** (live URL, real setup, eval results, simulated-vs-real). `ATTRIBUTIONS.md` complete. Secrets audit. | Deck draft complete ([outline](../submission/01-pitch-deck-outline.md)). | README and deck reviewed by both |
| **Sat 17 Oct** | Final release: `MIN_INSTANCES=1 scripts/release.sh` (tests, deploy, smoke test, demo-data reset, logged in [03-release-log](../submission/03-release-log.md)); freeze `main`. | **Record and edit the video** (≤ 2:55); upload to YouTube (Unlisted). Export the deck PDF. | Checklist sections B–E all ticked |
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
2. "Which pet suits me?" quiz in the Pets tab (the AI tab already does it)
3. Breeder pages (keep the directory cards with their pets listed inline)
4. Cart (keep starter-kit cards + total)
5. Activity panel styling (plain list)

**Never cut:** deployment, the three tabs with the welcome card, Pets grid + listing page + Contact, My farm sell form with "Fill with AI", trust screening with BLOCKED species, "Is this post safe?", the AI tab, README accuracy, video, deck.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Organisers consider the entry part of the earlier PetZonic project | Low (organisers confirmed startups are allowed, 10 Oct) | **Disqualification** | Fresh code only; written clarification from the organisers received (R25); deck presents the founder's experience, not the old platform |
| Billing/credits not ready | Medium | Blocks deploy | Do it first on day 1 |
| Model ID wrong or unavailable | Medium | Blocks AI | Day-1 hello-world; `GOOGLE_CLOUD_LOCATION=global`; model in an env var |
| ADK API differs from docs | Medium | Slows dev | Pin the version; check `adk --help` and the installed source |
| Gemini species ID unreliable for similar birds | Medium | Wrong trust result | Combine vision with text; protected decision on text **or** vision; demo with clear photos; photo-accuracy test: 8/8 protected species blocked from the photo alone, 0/37 false alarms (AI-generated test photos; add real ones) |
| Getting realistic bird/dog photos legally | Medium | Weak demo | Own photos (Sudarsan's aviary contacts, with permission) or Gemini-generated images; log in ATTRIBUTIONS |
| In-memory sessions lost on restart | Low | Chat resets | `min-instances=1`, `max-instances=1`; business data in Firestore |
| Portal trouble near the deadline | Medium | Missed deadline | Submit by 12:00 PM on 18 Oct |
| Credits expire during evaluation | Low | App down | Check expiry; budget alert; weekly check |
| One person unavailable | Medium | Delay | Daily push; docs; cut list |
