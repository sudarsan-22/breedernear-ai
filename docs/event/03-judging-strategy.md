# Judging Strategy

How BreederNear AI earns marks against each criterion. Weights come from T&C: Judging. Quotes are from the [kickoff session](05-kickoff-session-notes.md).

## Technical Merit & GenAI Implementation: 40%

> "It's not just a simple send a prompt to the AI, get a response and say I've used AI, I'm done." (Session)
>
> T&C: "robustness, Google Cloud architectural depth, technical execution."

| What judges look for | How BreederNear AI shows it | Where it's visible |
|---|---|---|
| Meaningful, non-trivial GenAI | **5-agent ADK system:** concierge, listing copilot, trust & compliance, matching, care | Architecture slide; agent activity panel in the UI |
| Multimodal + multilingual | Gemini reads listing photos **and** messy Tamil/English/mixed WhatsApp-style text → one structured listing | Demo video: breeder scene |
| Vision for safety | Species check, dye/disguise detection, visible health signs, stock-photo detection | Trust card reasons |
| Tool calling over real data | Firestore-backed tools: search with distance, price ranges, registries, products | Activity panel; `breedernear_core/tools/` |
| Structured, reliable outputs | `ListingDraft`, `PhotoScreen`, `CarePlan` schemas, Pydantic-validated | Code; deck slide 8 |
| Robustness and guardrails | Trust score, protected-species block, welfare rules and scam rules are **deterministic code**. The LLM can't override them (eval E12 proves it). | Demo: blocked listing |
| Classic + AI combined | Perceptual hashing for reused photos, haversine distance, rule engines alongside Gemini | Deck slide 9 |
| Evaluation | 14 ADK eval cases + golden-image set + unit tests in CI, with **measured pass rates** | README badge; deck slide 10 |
| Google Cloud depth | Cloud Run, Gemini via Agent Platform, ADK, Firestore, Cloud Storage, Cloud Build, Cloud Logging | Architecture slide |
| Scalability | Stateless Cloud Run, serverless DB, config-driven model, scale-up table | Deck slide 12 |

## Problem Alignment & Impact: 25%

> "Explain how what you have built is addressing the problem… how this use case is relevant to [the theme]." (Session)

- **Theme:** Retail & Commerce. Map each feature to the theme's own words (see the table in [../product/01-problem-and-vision.md](../product/01-problem-and-vision.md#theme-alignment-retail--commerce-keywords--breedernear)): conversational shopping, product discovery, personalisation, **fraud prevention**, customer insights, operational efficiency.
- **Real problem, real person:** the founder's 5 years as a breeder and broker. *"The breeder is 50 metres away. The customer never finds them."* Judges were told to bring *"what you are seeing in the industry"*, and this is exactly that.
- **Measurable impact in the demo:** listing time ≤ 60 s vs manual posting; fair-price position on every card; blocked illegal listings.
- **Sourced statistics only** (T&C: Content Warranties).

## Innovation & Creativity: 25%

> "Don't redo a solution that has already been built." (Session)

What existing pet marketplaces and classifieds don't do:
1. **Listing from a WhatsApp-style message:** photos plus a casual Tamil/English message become a structured, priced listing in under a minute.
2. **AI trust & compliance screening for live-animal commerce:** wildlife-law blocking, dyed-bird detection, reused-photo detection, price-anomaly and scam-language detection, combined into an explainable score.
3. **"Is this listing safe?" for posts outside our platform:** BreederNear protects buyers even inside the WhatsApp and Instagram groups where the trade actually happens.
4. **Whole first-week journey:** right pet → right breeder → right starter kit → care plan, in one conversation.

## User Experience & Solution Design: 10% (plus the Best UI/UX prize)

- **Zero friction:** no login; a first-visit welcome card explains the three tabs; "Try as Priya / Karthik" demo buttons.
- **Not "just a chatbot":** every core job (browse, contact, sell, check a post, starter kit) works by tapping in the Pets and Local Breeders tabs, with AI built into those screens; the multi-agent chat is the third tab.
- **Phone-first breeder flow:** camera upload, one message, one Publish tap.
- **Explainable trust:** every badge expands into ✅ / ⚠️ / ⛔ reasons and questions to ask the seller.
- **Accessible:** icon + word + colour for trust levels, AA contrast, keyboard navigation, alt text.

## Special prizes we can realistically target

| Prize | Why we have a chance |
|---|---|
| Most Impactful Solution | Wildlife protection + fair prices + breeder livelihoods, grounded in a real founder story |
| Best Use of Google Cloud AI Tools | Multimodal + multilingual Gemini, 5-agent ADK system, evals, Cloud Run/Firestore |
| Best UI/UX | If the phone-first breeder flow and trust cards are polished |
