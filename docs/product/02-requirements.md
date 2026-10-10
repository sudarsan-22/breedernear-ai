# Product Requirements: MVP for 18 Oct 2026

## Scope rule

**MVP** = must work end to end in the live app by 14 Oct. **Stretch** = only after every MVP item passes the smoke test. **Roadmap** = deck only, labelled as future, never presented as working.

## Species in scope (prototype)

| Group | Examples | Rule |
|---|---|---|
| Pet birds (exotic, commonly bred) | Budgerigar, lovebirds (incl. colour varieties), cockatiel, zebra finch, society finch, canary | Allowed |
| Exotic birds listed under CITES (e.g. African grey, macaws) | — | Allowed only with a **PARIVESH registration note** shown to the buyer; trust capped at "Caution" without a registration ID |
| **Protected Indian native birds** | Rose-ringed/Alexandrine/plum-headed parakeets, munias, silverbills, mynas, Indian ring-necks | **Always blocked**, enforced in code |
| Dogs | Labrador, Beagle, Shih Tzu, Indian breeds, etc. | Seller must provide a State Animal Welfare Board (SAWB) breeder registration no., checked against the **simulated** registry |
| Cats | Persian, Siamese, Indian cats | Allowed |

## Product shape: three tabs, AI everywhere, chat optional

Buying and selling happen in the **same app**. A new user must be able to complete every core job **by tapping, without chatting**, and the AI must still do the hard parts on those screens. Chat is a third way in, not the only one.

| Tab | Job | UI (no chat needed) | AI in that screen |
|---|---|---|---|
| 🐾 **Pets** | Buyer finds a pet | Browse grid, filters, listing page, contact form, starter kit, cart | Trust checks, fair-price indicator, quiz ranking (rules), care plan (Gemini), "Ask AI" |
| 🏡 **Local Breeders** (Direct Farm) | Buyer meets breeders; **seller lists pets** (My farm) | Breeder directory and pages; sell form, my listings, enquiries | "✨ Fill with AI" from photos + message (Gemini), trust screening on publish (Gemini vision + rules) |
| ✨ **BreederNear AI** | Anything, in English or Tamil | — | Multi-agent assistant (ADK) with cards and activity panel |

"Direct Farm" means buying straight from the breeder at the farm price, with no broker markup. This is the problem in the founder story.

## Feature list

| ID | Feature | Scope |
|---|---|---|
| F1 | Web app with **three tabs** (Pets · Local Breeders · BreederNear AI), district picker, cart, first-visit welcome card. Guest session, no login. | **MVP** |
| F2 | **Breeder listing assistant:** photos + casual message (English/Tamil/mixed) → AI-filled **sell form** (My farm) or chat draft → edit → publish | **MVP** |
| F3 | **Trust & compliance screening** on every listing → trust score, level, reasons | **MVP** |
| F3b | **"Is this post safe?":** a buyer uploads a screenshot or pastes a listing seen on WhatsApp/Instagram/Facebook and gets the same screening (form in Pets, or chat) | **MVP**: reuses the F2 + F3 pipeline |
| F4 | **Buyer matching:** Pets tab grid with filters (species, district, max price, trusted only) and listing pages; "Which pet suits me?" quiz; the same in chat via the match agent | **MVP** |
| F12 | **Local Breeders (Direct Farm):** breeder directory by district, breeder pages with their pets for sale | **MVP** |
| F5 | **Starter kit & care plan** for the chosen pet (accessories catalogue + first-14-days plan + vet warning signs) | **MVP** |
| F6 | **Buyer enquiry** to the breeder (demo: saved and shown in the breeder's inbox; no payment) | **MVP** |
| F7 | Agent activity panel ("which agent and tool ran") in the AI tab | **MVP**: cheap, shows technical depth |
| F8 | Breeder auto-reply: answers buyer questions from listing data on the breeder's behalf | Stretch |
| F9 | Semantic search over listings and products (Firestore vector search + embeddings) | Stretch |
| F10 | Tamil replies when the user writes in Tamil | Stretch (input already works via Gemini) |
| F11 | Google Maps view of nearby listings | Stretch |
| — | Payments/escrow, WhatsApp integration, pet ID registry, vet consults, pharmacy, real SAWB/PARIVESH integration | **Roadmap only** |

## User stories and acceptance criteria

### F1: App shell
- Opening the URL shows the **Pets** tab with nearby pets within 3 s (warm instance). No sign-up.
- Three tabs are always visible (bottom bar on phones): 🐾 Pets · 🏡 Local Breeders · ✨ BreederNear AI.
- **First visit:** a welcome card explains the three tabs in one line each, asks for the district, and offers "I'm a breeder: sell" and the demo buttons. It can be dismissed and does not come back.
- Every tab starts with a one-line explainer; every empty state says what to do next.
- "Try the demo" buttons: **Priya** (buyer, Tiruppur) opens Pets filtered for her; **Karthik** (breeder, Coimbatore) opens My farm › Sell with his message prefilled.
- The footer always shows: "Prototype — sample breeders, listings and products. No payments. Not veterinary advice."

### F2: Breeder listing assistant
*As a breeder, I want to create a listing from my phone in under a minute, the way I'd post in a WhatsApp group.*
- Input: 1–4 photos (JPEG/PNG/WebP/HEIC, ≤ 5 MB each) plus free text in English, Tamil or a mix.
- Output: listing draft (schema in [../implementation/02-agent-design.md](../implementation/02-agent-design.md#listingdraft)) with species, variety/colour, count, sex (if stated), age, price per unit/pair, district, locality, vaccination/health notes, description, and the fields the breeder still needs to fill.
- Gemini proposes the species from the photo. If the photo and text disagree, the draft says so and asks the breeder to confirm.
- A suggested **fair price range** for the species and variety comes from market data in code (sample data in the prototype).
- **Sell form (My farm):** "✨ Fill with AI" fills normal form fields; the breeder can edit any field before publishing; each edit is validated; missing fields are highlighted; the fair-price bar updates with the price.
- The same flow also works in the AI tab by chat.
- **Publishing always runs F3 first.** Blocked listings can't be published.
- **Sandboxing on the public demo:** listings created by guests are visible **only to that guest** (in their breeder view and their own buyer searches). Public search for everyone else shows only the curated seed listings. This stops strangers putting offensive or unlawful content in front of judges.
- Photos that aren't of an animal (`image_quality = not_animal`) are rejected; Gemini safety filters stay on.
- Target: ≤ 60 seconds from opening the form to a published listing, measured in the demo.

### F3: Trust & compliance screening
*As a buyer, I want to know whether a listing is trustworthy and legal before I contact the seller.*
- Runs on publish and is shown on every listing card.
- Checks:

| Check | How | Effect |
|---|---|---|
| Protected native species | Species from Gemini vision + text, matched against a protected-species list **in code** (names, synonyms, Tamil names) | **BLOCKED** |
| Dyed or disguised animal | Gemini vision flag (unnatural uniform colour, dye stains) | CAUTION + reason |
| Visible health concerns | Gemini vision: eyes, feathers/coat, posture, cage cleanliness. Wording is "signs to ask about", not a diagnosis. | CAUTION + questions to ask the seller |
| Reused or stolen photo | Perceptual hash compared with all other listings' photos (code) | CAUTION ("same photo used in another listing") |
| Price anomaly | Price vs species/variety range (code): far below → scam risk; far above → overpriced | CAUTION / info |
| Scam language | Rules + Gemini: "full advance only", "no visits", "courier only", pressure tactics | CAUTION |
| Dog breeder registration | SAWB number present and found in the **simulated** registry (code) | Missing/unknown → CAUTION; found → +trust |
| CITES exotic | Species on the CITES list (code) | PARIVESH note; no registration ID → CAUTION |

- Output: `trust_score` 0–100, `trust_level` (`TRUSTED` ≥ 75, `CAUTION` 40–74 or any caution flag, `BLOCKED`), and a list of reasons in plain language (✅ / ⚠️ / ⛔).
- **BLOCKED and the score thresholds are decided by code, not by the model.**

### F3b: "Is this listing safe?"
*As a buyer who found a pet in a WhatsApp group, I want to know whether the post shows warning signs before I pay anyone.*
- Input: a screenshot or photo of the post, and/or pasted text.
- BreederNear extracts the listing and runs every F3 check except duplicate-photo matching against non-BreederNear sources. The result is shown as a trust card with reasons and **questions to ask the seller**.
- Nothing is stored as a listing. The upload follows the normal 30-day deletion rule.
- This brings BreederNear's value to the informal groups where the trade actually happens today.

### F4: Buyer matching (Pets tab and chat)
*As a first-time buyer, I want help choosing the right pet and a trustworthy breeder near me at a fair price.*
- **Pets tab:** grid of published pets near the chosen district (never BLOCKED; own sandboxed listings tagged "Yours"), filters for species, max price and "trusted only", sorted trusted first, then distance. A listing page shows every trust check, the questions to ask, the breeder, Contact, Starter kit & care plan, and "Ask AI about this pet".
- **Quiz:** "Which pet suits me?" asks the same needs as the chat in 4–6 taps and shows up to 3 species options with reasons; "Show these pets" filters the grid.
- **Chat (AI tab):**
- Understands needs from conversation: home type, space, family (kids, elderly), experience, time available, noise tolerance, budget, district.
- Asks at most 2 clarifying questions per turn.
- Recommends 1–3 suitable species with reasons (e.g. "budgies: quieter, easy for kids, small cage fits a flat").
- Finds listings: species match, **not BLOCKED**, sorted by trust level → distance → price. Shows up to 4 listing cards.
- Each card shows the photo, species, price, "fair range ₹X–Y" indicator, trust badge with top reasons, district and distance, and the breeder's name (fictional in the prototype).
- If the user asks for a protected species, it refuses, explains the law briefly, and suggests legal alternatives.
- Never invents listings. Only shows results returned by the tool.

### F5: Starter kit & care plan
*As a new owner, I want to know exactly what to buy and how to care for my pet in the first two weeks.*
- Triggered by "I'll take this one" / "what do I need?" on a listing.
- Starter kit: 4–8 products from the accessories catalogue matched by species, count and size rules (e.g. minimum cage size per pair of lovebirds, enforced in code), with a total cost.
- Care plan: days 0–2, days 3–7, days 8–14 (settling in, diet, handling, hygiene), plus **"see a vet if…"** warning signs per species.
- Products can be added to a **demo cart**. No payment.

### F6: Buyer enquiry
- A "Contact breeder" form on the listing page, or the chat, creates an enquiry (buyer's message + chosen listing).
- **My farm › Enquiries** shows enquiries received on the guest's own listings (because listings are sandboxed, the demo uses one browser as both buyer and breeder).
- Clearly labelled: "Demo: no real breeder is contacted."

### F12: Local Breeders (Direct Farm)
*As a buyer, I want to buy directly from a breeder near me instead of paying a broker's markup.*
- Directory of breeders near the chosen district: name, locality, distance, species bred, years of experience, dog-breeder registration status (simulated registry), number of pets for sale, best trust level.
- Breeder page lists their published pets (same cards and listing page as the Pets tab).
- Only breeders with at least one published (not BLOCKED) listing are shown. All breeders are fictional.

### F7: Agent activity panel
- A collapsible list of `agent → tool → short result` for every turn (e.g. `trust_agent → screen_listing → CAUTION (price 60% below range)`).

## Non-functional requirements

| Area | Requirement |
|---|---|
| Availability | Live from 17 Oct until at least 7 Nov; until 4 Dec if shortlisted. `min-instances=1`. |
| Latency | First token < 4 s for text; listing draft from photos < 15 s (warm). |
| Mobile | Phone-first. Usable at 375 px width; bottom tab bar; tap targets ≥ 44 px. |
| Discoverability | A first-time user finds all three tabs and both sides (buy, sell) without instructions; tested with someone who hasn't seen the app. |
| Accessibility | WCAG AA contrast, alt text, keyboard navigation; status never conveyed by colour alone. |
| Security | No secrets in the repo; least-privilege service account; upload type and size validation. |
| Abuse/cost | ≤ 40 AI calls per guest and ≤ 150 per IP per hour (chat, AI fill, check, publish, care plan); capped `max-instances`; budget alert. |
| Privacy | Synthetic data only; uploads in a private bucket; no personal contact data collected. |
| Language | English UI and docs; Tamil and mixed **input** supported. |

## Explicitly out of scope

Real payments or escrow, real breeders or real contact details, live-animal delivery, real registry lookups, user accounts or passwords, diagnosis or medication advice.
