# Pitch Deck Outline (PDF)

The T&C (Deliverables) require the deck to cover **solution architecture and the business case**. The session asked for: theme alignment, the problem, how the solution addresses it, scalability/production path, and a user guide. Aim for **13–15 slides** in English, readable when zoomed out (body text ≥ 18 pt). Build in Google Slides and export to PDF.

**Present the founder's domain experience. Don't present the earlier PetZonic platform's features, screenshots or traction** (rule R25). Everything shown must come from this hackathon build.

| # | Slide | Content | Criterion |
|---|---|---|---|
| 1 | **Title** | PetZonic AI: trusted breeder-to-buyer pet commerce, powered by Gemini agents. Theme: **Retail & Commerce**. Team. Live URL, GitHub, video. | — |
| 2 | **"The breeder is 50 metres away."** | The founder's story: 5 years breeding and brokering birds in Coimbatore; ₹750 → ₹4L+ with a 100-person circle; customers overpay at shops; the market is hidden in district WhatsApp groups. Labelled as the founder's experience. | Alignment & Impact |
| 3 | **The problem, in four parts** | Discovery (can't find breeders), trust (scams, sick animals), legality (protected birds, dyed munias, unregistered dog breeders; **cited news/rules**), time (breeders lose hours to manual selling) | Alignment & Impact |
| 4 | **Theme alignment** | Theme keyword → PetZonic feature table (conversational shopping, product discovery, personalisation, fraud prevention, customer insights, efficiency) | Alignment (25%) |
| 5 | **Solution overview** | List → Check → Find → Start right. One screenshot per step. | Alignment, UX |
| 6 | **Breeder copilot** | Before: WhatsApp message. After: structured listing with fair-price bar. Timed: "≤ 60 s". | Innovation, UX |
| 7 | **Trust & compliance** | Trust card screenshot; the signals table; BLOCKED example; "Is this listing safe?" for outside posts | Innovation, Impact |
| 8 | **Solution architecture** | Diagram from [01-architecture.md](../implementation/01-architecture.md): Cloud Run, 5 ADK agents, Gemini, Firestore, Cloud Storage; list of services and what each does | Technical (40%) |
| 9 | **How the AI works** | Multimodal + multilingual extraction to JSON; vision screening; deterministic trust score; pHash + geo + rules alongside Gemini. Show one real `ListingDraft` JSON. | Technical (40%) |
| 10 | **Quality and evaluation** | Unit test count, 14 eval cases, golden-image pass rate (**real measured numbers**), CI badge, injection test (E12) | Technical (40%) |
| 11 | **Business case** | Revenue: listing boosts for breeders; verified-breeder subscription; commission on starter-kit and accessory sales; trust-screening API for classifieds and pet shops (B2B). Cost per listing screened, from real Gemini pricing with stated assumptions. Founder-led go-to-market through existing district groups. **Label assumptions as assumptions.** | Impact; T&C requirement |
| 12 | **Scale and production path** | Scale-up table from [01-architecture.md](../implementation/01-architecture.md#scale-up-path-for-the-decks-production-slide); simulated vs real today | Technical, Alignment |
| 13 | **Impact** | Buyers: fair prices, healthier, legal pets. Breeders: hours saved, wider reach. Wildlife: fewer protected birds traded. | Impact |
| 14 | **Roadmap** | Labelled future: WhatsApp onboarding, SAWB/PARIVESH integration, breeder score, escrow, pet ID, vet and pharmacy, regional languages | Impact |
| 15 | **User guide (appendix)** | Open URL → "Try as Karthik" (list a pet) → "Try as Priya" (find a pet) → "Is this listing safe?" with the sample screenshot | UX, session requirement |

## Rules for the deck

- Every statistic has a source footnote, or it's removed (T&C: Content Warranties). Founder numbers are labelled as personal experience.
- Every feature shown as working **is** working in the live app; everything else says "Roadmap".
- Label simulated parts: "simulated SAWB registry", "sample listings and prices", "demo enquiries".
- Fictional breeders and brands, and our own or generated images only.
- No legal-advice claims ("helps flag", not "guarantees legality"); no veterinary claims.
