# Brief description (submission form)

The form field "Brief Description of Your Solution (please include how you are leveraging Google services in your submission)" allows **1024 characters**. The submission rules ask us to cover **Firebase, Firestore, Cloud Run and Gemini**. Paste the text inside the block below exactly; `tests/unit/test_submission_text.py` fails if it grows past the limit or drops one of those names.

```text
BreederNear AI is a trusted breeder-to-buyer pet marketplace for India (Retail & Commerce). Buyers find healthy, legal pets from local breeders at fair prices; sellers list a pet from photos and a WhatsApp-style message in English or Tamil.

Gemini on Vertex AI powers five Google ADK agents: multimodal listing extraction, photo screening (protected species, dyed birds, stock photos), buyer matching, care plans and seller reply drafts. Code, not the model, decides trust: protected species are blocked, and ADK callbacks stop medicine doses.

Cloud Run runs the API and agents (FastAPI + ADK, streamed replies). Firestore stores accounts, listings, enquiries and carts. Firebase Hosting serves the web app from Google's CDN. Cloud Storage keeps uploads private; Cloud Build deploys.

Measured: agent evals 66/66 over 3 runs; 8/8 protected species blocked from photos alone with 0/37 false alarms; 0 accessibility issues (WCAG 2.2 AA).
```

Every claim above is checked: the numbers come from [evals/RESULTS.md](../../evals/RESULTS.md), [evals/VISION_RESULTS.md](../../evals/VISION_RESULTS.md) and the accessibility audit (`pytest -m ui tests/ui`). Update them if a later run changes.
