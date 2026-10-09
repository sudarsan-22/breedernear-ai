# Agent Design (ADK)

All agents are ADK `LlmAgent`s on the model in `BREEDERNEAR_MODEL`. Tools are plain Python functions in `breedernear_core/tools/`. They take a `ToolContext` to read session state (`guest_id`, `mode`, demo identity) and return JSON-serialisable dicts.

Confirm ADK API details against the installed version (`pip show google-adk`, then <https://adk.dev>). ADK releases weekly and has parallel 1.x and 2.x lines.

## Agent tree

```
breedernear_concierge (root)
├── listing_agent   breeder copilot
├── trust_agent     screening, "is this listing safe?", explanations
├── match_agent     buyer: which pet, which breeder
└── care_agent      buyer: starter kit + first-14-days care plan
```

Delegation uses ADK agent transfer (`transfer_to_agent`) based on each agent's `description`. Sub-agents can transfer back to the root or to a sibling (e.g. match → care once a pet is chosen).

### breedernear_concierge (root)

- **Role:** greet, detect mode (buying / breeder) and language, route, refuse off-topic requests.
- **Instruction essentials:**
  - Warm, short, practical. Reply in the user's language if they write in Tamil; keep listing data in English.
  - Breeder wants to list, edit or see enquiries → `listing_agent`.
  - "Is this seller/listing genuine?", a pasted or screenshotted listing from WhatsApp/Instagram, "why is this marked caution?" → `trust_agent`.
  - Wants a pet, or asks which pet suits them → `match_agent`.
  - What to buy or how to care for a new pet → `care_agent`.
  - Protected native species requests → refuse briefly and suggest legal alternatives (also enforced in tools).

### listing_agent (breeder copilot)

- **Description:** "Turns a breeder's photos and casual message (English/Tamil) into a structured pet listing, suggests a fair price, and publishes it after screening."
- **Tools:** `extract_listing`, `update_draft`, `publish_listing`, `my_listings`, `my_enquiries`
- **Behaviour:**
  1. Always call `extract_listing` with the upload IDs and the text. Never invent fields.
  2. Show the draft compactly, highlight the fair-price range, and list the missing fields (max 3 questions).
  3. On "publish", call `publish_listing`. It **always** runs screening in code and returns the trust result.
  4. If BLOCKED, explain why politely and don't help get around it.

### trust_agent

- **Description:** "Screens pet listings for legality, fraud and welfare red flags and explains trust results in plain language."
- **Tools:** `check_external_listing` (screenshot or pasted text from WhatsApp/Instagram, screened without publishing), `explain_screening(listing_id)`
- **Behaviour:** present ✅ / ⚠️ / ⛔ reasons; suggest questions to ask the seller (e.g. "Ask for a video call showing the birds in their aviary"); never call a seller a criminal, and say "this listing shows warning signs".

### match_agent

- **Description:** "Helps buyers choose a suitable pet for their home and finds trusted breeder listings nearby at fair prices."
- **Tools:** `recommend_species`, `search_listings`, `get_listing`, `create_enquiry`
- **Behaviour:**
  - Gather needs (home, space, family, experience, time, noise, budget, district) with at most 2 questions per turn.
  - `recommend_species` → 1–3 species with reasons.
  - `search_listings` → show up to 4 cards. **Only results from the tool.**
  - Explain trust level and price position on each card in one line.
  - Once a listing is chosen, offer the starter kit → transfer to `care_agent`.

### care_agent

- **Description:** "Builds a personalised starter kit and a first-14-days care plan for a newly chosen pet."
- **Tools:** `build_starter_kit`, `care_plan`, `add_to_cart`, `view_cart`
- **Behaviour:** show the kit as product cards with a total, then the care plan by phase, then the vet warning signs. The disclaimer is appended by code.

## Session state

| Key | Set by | Contents |
|---|---|---|
| `guest_id` | Session creation (UI) | UUID from browser localStorage |
| `mode` | UI | `buyer` or `breeder` |
| `demo_breeder_id` | "Try as breeder" | Firestore breeder ID (Karthik) |
| `buyer_district` | match_agent / UI | e.g. `tiruppur` |
| `draft_listing_id` | `extract_listing` | Current draft |
| `chosen_listing_id` | match_agent | Listing picked by the buyer |

Durable data always lives in Firestore.

### Attachment message convention

The UI uploads files first, then sends:

```
<user text>
[attachments upload_ids=UPL_a1,UPL_a2 kind=listing_photo]
```

`kind` is `listing_photo` (breeder) or `external_listing` (buyer checking a screenshot).

## Tools

All tools return `{"status": "ok" | "error", ...}`. Errors include a `message` the agent can relay.

| Tool | Signature (excluding `tool_context`) | Code-enforced logic |
|---|---|---|
| `extract_listing` | `(text, upload_ids)` | Gemini multimodal → `ListingDraft` schema; fair price range attached from data; draft saved |
| `update_draft` | `(field, value)` | Field validation (species enum, price > 0, district known) |
| `publish_listing` | `()` | Runs `screen_listing` internally; BLOCKED → not published; required fields (e.g. SAWB no. for dogs) |
| `my_listings` / `my_enquiries` | `()` | Demo breeder only |
| `check_external_listing` | `(text, upload_ids)` | extract → screen; nothing is stored as a listing |
| `explain_screening` | `(listing_id)` | Returns the stored checks |
| `recommend_species` | `(home_type, space, family, experience, time_per_day, noise_ok, budget_inr)` | Candidate species filtered **by rules** (budget vs typical price, space vs minimum cage, protected excluded); Gemini only writes the reasons |
| `search_listings` | `(species, district, max_price_inr=None, radius_km=60)` | Excludes BLOCKED; returns `public` listings plus the caller's own `owner_only` listings (sandboxing, R33); distance via `geo.py`; sort TRUSTED → CAUTION, then distance, then price; max 4 |
| `get_listing` | `(listing_id)` | — |
| `create_enquiry` | `(listing_id, message)` | Stored with `demo: true`; refuses BLOCKED listings |
| `build_starter_kit` | `(species, count)` | Product rules per species; `welfare_rules` minimum cage size; max 8 items; total |
| `care_plan` | `(species, age_months=None)` | Gemini → `CarePlan` schema; vet warning signs required; disclaimer appended |
| `add_to_cart` / `view_cart` | `(product_id, quantity=1)` / `()` | Stock check; demo cart |

`screen_listing(listing)` is internal (called by `publish_listing` and `check_external_listing`). It is not exposed to the model, so the model can't skip it or re-run it selectively.

## Structured schemas (Pydantic, in `breedernear_core/schemas.py`)

### ListingDraft

```python
class ListingDraft(BaseModel):
    species_common: str                    # "Lovebird"
    species_scientific: str | None         # "Agapornis fischeri"
    variety: str | None                    # "Lutino"
    animal_group: Literal["bird", "dog", "cat", "other"]
    count: int                             # number of animals
    unit: Literal["single", "pair", "litter"]
    sex: str | None
    age_months: int | None
    price_inr: int | None                  # per unit
    district: str | None                   # normalised to known districts
    locality: str | None
    health_notes: str | None               # vaccination, deworming, as stated by breeder
    sawb_registration_no: str | None       # dogs
    parivesh_registration_id: str | None   # CITES exotics
    description: str                       # clean English summary, ≤ 60 words
    language_detected: str                 # "ta", "en", "mixed"
    photo_text_consistent: bool            # does the photo match the stated species?
    missing_fields: list[str]
    confidence: float
```

### PhotoScreen (Gemini vision output; one call over all photos)

```python
class PhotoScreen(BaseModel):
    species_guess: str
    species_guess_confidence: float
    possibly_protected_native_species: bool
    possible_dye_or_disguise: bool
    dye_evidence: str | None
    visible_health_signs: list[str]        # "ruffled feathers", "discharge near eye"
    housing_observations: list[str]        # "crowded cage", "clean water visible"
    image_quality: Literal["good", "poor", "not_animal"]
    looks_like_stock_or_watermarked: bool
```

### Screening (computed in code)

```python
class Check(BaseModel):
    name: str            # "protected_species", "duplicate_photo", "price", ...
    result: Literal["pass", "warn", "block", "info"]
    detail: str          # plain-language reason shown to users

class Screening(BaseModel):
    trust_score: int     # 0–100
    trust_level: Literal["TRUSTED", "CAUTION", "BLOCKED"]
    checks: list[Check]
    questions_to_ask_seller: list[str]
```

### Trust score formula (`safety/trust_score.py`)

Start at **100** and apply:

| Signal | Effect |
|---|---|
| Protected native species (text or vision ≥ 0.5) | **BLOCKED** (score 0) |
| Photo reused from another listing (pHash distance ≤ 6) | −35 |
| Price < 50% of the range minimum | −30 (scam risk) |
| Price below the range minimum | −10 |
| Price > 150% of the range maximum | −5 (info: overpriced) |
| Scam language detected | −30 |
| Possible dye or disguise | −30 |
| Visible health signs (each, max 2) | −15 |
| Dog without SAWB no. / SAWB no. not in registry | −25 / −30 |
| CITES species without PARIVESH ID | −20 |
| Poor photo quality / stock-looking image | −10 |
| Photo doesn't match the stated species | −15 |

Level: **BLOCKED** if blocked; **TRUSTED** if score ≥ 75 and no `warn` with penalty ≥ 25; otherwise **CAUTION**. Thresholds live in config. Every rule has unit tests.

### SpeciesRecommendation

```python
class SpeciesOption(BaseModel):
    species: str
    why: list[str]              # tied to the buyer's stated needs
    watch_outs: list[str]       # e.g. "lovebirds can be loud"
    typical_price_range_inr: tuple[int, int]   # from data
```

### CarePlan

```python
class CarePlan(BaseModel):
    species: str
    phases: list[Phase]         # Phase(title="Days 0–2", steps=[...])
    diet: list[str]
    daily_routine: list[str]
    see_vet_if: list[str]       # min 3 items, required
    disclaimer: str             # set by code
```

## Callbacks

| Callback | Where | Purpose |
|---|---|---|
| `before_model_callback` | all agents | Inject mode, district and current draft/listing summary into the context |
| `after_model_callback` | match, care, trust | Block replies that mention medicines or doses, or promote a BLOCKED species; replace with a safe message |
| `before_tool_callback` | all | Log tool name, args and guest ID for the activity panel and Cloud Logging |

## Prompting guidelines

- Follow Google's Gemini prompting best practices: clear role, explicit constraints, output format, a few short examples (including Tamil/mixed breeder messages).
- Instructions live in `agents/breedernear/prompts.py`, one constant per agent.
- Safety rules go in prompts **and** code. Prompts make good behaviour likely; code makes bad outcomes impossible.
- Temperature: 0.2 for extraction and screening; default for conversation.
