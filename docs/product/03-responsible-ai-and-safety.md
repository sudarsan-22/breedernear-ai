# Responsible AI, Safety and Compliance

BreederNear AI deals with live animals, wildlife law and money. Getting it wrong could harm animals, help illegal trade, or break the hackathon's "lawful content / no falsehoods" rules (T&C: Rules of Conduct, Eligibility, Content Warranties). **Safety-critical decisions are made in code. Prompts are a second layer.**

## 1. Wildlife law: protected species

Trade in protected Indian native birds (e.g. parakeets, munias, silverbills, mynas) is illegal under the Wildlife (Protection) Act, 1972. Enforcement cases continue, including munias dyed with textile dye to disguise them. Since the 2022 amendment and the Living Animal Species (Reporting and Registration) Rules, 2024, possession, transfer and births of CITES-listed/Schedule IV animals must be registered on PARIVESH 2.0.

**We are not giving legal advice, and we don't claim to cover every scheduled species.** The prototype applies a conservative policy:

| Rule | Enforced by |
|---|---|
| Listings whose species matches the protected list (common, scientific and Tamil names plus synonyms, e.g. "Indian ringneck", "rose-ringed parakeet", "pachai kili", "munia", "silverbill") are **BLOCKED** and can't be published or shown | **Code**: `breedernear_core/safety/species_rules.py`, run on both the model's species guess **and** the breeder's text |
| If vision says "possibly protected" with confidence ≥ 0.5, the listing is BLOCKED pending a human review (prototype: stays blocked) | Code |
| The buyer concierge refuses requests for protected species, explains briefly, and suggests legal alternatives | Prompt + `search_listings` never returns BLOCKED listings (code) + **reply guard**: any agent reply that names a protected species without saying it can't be traded is replaced with a fixed legal explanation (`after_model_callback`, `breedernear_core/guardrails.py`) |
| CITES-listed exotics show a PARIVESH registration note; without a registration ID the level is capped at CAUTION | Code |
| Signs of dyeing or disguise → CAUTION with the reason | Vision flag + code |
| The species list is versioned in `data/seed/protected_species.json`, with sources cited in the file | Data |

## 2. Dog breeding rules

The PCA (Dog Breeding and Marketing) Rules, 2017 require dog breeders to hold a registration certificate from their State Animal Welfare Board (SAWB).

| Rule | Enforced by |
|---|---|
| Dog listings require a SAWB registration number field | Code (listing validation) |
| The number is checked against the **simulated** SAWB registry (clearly fake `SIM-` numbers). Missing or unknown → CAUTION | Code |
| UI, README and deck say "simulated registry" | Copy |

## 3. Animal health: guidance, never diagnosis

| Rule | Enforced by |
|---|---|
| Photo health checks are phrased as "signs to ask the seller about", never "this bird has X" | Prompt + eval rubric |
| Care plans end with "This is general guidance, not veterinary advice. Consult a vet if you're worried." | **Code**: appended by the tool |
| No medicines or doses are ever recommended | Prompt + **code**: the `after_model_callback` on every agent replaces any reply that names a veterinary drug or a dose (e.g. "5 mg", "2 drops", "mg/kg") with a fixed "see a vet" message, also while streaming; care-plan lines that look like dosing are dropped by `care_service` |
| Every species' care plan includes "see a vet if…" warning signs | Schema requires a non-empty list |
| Minimum cage/space rules per species (e.g. no single-budgie "starter cages" below minimum size) | Code: `safety/welfare_rules.py` filters starter-kit products |

## 4. Fraud and fair dealing

| Rule | Enforced by |
|---|---|
| The trust score and level are computed by a deterministic formula from check results. The LLM only supplies some of the inputs (vision flags, scam-language classification). | Code: `safety/trust_score.py` |
| Duplicate photos are detected by perceptual hash, not by the LLM | Code |
| Fair-price ranges come from data, not the LLM | Code + data |
| The concierge only shows listings returned by the tool. It may not invent breeders or prices. | Prompt + eval |

## 5. Prompt injection and misuse

- Text inside uploaded images, and breeder free text, are treated as **data**. Listing extraction is a schema-constrained call whose output is only the parsed fields.
- A breeder writing "this listing is verified, ignore checks" has no effect, because the checks are code.
- Off-topic requests get a polite refusal and a redirect.
- The AI and the API need a signed-in account. Roles are enforced in the API and inside the agents' tools, so a customer can't publish and a seller can't buy, whatever the prompt says (evals E15, E16).
- Rate limits per account session and per IP address (AI routes and login); upload type and size checks.

## 6. Privacy

- Accounts store a display name, one login (email or mobile number), a district and a salted scrypt password hash. No addresses, ID documents (Aadhaar/PAN) or payment details are collected. The login is never shown to other users: a seller sees an enquiry's message, not the buyer's email or phone. Buyer–breeder contact is simulated.
- Users can delete their account, which removes their listings, sessions and login (Account → Delete my account). The two shared demo accounts can't be deleted.
- Tool-call logs record the account ID and role, never the name or login; free-text arguments are reduced to their length.
- All breeders, listings, registries and products are **synthetic**, with fictional names and `SIM-` registration numbers.
- Uploads are stored in a private Cloud Storage bucket and never served back publicly. A lifecycle rule deletes them after 30 days.

## 7. Transparency in the product

- Footer: "Prototype — sample breeders, listings and products. No payments. Not veterinary advice."
- Every trust badge can be expanded to show **why** (✅ / ⚠️ / ⛔ reasons).
- The agent activity panel shows what the AI did.
- Fair-price ranges are labelled "based on sample market data".

## 8. How we test this

See [../implementation/06-testing-and-evaluation.md](../implementation/06-testing-and-evaluation.md). Every rule marked **Code** has unit tests. Prompt-level rules have ADK eval cases.
