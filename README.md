# BreederNear AI 🐾

### Find the trusted breeder next door: AI agents for safe, fair, direct pet commerce

**Google Cloud AI Builder Cup 2026 (JAPAC) · Theme: Retail & Commerce**

> 🚧 **Status: in active development** during the AI Builder Cup build window (prototype submission: 18 Oct 2026).
> The live demo link and demo video will be added here at submission. This README describes only what is built or being built. Future ideas are listed under [Roadmap](#roadmap).

---

## The problem

> **"The breeder is 50 metres away. The customer never finds them."**

Our founder spent five years as a bird breeder and broker in Coimbatore, India. Over and over he saw the same thing:

- **New buyers walk into a pet shop and overpay**, often for a less healthy animal, because the breeder down the street is invisible online.
- **The real market is hidden** in district WhatsApp and Facebook groups, visible only to insiders.
- **Buyers can't tell good sellers from bad.** Scams are common, and protected native birds are still traded illegally, sometimes dyed to disguise them.
- **Breeders lose hours every day** to manual selling: repeating answers, confirming stock, negotiating.

## One app, both sides, three tabs

| Tab | For | What you can do |
|---|---|---|
| 🐾 **Pets** | Buyers | Browse pets for sale near you, filter by species, price and trust; open a listing to see every trust check; contact the breeder; get a starter kit and care plan; take a quick "Which pet suits me?" quiz; check a post you saw on WhatsApp |
| 🏡 **Local Breeders** | Buyers and sellers | **Direct Farm:** meet breeders near you and buy at the farm price, with no broker markup. **My farm:** sell your animals: add photos and a quick message, tap "✨ Fill with AI", check the form, publish with a trust check; see your listings and buyer enquiries |
| ✨ **BreederNear AI** | Anyone | Ask in English or Tamil. Five Gemini agents find a pet, write a listing, check a post or plan the first two weeks, and show what they did |

Everything works by tapping; the AI does the hard parts on every screen. Chat is there when you'd rather just ask.

## What BreederNear AI does

| Step | What happens | How |
|---|---|---|
| **List** | A breeder sends photos plus a casual message, the way they'd post on WhatsApp, in English or Tamil. They get a complete, priced listing ready to publish. | Gemini multimodal and multilingual extraction into a validated schema; fair-price range from data |
| **Check** | Every listing is screened before buyers see it. Protected species are **blocked**. Dyed birds, visible health concerns, reused photos, suspicious prices and scam language are flagged. Buyers see an explainable trust score. | Gemini vision + deterministic rules (perceptual hashing, price rules, species lists) → trust score **computed in code** |
| **Find** | A buyer browses nearby pets, takes a short quiz or describes their home, family and budget. BreederNear suggests suitable pets and finds trusted breeders nearby, with fair-price indicators. | Rules + ADK agent with tool calls over Firestore; distance by district |
| **Start right** | A personalised starter kit (correct cage size, food, accessories) and a first-14-days care plan with "see a vet if…" signs | Product rules + Gemini structured care plans |
| **Is this listing safe?** | Upload a screenshot of a post seen on WhatsApp or Instagram and get the same trust screening | Same pipeline, nothing stored |

## Architecture

```mermaid
flowchart TD
    B[Breeder phone] -->|HTTPS| CR
    U[Buyer] -->|HTTPS| CR
    subgraph CR[Cloud Run service]
        WEB[Web UI]
        API[FastAPI endpoints]
        subgraph AG[Google ADK multi-agent system]
            ROOT[Concierge]
            LIST[Listing copilot]
            TRUST[Trust & compliance]
            MATCH[Buyer matching]
            CARE[Starter kit & care]
            ROOT --> LIST & TRUST & MATCH & CARE
        end
        CORE[Tools + safety rules + trust score]
        AG --> CORE
        API --> CORE
    end
    AG --> GEM[Gemini Flash]
    CORE --> GEM
    CORE --> FS[(Firestore)]
    CORE --> GCS[(Cloud Storage)]
```

| Layer | Technology |
|---|---|
| AI model | Gemini Flash (newest generally available version, set via configuration) |
| Agent framework | Google Agent Development Kit (ADK), Python |
| Runtime | Google Cloud Run |
| Database | Firestore |
| File storage | Cloud Storage (private bucket) |
| Build / deploy | Cloud Build, Artifact Registry |
| Quality | pytest unit tests, ADK evaluations, GitHub Actions |

Full design: [docs/implementation/01-architecture.md](docs/implementation/01-architecture.md)

## Safety and compliance by design

**AI perceives and converses; code decides.**

- Listings of protected Indian native species are **blocked in code**, whatever the model says.
- Trust scores come from a transparent, deterministic formula. Every badge shows its reasons.
- Dog listings need a State Animal Welfare Board registration number (checked against a *simulated* registry in this prototype).
- Health observations are "signs to ask the seller about", never a diagnosis. No medicine or dosage advice.
- Starter kits respect minimum cage sizes per species.

Details: [docs/product/03-responsible-ai-and-safety.md](docs/product/03-responsible-ai-and-safety.md)

## Simulated vs real

This is a hackathon prototype. To be transparent:

| Component | In this prototype |
|---|---|
| Breeders, listings, accessories | **Synthetic**: fictional names and brands; generated or our own images |
| Fair-price ranges | **Sample data** based on the founder's experience |
| State Animal Welfare Board registry | **Simulated**, with clearly fake `SIM-` numbers |
| Protected / CITES species lists | Curated from public sources (cited in the data files). Not legal advice. |
| Enquiries and cart | **Demo only**: no breeder is contacted, no payment is taken |
| AI extraction, screening, matching, care plans | **Real**: live Gemini calls |
| Trust score, species blocking, welfare rules | **Real**: enforced in code and covered by tests |

BreederNear AI is not a veterinary service and does not sell animals or products.

## Getting started

Requirements: Python 3.12, a Google Cloud project with the Vertex AI API enabled (or an AI Studio API key for local development). One-time cloud setup: [docs/implementation/05-gcp-setup-and-deployment.md](docs/implementation/05-gcp-setup-and-deployment.md).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                  # then fill in your project ID (or GOOGLE_API_KEY)
gcloud auth application-default login # not needed if you use GOOGLE_API_KEY

uvicorn app.main:app --reload --port 8080   # web app + API: http://localhost:8080 (sample data in memory)
PYTHONPATH=. adk web agents                 # ADK developer UI for testing agents
ruff check . && pytest -m "not live"        # lint + unit tests
GOOGLE_CLOUD_PROJECT=<your-project> PYTHONPATH=. python scripts/seed_firestore.py  # sample data (cloud only)
PROJECT_ID=<your-project> scripts/deploy.sh # deploy to Cloud Run
```

## Documentation

All planning, design and submission docs are in [docs/](docs/README.md).

## Roadmap

These are future ideas and are **not** part of the current prototype:

- List a pet by sending a WhatsApp message (WhatsApp Business Platform)
- Integration with State Animal Welfare Board and PARIVESH records
- Breeder score from buyer feedback and animal health after sale
- Escrow-protected payments and health guarantees
- Lifelong pet ID (leg ring / microchip), vet consultations, pharmacy
- Tamil, Hindi and other regional-language interfaces

## How it was built

All code in this repository was written during the AI Builder Cup 2026 build window. The running application uses only Google AI models (Gemini).

## Team

- Sudarsan N (team lead; 5 years as a bird breeder and broker)
- Shreya Azad

## License

MIT. See [LICENSE](LICENSE). Third-party assets are listed in [ATTRIBUTIONS.md](ATTRIBUTIONS.md).
