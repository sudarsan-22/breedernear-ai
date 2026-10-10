# Rules, Do's and Don'ts

This document lists **everything that can get BreederNear rejected, disqualified, or marked down**, along with what we do about each item. Every rule is traced to its source: "T&C: <section name>" = [Initiative Terms & Conditions](https://docs.google.com/document/d/e/2PACX-1vRm7ChZ6Ij9fG7uFDkxzUMpwgVeBmnQ6cMDnAIEEX84AiLBOOQ9cYbl3S5OzFBbcVb8TF55s-eVpiXb/pub); FAQ = [aibuildercup.com/Faqs.html](https://aibuildercup.com/Faqs.html); Session = [kickoff session](05-kickoff-session-notes.md).

Severity:
- 🔴 **Disqualification / ineligible:** the entry is thrown out.
- 🟠 **Heavy mark-down:** we lose most of a judging criterion.
- 🟡 **Risk:** this can break the demo or hurt us during evaluation.

---

## Risk tracker

Every risk below has a status. **✅ Resolved** = done and checked. **🔧 Built-in** = solved by the design; verify when the code lands. **👤 Owner action** = a person must do it by the date given.

| # | Risk | Status | Resolution / next action | Owner | By |
|---|---|---|---|---|---|
| R1 | README makes false or unbuilt claims (public repo) | ✅ Resolved | README rewritten 9 Oct (see §5). Final accuracy pass on 16 Oct. | Sudarsan | 16 Oct |
| R2 | README names Gemini 2.0 (retiring during judging) | ✅ Resolved | Removed. Model comes from `BREEDERNEAR_MODEL` in [.env.example](../../.env.example) (`gemini-3.8-flash`). Re-check the newest GA Flash ID before the final deploy. | Sudarsan | 17 Oct |
| R3 | README says MIT but there was no LICENSE | ✅ Resolved | [LICENSE](../../LICENSE) added (MIT, 2026, Sudarsan N and Shreya Azad) | — | — |
| R4 | README's setup steps (`npm`, `.env.example`) didn't exist | ✅ Resolved | Wrong npm steps removed; `.env.example` added; real setup steps go in with the code | Sudarsan | 16 Oct |
| R5 | Secrets accidentally committed to the public repo | ✅ Resolved (guard) | [.gitignore](../../.gitignore) blocks `.env`, keys and service-account JSON. Run the secrets check in the [submission checklist](04-submission-checklist.md) before submitting. | Sudarsan | 18 Oct |
| R6 | Copyright: real brands or others' images | ✅ Resolved (policy) | [ATTRIBUTIONS.md](../../ATTRIBUTIONS.md) policy: fictional brands, our own/generated images, every third-party asset logged before commit | Shreya | ongoing |
| R7 | Team emails or phone numbers in the public repo | ✅ Resolved | Docs contain names only; checked 9 Oct | — | — |
| R8 | Ineligible member (student) | 👤 Owner action | Both confirmed working professionals (9 Oct). **Still to confirm: neither is enrolled in a part-time course.** | Both | 11 Oct |
| R9 | ID / employment proof requested and not ready | 👤 Owner action | Keep a government ID and an employment letter or payslip ready for each member | Both | 11 Oct |
| R10 | Leaving the official channel | 👤 Owner action (Sudarsan ✅ joined 10 Oct; Shreya pending) | Both join the [Discord](https://discord.gg/x5GRzJbKpa) and stay in it; check email and dashboard daily | Both | 10 Oct |
| R11 | Pre-existing code (fresh-code rule) | 🔧 Built-in | All code written fresh in this repo; first commit 23 Sep is inside the window. **Commit and push every day**, and never squash history. | Both | daily |
| R12 | Shallow "prompt in, text out" AI (40% criterion) | 🔧 Built-in | Multi-agent ADK design, multimodal, tools, schemas, code guardrails, evals ([agent design](../implementation/02-agent-design.md)) | Sudarsan | 14 Oct |
| R13 | Theme misalignment (zero alignment score) | 🔧 Built-in | Retail & Commerce, mapped to the theme's own wording ([judging strategy](03-judging-strategy.md)) | Both | — |
| R14 | Diagnosis / dosage claims; welfare | 🔧 Built-in | Health signs worded as "ask the seller", disclaimer added by code, minimum cage rules ([safety](../product/03-responsible-ai-and-safety.md)) | Sudarsan | 14 Oct |
| R15 | Looks like real selling / soliciting business | 🔧 Built-in | Demo enquiries and cart only, no payments, fictional breeders, prototype labels in the UI and README | Both | 14 Oct |
| R16 | Not deployed on Google Cloud / no live URL | ✅ Resolved | Project `breedernear-ai-2026` with billing; deployed to Cloud Run on 10 Oct (`breedernear-00001-qb2`); live Gemini reply verified. Keep redeploying after each feature. | — | — |
| R17 | App down during evaluation (credits, cold start, quota abuse) | 👤 Owner action | Check credit expiry; budget alert; `min-instances=1`; rate limit; smoke test every 2–3 days | Sudarsan | 17 Oct → 7 Nov |
| R18 | Video ≥ 3:00 or not public | 👤 Owner action | Script targets 2:40 ([script](../submission/02-demo-video-script.md)); check uploaded duration; test the link in incognito | Shreya | 17 Oct |
| R19 | Deck missing architecture or business case | 👤 Owner action | Slides 7 and 12 in the [deck outline](../submission/01-pitch-deck-outline.md) | Shreya | 16 Oct |
| R20 | Invented statistics in the deck | 👤 Owner action | Only sourced numbers, with footnotes; otherwise leave them out | Shreya | 16 Oct |
| R21 | Deck or video shows features that don't work | 👤 Owner action | Every feature shown is live, or labelled "Roadmap" | Both | 17 Oct |
| R22 | Late submission / portal problems | 👤 Owner action | Submit by **18 Oct, 12:00 PM IST** | Both | 18 Oct |
| R23 | Repo not public at submission | ✅ Resolved | Repo is already public (checked 9 Oct). Keep it public. | — | — |
| R24 | Shortlisted but no visa in time | 👤 Owner action | Check Singapore visa requirements for both members now; apply right after 7 Nov | Both | 7 Nov |
| R25 | **Entry seen as part of the earlier PetZonic startup project** (T&C: Tech Stack & Freshness: "pre-existing products, ongoing projects… will be disqualified") | ✅ Resolved 10 Oct: Hack2skill support replied in writing that startups may participate, an existing startup or business idea is not an issue, founder domain knowledge may be used, and the startup background and founder journey may be mentioned in the deck and video, provided the submitted prototype complies with the guidelines. Reply kept (save it as PDF with the team records). | (1) Nothing copied from the old platform repos: code, UI designs, images, data or brand files ([ATTRIBUTIONS](../../ATTRIBUTIONS.md)). (2) This is a new, standalone AI-agent product built from scratch in this repo during the window. (3) Deck and video present the founder's *experience*, not the old platform's features, screenshots or traction. (4) Written clarification from the organisers received 10 Oct (see status); keep the email thread. (5) Old platform repos stay private (verified 9 Oct). (6) The startup's waitlist site **petzonic.co** is live and stays live: don't hide it, **disclose it** in the clarification email. (7) The entry was renamed **BreederNear AI** on 10 Oct to avoid confusion with the startup brand. The founder story stays in the deck, and the Git history keeps the old name (never rewrite it). | Sudarsan | 10 Oct |
| R26 | Wildlife and animal-law content: helping illegal trade, or overclaiming legal accuracy | 🔧 Built-in | Protected species blocked in code; lists cite sources; UI says "helps flag", never "guarantees legality"; no real registry claims ([safety](../product/03-responsible-ai-and-safety.md)) | Sudarsan | 14 Oct |
| R27 | Sample prices or registries mistaken for real data | 🔧 Built-in | Labelled "sample market data" and "simulated registry" in the UI, README and deck | Both | 14 Oct |
| R28 | **T&C is a live document**: it can change without notice and was renumbered on 9 Oct | 👤 Owner action | Re-read on 11, 15, 17 and 18 Oct, then weekly; log it in the [compliance matrix](06-terms-compliance-matrix.md#tc-re-check-log). Docs cite sections by name. | Sudarsan | 18 Oct |
| R29 | **Employer IP or confidentiality conflict** (we warrant we're sole authors; no confidential content) | 👤 Owner action | Each member checks their employment contract for IP-assignment or moonlighting clauses; if unclear, get written employer permission. Use personal laptops, accounts and time; nothing from work. | Both | 11 Oct |
| R30 | No agreement between the two members on IP ownership, prize split, taxes, travel, or post-hackathon use | 👤 Owner action | Sign the [team agreement](06-terms-compliance-matrix.md#team-agreement-r30-agree-in-writing-keep-it-private-not-in-this-repo); keep it private | Both | 12 Oct |
| R31 | **IP right of first refusal and publication rights vs the PetZonic startup** | 👤 Owner action | Until ~June 2027, no exclusive transfer or licence of this code (incl. to your own company or investors) without first offering the organiser the same terms. Keep this code separate. No confidential investor-deck material in the submission. | Sudarsan | ongoing |
| R32 | Public `petZonic` GitHub org profile described the earlier platform, linking the entry to an "ongoing project" | ✅ Resolved | All earlier-platform repos, including `petZonic/.github` (org profile) and `petzonic-keycloak`, made private and verified on 9 Oct. Keep them private until results. | — | — |
| R33 | Strangers post offensive or explicit listings on the public demo, which judges then see | 🔧 Built-in | Guest-created listings are **visible only to their creator**; public search shows only curated seed listings. Non-animal images are rejected. ([requirements](../product/02-requirements.md#f2-breeder-listing-assistant)) | Sudarsan | 13 Oct |
| R34 | Live-animal trade seen as "inconsistent with sponsor brand image" | 🔧 Built-in | Welfare-first framing (legal, healthy, responsibly bred animals); no "pets as products" language; no crowded cages or very young animals in visuals; adoption on the roadmap | Both | 16 Oct |
| R35 | Non-Google AI models at runtime | 🔧 Built-in | The running application uses only Google models (Gemini via Agent Platform). No third-party model APIs. | Both | ongoing |
| R36 | Personal email exposed in public commit history | 👤 Owner action (optional) | Commits show the author's Gmail. Optionally switch future commits to the GitHub noreply address (GitHub → Settings → Emails). | Sudarsan | optional |
| R37 | Name or trademark conflict for the entry's name | ✅ Resolved | Entry renamed **BreederNear AI** on 10 Oct. Checked on 10 Oct: no .com/.ai/.in/.co/.app domains registered, no app or trademark found in web search. ("PetZonic" clashed with petzonic.com, and "PetTrust" with a registered US trademark and pettrust.ai.) Optional: formal search on the IP India public trademark search before any commercial launch. | — | — |
| R38 | Real people, animals or premises in the video or photos without consent | 👤 Owner action | Written permission from anyone shown or heard, and from owners of any real animals or aviaries filmed; record it in `ATTRIBUTIONS.md` (without personal details) | Shreya | 17 Oct |
| R39 | Submission form has fields or limits we haven't seen (file size, character limits, editability) | 👤 Owner action | Open the Prototype Submission module **now** and paste every field here; plan the deck file size and text to fit | Sudarsan | 10 Oct |
| R40 | Fee or "fast-track" scams posing as the organiser | 👤 Owner action | Participation is free at every stage; never pay; report to support | Both | ongoing |
| R41 | Passport expires too soon for Singapore travel | 👤 Owner action | Both check passport validity (generally ≥ 6 months beyond travel); renew now if needed | Both | 15 Oct |
| R42 | Prize payment: TDS, PAN, bank details | 👤 Owner action | Covered by the team agreement; keep PAN and bank details ready | Both | if shortlisted |
| R43 | Dependency licence incompatible with MIT or the IP warranty | 🔧 Built-in | Permissive licences only (MIT/BSD/Apache-2.0/HPND); check before adding any dependency; listed in `requirements.txt` | Sudarsan | ongoing |
| R44 | **Breaking Hack2skill Discord community rules** (ban → lose the official channel) | 👤 Owner action | Never post promotional links (no petzonic.co, waitlist or startup links); don't reuse other members' ideas or repost community content; stay on-topic and respectful; never post emails or personal data in public channels; ask eligibility questions by email or the private 🎫 support ticket | Both | ongoing |
| R45 | **No confirmed Google Cloud credits**, so the project runs on our own billing | ✅ Mitigated | Paid billing account linked (no free-trial credits). Budget **₹1,000/month** with email alerts at 25/50/90/100% and forecast 100% (created 10 Oct). `min-instances=0` until 17 Oct. Check spend weekly. | Sudarsan | weekly |

---

## 1. Team and eligibility

| | Rule | Source | What we do |
|---|---|---|---|
| 🔴 | No student on the team, full-time or part-time. One student disqualifies everyone, even after the finale. | T&C: Eligibility, FAQ | Both members are working professionals employed at organisations (confirmed 9 Oct). Still confirm that neither is enrolled in any part-time course, degree or diploma. |
| 🔴 | Every member is 21+ at registration. | T&C: Eligibility | Confirmed. |
| 🔴 | Every member is physically based in and a legal resident of a JAPAC country. | T&C: Eligibility | Confirmed (India). |
| 🔴 | The organiser can ask for government ID or employment proof at any time. Not complying means immediate disqualification. | T&C: Eligibility | Keep an ID and an employment letter or payslip ready for each member. |
| 🔴 | One person on one team, one submission, one theme. Cross-team entries disqualify all of them. | T&C: Team Composition, FAQ | Neither member joins any other team. We submit once, under Retail & Commerce. |
| 🔴 | The roster freezes on **11 Oct, 11:59 PM IST**. No adds or swaps after that. | T&C: Team Composition | Decided: the team stays at 2 (Sudarsan N, Shreya Azad). Minimum met; both can travel if shortlisted. |
| 🔴 | Shortlisted teams must respond on the official channels and attend checkpoints. Leaving the dashboard or the Discord is a disqualification risk. | T&C: Team Composition, Rules of Conduct | Both members join the Discord and stay in it. Check email and the dashboard daily until 4 Dec. |

## 2. Originality and the code itself

| | Rule | Source | What we do |
|---|---|---|---|
| 🔴 | **Fresh code only**, created during the hackathon timeline. Pre-existing products, ongoing projects, or code developed before launch are disqualified. | T&C: Tech Stack & Freshness, FAQ | All code is written in this repo from scratch. **Don't copy code from any earlier personal or company project.** Open-source *libraries* installed as dependencies (ADK, FastAPI…) are fine. |
| 🟠 | Judges check the GitHub repo to confirm the work was done during the hackathon. | Session | **Commit small and often, every day, with meaningful messages.** Never squash the history into one commit. The first commit (23 Sep 2026) is inside the window. |
| 🔴 | No third-party copyrighted or proprietary content without permission. This covers images, logos, brand names, datasets and fonts. | T&C: Rules of Conduct, Intellectual Property, Content Warranties | Breeders, listings and the accessories catalogue use **fictional names and brands and our own or generated images**. No real brand logos or product photos (no Royal Canin, Drools, Pedigree, etc.). Animal photos are our own (with the owner's permission) or CC0, and their source is recorded in `ATTRIBUTIONS.md`. |
| 🔴 | No malware or harmful code. | T&C: Intellectual Property, Content Warranties | Standard dependencies only, installed from PyPI/npm. |
| 🔴 | No **falsehoods or misrepresentations**. | T&C: Content Warranties | Don't claim features, users, partnerships, certifications or numbers we don't have. Mark mocked parts as "simulated" everywhere (UI, README, deck). See §5 below. |
| 🔴 | The submission must not **advertise or solicit business**. | T&C: Content Warranties | No real payments, no real breeders, no real animal sales. Enquiries and the cart are clearly labelled **demo**, and the app is described as a prototype. |
| 🔴 | No unlawful, offensive, explicit or brand-damaging content. | T&C: Rules of Conduct, Eligibility, Content Warranties | Keep the content family-friendly. Don't show graphic injury images in the demo; use mild cases (rash, eye discharge, hot spot). |

## 3. Technology requirements

| | Rule | Source | What we do |
|---|---|---|---|
| 🔴 | Built **primarily on Google Cloud**. Primarily another cloud means disqualification. | T&C: Tech Stack & Freshness, FAQ | 100% Google Cloud: Cloud Run, Firestore, Cloud Storage, Gemini, Secret Manager, Cloud Build, Artifact Registry. Don't add AWS, Azure, Vercel or Supabase. |
| 🔴 | Must use **Gemini or Gemma**, or an agentic platform (Agent Platform, Antigravity, AI Studio). | Themes page, Session | Gemini (Flash) via ADK. |
| 🟠 | Leveraging Google technologies "in the right way" | Session | **No non-Google model APIs at runtime**: the app calls only Gemini. |
| 🔴 | Must be **deployed** on Cloud Run or Firebase, with a working live link. | T&C: Deliverables, FAQ | Cloud Run, region `asia-south1`. |
| 🟠 | "Not just a simple send a prompt to the AI, get a response." Superficial AI scores low on the 40% criterion. | Session, Themes page | Multi-agent ADK system with tool calling, structured outputs, multimodal input, code-enforced guardrails and evals. See [03-judging-strategy.md](03-judging-strategy.md). |
| 🟡 | **Model retirement:** `gemini-2.5-flash` and `gemini-2.5-pro` retire on **20 Oct 2026**, which is *during* evaluation. `gemini-3.6-flash` retires 19 Nov 2026. | Google model lifecycle docs | Use the newest GA Flash model (`gemini-3.8-flash` as of 9 Oct, re-check in AI Studio on build day). The model ID lives in **one env var** (`BREEDERNEAR_MODEL`) so it can be swapped without code changes. **Never use `gemini-2.x`.** The current README mentions "Gemini 2.0" and must be fixed. |

## 4. Submission artefacts

| | Rule | Source | What we do |
|---|---|---|---|
| 🔴 | Live URL works end to end. | T&C: Deliverables | Smoke-test from an incognito window on a phone **and** a laptop before submitting, and again daily during evaluation. |
| 🔴 | Video **strictly under 3:00**. | T&C: Deliverables | Target **2:40**, hard max 2:55. Check the duration on the uploaded file. |
| 🔴 | Video link is **public**. Drive links need "Anyone with the link: Viewer". | Session | Prefer **YouTube (Unlisted or Public)**. Test the link in incognito while logged out. |
| 🔴 | GitHub repo is **public** and contains the source. | T&C: Deliverables | Make it public before submission. Test in incognito. |
| 🔴 | Deck covers **solution architecture and the business case**. | T&C: Deliverables | Uploaded as PDF. See [../submission/01-pitch-deck-outline.md](../submission/01-pitch-deck-outline.md). |
| 🟠 | The prototype must **actually show what the deck says**. | Session | Every feature in the deck is either live in the demo or labelled "Roadmap". |
| 🔴 | Everything is in **English**: code, docs, deck, video. | Themes page, Session | Even if we add Hindi or Tamil chat support as a feature, the docs, deck and video narration stay in English. |
| 🟠 | State the chosen theme clearly. | Themes page | "Retail & Commerce" appears on deck slide 1, in the README, and in the submission form. |

## 5. Things in the current README that must change before submission

✅ **Resolved on 9 Oct.** The README written on 23 Sep described things that didn't exist and parts that were technically wrong, and the repo is public. Under T&C: Content Warranties (no misrepresentation) and "the prototype must show what you claim", it was rewritten on 9 Oct: status marked "in development", all items below fixed, and a "Simulated vs real" table added. **On 16 Oct it gets a final pass** to add the live URL, video link, real setup commands and measured eval results, and to remove anything that didn't get built.

Record of what was wrong and how it was fixed:

| README says | Problem | Fix |
|---|---|---|
| "Gemini 2.0 / 1.5" | Retired or retiring models | Name the model we actually use |
| "Google Antigravity Multi-Agent Orchestrator" running inside Cloud Run | Antigravity is a development tool (an agentic IDE/harness), not a runtime orchestrator. Google judges will spot this. | Runtime orchestration = **ADK**. Mention Antigravity only if we really use it to build. |
| "Zero-cold-start performance", "100% serverless microservices" | Not true by default (cold starts exist unless `min-instances ≥ 1`), and we run one service, not microservices | Describe what we actually configure |
| "Cross-referencing Schedule H/VCI regulatory registries" | No public registry API exists and we won't have one | "Validated against a *simulated* vet registry. Real registry integration is on the roadmap." |
| "Real-time geolocation", "Automated courier dispatch", "Ethical breeder hub" | Not in the MVP | Move to Roadmap |
| `npm install`, `npm run dev`, `.env.example`, LICENSE | None of these exist; the stack is Python | Correct setup instructions; add LICENSE and `.env.example` |
| Antigravity badge links to cloud.google.com | Misleading link | Remove or fix |

## 6. Privacy and personal data

| | Rule | Source | What we do |
|---|---|---|---|
| 🔴 | Data handling follows India's IT Act. Don't use others' personal data without permission. | T&C: Content Warranties, Data Security | **Synthetic data only.** No real breeder or customer names, phone numbers or registration numbers (simulated registry uses `SIM-` numbers). Sample "scam post" screenshots are written by us, not taken from real groups. |
| 🟡 | The public repo is visible to everyone. | — | **Never commit** API keys, `.env`, service-account JSON or team emails and phone numbers. `.gitignore` covers `.env*` and `*.json` keys. Use Secret Manager or ADC. |

## 7. Staying alive during evaluation (19 Oct – 7 Nov, and to 4 Dec if shortlisted)

| | Risk | What we do |
|---|---|---|
| 🟡 | Free-trial credits or billing run out, so the app goes down | Check the billing account and credit expiry date. Set a **budget alert**. Don't delete the project. |
| 🟡 | A judge opens the link and waits through a cold start, or gets an error | `--min-instances=1` from 17 Oct to the end of evaluation |
| 🟡 | Strangers abuse the public endpoint and burn the Gemini quota or budget | Per-guest rate limit, 5 MB upload cap, capped `--max-instances` (1 while sessions are in-memory), budget alert |
| 🟡 | A judge has to sign up or log in | **No login.** Guest session is created automatically. "Try as Priya (buyer)" / "Try as Karthik (breeder)" buttons preload demo identities. |
| 🟡 | A new user or judge doesn't discover the features, or sees the app as "just a chatbot" | Three always-visible tabs (Pets · Local Breeders · BreederNear AI); first-visit welcome card; every core job works by tapping, with AI inside those screens; chat is optional (decided 10 Oct). Test with someone who hasn't seen the app. |
| 🟡 | We push a broken change after submitting | Freeze `main` after submission. Redeploys only for critical fixes, and only after the smoke test. Keep the last good revision's name so we can roll back with one command. |

## 8. Quick do / don't list

**Do**
- Build one deep, polished end-to-end flow rather than many shallow features.
- Make AI essential: multimodal input, multi-agent routing, tool calls, structured outputs.
- Enforce safety rules **in code**, not just in prompts.
- Label everything simulated as simulated.
- Commit daily and keep the history.
- Deploy on day 1 and redeploy often.
- Submit **early on 18 Oct**, not at 11:58 PM.
- Keep the app running until results, and until 4 Dec if shortlisted.

**Don't**
- Don't paste code from earlier projects.
- Don't use real brand names, logos, product photos or someone's pet photo without permission.
- Don't claim a diagnosis. Photo health observations are "signs to ask the seller about".
- Don't recommend medicines or dosages.
- Don't let any listing of a protected native species through, and don't claim the lists are complete legal advice.
- Don't copy anything from the earlier PetZonic platform repos, and don't present that platform's features or traction as this entry.
- Don't take real payments or link to real stores.
- Don't use `gemini-2.x` models.
- Don't commit secrets or personal contact details.
- Don't put a login wall in front of the judges.
- Don't let the video reach 3:00.
- Don't leave the Discord or ignore organiser emails.
