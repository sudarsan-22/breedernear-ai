# Deck sources and measurements

Every number in `BreederNear-AI-deck.pdf` (built by `scripts/build_deck.py` on the organisers' template) comes from here.

## Problem statistics (cited on the "Brief about the idea" and "Business case" slides)

| Claim | Source |
|---|---|
| About 39 million pets in India (2025) | [Euromonitor, Pet Care in India](https://www.euromonitor.com/pet-care-in-india/report) |
| OLX India does not allow pets or any live animals | [OLX: items not allowed](https://help.olx.in/hc/en-us/articles/10910969828637-Items-Services-not-allowed-on-OLX), [Deccan Herald](https://www.deccanherald.com/business/olx-india-has-removed-all-animal-listings-from-its-website-peta-india-880590.html) |
| 300+ of India's ~1,200 bird species found in illegal trade | [WWF-India / TRAFFIC newsletter (c. 2014)](http://awsassets.wwfindia.org/downloads/traffic_panda_8_oct.pdf) |
| Munias dyed to disguise them | [Deccan Herald, Aug 2023: 95 munias dipped in textile dye rescued in Bengaluru](https://www.deccanherald.com/india/karnataka/bengaluru/95-munias-dipped-in-textile-dye-rescued-from-pet-shop-owner-in-south-bengaluru-2657076); [Wildlife SOS, Delhi seizure](https://news.wildlifesos.org/large-scale-illegal-trade-of-birds-exposed-in-new-delhi/) |
| Still happening in 2026: dyed chicks on sale in an unlicensed Bengaluru pet shop; 50+ animals rescued | [PETA India press release, 25 Jun 2026](https://www.petaindia.com/?p=96269) (an advocacy group's own account; the shop was served a notice under the Pet Shop Rules, 2018) |
| Dog breeders must register with the State Animal Welfare Board | PCA (Dog Breeding and Marketing) Rules 2017, e.g. [SCC Online](https://www.scconline.com/blog/post/2017/01/11/mandatory-for-dog-breeders-marketers-to-register-with-state-animal-welfare-board/) |
| India pet care products market: USD 8.6 B (2025), 9.2 B (2026), 13.9 B by 2034 (5.24% CAGR) | [IMARC Group](https://www.imarcgroup.com/india-pet-care-products-market), checked 12 Oct 2026 |
| Founder: five years as breeder, shop owner and broker in Coimbatore; ₹750 setup → over ₹4 lakh; knew about 100 people | Sudarsan's own experience, labelled as such on the slide |
| Trade in all Indian bird species banned since 1990–91; munias and parakeets most traded | [TRAFFIC Post, May 2018](http://awsassets.wwfindia.org/downloads/traffic_post_may_20181.pdf), [Down to Earth](https://www.downtoearth.org.in/coverage/free-as-a---bird-24828) |

We found no reliable Indian statistics on pet-sale scams, so the deck describes the pattern without a number.

## Measured on 10 Oct 2026

| Measure | Result | How |
|---|---|---|
| Agent evals | 69/69 (23 cases × 3 runs) | `scripts/run_evals.sh 3` → `evals/RESULTS.md` |
| Photo screening | 8/8 protected blocked, 0/37 false alarms, 202/202 checks (AI-generated photos; prompt tuned on them) | `scripts/vision_accuracy.py` → `evals/VISION_RESULTS.md` |
| Accessibility | 0 axe-core problems, WCAG 2.2 AA, light/dark, 320/390/1280 px | `pytest -m ui tests/ui` |
| Unit tests / smoke test | 335 / 17 of 17 | CI; `scripts/smoke_test.py` |
| List a pet on the live app (upload + AI fill + publish with trust check) | 17.1 s and 27.3 s (two runs) | live API calls, seller demo account |
| Check a pasted post | 7.0 s and 4.8 s | live API |
| Web app load from Firebase Hosting | ≈ 0.6–0.7 s (index + app.js) | `curl` |
| Gemini: read a certificate / scan a message / symptom urgency / daily-log feedback | 9.4 and 7.6 s / 2.4 and 3.3 s / 7.5 and 6.7 s / 4.3 and 10.4 s (two runs each, 12 Oct, measured while an eval run was also calling Gemini) | `GeminiVision` called directly with the sample certificate and short texts |
| Gemini: listing from a Tamil voice note (15 s audio, no photo) | 13.2 s (12 Oct) | `GeminiVision.extract_listing` with `tests/evals/data/tamil_voice_note.ogg` |
| Gemini tokens: extract listing (1 photo + message) | 2,691 in; 153 out + up to 487 thinking | `usage_metadata`, 2 runs |
| Gemini tokens: screen a photo | 1,869 in; ≈150 out + up to 281 thinking | same |
| Gemini tokens: care plan | 562 in; ≈600 out + up to 1,077 thinking | same |
| Gemini tokens: reply draft | 500 in; ≈157 out + up to 629 thinking | same |
| Gemini tokens: check a text-only post | 1,620 in; ≈149 out + up to 295 thinking | same |

## Cost assumptions

- Gemini 3.8 Flash: $1.50 per 1M input and $7.50 per 1M output tokens (thinking counted as output). This is the price from 1 Jan 2027 as reported by price trackers ([OpenRouter](https://openrouter.ai/google/gemini-3.8-flash), [pricepertoken](https://pricepertoken.com/pricing-page/model/google-gemini-3.8-flash)); the introductory price until then is half. Check Google's [Vertex AI pricing page](https://cloud.google.com/vertex-ai/generative-ai/pricing) before quoting.
- ₹88 = $1.
- Cloud Run with one always-on instance: ₹600–1,000 a month is an estimate, not a measured bill.
