# Submission Checklist

Use this from **16 Oct** onward. Every box must be ticked before pressing Submit on the Hack2skill dashboard.

**Deadline:** 18 Oct 2026, 11:59 PM IST (the "Prototype Submission" module on the Hack2skill dashboard, open since 7 Sep). **Our target:** 18 Oct, 12:00 PM IST. The portal can be slow near the deadline, and uploads can fail.

## A. Eligibility (do once, by 11 Oct)

- [x] Both members are working professionals employed at organisations (confirmed 9 Oct)
- [x] Both members confirmed: 21+, not enrolled in any course (full- or part-time), living in India (confirmed 10 Oct)
- [x] ID and employment proof ready for both members (confirmed 10 Oct)
- [ ] Neither member is on any other AI Builder Cup team
- [x] Team stays at 2 members (Sudarsan N, Shreya Azad); no 3rd/4th member (decided 9 Oct)
- [ ] Both members joined the official Discord (Sudarsan ✅ 10 Oct; Shreya pending)
- [x] Organisers confirmed in writing that the startup background is fine (R25, 10 Oct); reply email saved

## B. Live prototype URL

- [ ] Deployed on **Cloud Run**; URL in the form `https://breedernear-…run.app`
- [ ] Opens in an **incognito window while logged out**, on a laptop
- [ ] Opens on a **phone** (mobile data, not Wi-Fi), and the layout fits the screen
- [ ] The login screen shows both demo logins; **Demo customer · Priya** and **Demo seller · Karthik** log straight in with preloaded data
- [ ] Customer app (Pets, Local Breeders, AI, Account) and seller app (Dashboard, Listings, Enquiries, AI, Farm) work by tapping and in the AI tab
- [ ] Every step of the smoke test passes, see [../implementation/06-testing-and-evaluation.md](../implementation/06-testing-and-evaluation.md#4-pre-submission-smoke-test)
- [ ] `--min-instances=1` set (no cold start for judges): `MIN_INSTANCES=1 scripts/release.sh` on 17 Oct
- [x] Budget alert configured (₹1,000/month); free-trial credit valid until 9 Jan 2027, after the 4 Dec end of judging (checked 10 Oct)
- [ ] Model is **not** `gemini-2.x`; it is set via `BREEDERNEAR_MODEL`
- [ ] "Prototype — sample breeders, listings and products. No payments. Not veterinary advice." visible in the UI footer
- [ ] Revision name of this known-good deployment written down for rollback: `________________`

## C. GitHub repository

- [x] Repo is **public**: https://github.com/sudarsan-22/breedernear-ai (checked 9 Oct; keep it public)
- [ ] README rewritten to match what is actually built (see [02-rules-dos-and-donts.md §5](02-rules-dos-and-donts.md#5-things-in-the-current-readme-that-must-change-before-submission))
- [ ] README contains: theme, one-line pitch, **live URL**, **video link**, architecture diagram, Google Cloud services used, local setup steps that really work, how to run tests and evals, a "Simulated vs real" table, roadmap, team
- [x] `LICENSE` file present (MIT, matching the README), added 9 Oct
- [ ] `.env.example` present; **no** `.env`, keys or service-account JSON committed (`git log -p | grep -i "api_key\|private_key"` returns nothing)
- [ ] `ATTRIBUTIONS.md` (created 9 Oct) lists the source and licence of every image or dataset not created by us
- [ ] Commit history shows steady daily work (not one giant commit)
- [ ] CI (GitHub Actions) is green
- [ ] No team emails or phone numbers anywhere in the repo

## D. Demo video

- [x] Video built 10 Oct: `~/Downloads/BreederNear-AI-demo.mp4`, 2:38, 1080p ([script](../submission/02-demo-video-script.md))
- [ ] Duration **≤ 2:55** (strictly under 3:00), checked on the *uploaded* file
- [ ] Uploaded to YouTube as **Unlisted or Public** (or Drive with "Anyone with the link: Viewer")
- [ ] Link opens in incognito while logged out
- [ ] English voice-over; captions on
- [ ] Shows the **live deployed URL** in the browser address bar at least once
- [ ] Covers the scenes in [../submission/02-demo-video-script.md](../submission/02-demo-video-script.md)
- [ ] Every feature shown is real and works in the live app

## E. Deck (PDF)

- [x] Draft built 10 Oct: `docs/submission/BreederNear-AI-deck.pdf` (1.4 MB); video link still to add
- [ ] Built on the **organisers' template** (Google Slides → File → Download → PPTX; keep its slide order and headings), content from [../submission/01-pitch-deck-outline.md](../submission/01-pitch-deck-outline.md)
- [ ] Includes **solution architecture** and **business case** (both are T&C requirements)
- [ ] Theme "Retail & Commerce" stated on the title slide
- [ ] Explains theme alignment, problem, how the solution addresses it, scalability/production path, and a short user guide
- [ ] Every statistic has a source in a footnote; nothing invented
- [ ] Simulated parts are labelled; roadmap items are labelled "Roadmap"
- [ ] Contains live URL, GitHub URL, video URL
- [ ] Exported as **PDF, ≤ 5 MB**; text readable when zoomed out
- [ ] All in English

## F. Submission form

The "Prototype Submission" module (read 10 Oct). Every field is required; nothing says it can be edited after Submit, so treat Submit as final.

| Field | Limit | Our answer |
|---|---|---|
| Prototype Link Deployed on GCP or Cloud Run | URL | `https://breedernear-655711985039.asia-south1.run.app` (Cloud Run, as the field asks; the Firebase Hosting URL `https://breedernear-ai-2026.web.app` is in the README and deck) |
| Final Prototype PPT/Deck converted into PDF | **PDF, up to 5 MB**; must use the organisers' template (R47) | `BreederNear-AI-deck.pdf` |
| GitHub Repository Link (Public Access) | URL with `https://` | `https://github.com/sudarsan-22/breedernear-ai` |
| Demo Video Link (up to 3 minutes) | URL | YouTube (Unlisted) |
| Brief Description of Your Solution (how we use Google services) | **1024 characters**; must cover Firebase, Firestore, Cloud Run and Gemini (R46) | [../submission/04-brief-description.md](../submission/04-brief-description.md) |

- [ ] Live URL pasted and clicked from the form preview
- [ ] GitHub URL pasted and clicked
- [ ] Video URL pasted and clicked
- [ ] Deck PDF uploaded (≤ 5 MB, on the template)
- [ ] Brief description pasted; counter shows ≤ 1024
- [ ] All text fields in English, proofread
- [ ] **Submitted.** Screenshot of the confirmation saved, and the confirmation email received

## G. After submission (19 Oct – 7 Nov, and to 4 Dec if shortlisted)

- [ ] `main` frozen; only critical fixes, each followed by the smoke test
- [ ] Smoke test run every 2–3 days; app still up
- [ ] Billing and credits checked weekly
- [ ] Email, dashboard and Discord checked daily
- [ ] If shortlisted on 7 Nov: decide the 2 travellers immediately and start Singapore visas (~4 weeks' notice)
