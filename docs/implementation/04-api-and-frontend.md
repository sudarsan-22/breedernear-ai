# API and Frontend

One FastAPI app (`app/main.py`) built with ADK's `get_fast_api_app(...)`. It serves three things:

| Prefix | What | Provided by |
|---|---|---|
| `/`, `/img/*`, `/app.js`, `/styles.css` | Web UI static files | FastAPI `StaticFiles` mounting `web/` (mounted **last**) |
| `/apps/*`, `/run`, `/run_sse`, `/list-apps` | ADK agent runtime: sessions and runs | `get_fast_api_app(agents_dir="agents", web=False)` |
| `/api/*` | Our endpoints | `app/api.py` |

## ADK runtime endpoints used by the UI

Check exact shapes against the installed ADK version: run `adk api_server agents` locally and open `/docs`.

| Call | Purpose |
|---|---|
| `POST /apps/breedernear/users/{guest_id}/sessions` with `{"state": {"guest_id": "...", "mode": "buyer"}}` | Create a chat session |
| `GET /apps/breedernear/users/{guest_id}/sessions/{session_id}` | Restore after reload |
| `POST /run_sse` with `{"app_name": "breedernear", "user_id": guest_id, "session_id": ..., "new_message": {"role": "user", "parts": [{"text": "..."}]}, "streaming": true}` | Send a message; stream events |

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

| Method & path | Body / params | Returns | Notes |
|---|---|---|---|
| `GET /api/health` | — | `{"status":"ok","model":"...","version":"<git sha>"}` | Smoke test |
| `POST /api/uploads` | multipart `file`, `kind`; header `X-Guest-Id` | `{"upload_id":"UPL_…"}` | Type/size validation (≤ 5 MB) |
| `POST /api/demo/breeder` | — | Demo breeder profile (Karthik) bound to this guest | "Try as breeder" |
| `POST /api/demo/buyer` | — | Demo buyer context (Priya, Tiruppur) | "Try as buyer" |
| `GET /api/listings` | `species`, `district`, `max_price` | Published listings (never BLOCKED) | Browse view, same function as `search_listings` |
| `GET /api/listings/{id}` | — | Listing + screening | |
| `GET /api/breeder/listings` | header `X-Guest-Id` | Demo breeder's listings incl. BLOCKED/DRAFT | |
| `GET /api/breeder/enquiries` | header `X-Guest-Id` | Enquiries for the demo breeder | Inbox |
| `POST /api/enquiries` | `{listing_id, message}` | enquiry | Same function as the `create_enquiry` tool |
| `GET /api/cart`, `POST /api/cart/items`, `DELETE /api/cart/items/{id}` | — | cart | Demo cart |

Every `/api` route and `/run_sse` goes through the rate limiter (`app/ratelimit.py`): an in-memory token bucket per guest ID and IP, 30 messages per hour, returning 429 with a friendly message.

## Frontend (`web/`)

Plain HTML, CSS and JavaScript. No build step. **Mobile-first**: breeders will use phones.

### Home

```
┌──────────────────────────────────────────┐
│ 🐾 BreederNear AI                            │
│ Find trusted breeders near you.           │
│ Fair prices. Legal, healthy pets.         │
│                                           │
│ [ 🛒 I'm buying a pet ]                    │
│ [ 🐣 I'm a breeder    ]                    │
│ [ 🔍 Is this listing safe? ]               │
│                                           │
│ Try the demo: Priya (buyer) · Karthik     │
├──────────────────────────────────────────┤
│ Prototype — sample breeders, listings &   │
│ products. No payments. Not vet advice.    │
└──────────────────────────────────────────┘
```

### Breeder mode

```
┌──────────────────────────────────────────┐
│ Karthik's Aviary · Coimbatore   📥 2      │  inbox count
├──────────────────────────────────────────┤
│ [photo][photo]                            │
│ "4 lutino lovebird pairs 5 months         │
│  ₹1800/pair Saibaba Colony"               │
│ ┌ Draft listing ───────────────────────┐  │
│ │ Lovebird · Lutino · 4 pairs · 5 mo   │  │
│ │ ₹1,800/pair  ▮▮▮▮▮▯▯ fair range       │  │
│ │ ₹1,500–3,000 (sample data)            │  │
│ │ Missing: health notes                 │  │
│ │ [Edit] [Publish]                      │  │
│ └──────────────────────────────────────┘  │
│ ┌ Trust check ─────── ✅ TRUSTED 90 ┐      │
│ │ ✅ Legal species  ✅ Original photos │      │
│ │ ✅ Fair price     ⚠️ Add vaccination  │      │
│ └─────────────────────────────────────┘      │
│ ▸ What the AI did (4 steps)               │
├──────────────────────────────────────────┤
│ [📷] [ Describe your animals…   ] [Send]  │
└──────────────────────────────────────────┘
```

### Buyer mode

Chat with species option cards → listing cards (photo, species, price, fair-range marker, trust badge, district and distance, "Contact" and "Starter kit" buttons) → kit product cards and care plan → cart drawer.

### "Is this listing safe?"

Upload a screenshot and/or paste text → trust card with reasons and "Questions to ask the seller".

### Components

| Component | Behaviour |
|---|---|
| Trust badge | Level shown as **icon + word + colour** (✅ TRUSTED / ⚠️ CAUTION / ⛔ BLOCKED), score, tap to expand reasons |
| Fair-price bar | Position of the price within the sample range: below / fair / above |
| Listing card | Photo, species & variety, count, age, price, badge, district + km, breeder name (fictional) |
| Draft card | Inline-editable fields; missing fields highlighted |
| Product card | Image, name, fictional brand, ₹ price, "why" line, Add |
| Care plan card | Phases as steps; "See a vet if" in a highlighted box; disclaimer |
| Activity panel | Collapsible `agent → tool → short result` |

### Client state

- `localStorage.breedernear_guest_id`: UUID v4
- `localStorage.breedernear_session_id`, `breedernear_mode`
- Wrap every `localStorage` access in try/catch with an in-memory fallback.

### Quality bar

- Contrast ≥ 4.5:1, visible focus, labelled buttons, `alt` on images
- Works at 375 px wide; no horizontal scroll; camera capture on phones (`accept="image/*" capture="environment"`)
- `aria-live="polite"` for streaming text
- Loading states: "Reading your photos…", "Running trust checks…"
- Human-readable errors only
