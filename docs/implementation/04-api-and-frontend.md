# API and Frontend

One FastAPI app (`app/main.py`) built with ADK's `get_fast_api_app(...)`.

**One tool layer, two front doors.** The same service functions (`breedernear_core/*_service.py`) are called by the ADK agents (chat, in the **BreederNear AI** tab) and directly by the UI screens (**Pets** and **Local Breeders** tabs) through `/api`. A new user can buy or sell entirely by tapping, and every screen still uses AI where it helps (filling a listing from a photo, trust checks, care plans). Rules and trust decisions are identical on both paths because they are the same code.

The app serves three things:

| Prefix | What | Provided by |
|---|---|---|
| `/`, `/img/*`, `/app.js`, `/styles.css` | Web UI static files | FastAPI `StaticFiles` mounting `web/` (mounted **last**) |
| `/apps/*`, `/run`, `/run_sse`, `/list-apps` | ADK agent runtime: sessions and runs | `get_fast_api_app(agents_dir="agents", web=False)` |
| `/api/*` | Our endpoints | `app/api.py` |

## ADK runtime endpoints used by the UI

Only these ADK routes are reachable, all behind login (`app/gatekeeper.py`); every other ADK route (docs, memory, artifacts, the live WebSocket) returns 404. The `user_id` must be the signed-in account's.

| Call | Purpose |
|---|---|
| `POST /apps/breedernear/users/{user_id}/sessions` with `{}` and the Bearer token | Create a chat session; the gatekeeper writes `role`, `user_name`, `device_id` and `district` into its state server-side |
| `GET /apps/breedernear/users/{user_id}/sessions/{session_id}` | Restore after reload |
| `POST /run_sse` with `{"app_name": "breedernear", "user_id": user_id, "session_id": ..., "new_message": {"role": "user", "parts": [{"text": "..."}]}, "streaming": true}` | Send a message; stream events |

SSE events carry an `author` (agent) and `content.parts` (`text`, `function_call`, `function_response`). The UI renders:

| Event | Rendered as |
|---|---|
| `text` | Chat bubble (streamed) |
| any `function_call` | Activity panel line: `agent → tool` |
| `extract_listing` response | **Listing draft card** (editable fields, fair-price bar, missing fields) |
| `publish_listing` / `check_external_listing` / `explain_screening` response | **Trust card** (level badge, score, ✅/⚠️/⛔ reasons, questions to ask) |
| `recommend_species` response | **Species option cards** |
| `search_listings` response | **Listing cards** |
| `build_starter_kit` response | **Product cards** + total |
| `care_plan` response | **Care plan card** (phases, warning signs) |

## Our endpoints (`/api`)

| Method & path | Body / params | Returns | Used by | AI? |
|---|---|---|---|---|
| `GET /api/health` | — | `{"status":"ok","model":"...","version":"<git sha>"}` | Smoke test | — |
| `POST /api/auth/signup` | `{role, name, login (email or mobile), password, district, remember, farm?}`; header `X-Device-Id` | `{token, user}` | Sign-up screen | — |
| `POST /api/auth/login` | `{login, password, remember}`; header `X-Device-Id` | `{token, user}`; 401 "Wrong email/mobile or password" | Login screen | — |
| `POST /api/auth/demo` | `{role}` (`customer` or `seller`); header `X-Device-Id` | Session for the shared demo account of that role (Priya or Karthik, preloaded data) | Demo buttons | — |
| `GET /api/auth/me`, `POST /api/auth/logout`, `DELETE /api/auth/me` | `Authorization: Bearer <token>` | Profile / logout / delete account | Account, Farm profile | — |
| `PATCH /api/auth/me` | profile fields (name, district; seller: farm fields) | Updated profile | Profile edit | — |
| `GET /api/seller/dashboard` | seller token | Counts (active, paused, sold, blocked listings; enquiries; views), verification status, recent activity | Seller dashboard | — |
| `PATCH /api/seller/listings/{id}` / `DELETE` | `{status: "PUBLISHED" | "PAUSED" | "SOLD"}` | Updated listing / removed | My listings | — |
| `POST /api/uploads` | multipart `file`, `kind` (`listing_photo` needs a seller) | `{"upload_id":"UPL_…"}` | Sell form, safety check, chat | — |
| `GET /api/pets` | `district`, `species` (optional; `all`), `max_price`, `trusted_only`, `limit` | Published listings near the district: public + the caller's own, never BLOCKED; sorted TRUSTED → CAUTION, then distance, then newest | **Pets** tab grid | — |
| `GET /api/listings/{id}` | — | Listing card + checks + questions + breeder | Listing page | — |
| `GET /api/listings` | `species`, `district`, `max_price` | Same as the `search_listings` tool (max 4) | Chat parity | — |
| `POST /api/recommend` | `{animal_group, home_type, has_young_children, first_time_owner, time_per_day_minutes, noise_ok, budget_inr}` | Up to 3 species options with reasons, plus excluded ones | "Which pet suits me?" quiz | Rules |
| `GET /api/breeders` | `district`, `species` (optional) | Breeders with distance, species bred, years, dog-registration status (simulated), active listings, best trust level | **Local Breeders** directory | — |
| `GET /api/breeders/{id}` | — | Breeder profile + their published listings | Breeder page | — |
| `POST /api/sell/drafts` | `{text, upload_ids}` | Draft + fair-price range + missing fields | Sell form "✨ Fill with AI" | **Gemini** |
| `PATCH /api/sell/drafts/{id}` | `{field: value, ...}` (editable fields only) | Updated draft (validated) | Sell form edits | — |
| `POST /api/sell/drafts/{id}/publish` | — | Listing ID, status, screening | Sell form Publish | **Gemini + rules** |
| `GET /api/seller/listings` | seller token | The seller's own listings incl. PAUSED, SOLD and BLOCKED | Seller Listings | — |
| `GET /api/seller/enquiries` | seller token | Enquiries received on the seller's own listings (message and any reply; no buyer contact details) | Seller Enquiries | — |
| `POST /api/seller/enquiries/{id}/draft-reply` | seller token | `{reply, needs_seller_input}` drafted from the listing's facts; nothing is sent | Reply sheet "✨ Draft with AI" | **Gemini** |
| `POST /api/seller/enquiries/{id}/reply` | `{text}` (≤ 800 chars) | The enquiry with its reply; the buyer sees it under Account | Reply sheet Send | — |
| `POST /api/check` | `{text, upload_ids}` | Extracted post + screening; nothing stored | "Is this post safe?" form | **Gemini + rules** |
| `POST /api/enquiries` | `{listing_id, message}` (customer token) | Enquiry (demo) | Contact form | — |
| `GET /api/enquiries/sent` | customer token | Enquiries this customer sent, with the seller's reply | Account | — |
| `GET /api/starter-kit` | `species`, `count` | Kit items with welfare-sized cage + total | Listing page | Rules |
| `GET /api/care-plan` | `species`, `age_months` | 14-day plan + vet signs + disclaimer | Listing page | **Gemini** |
| `GET /api/cart`, `POST /api/cart/items`, `DELETE /api/cart/items/{id}` | customer token | Cart | Cart drawer | — |

**Auth:** every `/api` route except health, meta and auth requires `Authorization: Bearer <token>`. Role checks: seller-only routes (`/api/sell/*`, `/api/seller/*`, `listing_photo` uploads) and customer-only routes (`/api/cart*`, `POST /api/enquiries`) return 403 for the wrong role. The ADK runtime (`/run`, `/run_sse`, `/apps/...`) also requires the token, and the `user_id` in the path or body must be the token's user. Agent tools check the role again (`listing_agent` tools need a seller; `match_agent`/`care_agent` enquiry and cart tools need a customer).

All functions behind these routes are the same ones the agents' tools call (`listing_service`, `match_service`, `care_service`, plus a small `directory_service` for breeders). Errors return 400 with a human-readable `detail`.

Every route that calls Gemini (`/run_sse`, `/run`, `POST /api/sell/drafts`, `.../publish`, `POST /api/check`, `GET /api/care-plan`, `.../draft-reply`) goes through the rate limiter (`app/ratelimit.py`): an in-memory sliding window per login session and per IP, 40 AI calls per session and 150 per IP per hour (login and sign-up are limited too), returning 429 with a friendly message. Read-only routes are not limited.

## Frontend (`web/`)

Plain HTML, CSS and JavaScript. No build step. **Mobile-first**: breeders and most buyers use phones.

### Accounts and the two apps (added 10 Oct)

Signed-out users see the **login screen** (layout idea from the founder's earlier PetZonic product; fresh code and Meadow styling):

```
┌──────────────────────────────────┐
│            [🐾]                   │
│        Welcome back               │
│ ┌ [ Log in | Sign up ] ─────────┐ │
│ │ Email or mobile number        │ │
│ │ Password                 [👁]  │ │
│ │ [✓] Remember me  Forgot pwd?  │ │
│ │ [        Log in        ]      │ │
│ │ Don't have an account? Sign up│ │
│ │ ── OR TRY THE DEMO ──         │ │
│ │ [ Demo customer · Priya ]     │ │
│ │ [ Demo seller · Karthik ]     │ │
│ └───────────────────────────────┘ │
└──────────────────────────────────┘
```

- **Sign up:** "I want to: Buy pets | Sell pets", name, email or mobile, password (eye toggle, 8+ characters), district; sellers also give farm name, type (home / kennel / farm), area, species bred and, for dogs, the registration number.
- **Remember me:** token kept in localStorage (30 days); otherwise sessionStorage (until the browser closes, server session 24 h).
- **Forgot password:** honest sheet: not available without an email/SMS service; create a new account or use a demo.
- **Demo buttons:** one private demo customer and one demo seller per device, reused when switching, so a judge can play both sides.

| Customer app (bottom tabs) | Seller app (bottom tabs) |
|---|---|
| 🐾 Pets · 🏡 Local Breeders · ✨ BreederNear AI · 👤 Account | 📊 Dashboard · 📋 Listings · ✉️ Enquiries · ✨ AI · 🏡 Farm |
| Account: profile, district, cart, enquiries sent, "Want to sell? Sellers use a separate account", log out, delete account | Dashboard: greeting, verification badge, "Sell a pet with AI", live listings / enquiries / views / trusted counts, recent activity. Listings: filter by status; Pause, Resume, Mark sold, View, Remove. Sell: the AI-filled form. Farm: edit farm profile and registration; log out; delete account |

The sections below describe the customer tabs; "My farm" is replaced by the seller app.

### Navigation: three tabs

Bottom tab bar on phones, top tabs on wider screens. The header shows the brand, a **📍 district picker** (remembered; default Coimbatore) and the **🛒 cart**.

```
┌──────────────────────────────────────────┐
│ 🐾 BreederNear AI        📍 Tiruppur  🛒 3 │
├──────────────────────────────────────────┤
│                 (tab content)             │
├──────────────────────────────────────────┤
│  🐾 Pets   │ 🏡 Local Breeders │ ✨ BreederNear AI │
└──────────────────────────────────────────┘
  Prototype — sample breeders, listings & products. No payments. Not vet advice.
```

| Tab | Purpose | Main screens |
|---|---|---|
| 🐾 **Pets** | Buy: browse pets for sale near you | Grid, filters, listing page, contact form, starter kit + care plan, "Which pet suits me?" quiz, "Is this post safe?" check |
| 🏡 **Local Breeders** | "Direct Farm": buy straight from local breeders at farm prices, no broker markup; and **sell** (My farm) | Breeder directory, breeder page, **My farm**: sell form, my listings, enquiries |
| ✨ **BreederNear AI** | The multi-agent assistant for anything, in English or Tamil | Chat with cards and the activity panel; quick starts: *Find my pet*, *List my animals*, *Is this post safe?* |

The idea of a "Local Breeders / Direct Farm" section comes from the founder's earlier PetZonic product concept. No code or design was copied (fresh-code rule, R25).

### First visit (onboarding)

New users don't know the features, so the first visit shows a welcome card at the top of **Pets** (dismissible, remembered):

```
┌ Welcome to BreederNear AI ───────────────┐
│ Buy pets direct from trusted local        │
│ breeders. Every listing is checked.       │
│ 📍 Your district: [Tiruppur ▾]            │
│ 🐾 Browse pets   🏡 Meet local breeders   │
│ ✨ Ask the AI    🐣 I'm a breeder: sell → │
│ Try the demo: Priya (buyer) · Karthik     │
└───────────────────────────────────────────┘
```

Each tab also has a one-line explainer at the top, and empty states always say what to do next.

### 🐾 Pets tab

```
┌──────────────────────────────────────────┐
│ ✨ Not sure which pet? [Take the 4-question quiz] │
│ 🔍 Saw a pet on WhatsApp? [Check the post]│
│ [All][Budgies][Lovebirds][Cockatiels]     │
│ [Finches][Canaries][Dogs][Cats]           │
│ Max ₹ [____]   [✓] Trusted only           │
│ ┌────────┐ ┌────────┐                     │
│ │ 🦜     │ │ 🐕     │  listing cards       │
│ │ Budgie │ │ Lab    │  (badge, price bar,  │
│ │ ₹500 ✅│ │ ₹18k ⚠️│   distance, breeder) │
│ └────────┘ └────────┘                     │
└──────────────────────────────────────────┘
```

- **Listing page** (sheet): photo, species, price with fair-price bar, trust badge with every check (✅/⚠️/⛔), questions to ask the seller, breeder (link to breeder page). Buttons:
  - **Contact breeder**: a short form (message prefilled, editable) → `POST /api/enquiries` → "Demo: saved to the breeder's inbox".
  - **Starter kit & care plan**: kit products with Add / Add all, then the AI care plan.
  - **✨ Ask AI about this pet**: opens the AI tab with the question prefilled.
- **Quiz** ("Which pet suits me?"): 4–6 taps (bird/dog/cat/any, flat/house, young kids, first pet, minutes per day, noise OK, budget) → species option cards → "Show these pets" filters the grid.
- **Is this post safe?** form: paste text and/or upload a screenshot → **Check** → trust card + questions. Nothing is stored.
- The caller's own sandboxed listings appear with a "Yours" tag.

### 🏡 Local Breeders tab (Direct Farm)

```
┌──────────────────────────────────────────┐
│ Direct from the farm: meet breeders near │
│ you. Farm prices, no broker markup.      │
│ [ 🐣 I'm a breeder: open My farm → ]      │
│ ┌ Palladam Pet Birds ─── in your district ┐│
│ │ Budgies · Lovebirds · Cockatiels        ││
│ │ 6 yrs · 3 pets for sale · ✅ trusted    ││
│ └─────────────────────────────────────────┘│
│ ┌ Kovai Paws Kennel ───── about 43 km ────┐│
│ │ Labrador · ✅ Dog-breeder reg. (sim.)    ││
│ └─────────────────────────────────────────┘│
└──────────────────────────────────────────┘
```

- **Breeder page:** name, locality, years, species bred, registration status (dogs; simulated registry), and their pets for sale (same listing cards → listing page).
- **My farm** (the seller side, same app):

```
┌ My farm ──────────────────────────────────┐
│ [ Sell ] [ My listings (2) ] [ Enquiries 1 ] │
│ Sell:                                       │
│ [📷 Add photos] [img][img]                  │
│ "4 jodi lutino lovebird, 5 maasam, 1800…"   │
│ [ ✨ Fill with AI ]                          │
│ Species [Lovebird]  Variety [Lutino]        │
│ Count [4] Unit [pair▾] Age [5] mo           │
│ Price [1800] ▮▮▮▮▯ fair ₹1,500–3,000 (sample)│
│ District [Coimbatore▾] Locality [...]       │
│ Health notes [ ]   ⚠️ missing               │
│ (dogs) SAWB reg. no. [ ]                    │
│ [ Publish with trust check ]                │
│ → ✅ TRUSTED 100 · reasons                   │
└─────────────────────────────────────────────┘
```

  - "✨ Fill with AI" sends photos + message to Gemini and fills a **normal form**; the breeder edits any field (each edit is validated by `PATCH`); missing fields are highlighted; the fair-price bar updates as the price changes.
  - **Publish with trust check** runs the full screening; BLOCKED explains why and suggests legal species.
  - **My listings**: status and trust badge per listing. **Enquiries**: buyer messages per listing.
  - The breeder can skip the form and use the AI tab instead ("List my animals").

### ✨ BreederNear AI tab

The existing multi-agent chat (concierge → listing / trust / match / care agents) with streaming replies, the same cards as the other tabs, photo upload and the **"What the AI did"** activity panel. Quick-start chips: *Find my pet*, *List my animals*, *Is this post safe?*. Opening it from a listing page prefills a question about that listing. The session state carries the quick start's `mode` so the concierge routes correctly.

### Demo buttons

"Try the demo" needs no server endpoint:
- **Priya (buyer, Tiruppur):** sets the district to Tiruppur, opens **Pets** filtered to birds, and shows the quiz prompt; one tap continues in the AI tab with her preset message.
- **Karthik (breeder, Coimbatore):** opens **Local Breeders › My farm › Sell** with his Tamil-English lovebird message prefilled, ready for "✨ Fill with AI".

### Components

| Component | Behaviour |
|---|---|
| Trust badge | Level shown as **icon + word + colour** (✅ TRUSTED / ⚠️ CAUTION / ⛔ BLOCKED) and score |
| Fair-price bar | Position of the price within the sample range: below / fair / above, with a text label |
| Listing card | Photo (or species emoji), species & variety, price per unit, badge, district + distance, breeder name (fictional), "Yours" tag |
| Breeder card | Name, locality, distance, species bred, years, registration status, pets for sale |
| Sell form | Real inputs, AI-filled, validated per field, missing fields highlighted |
| Product card | Name, fictional brand, ₹ price, "why" line, Add |
| Care plan card | Phases as steps; "See a vet if" in a highlighted box; disclaimer |
| Activity panel | Collapsible `agent → tool → short result` (AI tab) |

### Client state

- `breedernear_token`: the login session token (localStorage with "Remember me", otherwise sessionStorage)
- `breedernear_guest_id`: a random device ID (UUID v4) sent as `X-Device-Id`, used only for the same-device sandbox (R33); it is not a login
- `breedernear_district`, `breedernear_tab`, `breedernear_welcome_done`, `breedernear_ai_session_{user}` (the AI tab chat, restored after reload)
- Wrap every `localStorage` access in try/catch with an in-memory fallback.
- Photos are resized in the browser to 1600 px JPEG before upload (phone photos often exceed 5 MB).
- Agent replies are rendered with a minimal markdown renderer that escapes HTML first.
- Agents keep replies short because the cards carry the details (shared prompt rule).
- Tamil text uses Noto Sans Tamil from Google Fonts so it renders on laptops without Tamil fonts.

### Quality bar

- Contrast ≥ 4.5:1, visible focus, labelled buttons, `alt` on images
- Works at 375 px wide; no horizontal scroll; camera capture on phones (`accept="image/*" capture="environment"`)
- `aria-live="polite"` for streaming text
- Loading states: "Reading your photos…", "Running trust checks…"
- Human-readable errors only
