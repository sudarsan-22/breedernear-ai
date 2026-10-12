# ruff: noqa: E501  (narration text: long strings are easier to edit than wrapped ones)
"""Build the demo video from real recordings of the live app (dev only).

Usage:
    PYTHONPATH=. python scripts/build_video.py [OUT_DIR]
    PYTHONPATH=. python scripts/build_video.py --assemble [OUT_DIR]   # title card and final join only, reusing the clips

Needs Playwright with Chromium (CHROMIUM=/path/to/chrome to use a local build), imageio-ffmpeg (a portable
ffmpeg with libx264 and libass), poppler's pdftoppm for the deck slide, and gcloud Application Default
Credentials for Google Cloud Text-to-Speech. Every scene is recorded live from the Firebase-hosted app with the
demo accounts; nothing is mocked. The narration is synthesised per scene, and each recording is fitted to its
narration. Writes BreederNear-AI-demo.mp4 (captions burned in) and BreederNear-AI-demo.srt. The script recorded
here is also in docs/submission/02-demo-video-script.md.

Recording publishes test listings on the shared demo seller account; run scripts/seed_firestore.py afterwards.
"""

import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
WEB = "https://breedernear-ai-2026.web.app"
VOICE_NOTE = ROOT / "tests" / "evals" / "data" / "tamil_voice_note.ogg"   # synthetic Text-to-Speech, not a real voice
VOICE_SECONDS = 15
HOST = "breedernear-ai-2026.web.app"
PROJECT = "breedernear-ai-2026"
VOICE = "en-IN-Chirp3-HD-Kore"
VW, VH, BAR = 1440, 765, 60                    # page viewport (CSS px), scaled ×1.333 under a 60 px address bar
W, H = 1920, 1080
GAP = 0.35                                      # silence after each scene's narration (s)
HOLD_MS = 3000                                  # the last result stays on screen at least this long (before speed-up)
FONTS = Path.home() / ".local/share/fonts/googlesansflex"

# The closing line's numbers come from evals/RESULTS.md and evals/VISION_RESULTS.md (see close_line()).
SCENES = [
    ("title", "/", "In India, pets are sold on social media like WhatsApp, Instagram and Facebook, but there is no dedicated, trusted platform for this market. BreederNear AI is that platform. Our founder, a bird breeder from Coimbatore, watched buyers overpay while healthy birds waited a street away."),
    ("login", "/", "BreederNear AI connects buyers with trusted local breeders. It runs on Google Cloud, with Gemini agents on Cloud Run, Firestore and Firebase. We log in as our demo buyer, Priya."),
    ("pets", "/#pets", "Every pet shows a match score for Priya's home, worked out by fixed rules, and trusted breeders nearby come first. Open a listing to see each trust check and the questions to ask."),
    ("kit", "/#pets", "Tap Starter kit: the cage is sized for the animals, never smaller, and Gemini writes a fourteen-day care plan with the signs that need a vet."),
    ("visit", "/#pets", "Priya can message the breeder with an AI-drafted note, and book a visit. There is no delivery and no payment in the app: she sees the birds and their parents first."),
    ("companion", "/#account", "After the visit she taps I bought this pet, and the care companion starts: a daily log with AI feedback, a growth tracker, a health calendar, and a symptom checker that says how urgently to see a vet, never which medicine."),
    ("check", "/#pets", "Saw a pet for sale on social media? Paste the post into Is this post safe. Our rules flag a price far below the market, full advance payment and courier-only delivery."),
    ("chat", "/#ai", "Prefer to talk? Seven Gemini agents understand English and Tamil, and use the same tools as the screens."),
    ("dashboard", "/#dashboard", "Now the seller side. Karthik sees this week against last, a nudge to answer a waiting visit, and charts of his views, enquiries and sales."),
    ("verify", "/#farm", "He is a Verified breeder: a phone code and facility photos checked by Gemini, with no ID documents."),
    ("sell", "/#sell", "A breeder doesn't even need to type. Karthik adds a photo and records a voice note in Tamil. Gemini listens, writes out what it heard, and fills in the listing. Every listing is screened before it goes live. This one is trusted."),
    ("blocked", "/#sell", "Try to sell native rose-ringed parakeet chicks, and the listing is blocked. Trading protected Indian birds is illegal, and this decision is made in code."),
    ("reply", "/#enquiries", "Visit requests and messages arrive here. Gemini drafts a reply from the listing's facts, and Karthik edits and sends it."),
    ("close", "/", ""),
]


def close_line() -> str:
    import re as _re

    evals = (ROOT / "evals" / "RESULTS.md").read_text()
    m = _re.search(r"(\d+) full runs: (\d+)/(\d+) case runs passed", evals)
    runs = (f"{m.group(2)} of {m.group(3)} agent test runs passed" if m and m.group(2) != m.group(3)
            else f"all {m.group(3)} agent test runs passed" if m else "the agent tests passed")
    return ("Under the hood: seven agents on Cloud Run, Gemini on Vertex AI, Firestore and Firebase. In testing, "
            f"every protected species photo was blocked and {runs}. BreederNear AI: find the trusted breeder next door.")


# ---------------------------------------------------------------- tools
def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(*args):
    subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *map(str, args)], check=True)


def token() -> str:
    out = subprocess.run(["gcloud", "auth", "application-default", "print-access-token"], check=True,
                         capture_output=True, text=True)
    return out.stdout.strip()


def tts(text: str, path: Path) -> float:
    body = {"input": {"text": text}, "voice": {"languageCode": "en-IN", "name": VOICE},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 48000, "speakingRate": 1.0}}
    req = urllib.request.Request("https://texttospeech.googleapis.com/v1/text:synthesize", json.dumps(body).encode(),
                                 {"Authorization": f"Bearer {token()}", "x-goog-user-project": PROJECT,
                                  "Content-Type": "application/json"})
    path.write_bytes(base64.b64decode(json.load(urllib.request.urlopen(req, timeout=120))["audioContent"]))
    return wav_seconds(path)


def wav_seconds(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def font(size: int, weight: int = 400):
    return ImageFont.truetype(str(FONTS / f"GoogleSansFlex-{weight}.ttf"), size)


def address_bar(path_part: str, out: Path) -> None:
    img = Image.new("RGB", (W, BAR), (222, 225, 230))
    d = ImageDraw.Draw(img)
    for i, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
        d.ellipse((22 + i * 26, 22, 38 + i * 26, 38), fill=c)
    d.rounded_rectangle((120, 10, W - 40, BAR - 10), radius=20, fill=(255, 255, 255))
    d.text((150, BAR // 2), f"https://{HOST}{'' if path_part == '/' else path_part}", font=font(24), fill=(32, 33, 36),
           anchor="lm")
    img.save(out)


def title_card(out: Path) -> None:
    img = Image.new("RGB", (W, H), (194, 65, 12))
    d = ImageDraw.Draw(img)
    for y in range(H):                                   # the app's Sunrise gradient: saffron to deep orange
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(234 - 60 * t), int(108 - 52 * t), int(28 - 16 * t)))
    d.rounded_rectangle((W // 2 - 90, 250, W // 2 + 90, 430), radius=44, fill=(255, 255, 255))
    d.text((W // 2, 342), "BN", font=font(84, 700), fill=(194, 65, 12), anchor="mm")
    d.text((W // 2, 540), "BreederNear AI", font=font(110, 700), fill=(255, 255, 255), anchor="mm")
    d.text((W // 2, 640), "Find the trusted breeder next door", font=font(54, 500), fill=(255, 237, 213), anchor="mm")
    d.text((W // 2, 800), "Google Cloud AI Builder Cup 2026  ·  Retail & Commerce", font=font(36), fill=(254, 215, 170),
           anchor="mm")
    img.save(out)


def deck_slide(page: int, out: Path) -> None:
    prefix = out.with_suffix("")
    subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-scale-to-x", str(W), "-scale-to-y", str(H), "-png",
                    "-singlefile", str(ROOT / "docs/submission/BreederNear-AI-deck.pdf"), str(prefix)], check=True)


# ---------------------------------------------------------------- browser scenes
def lovebird_photo(out: Path) -> Path:
    img = Image.open(ROOT / "web/img/listings/LST-0002.webp").convert("RGB")
    img = ImageOps.mirror(img).crop((30, 20, img.width - 30, img.height - 20))     # fresh photo, not a duplicate
    img.save(out, "JPEG", quality=90)
    return out


def goto(page, url):
    """page.goto with retries: Chromium sometimes fails a navigation when the system certificate store changes."""
    for attempt in range(4):
        try:
            return page.goto(url)
        except Exception:  # noqa: BLE001
            if attempt == 3:
                raise
            page.wait_for_timeout(1500)


def login(page, email):
    goto(page, WEB)
    page.evaluate("localStorage.clear(); sessionStorage.clear(); localStorage.setItem('breedernear_welcome_done','1')")
    goto(page, WEB)
    page.wait_for_selector("#auth-login")
    page.fill("#auth-login", email)
    page.fill("#auth-password", "demo12345")
    page.get_by_role("button", name="Log in", exact=True).last.click()
    page.wait_for_function("['#pets','#dashboard'].includes(location.hash)")
    page.wait_for_load_state("networkidle")


def slow_type(page, selector, text_value, delay=28):
    page.click(selector)
    page.keyboard.type(text_value, delay=delay)


def scroll_sheet(page, to):
    page.evaluate(f"document.querySelector('#sheet .panel .content').scrollTo({{top: {to}, behavior: 'smooth'}})")


def act_login(page, d):
    goto(page, WEB)
    page.evaluate("localStorage.clear(); sessionStorage.clear(); localStorage.setItem('breedernear_welcome_done','1')")
    goto(page, WEB)
    page.wait_for_selector("#auth-login")
    return lambda: (page.wait_for_timeout(int(d * 600)),
                    page.get_by_role("button", name="Demo customer · Priya").click(),
                    page.wait_for_selector(".pet"))


def act_pets(page, d):
    goto(page, WEB + "/#pets")
    page.wait_for_selector(".pet")

    def go():
        page.wait_for_timeout(1500)
        page.mouse.wheel(0, 380)
        page.wait_for_timeout(int(d * 330))
        page.locator(".pet").nth(0).click()
        page.wait_for_selector("#sheet[open] .fact")
        page.wait_for_timeout(int(d * 180))
        scroll_sheet(page, 420)
    return go


def act_kit(page, d):
    goto(page, WEB + "/#pets")
    page.wait_for_selector(".pet")
    page.locator(".pet").nth(0).click()
    page.wait_for_selector("#sheet[open] .fact")

    def go():
        page.get_by_role("button", name="Starter kit").click()
        page.wait_for_selector("text=See a vet if", timeout=90000)
        page.wait_for_timeout(int(d * 250))
        page.evaluate("(()=>{const c=document.querySelector('#sheet .panel .content'); const t=[...c.querySelectorAll('h3')].find(e=>e.textContent.startsWith('First 14 days')); c.scrollTo({top: t ? t.offsetTop - 20 : 900, behavior:'smooth'});})()")
        page.wait_for_timeout(int(d * 250))
        page.evaluate("(()=>{const c=document.querySelector('#sheet .panel .content'); const t=[...c.querySelectorAll('*')].find(e=>e.textContent.trim().startsWith('See a vet if')); c.scrollTo({top: t ? t.offsetTop - 60 : 1600, behavior:'smooth'});})()")
    return go


def act_quiz(page, d):
    goto(page, WEB + "/#pets")
    page.wait_for_selector(".pet")

    def go():
        page.wait_for_timeout(600)
        page.get_by_role("button", name="Which pet suits me?").click()
        page.wait_for_selector("#sheet[open]")
        page.wait_for_timeout(int(d * 250))
        page.get_by_role("button", name="Show my matches").click()
        page.wait_for_selector("#sheet-content >> text=Best match", timeout=60000)
    return go


def act_breeders(page, d):
    goto(page, WEB + "/#pets")
    page.wait_for_selector(".pet")

    def go():
        page.wait_for_timeout(500)
        page.locator("#top-tabs a[href='#breeders'], #tabbar a[href='#breeders']").first.click()
        page.wait_for_selector(".breeder")
        page.wait_for_timeout(int(d * 300))
        page.mouse.wheel(0, 300)
        page.wait_for_timeout(int(d * 150))
        page.locator(".breeder").first.click()
        page.wait_for_selector("#sheet[open] .avatar.lg")
    return go


def act_dashboard(page, d):
    goto(page, WEB + "/#dashboard")
    page.wait_for_selector(".metric .spark", timeout=30000)

    def go():
        page.wait_for_timeout(int(d * 250))
        page.evaluate("document.querySelector('.metrics').scrollIntoView({block: 'center', behavior: 'smooth'})")
        page.wait_for_timeout(int(d * 300))
        page.evaluate("document.querySelector('.chart-card').scrollIntoView({block: 'start', behavior: 'smooth'})")
    return go


def act_visit(page, d):
    goto(page, WEB + "/#pets")
    page.wait_for_selector(".pet")

    def go():
        page.locator(".pet").nth(1).click()
        page.wait_for_selector("#sheet[open] .fact")
        page.wait_for_timeout(int(d * 120))
        page.get_by_role("button", name="Contact").click()
        page.get_by_role("button", name="Draft with AI").click()
        page.wait_for_function("document.querySelector('#sheet textarea').value.length > 40 && !document.querySelector('#sheet textarea').value.startsWith('Hello, is your')", timeout=60000)
        page.wait_for_timeout(1500)
        page.get_by_role("button", name="Back").click()
        page.wait_for_selector("#sheet[open] .fact")
        page.get_by_role("button", name="Book a visit").click()
        page.wait_for_selector("text=Request visit")
        page.wait_for_timeout(1200)
        page.get_by_role("button", name="Request visit").click()
        page.wait_for_selector("text=See my visits")
    return go


def act_companion(page, d):
    goto(page, WEB + "/#account")
    page.wait_for_selector("text=My visits")
    page.wait_for_selector("button:has-text('I bought this pet')", timeout=20000)

    def go():
        page.evaluate("document.querySelector('button.btn.small.primary').scrollIntoView({block: 'center', behavior: 'smooth'})")
        page.wait_for_timeout(1200)
        page.get_by_role("button", name="I bought this pet").first.click()
        page.wait_for_selector("#sheet[open] input")
        slow_type(page, "#sheet input", "Kiwi", 60)
        page.get_by_role("button", name="Yes, I bought this pet").click()
        page.wait_for_selector("text=Today's log", timeout=20000)
        page.wait_for_timeout(1500)
        goto(page, WEB + "/#mypets/PET_DEMO_MANGO")
        page.wait_for_selector("text=Today's log", timeout=20000)
        page.wait_for_timeout(int(d * 120))
        for anchor in ("Recent days", "Growth", "Symptom checker"):
            page.evaluate(f"[...document.querySelectorAll('.h-sub')].find(e => e.textContent === '{anchor}')?.scrollIntoView({{block: 'start', behavior: 'smooth'}})")
            page.wait_for_timeout(int(d * 150))
    return go


def act_verify(page, d):
    goto(page, WEB + "/#farm")
    page.wait_for_selector("text=Mobile number")

    def go():
        page.wait_for_timeout(600)
        page.evaluate("[...document.querySelectorAll('b')].find(e => e.textContent === 'Verification')?.scrollIntoView({block: 'start', behavior: 'smooth'})")
    return go


def act_check(page, d):
    goto(page, WEB + "/#pets")
    page.wait_for_selector(".pet")

    def go():
        page.wait_for_timeout(800)
        page.get_by_role("button", name="Check a seller post").click()
        page.wait_for_selector("#sheet[open] textarea")
        slow_type(page, "#sheet-content textarea", "Lovebirds pair 500 only!! Full advance GPay, courier only, all India delivery", 22)
        page.get_by_role("button", name="Check this post").click()
        page.wait_for_selector("#sheet-content .tag", timeout=120000)
        page.wait_for_timeout(int(d * 200))
        scroll_sheet(page, 260)
    return go


def act_chat(page, d):
    goto(page, WEB + "/#ai")
    page.wait_for_selector("#chat-input")

    def go():
        slow_type(page, "#chat-input", "Pet bird for my 8 year old daughter. We live in a flat in Tiruppur, budget 3000.", 20)
        page.keyboard.press("Enter")
        page.wait_for_selector(".bubble.ai", timeout=120000)
        page.wait_for_timeout(9000)
        page.evaluate("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'})")
    return go


def act_sell(page, d, photo):
    goto(page, WEB + "/#sell")
    page.wait_for_selector(".big-input")

    def go():
        with page.expect_file_chooser() as fc:
            page.locator(".add-photo").first.click()
        fc.value.set_files(str(photo))
        page.wait_for_timeout(600)
        page.fill(".big-input", "")
        page.get_by_role("button", name="Record a voice note instead").click()   # the fake microphone plays VOICE_NOTE
        page.wait_for_selector(".voice-live")
        page.wait_for_timeout(int(VOICE_SECONDS * 1000) + 400)
        page.get_by_role("button", name="Stop").click()
        page.wait_for_selector(".voice-clip")
        page.wait_for_timeout(600)
        page.get_by_role("button", name="Fill with AI").click()
        page.wait_for_selector("#f-price_inr", timeout=120000)
        page.locator(".callout.info", has_text="What Gemini heard").scroll_into_view_if_needed()
        page.wait_for_timeout(2600)
        page.mouse.wheel(0, 500)
        page.wait_for_timeout(1500)
        page.get_by_role("button", name="Publish with trust check").click()
        page.wait_for_selector(".success", timeout=120000)
        page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        page.wait_for_timeout(1500)
        page.mouse.wheel(0, 320)
    return go


def act_blocked(page, d):
    goto(page, WEB + "/#sell")
    page.wait_for_selector(".big-input")

    def go():
        page.fill(".big-input", "")
        slow_type(page, ".big-input", "pachai kili kunjugal virpanaikku, 2 for 800 rubai, Kovai", 24)
        page.get_by_role("button", name="Fill with AI").click()
        page.wait_for_selector("#f-price_inr", timeout=120000)
        page.wait_for_timeout(1200)
        page.get_by_role("button", name="Publish with trust check").click()
        page.wait_for_selector(".success, .callout.bad", timeout=120000)
        page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
    return go


def act_reply(page, d):
    goto(page, WEB + "/#enquiries")
    page.wait_for_selector(".list-row")

    def go():
        page.wait_for_timeout(1200)
        page.get_by_role("button", name="Reply").first.click()
        page.wait_for_selector("#sheet[open]")
        page.wait_for_timeout(800)
        page.get_by_role("button", name="Draft with AI").click()
        page.wait_for_function("document.querySelector('#sheet textarea').value.length > 20", timeout=120000)
        page.wait_for_timeout(int(d * 250))
    return go


def record(pw, name, role, act, duration, work: Path, chromium) -> tuple[Path, float]:
    """Record one scene; returns the video and the offset where the scene's action starts."""
    args, permissions = [], []
    if name == "sell":            # the sell scene records a Tamil voice note through a fake microphone
        wav = work / "voice-note.wav"
        run("-i", VOICE_NOTE, "-ar", "48000", "-ac", "1", wav)
        args = ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                f"--use-file-for-fake-audio-capture={wav}"]
        permissions = ["microphone"]
    browser = pw.chromium.launch(executable_path=chromium, args=args) if chromium else pw.chromium.launch(args=args)
    state = work / f"state-{role}.json"
    ctx = browser.new_context(viewport={"width": VW, "height": VH}, permissions=permissions,
                              storage_state=str(state) if state.exists() and name != "login" else None,
                              record_video_dir=str(work / f"rec-{name}"), record_video_size={"width": VW, "height": VH})
    page = ctx.new_page()
    t0 = time.monotonic()
    go = act(page, duration)
    page.wait_for_timeout(700)
    offset = time.monotonic() - t0
    start = time.monotonic()
    go()
    page.wait_for_timeout(HOLD_MS)                 # keep the final result on screen
    left = duration + GAP - (time.monotonic() - start)
    if left > 0:
        page.wait_for_timeout(int(left * 1000) + 300)
    video = page.video
    ctx.close()
    browser.close()
    return Path(video.path()), offset


def save_state(pw, role, email, work: Path, chromium):
    browser = pw.chromium.launch(executable_path=chromium) if chromium else pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": VW, "height": VH})
    page = ctx.new_page()
    login(page, email)
    ctx.storage_state(path=str(work / f"state-{role}.json"))
    browser.close()


# ---------------------------------------------------------------- assembly
def fit_clip(video: Path, offset: float, target: float, bar: Path, out: Path) -> None:
    """Fit a recording to its narration: speed up the action if needed, but play the final 2 s at 1×."""
    probe = subprocess.run([ffmpeg(), "-i", str(video)], capture_output=True, text=True).stderr
    dur = next(float(h) * 3600 + float(m) * 60 + float(s) for line in probe.splitlines() if "Duration" in line
               for h, m, s in [line.split("Duration: ")[1].split(",")[0].split(":")])
    end = dur - 0.2
    hold = 2.0
    main = max(0.5, end - hold - offset)
    speed = max(1.0, main / max(0.5, target - hold))
    vf = (f"[0:v]trim=start={offset:.2f}:end={end - hold:.2f},setpts=(PTS-STARTPTS)/{speed:.3f}[a];"
          f"[0:v]trim=start={end - hold:.2f}:end={end:.2f},setpts=PTS-STARTPTS[b];"
          f"[a][b]concat=n=2:v=1,fps=30,tpad=stop_mode=clone:stop_duration={target:.2f},trim=duration={target:.2f},"
          f"scale={W}:{H - BAR}:flags=lanczos[v];[1:v]scale={W}:{BAR}[bar];[bar][v]vstack=inputs=2,format=yuv420p[out]")
    run("-i", video, "-i", bar, "-filter_complex", vf, "-map", "[out]", "-c:v", "libx264", "-preset", "medium",
        "-crf", "20", "-r", "30", out)
    print(f"  {out.name}: recorded {main + hold:.1f}s → {target:.1f}s (action ×{speed:.2f})")


def still_clip(image: Path, target: float, out: Path) -> None:
    run("-loop", "1", "-i", image, "-t", f"{target:.2f}", "-vf", f"scale={W}:{H},format=yuv420p,fps=30",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", "30", out)


def srt_time(t: float) -> str:
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(t * 1000 % 1000):03d}"


def captions(scenes, durations) -> str:
    cues, t, n = [], 0.0, 1
    for (_, _, narration), d in zip(scenes, durations, strict=True):
        words, chunks, cur = narration.split(), [], []
        for word in words:
            cur.append(word)
            if len(" ".join(cur)) > 70 or word.endswith((".", "?", ":")) and len(" ".join(cur)) > 35:
                chunks.append(" ".join(cur))
                cur = []
        if cur:
            chunks.append(" ".join(cur))
        total = sum(len(c) for c in chunks)
        start = t
        for c in chunks:
            length = d * len(c) / total
            cues.append(f"{n}\n{srt_time(start)} --> {srt_time(start + length - 0.05)}\n{c}\n")
            n += 1
            start += length
        t += d + GAP
    return "\n".join(cues)


def main(out_dir: Path) -> None:
    from playwright.sync_api import sync_playwright

    work = out_dir / "work"
    work.mkdir(parents=True, exist_ok=True)
    chromium = os.environ.get("CHROMIUM")
    durations = []
    scenes = [(n, path, close_line() if n == "close" else t) for n, path, t in SCENES]
    for name, _, narration in scenes:
        d = tts(narration, work / f"{name}.wav")
        durations.append(d)
        print(f"voice {name}: {d:.1f}s")
    total = sum(durations) + GAP * len(durations)
    print(f"narration total {total:.1f}s")
    if total > 175:
        sys.exit("Narration is longer than 2:55; shorten the script.")
    photo = lovebird_photo(work / "lovebird.jpg")
    title_card(work / "title.png")
    deck_slide(7, work / "architecture.png")
    actions = {"login": ("customer", act_login), "pets": ("customer", act_pets), "kit": ("customer", act_kit),
               "visit": ("customer", act_visit), "companion": ("customer", act_companion),
               "verify": ("seller", act_verify),
               "quiz": ("customer", act_quiz), "breeders": ("customer", act_breeders),
               "dashboard": ("seller", act_dashboard),
               "check": ("customer", act_check), "chat": ("customer", act_chat),
               "sell": ("seller", lambda p, d: act_sell(p, d, photo)), "blocked": ("seller", act_blocked),
               "reply": ("seller", act_reply)}
    clips = []
    with sync_playwright() as pw:
        save_state(pw, "customer", "priya.customer@example.com", work, chromium)
        save_state(pw, "seller", "karthik.seller@example.com", work, chromium)
        for (name, path_part, _), d in zip(scenes, durations, strict=True):
            target = d + GAP
            clip = work / f"clip-{name}.mp4"
            if name == "title":
                still_clip(work / "title.png", target, clip)
            elif name == "close":
                still_clip(work / "architecture.png", target, clip)
            else:
                role, act = actions[name]
                print(f"recording {name}…")
                video, offset = record(pw, name, role, act, d, work, chromium)
                address_bar(path_part, work / f"bar-{name}.png")
                fit_clip(video, offset, target, work / f"bar-{name}.png", clip)
            clips.append(clip)
    assemble(out_dir, scenes, durations, clips)


def assemble(out_dir: Path, scenes: list, durations: list, clips: list) -> None:
    """Join the scene clips and narration and burn in captions (re-run alone with --assemble)."""
    work = out_dir / "work"
    # audio: each scene's narration followed by GAP seconds of silence
    concat_audio = work / "audio.txt"
    lines = []
    for name, _, _ in scenes:
        padded = work / f"{name}-pad.wav"
        run("-i", work / f"{name}.wav", "-af", f"apad=pad_dur={GAP}", padded)
        lines.append(f"file '{padded}'")
    concat_audio.write_text("\n".join(lines))
    run("-f", "concat", "-safe", "0", "-i", concat_audio, "-c:a", "pcm_s16le", work / "narration.wav")
    concat_video = work / "video.txt"
    concat_video.write_text("\n".join(f"file '{c}'" for c in clips))
    run("-f", "concat", "-safe", "0", "-i", concat_video, "-c", "copy", work / "silent.mp4")
    srt = out_dir / "BreederNear-AI-demo.srt"
    srt.write_text(captions(scenes, durations))
    style = "FontName=Google Sans Flex,FontSize=15,PrimaryColour=&H00FFFFFF,BackColour=&H99000000,BorderStyle=4,Outline=0,Shadow=0,MarginV=28"
    out = out_dir / "BreederNear-AI-demo.mp4"
    run("-i", work / "silent.mp4", "-i", work / "narration.wav", "-vf", f"subtitles={srt}:force_style='{style}'",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-shortest",
        "-movflags", "+faststart", out)
    print(f"{out} ({out.stat().st_size / 1e6:.1f} MB), {srt}")


def reassemble(out_dir: Path) -> None:
    """Rebuild the title card and the final video from the clips and narration of an earlier run."""
    work = out_dir / "work"
    scenes = [(n, path, close_line() if n == "close" else t) for n, path, t in SCENES]
    durations = [wav_seconds(work / f"{n}.wav") for n, _, _ in scenes]
    title_card(work / "title.png")
    still_clip(work / "title.png", durations[0] + GAP, work / "clip-title.mp4")
    assemble(out_dir, scenes, durations, [work / f"clip-{n}.mp4" for n, _, _ in scenes])


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--assemble"]
    target = Path(args[0]) if args else ROOT / "build" / "video"
    reassemble(target) if "--assemble" in sys.argv else main(target)
