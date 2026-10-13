# Demo Video Script

**Length:** 2:38 (the form says "up to 3 minutes"; the rules penalise only videos that run over). **Format:** 1920×1080, real screen recordings of the live app at `https://breedernear-ai-2026.web.app` (address bar shown), English voice-over, captions burned in plus an `.srt` file.

**How it was made:** `scripts/build_video.py` records every scene live in Chromium with the two demo accounts (nothing is mocked), synthesises the narration with Google Cloud Text-to-Speech (voice `en-IN-Chirp3-HD-Kore`), fits each recording to its narration (waits for Gemini are sped up; every final result is held for 2 s at normal speed) and joins everything with ffmpeg. Rebuild after any UI change, then reset the demo data (`scripts/seed_firestore.py`).

The narration is in the third person ("our founder…"). To use a team member's own voice instead, record the same lines over the video; the scene timings are in the `.srt` file.

| # | Scene | Screen | Narration |
|---|---|---|---|
| 1 | Title card | `/` | In India, pets are sold on social media like WhatsApp, Instagram and Facebook, with no checks at all, and no dedicated platform we found checks every listing before it goes live. BreederNear AI does. Our founder, a bird breeder from Coimbatore, watched buyers overpay while healthy birds waited a street away. |
| 2 | Login: one tap on Demo customer · Priya | `/` | BreederNear AI connects buyers with trusted local breeders. It runs on Google Cloud: Gemini agents built with the Agent Development Kit on Cloud Run, with Firestore and Firebase Hosting. This is the live app. We log in as our demo buyer, Priya, in Tiruppur. |
| 3 | Pets near Tiruppur → open a listing → trust checks | `/#pets` | Trusted pets nearby come first, and every card shows the distance and whether the price is fair. Open a listing to see why it is trusted: each check, the health notes, and the questions to ask the breeder. |
| 4 | Starter kit (welfare-sized) → 14-day care plan → “See a vet if” | `/#pets` | Tap Starter kit. The cage is sized for the animals, never smaller. Gemini writes a fourteen-day care plan with the warning signs that need a vet, and it never suggests medicine doses. |
| 5 | “Which pet suits me?” → best match | `/#pets` | Not sure which pet fits? Which pet suits me takes a few taps, and rules in code match species to your home, family, time and budget. |
| 6 | Local Breeders directory → breeder page | `/#breeders` | Local Breeders is the direct-from-farm directory: breeders near you, what they breed, and how much you can trust them. Buy straight from the farm, without a broker. |
| 7 | “Is this post safe?”: paste a scam-style post → CAUTION with reasons | `/#pets` | Saw a pet for sale on social media? Paste the post into Is this post safe. Our rules flag a price far below the market, full advance payment and courier-only delivery. |
| 8 | AI tab: family, flat, ₹3,000 → species and listing cards | `/#ai` | Prefer to talk? Seven Gemini agents understand English and Tamil, and use the same tools as the screens. |
| 9 | Seller dashboard (Karthik) | `/#dashboard` | Now the seller side. Karthik sees the last seven days against the week before, a nudge to answer a waiting visit, and charts of his views, enquiries and sales. |
| 10 | Sell: photo + Tamil voice note → Fill with AI → What Gemini heard → Publish → TRUSTED 100 | `/#sell` | A breeder doesn't even need to type. Karthik adds a photo and a voice note in Tamil, a generated voice for this demo. Gemini listens, writes out what it heard, and fills in the listing. Every listing is screened before it goes live. This one is trusted. |
| 11 | Sell a rose-ringed parakeet → BLOCKED in code | `/#sell` | Now try to sell native rose-ringed parakeet chicks. The listing is blocked. Trading protected Indian birds is illegal, and this decision is made in code, so no prompt can talk the AI into it. |
| 12 | Enquiries → Reply → Draft with AI | `/#enquiries` | When a buyer asks a question, Gemini drafts a reply from the listing's facts only, and flags what only the seller can answer. Karthik edits it and sends it. |
| 13 | Architecture slide from the deck | `/` | Under the hood: seven agents on Cloud Run, Gemini on Vertex AI, Firestore and Firebase. In testing, every protected species photo was blocked and all 66 agent test runs passed (generated from evals/RESULTS.md). BreederNear AI: find the trusted breeder next door. |

## Upload checklist

- [ ] Watch the whole file once; check the sound
- [ ] YouTube → Upload → title "BreederNear AI: find the trusted breeder next door (AI Builder Cup 2026)" → visibility **Unlisted**
- [ ] Optional: Subtitles → upload `BreederNear-AI-demo.srt` (captions are already burned in)
- [ ] Open the link in a private window while logged out; it plays
- [ ] Put the link in the deck (`VIDEO_URL` in `scripts/build_deck.py`, then rebuild), the README and the submission form

## The 3–4 minute cut (`scripts/build_video.py --long`)

The organisers' wording on video length differs: the T&C say "strictly under three minutes" and the form field says "up to 3 minutes", while the submission page and emails say "3 to 4 minutes". We submitted the 2:31 cut on 12 Oct and asked support which applies. **On 13 Oct support confirmed in writing: strictly under 3 minutes, and 2:31 meets it.** The long cut (3:11) is therefore not used; it is kept here only for reference: the same scenes plus four, each inserted after the scene named.

| After | Scene | Narration |
|---|---|---|
| Starter kit | "Which pet suits me?" → best match | Not sure which pet fits? Which pet suits me takes a few taps and suggests pets for Priya's home, from the same fixed rules, with the reasons. Pets that don't suit a flat or young children are left out, and she is told why. |
| Visit | Local Breeders → tap the Verified breeder badge | Local Breeders lists the breeders near her, with their distance and whether they are verified. Tap any badge to see exactly what it means and how it was decided. Buying straight from the breeder means farm prices, with no broker in between. |
| Post check | Share this warning; Impact so far | She can share that warning back to the group in one tap, and a protected bird comes with a way to report it. Impact so far counts the listings checked, the animals stopped and the scam warnings raised, live from the app's own data. |
