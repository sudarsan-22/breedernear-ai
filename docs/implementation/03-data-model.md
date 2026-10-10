# Data Model

Firestore (Native mode, location `asia-south1`). **All data is synthetic**: fictional breeders, listings, products and registries.

## Collections

### `users/{user_id}` (accounts, added 10 Oct)

```json
{ "id": "USR_8f2c…", "role": "seller", "name": "Karthik", "login": "karthik@example.com", "login_type": "email",
  "password_hash": "scrypt$16384$8$1$<salt-b64>$<hash-b64>", "district": "coimbatore", "device_id": "<uuid>",
  "demo": false, "created_at": "...",
  "farm": { "farm_name": "Karthik's Aviary", "seller_type": "home_breeder", "locality": "Saibaba Colony",
            "species": ["lovebird", "budgerigar"], "sawb_registration_no": null, "verification": "not_required" } }
```

- `login_index/{normalized login}` → `{ "user_id": ... }`, created with a create-if-absent write so two accounts can't share an email or mobile.
- `auth_sessions/{sha256(token)}` → `{ "user_id", "role", "device_id", "expires_at" }`. The token itself is never stored.
- Mobile numbers are normalised to `+91XXXXXXXXXX`; emails to lower case.
- Demo accounts (`demo: true`) have no password and expire with their session.
- A seller's listings carry `owner_user_id` and `device_id`; they are visible to the owner and to any account signed in with the same `device_id` (same-device sandbox, R33).

### `breeders/{breeder_id}`

```json
{
  "id": "BRD-CBE-001",
  "display_name": "Karthik's Aviary",
  "district": "coimbatore",
  "locality": "Saibaba Colony",
  "species_bred": ["lovebird", "budgerigar", "cockatiel"],
  "years_experience": 5,
  "sawb_registration_no": null,
  "simulated": true
}
```

Seed about 12 breeders across Coimbatore, Tiruppur, Erode, Salem, Madurai, Chennai and Bengaluru: birds, dogs and cats. Include one dog breeder **without** a SAWB number and one with a number not in the registry, to demonstrate CAUTION.

### `listings/{listing_id}`

```json
{
  "id": "LST-0007",
  "breeder_id": "BRD-CBE-001",
  "status": "PUBLISHED",
  "visibility": "public",
  "owner_user_id": null,
  "draft": { "...ListingDraft..." },
  "photos": ["img/listings/LST-0007.webp"],
  "photo_hashes": ["c3a1f0..."],
  "screening": { "...Screening..." },
  "trust_level": "TRUSTED",
  "trust_score": 90,
  "species_key": "lovebird",
  "district": "coimbatore",
  "price_inr": 1800,
  "created_at": "..."
}
```

`status` is one of `DRAFT`, `PUBLISHED`, `BLOCKED`. `visibility` is `public` for curated seed listings and `owner_only` for every guest-created listing (sandboxing, rule R33). Guest listings carry `owner_user_id`. Top-level `species_key`, `district`, `price_inr` and `trust_level` are copied out of `draft` and `screening` for querying.

Composite index: `species_key` + `status` + `price_inr`.

Seed about 40 listings, including deliberate demo cases:

| Case | Expected |
|---|---|
| Healthy budgie pair, fair price, clear photo | TRUSTED |
| Lovebird pair priced at 30% of the range minimum, "full advance, courier only" | CAUTION (price + scam language) |
| Cockatiel listing reusing another listing's photo | CAUTION (duplicate photo) |
| Labrador litter, no SAWB number | CAUTION |
| "Indian ringneck / pachai kili" listing | BLOCKED (never shown to buyers) |
| Munia listing with unnaturally bright colour | BLOCKED (protected) and dye flagged |

### `drafts/{draft_id}`

Unpublished `ListingDraft` + `upload_ids` + `breeder_id`. Deleted on publish.

### `enquiries/{enquiry_id}`

```json
{ "listing_id": "LST-0007", "breeder_id": "BRD-CBE-001", "guest_id": "...", "message": "...", "demo": true, "created_at": "..." }
```

### Accessories catalogue (`data/seed/products.json`, read-only)

```json
{
  "id": "PRD-CAGE-003",
  "name": "Roomy Flight Cage 76×46×92 cm",
  "brand": "Featherhaven",
  "species": ["budgerigar", "lovebird_peach_faced", "cockatiel", "..."],
  "category": "cage",
  "dimensions_cm": [76, 46, 92],
  "price_inr": 3499,
  "stock": 15,
  "description": "..."
}
```

The catalogue is a versioned file like the other reference data (the demo cart never changes stock). Starter kits pick the cheapest in-stock product per category for the species; cages must pass `welfare_rules.cage_is_big_enough` for the species and count, and the deliberately too-small `PRD-CAGE-001` demonstrates that rule. Breeding products (nest boxes) are never put in a starter kit.

Fictional brands only: Featherhaven, Tailnook, PawNest, Whiskerwell. Each name was web-searched on 10 Oct and no pet brand with that name was found ("Tailwise" was dropped because it is a real dog-breeder marketplace). Re-check before adding a new brand name. No medicines are sold. 45 products: cages, perches, feeders, seed/pellet food, cuttlebone, nest boxes, dog beds, collars, puppy food, cat litter, carriers.

### `carts/{guest_id}`

Demo cart: `{"items": [{"product_id": "...", "quantity": 1}], "updated_at": "..."}`

### Reference data (versioned JSON files, read-only)

Reference data is read from `data/seed/` at runtime rather than Firestore, so every change is reviewable in git and the deployed rules always match the code.

| File | Contents |
|---|---|
| `price_ranges.json` | Per species: `unit` and `varieties` (`{"default": [1200, 2500], "lutino": [1500, 3000]}`); flagged `confirmed_by_founder: false` until reviewed |
| `districts.json` | District centroids (`{"key": "coimbatore", "name": "Coimbatore", "state": "TN", "lat": 11.0168, "lng": 76.9558}`) and aliases (Kovai, Tirupur, Trichy…) |
| `species.json` | Care facts used by rules: group, lifespan, min cage size per pair, noise, beginner- and kid-friendly, hands-on, space needed, daily minutes, watch-outs |
| `sawb_registry_sample.json` | Simulated: `{ "registration_no": "SIM-TNAWB-DB-0042", "name": "...", "state": "TN", "valid_until": "2027-03-31" }` |

Protected and CITES species lists are files too: `data/seed/protected_species.json` and `data/seed/cites_species.json`. Each entry has common names, scientific name, Tamil and Hindi names where known, synonyms, and a `source` field.

**All price ranges are sample data** and are labelled so in the UI ("based on sample market data"). Base them on the founder's experience; don't present them as official market prices.

## Cloud Storage

Bucket `gs://<PROJECT_ID>-breedernear-uploads` (`asia-south1`, uniform access, **not public**).

- Path: `uploads/{guest_id}/{upload_id}.{ext}`; metadata `kind` = `listing_photo` | `external_listing`
- Lifecycle: delete after 30 days
- Accepted: `image/jpeg`, `image/png`, `image/webp`, `image/heic`, max 5 MB each, validated server-side
- Not served back from the bucket. Seeded listing images are static files in `web/img/listings/`.

## Seed files and assets

| File | Contents | Created by |
|---|---|---|
| `data/seed/breeders.json`, `listings.json`, `products.json` | Synthetic records | Us (Gemini-assisted drafting, human-reviewed) |
| `data/seed/price_ranges.json`, `districts.json`, `species.json` | Reference data | Us (founder's experience; labelled sample) |
| `data/seed/protected_species.json`, `cites_species.json` | Species lists with `source` per entry | Us, from official schedules/CITES lists |
| `data/seed/sawb_registry_sample.json` | ~10 fake registrations (`SIM-` prefix) | Us |
| `web/img/listings/*` | One illustrative photo per visible sample listing (the reused-photo demo pair shares one on purpose) | Generated with `gemini-3.1-flash-image` by `scripts/generate_sample_images.py`; labelled "Illustrative photo" in the app; recorded in `ATTRIBUTIONS.md` |
| `data/samples/*` | Demo/eval photos (healthy pair, dyed-looking bird, duplicate, screenshot of a "scam" post we write ourselves) | Us |

`scripts/seed_firestore.py` loads the seed files idempotently. Screening for sample listings is computed by the same trust code as guest listings (`breedernear_core/catalog.py`), including pHashes of seeded listing images once they exist; re-run the script after changing trust rules. Local runs (`BREEDERNEAR_BACKEND=memory`) load the same sample data in memory.
