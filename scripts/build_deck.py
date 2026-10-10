# ruff: noqa: E501  (slide text: long strings are easier to edit than wrapped ones)
"""Build the submission deck on the organisers' template (docs/submission/BreederNear-AI-deck.pptx + .pdf).

Usage (dev only; needs python-pptx from requirements-dev.txt and LibreOffice for the PDF):
    PYTHONPATH=. python scripts/build_deck.py

The organisers require their template ("Submission Template | AI Builder Cup", Google Slides). This script
downloads it as PPTX, keeps its branding and slide titles, removes only the "how to download" note slide,
and fills each slide. Every number comes from evals/, the live measurements in
docs/submission/05-deck-sources.md, or a cited source.
"""

import copy
import io
import subprocess
import urllib.request
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "submission"
SHOTS = ROOT / "docs" / "screenshots"
TEMPLATE_URL = ("https://docs.google.com/presentation/d/13rg7vW43mEH6DkpuusAE6fdoEylSFz8waNpE4RLzoUg"
                "/export/pptx")

TEAM_NAME = "BreederNear AI"
LEADER = "Sudarsan N"
WEB_URL = "https://breedernear-ai-2026.web.app"
API_URL = "https://breedernear-655711985039.asia-south1.run.app"
REPO_URL = "https://github.com/sudarsan-22/breedernear-ai"
VIDEO_URL = "[add the YouTube link on 17 Oct]"

FONT = "Google Sans Flex"
INK, MUTED = RGBColor(0x1D, 0x1D, 0x1F), RGBColor(0x5F, 0x5F, 0x64)
GREEN, GREEN_BG = RGBColor(0x1F, 0x6E, 0x43), RGBColor(0xE5, 0xF0, 0xE8)
AMBER, AMBER_BG = RGBColor(0x9A, 0x57, 0x00), RGBColor(0xFB, 0xEF, 0xD9)
RED, RED_BG = RGBColor(0xC0, 0x26, 0x1C), RGBColor(0xFB, 0xE4, 0xE2)
BLUE, BLUE_BG = RGBColor(0x1F, 0x5F, 0xA8), RGBColor(0xE4, 0xED, 0xF8)
GREY_BG, LINE = RGBColor(0xF3, 0xF3, 0xF0), RGBColor(0xD6, 0xD6, 0xD2)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
X0, Y0, W, BOTTOM = 0.35, 1.22, 9.3, 5.42          # content area below the template's slide title (inches)


# ---------------------------------------------------------------- helpers
def text(slide, x, y, w, h, paras, size=11, color=INK, anchor=MSO_ANCHOR.TOP, align=PP_ALIGN.LEFT):
    """paras: list of str or (str, {bold, size, color, bullet}) or list of runs [(str, {...}), ...]."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap, tf.vertical_anchor = True, anchor
    tf.margin_left = tf.margin_right = Inches(0.04)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        runs = para if isinstance(para, list) else [para]
        style0 = runs[0][1] if isinstance(runs[0], tuple) else {}
        if style0.get("bullet"):
            _bullet(p, style0.get("bullet"))
        p.space_after = Pt(style0.get("after", 3))
        for run in runs:
            t, st = run if isinstance(run, tuple) else (run, {})
            r = p.add_run()
            r.text = t
            f = r.font
            f.name = FONT if not st.get("bold") else f"{FONT} SemiBold"
            f.size = Pt(st.get("size", size))
            f.color.rgb = st.get("color", color)
            f.italic = st.get("italic", False)
    return box


def _bullet(p, char):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(Inches(0.16)))
    pPr.set("indent", str(-Inches(0.14)))
    bu = pPr.makeelement(qn("a:buChar"), {"char": "•" if char is True else char})
    pPr.append(bu)


def box(slide, x, y, w, h, fill=GREY_BG, line=None, radius=0.08, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1)
    s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = min(0.5, radius / min(w, h))
    s.text_frame.text = ""
    return s


def card(slide, x, y, w, h, title, lines, fill=GREY_BG, title_color=INK, size=10, title_size=11.5):
    box(slide, x, y, w, h, fill)
    paras = [(title, {"bold": True, "size": title_size, "color": title_color, "after": 4})]
    paras += [(ln, {"bullet": True, "size": size}) if isinstance(ln, str) else ln for ln in lines]
    text(slide, x + 0.1, y + 0.08, w - 0.2, h - 0.12, paras)


def node(slide, x, y, w, h, label, sub=None, fill=GREY_BG, color=INK, size=9.5):
    box(slide, x, y, w, h, fill, radius=0.07)
    paras = [(label, {"bold": True, "size": size, "color": color, "after": 1})]
    if sub:
        paras.append((sub, {"size": size - 1.5, "color": MUTED, "after": 0}))
    text(slide, x + 0.04, y, w - 0.08, h, paras, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)


def arrow(slide, x1, y1, x2, y2, color=MUTED, label=None):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(1.25)
    ln = c.line._get_or_add_ln()
    ln.append(ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
    if label:
        text(slide, (x1 + x2) / 2 - 0.6, (y1 + y2) / 2 - 0.2, 1.2, 0.18,
             [(label, {"size": 7, "color": MUTED})], align=PP_ALIGN.CENTER)
    return c


def picture(slide, name, x, y, h, caption=None):
    img = Image.open(SHOTS / f"{name}.webp").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=82)
    buf.seek(0)
    pic = slide.shapes.add_picture(buf, Inches(x), Inches(y), height=Inches(h))
    pic.line.color.rgb = LINE
    pic.line.width = Pt(0.75)
    if caption:
        text(slide, x - 0.15, y + h + 0.04, pic.width / 914400 + 0.3, 0.3, [(caption, {"size": 8.5, "color": MUTED})],
             align=PP_ALIGN.CENTER)
    return pic


def table(slide, x, y, w, rows, widths, size=9, header_fill=INK, zebra=GREY_BG, row_h=0.26):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w),
                                   Inches(row_h * len(rows)))
    tbl = shape.table
    tbl.first_row = True
    for i, wd in enumerate(widths):
        tbl.columns[i].width = Inches(wd)
    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(row_h)
        for c, value in enumerate(row):
            cell = tbl.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.06)
            cell.margin_top = cell.margin_bottom = Inches(0.025)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = header_fill if r == 0 else (zebra if r % 2 == 0 else WHITE)
            tf = cell.text_frame
            tf.word_wrap = True
            runs = value if isinstance(value, list) else [(value, {})]
            p = tf.paragraphs[0]
            for t, st in runs:
                run = p.add_run()
                run.text = t
                run.font.name = f"{FONT} SemiBold" if (r == 0 or st.get("bold")) else FONT
                run.font.size = Pt(st.get("size", size))
                run.font.color.rgb = WHITE if r == 0 else st.get("color", INK)
    return tbl


def footnote(slide, lines):
    text(slide, X0, 5.12, W, 0.3, [(" · ".join(lines), {"size": 6.5, "color": MUTED})])


def set_title_slide(slide):
    """Fill 'Team name: / Team leader name: / Problem Statement:' in the template's own text box."""
    tb = next(s for s in slide.shapes if s.has_text_frame and "Team name" in s.text_frame.text)
    values = {"Team name": TEAM_NAME, "Team leader name": LEADER,
              "Problem Statement": "Retail & Commerce: trusted, legal breeder-to-buyer pet commerce in India "
                                   "(BreederNear AI)"}
    for p in tb.text_frame.paragraphs:
        for key, value in values.items():
            if p.runs and p.runs[0].text.strip().startswith(key):
                r = copy.deepcopy(p.runs[0]._r)
                p._p.append(r)
                p.runs[-1].text = value
                p.runs[-1].font.name = f"{FONT} Medium"


def delete_slide(prs, index):
    sld_ids = prs.slides._sldIdLst
    rid = sld_ids[index].get(qn("r:id"))
    prs.part.drop_rel(rid)
    del sld_ids[index]


def move_after(prs, slide, anchor):
    ids = prs.slides._sldIdLst
    entries = list(ids)
    mine = next(e for e, sl in zip(entries, prs.slides, strict=True) if sl is slide)
    target = next(e for e, sl in zip(entries, prs.slides, strict=True) if sl is anchor)
    ids.remove(mine)
    target.addnext(mine)


def title_of(slide):
    return next((s.text_frame.text.split("\n")[0].strip() for s in slide.shapes if s.has_text_frame
                 and s.text_frame.text.strip()), "")


# ---------------------------------------------------------------- slides
def s_brief(s):
    text(s, X0, Y0 - 0.05, W, 0.4, [[("BreederNear AI: ", {"bold": True, "size": 15, "color": GREEN}),
                                    ("find the trusted breeder next door.", {"bold": True, "size": 15})]])
    card(s, X0, 1.68, 4.55, 3.35, "The problem", [
        "India has about 39 million pets¹, but buying one is a gamble. OLX stopped live-animal listings², "
        "so the trade moved to WhatsApp and Facebook groups with no checks at all.",
        "Buyers overpay in shops or lose money to “full advance, courier only” posts with stolen photos.",
        "Protected native birds are still sold: 300+ of India’s ~1,200 bird species are found in illegal "
        "trade³, and munias are dyed to disguise them⁴.",
        "Real local breeders, often a street away, are invisible and lose hours to manual selling.",
    ], fill=RED_BG, title_color=RED, size=10.8, title_size=12.5)
    card(s, X0 + 4.75, 1.68, 4.55, 3.35, "Our solution", [
        "A breeder-to-buyer pet marketplace where every listing is screened by Gemini and by rules in code "
        "before any buyer sees it.",
        "Sellers list from photos and a casual Tamil or English message in under a minute.",
        "Buyers find trusted pets nearby at fair prices, then get a welfare-sized starter kit and a 14-day "
        "care plan.",
        "“Is this post safe?”: buyers can check any post they saw in a WhatsApp or Instagram group.",
        ("Built from our founder’s five years as a bird breeder and broker in Coimbatore.",
         {"size": 10, "color": GREEN, "bold": True}),
    ], fill=GREEN_BG, title_color=GREEN, size=10.8, title_size=12.5)
    footnote(s, ["¹ Euromonitor, Pet Care in India (2025)", "² OLX India: items not allowed",
                 "³ WWF-India / TRAFFIC", "⁴ Wildlife SOS, Delhi seizure report"])


def s_opportunities(s):
    tb = next(x for x in s.shapes if x.has_text_frame and "Opportunities" in x.text_frame.text)
    tb.text_frame.paragraphs[0].runs[0].text = "Opportunities"
    for p in list(tb.text_frame.paragraphs)[1:]:
        p._p.getparent().remove(p._p)
    cols = [
        ("How is it different?", BLUE, BLUE_BG, [
            "Classifieds such as OLX stopped live-animal listings; big pet platforms sell food and accessories.",
            "A few kennel websites sell dogs, checking only themselves.",
            ("No platform we found checks every listing for wildlife law, registration, scam prices and "
             "reused photos before it goes live, or checks posts from outside groups.", {"bold": True, "size": 10.4}),
        ]),
        ("How does it solve the problem?", GREEN, GREEN_BG, [
            "Gemini turns photos and a messy message into a structured, fairly priced listing.",
            "Trust is decided by transparent code: protected species blocked, dog registration checked, "
            "price and scam-language warnings, reused-photo detection.",
            "Buyers see why: every badge lists its reasons and the questions to ask.",
            "In-person handover; AI-drafted replies; starter kit and care plan.",
        ]),
        ("USP", AMBER, AMBER_BG, [
            ("Trust built in, not bolted on.", {"bold": True, "size": 10.4}),
            "Protected species blocked from the photo alone: 8/8 in testing, 0/37 false alarms.",
            "The AI can’t override the rules: prompt injection still ends in CAUTION (eval E12).",
            "Works where the trade happens: Tamil/English messages and outside posts.",
            "One tool layer for tap screens and the AI chat.",
        ]),
    ]
    cw = (W - 0.4) / 3
    for i, (title, color, bg, lines) in enumerate(cols):
        card(s, X0 + i * (cw + 0.2), Y0 + 0.05, cw, 3.85, title, lines, fill=bg, title_color=color, size=10.4,
             title_size=12.5)


def s_features(s):
    cw = (W - 0.3) / 2
    card(s, X0, Y0, cw, 2.75, "For buyers (customer app)", [
        "Pets near me: trusted first, distance, fair-price bar",
        "Listing page: trust checks, health notes, questions to ask",
        "“Which pet suits me?” quiz: home, family, time, budget",
        "“Is this post safe?” for WhatsApp or Instagram posts",
        "Contact the breeder; replies appear under Account",
        "Welfare-sized starter kit, 14-day care plan with vet warning signs",
        "Local Breeders directory: buy direct at farm prices",
    ], fill=GREEN_BG, title_color=GREEN, size=10.6, title_size=12.5)
    card(s, X0 + cw + 0.3, Y0, cw, 2.75, "For sellers (seller app)", [
        "“Fill with AI”: photos + a Tamil/English message become a listing",
        "Publish with trust check: TRUSTED, CAUTION or BLOCKED, with reasons",
        "Dashboard: live listings, views, enquiries, trust status",
        "Manage listings: pause, resume, mark sold",
        "Enquiries with AI-drafted replies from the listing’s facts",
        "Farm profile and dog-breeder registration (simulated registry)",
    ], fill=BLUE_BG, title_color=BLUE, size=10.6, title_size=12.5)
    card(s, X0, Y0 + 2.9, W, 1.15, "Everywhere", [
        [("BreederNear AI chat", {"bold": True, "size": 10.4}),
         (" (5 Gemini agents, English or Tamil) uses the same tools as the screens.  ", {"size": 10.4}),
         ("Safety:", {"bold": True, "size": 10.4}),
         (" separate customer and seller accounts, roles checked in the API and inside the AI tools, rate "
          "limits, AI replies checked for medicine doses.  ", {"size": 9.6}),
         ("Accessible:", {"bold": True, "size": 10.4}),
         (" WCAG 2.2 AA, light and dark, phone to desktop.", {"size": 10.4})],
    ], size=10.4, title_size=12.5)


def s_flow(s):
    # Seller lane
    text(s, X0, Y0 - 0.02, 2, 0.25, [("SELLER", {"bold": True, "size": 9, "color": BLUE})])
    y, h, w = Y0 + 0.25, 0.72, 1.62
    xs = [X0 + i * (w + 0.29) for i in range(5)]
    steps = [("Photos + message", "Tamil or English, as in WhatsApp"), ("Gemini fills the form", "multimodal, JSON schema"),
             ("Seller checks it", "edit any field"), ("Trust screening", "Gemini vision + rules in code"),
             ("Decision in code", "")]
    for i, (a, b) in enumerate(steps[:4]):
        node(s, xs[i], y, w, h, a, b, fill=BLUE_BG)
        arrow(s, xs[i] + w, y + h / 2, xs[i + 1], y + h / 2)
    node(s, xs[4], y - 0.05, w, 0.36, "BLOCKED", "never shown to buyers", fill=RED_BG, color=RED, size=8.5)
    node(s, xs[4], y + 0.41, w, 0.36, "TRUSTED / CAUTION", "published with reasons", fill=GREEN_BG, color=GREEN, size=8.5)
    # Buyer lane
    yb = Y0 + 1.45
    text(s, X0, yb - 0.27, 2, 0.25, [("BUYER", {"bold": True, "size": 9, "color": GREEN})])
    bsteps = [("Browse or take the quiz", "pets near my district"), ("Listing + trust card", "reasons, fair price"),
              ("Contact breeder", "enquiry, no contact details"), ("Seller replies", "AI draft, seller edits"),
              ("Visit and pay in person", "see the parents first")]
    for i, (a, b) in enumerate(bsteps):
        node(s, xs[i], yb, w, h, a, b, fill=GREEN_BG)
        if i < 4:
            arrow(s, xs[i] + w, yb + h / 2, xs[i + 1], yb + h / 2)
    arrow(s, xs[4] + w / 2, y + 0.77, xs[1] + w / 2, yb, color=GREEN, label="published listings")
    # Aftercare + outside posts
    yc = yb + 1.1
    node(s, xs[4], yc, w, h, "Starter kit", "cage sized for the animals", fill=AMBER_BG)
    node(s, xs[3], yc, w, h, "14-day care plan", "vet warning signs, no doses", fill=AMBER_BG)
    arrow(s, xs[4] + w / 2, yb + h, xs[4] + w / 2, yc)
    arrow(s, xs[4], yc + h / 2, xs[3] + w, yc + h / 2)
    node(s, xs[0], yc, w, h, "Post in a WhatsApp group", "", fill=GREY_BG)
    node(s, xs[1], yc, w, h, "“Is this post safe?”", "nothing is stored", fill=GREY_BG)
    node(s, xs[2], yc, w, h, "CAUTION + questions", "never pay before visiting", fill=AMBER_BG, color=AMBER)
    arrow(s, xs[0] + w, yc + h / 2, xs[1], yc + h / 2)
    arrow(s, xs[1] + w, yc + h / 2, xs[2], yc + h / 2)
    text(s, X0, 5.08, W, 0.3, [("Every step works by tapping, or by asking BreederNear AI in chat: the same "
                                "tools, the same checks.", {"size": 8.5, "color": MUTED})])


def s_wireframes(s):
    names = [("01-login", "Login: one-tap demo accounts"), ("02-pets", "Pets near me"),
             ("03-listing-trust", "Listing + trust checks"), ("08-starter-kit", "Welfare-sized kit"),
             ("10-ai-chat", "AI buyer guide")]
    h, gap = 3.55, 0.28
    width = h * 585 / 1266
    x = X0 + (W - (len(names) * width + (len(names) - 1) * gap)) / 2
    for name, cap in names:
        picture(s, name, x, Y0, h, cap)
        x += width + gap


def s_architecture(s):
    # Users and Firebase
    node(s, X0, 1.35, 1.35, 0.62, "Buyers & sellers", "phone or laptop", fill=GREY_BG)
    node(s, X0, 2.35, 1.35, 0.8, "Firebase Hosting", "web app on Google’s CDN", fill=AMBER_BG, color=AMBER)
    arrow(s, X0 + 0.67, 1.97, X0 + 0.67, 2.35)
    # Cloud Run container
    cx, cy, cw, ch = X0 + 1.75, 1.25, 4.6, 3.75
    box(s, cx, cy, cw, ch, WHITE, line=BLUE, radius=0.1)
    text(s, cx + 0.12, cy + 0.05, cw, 0.25, [("Cloud Run (asia-south1)", {"bold": True, "size": 10, "color": BLUE})])
    node(s, cx + 0.15, cy + 0.38, cw - 0.3, 0.42, "Gatekeeper · login · rate limits",
         "only the routes the app uses; roles from the server", fill=GREY_BG, size=8.5)
    node(s, cx + 0.15, cy + 0.92, 1.5, 0.72, "FastAPI /api", "tap screens", fill=BLUE_BG, size=9)
    box(s, cx + 1.8, cy + 0.92, cw - 1.95, 1.55, BLUE_BG, radius=0.07)
    text(s, cx + 1.85, cy + 0.95, cw - 2.05, 0.22, [("Google ADK agents", {"bold": True, "size": 9, "color": BLUE})],
         align=PP_ALIGN.CENTER)
    ax = cx + 1.92
    node(s, ax + 0.55, cy + 1.2, 1.4, 0.3, "Concierge", None, fill=WHITE, size=8)
    for i, name in enumerate(["Listing", "Trust", "Match", "Care"]):
        node(s, ax + i * 0.62, cy + 1.7, 0.56, 0.3, name, None, fill=WHITE, size=7.5)
    text(s, cx + 1.85, cy + 2.05, cw - 2.05, 0.4, [("callbacks: context · reply guard · tool log",
                                                    {"size": 7, "color": MUTED})], align=PP_ALIGN.CENTER)
    node(s, cx + 0.15, cy + 2.62, cw - 0.3, 0.95, "breedernear_core",
         "one tool layer: listings · matching · care · accounts\nsafety rules · deterministic trust score · "
         "reused-photo hashing · distance", fill=GREEN_BG, color=GREEN, size=9)
    arrow(s, cx + 0.9, cy + 1.64, cx + 0.9, cy + 2.62)
    arrow(s, cx + 3.1, cy + 2.47, cx + 3.1, cy + 2.62)
    arrow(s, X0 + 1.35, 2.75, cx, 2.75)
    text(s, X0 + 0.05, 3.2, 1.3, 0.4, [("calls Cloud Run directly: API + streamed AI", {"size": 7, "color": MUTED})],
         align=PP_ALIGN.CENTER)
    # Google services on the right
    rx, rw = cx + cw + 0.4, W + X0 - (cx + cw + 0.4)
    services = [("Gemini 3.8 Flash", "Vertex AI: agents, photo screening,\nextraction, care plans, replies", AMBER_BG, AMBER),
                ("Firestore", "accounts, listings, enquiries, carts", GREEN_BG, GREEN),
                ("Cloud Storage", "private uploads, deleted after 30 days", BLUE_BG, BLUE),
                ("Cloud Logging", "one JSON line per tool call", GREY_BG, INK),
                ("Cloud Build + Artifact Registry", "deploy from source; GitHub Actions CI", GREY_BG, INK)]
    for i, (a, b, bg, col) in enumerate(services):
        yy = 1.25 + i * 0.77
        node(s, rx, yy, rw, 0.66, a, b, fill=bg, color=col, size=9)
        arrow(s, cx + cw, yy + 0.33, rx, yy + 0.33)


def s_tech(s):
    rows = [["Google technology", "How BreederNear AI uses it"],
            ["Gemini 3.8 Flash (Vertex AI)", "Five ADK agents; multimodal listing extraction from photos + Tamil/English text; "
             "photo screening (species, dye, stock photos); care plans; reply drafts. JSON-schema outputs."],
            ["Google ADK (Python)", "Concierge + listing, trust, match and care agents; tools; callbacks on every agent; "
             "sessions; streamed replies"],
            ["Cloud Run", "API and agents in one container; login gatekeeper; rate limits; asia-south1"],
            ["Firebase Hosting", "The web app on Google’s CDN; calls Cloud Run directly (CORS) so AI replies stream"],
            ["Firestore", "Accounts (scrypt-hashed passwords), listings, drafts, enquiries, carts"],
            ["Cloud Storage", "Private upload bucket, 30-day deletion"],
            ["Cloud Build, Artifact Registry, Cloud Logging", "Deploy from source; structured tool-call logs"],
            ["gemini-3.1-flash-image", "Illustrative photos for the fictional sample listings (labelled in the app)"]]
    table(s, X0, Y0, 6.1, rows, [1.9, 4.2], size=8.3, row_h=0.36)
    card(s, X0 + 6.3, Y0, W - 6.3, 3.24, "Also used", [
        "Python 3.12, FastAPI, Pydantic",
        "imagehash: perceptual hashing for reused photos",
        "Plain HTML, CSS and JavaScript: no build step",
        "pytest, Playwright + axe-core, GitHub Actions",
        "Firebase CLI (deploy only)",
    ], size=9.3)


def s_cost(s):
    rows = [["AI action (measured, real calls)", "Gemini tokens", "Cost per action*"],
            ["List a pet: extract listing + screen photo", "≈ 4,560 in · ≤ 1,075 out", "≈ ₹1.3"],
            ["Check an outside post (text only; a screenshot adds ≈ ₹0.5)", "≈ 1,620 in · ≤ 445 out", "≈ ₹0.5"],
            ["14-day care plan (cached per species and age)", "≈ 560 in · ≤ 1,680 out", "≈ ₹1.2, once per species"],
            ["Reply draft for an enquiry", "≈ 500 in · ≤ 790 out", "≈ ₹0.6"]]
    table(s, X0, Y0, W, rows, [3.9, 3.0, 2.4], size=9, row_h=0.32)
    infra = [["Running cost", "Prototype through judging", "Example: 10,000 listings a month"],
             ["Cloud Run (1 always-on instance)", "≈ ₹600–1,000 / month (estimate)", "scales per request"],
             ["Firestore, Cloud Storage, Firebase Hosting", "within free usage at prototype scale", "pay per use (not measured)"],
             ["Gemini", "a few hundred ₹ (tests + judges)", "≈ ₹13,000 / month for screening"]]
    table(s, X0, Y0 + 1.82, W, infra, [3.9, 3.0, 2.4], size=9, row_h=0.32)
    text(s, X0, Y0 + 3.2, W, 0.6, [
        ("Screening a listing costs about ₹1.3, against animals priced from ₹400 to ₹25,000 in our sample "
         "listings, so trust checks are affordable on every listing.", {"size": 9.5, "bold": True, "color": GREEN})])
    footnote(s, ["*Measured tokens (10 Oct 2026); thinking tokens counted as output",
                 "Gemini 3.8 Flash at $1.50 in / $7.50 out per 1M tokens (list price from 1 Jan 2027, as reported "
                 "by price trackers; introductory price until then is half)", "₹88 = $1 (assumption)",
                 "Estimates are labelled"])


def s_snapshots(s):
    names = [("04-post-check", "“Is this post safe?”"), ("06-blocked", "Protected species: blocked"),
             ("05-seller-dashboard", "Seller dashboard"), ("07-reply-draft", "AI-drafted reply"),
             ("09-care-plan", "14-day care plan")]
    h, gap = 3.55, 0.28
    width = h * 585 / 1266
    x = X0 + (W - (len(names) * width + (len(names) - 1) * gap)) / 2
    for name, cap in names:
        picture(s, name, x, Y0, h, cap)
        x += width + gap


def s_performance(s):
    q = [["Quality (real Gemini, 10 Oct 2026)", "Result"],
         ["Agent evals: 18 cases × 3 runs (listing, Tamil, blocking, scams, reused photos, prompt injection, "
          "no medicine advice, roles, explanations, reply drafts)", [("54/54 passed", {"bold": True, "color": GREEN})]],
         ["Protected species blocked from the photo alone", [("8/8", {"bold": True, "color": GREEN})]],
         ["Ordinary pets wrongly flagged as protected", [("0/37", {"bold": True, "color": GREEN})]],
         ["All photo checks: species, dye, blur, no animal, watermark, screenshot", [("202/202*", {"bold": True})]],
         ["Accessibility: axe-core, WCAG 2.2 AA, light + dark, 320–1280 px", [("0 problems", {"bold": True, "color": GREEN})]],
         ["Unit tests in CI · live smoke test", [("249 · 17/17", {"bold": True})]]]
    table(s, X0, Y0, 5.75, q, [4.55, 1.2], size=8.3, row_h=0.4)
    p = [["Speed (live)", "Time"],
         ["List a pet: upload, AI fill, publish with trust check", "17–27 s"],
         ["Check a pasted post", "5–7 s"],
         ["Web app load (Firebase CDN)", "≈ 0.7 s"],
         ["Gemini: extract a listing", "3–7 s"],
         ["Gemini: screen a photo", "4–5 s"]]
    table(s, X0 + 5.95, Y0, W - 5.95, p, [2.45, 0.9], size=8.3, row_h=0.4)
    text(s, X0 + 5.95, Y0 + 2.55, W - 5.95, 1.2, [
        ("How we test", {"bold": True, "size": 9.5, "after": 2}),
        ("Gemini isn’t deterministic, so each eval runs three times and we report the count. Trust decisions are "
         "made by tested code, so the model can’t be talked out of them.", {"size": 8.5})])
    footnote(s, ["*Test photos are AI-generated and the screening prompt was tuned on them (first run 196/202), "
                 "so treat this as an upper bound", "Reproduce: scripts/run_evals.sh 3 · scripts/vision_accuracy.py · "
                 "pytest -m ui tests/ui", "evals/RESULTS.md, evals/VISION_RESULTS.md"])


def s_future(s):
    cw = (W - 0.3) / 2
    card(s, X0, Y0, cw, 3.6, "Roadmap (not in the prototype)", [
        "Pilot with real breeders in Coimbatore and Tiruppur, from the founder’s network",
        "List by sending a WhatsApp message (WhatsApp Business Platform)",
        "Live State Animal Welfare Board and PARIVESH registry checks; the platform registrations India’s "
        "pet-trade rules require",
        "Chat history in Agent Engine sessions, so Cloud Run can scale past one instance",
        "Breeder ratings from buyer feedback and the pet’s health after sale",
        "Hindi, Telugu, Kannada and more districts; vet and pet-pharmacy partners",
    ], fill=BLUE_BG, title_color=BLUE, size=10.8, title_size=12.5)
    card(s, X0 + cw + 0.3, Y0, cw, 3.6, "Responsible by design (already built)", [
        "Protected species blocked in code, whatever the model says",
        "No medicine names or doses: checked on every AI reply, even while streaming",
        "Health signs are “ask the seller”, never a diagnosis",
        "No addresses, ID documents or payment details collected; sellers never see buyers’ logins",
        "Synthetic sample data, clearly labelled; simulated registry numbers start with SIM-",
    ], fill=GREEN_BG, title_color=GREEN, size=10.8, title_size=12.5)


def s_links(s):
    tb = next(x for x in s.shapes if x.has_text_frame and "Provide links" in x.text_frame.text)
    values = {"GitHub Public Repository": REPO_URL, "Demo Video Link (3 Minutes)": VIDEO_URL,
              "Final Product Link": f"{WEB_URL}  (API: {API_URL})"}
    for p in tb.text_frame.paragraphs:
        if p.runs and p.runs[0].text.strip() in values:
            r = copy.deepcopy(p.runs[0]._r)
            p._p.append(r)
            p.runs[-1].text = ": " + values[p.runs[0].text.strip()]
            p.runs[-1].font.name = FONT
            p.runs[-1].font.size = Pt(11)
            p.runs[-1].font.color.rgb = GREEN
    card(s, X0, 2.35, W, 1.05, "Try it in 2 minutes: demo accounts with preloaded data", [
        [("Customer: ", {"bold": True, "size": 11}), ("priya.customer@example.com", {"size": 11}),
         ("    Seller: ", {"bold": True, "size": 11}), ("karthik.seller@example.com", {"size": 11}),
         ("    Password: ", {"bold": True, "size": 11}), ("demo12345", {"size": 11})],
        ("Or tap “Demo customer · Priya” / “Demo seller · Karthik” on the login screen. The README has a "
         "step-by-step walkthrough.", {"size": 10, "color": MUTED}),
    ], fill=GREEN_BG, title_color=GREEN)


def s_business(s):
    cw = (W - 0.4) / 3
    card(s, X0, Y0, cw, 2.6, "Revenue (planned)", [
        "Verified-breeder subscription: badge, dashboard insights, more listings",
        "Featured listings in a district",
        "Commission on starter kits and accessories from partner brands",
        "B2B: trust-screening API for classifieds and pet shops",
    ], fill=GREEN_BG, title_color=GREEN, size=10.6, title_size=12.5)
    card(s, X0 + cw + 0.2, Y0, cw, 2.6, "Why it works", [
        "Screening costs about ₹1.3 per listing (measured tokens)",
        "Serverless: Cloud Run and Firestore cost little when idle and scale per district",
        "Trust is the product: OLX left this market because it couldn’t police sellers",
    ], fill=BLUE_BG, title_color=BLUE, size=10.6, title_size=12.5)
    card(s, X0 + 2 * (cw + 0.2), Y0, cw, 2.6, "Go-to-market", [
        "Start where the founder trades: Coimbatore and Tiruppur breeder groups",
        "Breeders onboard with one message and their phone photos",
        "Buyers arrive via “Is this post safe?” links shared in the same groups",
        "Then district by district across Tamil Nadu",
    ], fill=AMBER_BG, title_color=AMBER, size=10.6, title_size=12.5)
    text(s, X0, Y0 + 2.75, W, 1.0, [
        ("Who benefits", {"bold": True, "size": 10, "after": 2}),
        ("Buyers: fair prices and healthier, legal pets.  Breeders: hours saved and buyers beyond their own "
         "contacts.  Wildlife: fewer protected birds traded, because illegal listings never go live.", {"size": 10.5}),
        ("Revenue lines and the rollout are plans and assumptions, not results.", {"size": 8, "color": MUTED}),
    ])


def add_slide_title(slide, title, like):
    """Copy the template's own title box from another slide, so the new title matches exactly."""
    src = next(sh for sh in like.shapes if sh.has_text_frame and sh.text_frame.text.strip())
    el = copy.deepcopy(src._element)
    slide.shapes._spTree.append(el)
    tb = slide.shapes[-1]
    runs = tb.text_frame.paragraphs[0].runs
    runs[0].text = title
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def build() -> Path:
    raw = urllib.request.urlopen(TEMPLATE_URL, timeout=60).read()
    prs = Presentation(io.BytesIO(raw))
    slides = list(prs.slides)
    by_title = {title_of(sl): sl for sl in slides}
    set_title_slide(slides[0])
    fill = {"Brief about the idea": s_brief, "Opportunities": s_opportunities,
            "List of features offered by the solution": s_features,
            "Process flow diagram or Use-case diagram": s_flow,
            "Wireframes/Mock diagrams of the proposed solution (optional)": s_wireframes,
            "Architecture diagram of the proposed solution": s_architecture,
            "Technologies to be used in the solution": s_tech,
            "Estimated implementation cost (optional)": s_cost, "Snapshots of the prototype": s_snapshots,
            "Prototype Performance report/Benchmarking": s_performance,
            "Additional Details/Future Development (if any)": s_future, "Provide links to your:": s_links}
    for title, fn in fill.items():
        fn(by_title[title])
    blank = slides[14]                     # the template's spare content slide: used for the business case
    add_slide_title(blank, "Business case and go-to-market", by_title["Snapshots of the prototype"])
    s_business(blank)
    delete_slide(prs, 1)                   # the template's "how to download" note
    move_after(prs, blank, by_title["Estimated implementation cost (optional)"])
    pptx = OUT / "BreederNear-AI-deck.pptx"
    prs.save(pptx)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(pptx)],
                   check=True, capture_output=True)
    return pptx


if __name__ == "__main__":
    path = build()
    pdf = path.with_suffix(".pdf")
    print(path, f"{path.stat().st_size / 1e6:.2f} MB")
    print(pdf, f"{pdf.stat().st_size / 1e6:.2f} MB (limit 5 MB)")
