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
    text(s, X0, Y0 - 0.08, W, 0.4, [[("“The breeder is 50 metres away. The customer never finds them.”",
                                     {"bold": True, "size": 15, "color": RED})]])
    box(s, X0, 1.62, W, 0.78, AMBER_BG)
    text(s, X0 + 0.12, 1.66, W - 0.24, 0.72, [
        ("Why we are building this", {"bold": True, "size": 11, "color": AMBER, "after": 2}),
        [("Our founder Sudarsan N spent five years as a bird breeder, pet-shop owner and broker in Coimbatore. "
          "He started with a ₹750 setup and earned over ₹4 lakh while knowing only about 100 people. Every week he "
          "watched buyers walk past a breeder on their own street into a shop, pay more for a weaker bird, or lose "
          "money to a stranger in a WhatsApp group.", {"size": 10})],
    ])
    cw = (W - 0.4) / 3
    cols = [
        ("Buyers lose money and trust", [
            "Can’t find the breeder next door, so they pay shop prices",
            "Can’t tell a real seller from a scam: “full advance, courier only”, stolen photos",
            "Don’t know which birds are protected or that dog breeders must register⁵",
            "Alone after buying: wrong cage, wrong food, late to the vet",
        ]),
        ("Breeders lose time and reach", [
            "Sell only inside their own small circle and district groups",
            "Hours of calls every day, the same 20 questions, the same post retyped in every group",
            "Good breeders look exactly like bad ones: no way to prove it",
        ]),
        ("Animals and the law lose most", [
            "300+ of India’s ~1,200 bird species are found in illegal trade³",
            "Munias are dyed to disguise them⁴; dyed chicks were still on sale in an unlicensed Bengaluru shop in "
            "June 2026⁶",
            "Sick animals are sold because nobody checks before the sale",
        ]),
    ]
    for i, (title, lines) in enumerate(cols):
        card(s, X0 + i * (cw + 0.2), 2.5, cw, 2.05, title, lines, fill=RED_BG, title_color=RED, size=9.6,
             title_size=11)
    box(s, X0, 4.63, W, 0.45, INK)
    text(s, X0 + 0.12, 4.63, W - 0.24, 0.45, [[
        ("Still unsolved in 2026: ", {"bold": True, "size": 10.2, "color": WHITE}),
        ("OLX stopped live-animal listings², big pet platforms sell food and accessories, so India’s ~39 million-pet "
         "market¹ still buys animals through WhatsApp, Facebook and Instagram groups with no checks at all.",
         {"size": 10.2, "color": WHITE})]], anchor=MSO_ANCHOR.MIDDLE)
    footnote(s, ["Founder figures are his own experience", "¹ Euromonitor 2025", "² OLX India: items not allowed",
                 "³ WWF-India / TRAFFIC", "⁴ Deccan Herald, Aug 2023", "⁵ PCA (Dog Breeding and Marketing) Rules 2017",
                 "⁶ PETA India, 25 Jun 2026"])


def s_journey(s):
    """Every pain on the problem slide, mapped to what the product does and what we measured."""
    G = {"color": GREEN, "bold": True}
    rows = [
        ["Step", "Today, in groups and shops", "With BreederNear AI", "Built and measured"],
        ["Find", "Walk into the nearest shop; the breeder next door is invisible",
         "Pets near you, trusted first, a match % for your home, a fair-price bar", [("Match % calculated in code; 16 breeders, 36 pets", {})]],
        ["List", "Breeder retypes the same post in every group",
         "Photos + a Tamil or English message become a full listing", [("17–27 s live: upload, AI fill, trust check", {})]],
        ["Trust", "No checks: stolen photos, scam prices, protected birds",
         "Every listing screened before it goes live; Verified breeder badge", [("8/8 protected species blocked, 0/37 false alarms", G)]],
        ["Check", "Pay a stranger on social media in full, in advance",
         "Paste any outside post: “Is this post safe?”; share the warning back to the group; report protected animals",
         [("5–7 s per post; nothing stored", {})]],
        ["Talk", "Endless calls and the same answers",
         "AI drafts the buyer’s first message and the breeder’s reply; scam shield on both", [("Scam scan on every enquiry and reply", {})]],
        ["Buy", "“Courier only”, no handover",
         "Book a visit, see the pet, pay in person, tap “I bought this pet”", [("No payments in the app, by design", {})]],
        ["After", "New owner on their own",
         "Starter kit sized for welfare, 14-day plan, daily log, growth, symptom urgency", [("Never a medicine or dose (evals E11, E19)", G)]],
        ["Grow", "Breeder has no data",
         "Dashboard: views, enquiries, visits and sales, week on week", [("8-week charts and trend cards", {})]],
    ]
    table(s, X0, Y0 - 0.02, W, rows, [0.75, 2.55, 3.45, 2.55], size=8.8, row_h=0.39)
    text(s, X0, 4.82, W, 0.3, [[
        ("One tool layer, two ways in: ", {"bold": True, "size": 10, "color": GREEN}),
        ("every step works by tapping or by asking seven Gemini agents in English or Tamil. "
         f"Live now: {_eval_numbers()[0].split()[0]} agent eval runs, {_unit_tests()} unit tests, 0 accessibility problems.",
         {"size": 10})]])


def s_opportunities(s):
    tb = next(x for x in s.shapes if x.has_text_frame and "Opportunities" in x.text_frame.text)
    tb.text_frame.paragraphs[0].runs[0].text = "Opportunities"
    for p in list(tb.text_frame.paragraphs)[1:]:
        p._p.getparent().remove(p._p)
    cols = [
        ("How is it different?", BLUE, BLUE_BG, [
            [("WhatsApp / Facebook groups: ", {"bold": True, "size": 10}), ("reach, but no checks, no records, no recourse", {"size": 10})],
            [("Classifieds (OLX): ", {"bold": True, "size": 10}), ("stopped live-animal listings", {"size": 10})],
            [("Pet super-apps: ", {"bold": True, "size": 10}), ("food, accessories and vets, not the animal", {"size": 10})],
            [("Kennel websites: ", {"bold": True, "size": 10}), ("one seller vouching for itself", {"size": 10})],
            ("No platform we found checks every listing for wildlife law, registration, scam prices and reused "
             "photos before it goes live, and then stays with the buyer after the sale.", {"bold": True, "size": 10}),
        ]),
        ("How does it solve the problem?", GREEN, GREEN_BG, [
            [("Invisible breeders → ", {"bold": True, "size": 10}), ("listed in a minute from photos and a Tamil message", {"size": 10})],
            [("Scams → ", {"bold": True, "size": 10}), ("price, wording and reused-photo checks; outside posts checked too", {"size": 10})],
            [("Illegal birds → ", {"bold": True, "size": 10}), ("blocked in code from the photo alone", {"size": 10})],
            [("Unproven breeders → ", {"bold": True, "size": 10}), ("Verified badge: phone, facility photos, registration", {"size": 10})],
            [("Lost hours → ", {"bold": True, "size": 10}), ("AI drafts replies; visits booked in the app", {"size": 10})],
            [("Alone after buying → ", {"bold": True, "size": 10}), ("starter kit, care plan, daily log, vet urgency", {"size": 10})],
        ]),
        ("USP", AMBER, AMBER_BG, [
            ("Trust built in, not bolted on.", {"bold": True, "size": 10.4}),
            "Rules in code decide; Gemini reads and explains. A prompt injection still ends in CAUTION (eval E12).",
            "Protected species blocked from the photo alone: 8/8 in testing, 0/37 false alarms.",
            "Works where the trade already happens: Tamil and English messages, posts from groups.",
            "Founder–market fit: designed from five years inside this exact trade.",
        ]),
    ]
    cw = (W - 0.4) / 3
    for i, (title, color, bg, lines) in enumerate(cols):
        card(s, X0 + i * (cw + 0.2), Y0 + 0.05, cw, 3.85, title, lines, fill=bg, title_color=color, size=10.4,
             title_size=12.5)


def s_features(s):
    cw = (W - 0.3) / 2
    card(s, X0, Y0, cw, 2.95, "For buyers (customer app)", [
        "Pets near me with a match % for your home, trusted first, fair-price bar",
        "Listing page: trust checks, health notes, questions to ask",
        "AI-drafted first message; scam warnings on replies",
        "Book a visit; “I bought this pet” after it (paid in person)",
        "My pets: daily log with AI feedback, growth, health calendar",
        "Symptom checker: how urgently to see a vet (never medicines)",
        "“Is this post safe?”, starter kit, Local Breeders directory",
    ], fill=GREEN_BG, title_color=GREEN, size=10.2, title_size=12.5)
    card(s, X0 + cw + 0.3, Y0, cw, 2.95, "For sellers (seller app)", [
        "“Fill with AI”: photos + a Tamil/English message become a listing",
        "Publish with trust check: TRUSTED, CAUTION or BLOCKED, with reasons",
        "Dashboard charts: views, enquiries, visits, sales, funnel",
        "Verified breeder badge: phone code, facility photos read by Gemini, dog-breeder certificate (no ID documents)",
        "Visit requests to confirm; AI-drafted replies to enquiries",
        "Vaccination card read into the trust check",
    ], fill=BLUE_BG, title_color=BLUE, size=10.2, title_size=12.5)
    card(s, X0, Y0 + 3.05, W, 1.0, "Everywhere", [
        [("Seven Gemini agents", {"bold": True, "size": 10}),
         (" in English or Tamil use the same tools as the screens.  ", {"size": 10}),
         ("Sign-in:", {"bold": True, "size": 10}), (" password, one-time code or Google (Firebase Authentication).  ", {"size": 10}),
         ("Safety:", {"bold": True, "size": 10}), (" roles checked in the API and the AI tools, rate limits, every AI reply "
          "checked for medicine doses.  ", {"size": 10}),
         ("Accessible:", {"bold": True, "size": 10}), (" WCAG 2.2 AA, phone to desktop.", {"size": 10})],
    ], size=10, title_size=12)


def s_flow(s):
    text(s, X0, Y0 - 0.02, 2, 0.25, [("SELLER", {"bold": True, "size": 9, "color": BLUE})])
    y, h, w = Y0 + 0.25, 0.72, 1.62
    xs = [X0 + i * (w + 0.29) for i in range(5)]
    steps = [("Photos + message", "Tamil or English, as in WhatsApp"), ("Gemini fills the form", "multimodal, JSON schema"),
             ("Seller checks it", "+ optional vaccination card"), ("Trust screening", "Gemini vision + rules in code")]
    for i, (a, b) in enumerate(steps):
        node(s, xs[i], y, w, h, a, b, fill=BLUE_BG)
        arrow(s, xs[i] + w, y + h / 2, xs[i + 1], y + h / 2)
    node(s, xs[4], y - 0.05, w, 0.36, "BLOCKED", "never shown to buyers", fill=RED_BG, color=RED, size=8.5)
    node(s, xs[4], y + 0.41, w, 0.36, "TRUSTED / CAUTION", "published with reasons", fill=GREEN_BG, color=GREEN, size=8.5)
    yb = Y0 + 1.45
    text(s, X0, yb - 0.27, 2, 0.25, [("BUYER", {"bold": True, "size": 9, "color": GREEN})])
    bsteps = [("Pets with match %", "rules score your home"), ("Listing + trust card", "reasons, fair price"),
              ("Message the breeder", "AI draft, scam shield"), ("Book a visit", "seller confirms"),
              ("See it, pay in person", "“I bought this pet”")]
    for i, (a, b) in enumerate(bsteps):
        node(s, xs[i], yb, w, h, a, b, fill=GREEN_BG)
        if i < 4:
            arrow(s, xs[i] + w, yb + h / 2, xs[i + 1], yb + h / 2)
    arrow(s, xs[4] + w / 2, y + 0.77, xs[1] + w / 2, yb, color=GREEN, label="published listings")
    yc = yb + 1.1
    node(s, xs[4], yc, w, h, "My pets", "daily log, growth, calendar", fill=AMBER_BG)
    node(s, xs[3], yc, w, h, "Symptom checker", "urgency + vet, never doses", fill=AMBER_BG)
    arrow(s, xs[4] + w / 2, yb + h, xs[4] + w / 2, yc)
    arrow(s, xs[4], yc + h / 2, xs[3] + w, yc + h / 2)
    node(s, xs[0], yc, w, h, "Post in a WhatsApp group", "", fill=GREY_BG)
    node(s, xs[1], yc, w, h, "“Is this post safe?”", "nothing is stored", fill=GREY_BG)
    node(s, xs[2], yc, w, h, "CAUTION + questions", "never pay before visiting", fill=AMBER_BG, color=AMBER)
    arrow(s, xs[0] + w, yc + h / 2, xs[1], yc + h / 2)
    arrow(s, xs[1] + w, yc + h / 2, xs[2], yc + h / 2)
    text(s, X0, 5.08, W, 0.3, [("Every step works by tapping, or by asking BreederNear AI in chat: the same tools, the same "
                                "checks. Sellers also earn a Verified breeder badge.", {"size": 8.5, "color": MUTED})])


def _phones(s, names):
    h, gap = 3.55, 0.28
    width = h * 585 / 1266
    x = X0 + (W - (len(names) * width + (len(names) - 1) * gap)) / 2
    for name, cap in names:
        picture(s, name, x, Y0, h, cap)
        x += width + gap


def s_wireframes(s):
    _phones(s, [("01-login", "Sign in or one-tap demo"), ("14-pets-match", "Pets with match %"),
                ("03-listing-trust", "Listing + trust checks"), ("17-my-visits", "Visits, then “I bought it”"),
                ("15-my-pet", "My pets companion")])


def s_architecture(s):
    node(s, X0, 1.3, 1.35, 0.58, "Buyers & sellers", "phone or laptop", fill=GREY_BG)
    node(s, X0, 2.15, 1.35, 0.72, "Firebase Hosting", "web app on Google’s CDN", fill=AMBER_BG, color=AMBER)
    node(s, X0, 3.1, 1.35, 0.72, "Firebase Auth", "Google sign-in (ID token)", fill=AMBER_BG, color=AMBER)
    arrow(s, X0 + 0.67, 1.88, X0 + 0.67, 2.15)
    cx, cy, cw, ch = X0 + 1.75, 1.25, 4.6, 3.8
    box(s, cx, cy, cw, ch, WHITE, line=BLUE, radius=0.1)
    text(s, cx + 0.12, cy + 0.05, cw, 0.25, [("Cloud Run (asia-south1)", {"bold": True, "size": 10, "color": BLUE})])
    node(s, cx + 0.15, cy + 0.36, cw - 0.3, 0.4, "Gatekeeper · login · rate limits · Gemini retries",
         "only the routes the app uses; roles from the server", fill=GREY_BG, size=8.5)
    node(s, cx + 0.15, cy + 0.88, 1.3, 0.8, "FastAPI /api", "tap screens", fill=BLUE_BG, size=9)
    box(s, cx + 1.6, cy + 0.88, cw - 1.75, 1.62, BLUE_BG, radius=0.07)
    text(s, cx + 1.65, cy + 0.9, cw - 1.85, 0.22, [("Google ADK: 7 agents", {"bold": True, "size": 9, "color": BLUE})],
         align=PP_ALIGN.CENTER)
    ax = cx + 1.68
    node(s, ax + 0.75, cy + 1.14, 1.3, 0.28, "Concierge", None, fill=WHITE, size=8)
    for i, name in enumerate(["Listing", "Trust", "Match"]):
        node(s, ax + i * 0.95, cy + 1.52, 0.88, 0.27, name, None, fill=WHITE, size=7.5)
    for i, name in enumerate(["Care", "Verify", "Companion"]):
        node(s, ax + i * 0.95, cy + 1.85, 0.88, 0.27, name, None, fill=WHITE, size=7.5)
    text(s, cx + 1.65, cy + 2.17, cw - 1.85, 0.3, [("callbacks: context · reply guard · tool log", {"size": 7, "color": MUTED})],
         align=PP_ALIGN.CENTER)
    node(s, cx + 0.15, cy + 2.62, cw - 0.3, 1.05, "breedernear_core: one tool layer",
         "listings · trust score · verification · match % · visits · care companion\nanalytics · accounts · safety rules "
         "in code · reused-photo hashing", fill=GREEN_BG, color=GREEN, size=9)
    arrow(s, cx + 0.8, cy + 1.68, cx + 0.8, cy + 2.62)
    arrow(s, cx + 3.1, cy + 2.5, cx + 3.1, cy + 2.62)
    arrow(s, X0 + 1.35, 2.5, cx, 2.5)
    arrow(s, X0 + 1.35, 3.45, cx, 3.45)
    rx, rw = cx + cw + 0.4, W + X0 - (cx + cw + 0.4)
    services = [("Gemini 3.8 Flash", "Vertex AI: agents, photos, certificates,\nlistings, care, scam scan", AMBER_BG, AMBER),
                ("Firestore", "accounts, listings, visits, pets,\nverification, analytics events", GREEN_BG, GREEN),
                ("Cloud Storage", "private uploads, deleted once read", BLUE_BG, BLUE),
                ("Cloud Logging", "one JSON line per tool call", GREY_BG, INK),
                ("Cloud Build + Artifact Registry", "deploy from source; GitHub Actions CI", GREY_BG, INK)]
    for i, (a, b, bg, col) in enumerate(services):
        yy = 1.25 + i * 0.77
        node(s, rx, yy, rw, 0.66, a, b, fill=bg, color=col, size=9)
        arrow(s, cx + cw, yy + 0.33, rx, yy + 0.33)


def s_tech(s):
    rows = [["Google technology", "How BreederNear AI uses it"],
            ["Gemini 3.8 Flash (Vertex AI)", "Seven ADK agents; listing extraction from photos + Tamil/English; photo, facility and "
             "certificate reading; care plans, daily-log feedback, symptom urgency; message drafts and scam scan. JSON schemas."],
            ["Google ADK (Python)", "Concierge + listing, trust, match, care, verification and companion agents; tools; "
             "callbacks on every agent; streamed replies"],
            ["Cloud Run", "API and agents; login gatekeeper; rate limits; Gemini retries with backoff"],
            ["Firebase Hosting", "The web app on Google’s CDN; calls Cloud Run directly (CORS) so AI replies stream"],
            ["Firebase Authentication", "Continue with Google; the server verifies the Firebase ID token"],
            ["Firestore", "Accounts, listings, enquiries, visits, sales, pets and logs, verification, analytics"],
            ["Cloud Storage, Cloud Build, Artifact Registry, Cloud Logging", "Private uploads; deploy from source; tool-call logs"],
            ["gemini-3.1-flash-image", "Illustrative photos for the fictional sample listings (labelled in the app)"]]
    table(s, X0, Y0, 6.25, rows, [1.95, 4.3], size=8.0, row_h=0.35)
    card(s, X0 + 6.45, Y0, W - 6.45, 3.15, "Also used", [
        "Python 3.12, FastAPI, Pydantic",
        "imagehash: reused-photo detection",
        "Plain HTML, CSS, JavaScript and SVG charts: no build step",
        "pytest, Playwright + axe-core, GitHub Actions",
        "Firebase CLI (deploy only)",
    ], size=9.2)


def s_snapshots(s):
    _phones(s, [("11-seller-charts", "Seller analytics"), ("12-verification", "Verified breeder"),
                ("06-blocked", "Protected species: blocked"), ("04-post-check", "“Is this post safe?”"),
                ("18-symptom-check", "Symptom urgency, no doses")])


def _eval_numbers() -> tuple[str, str]:
    """('84/84', '28 cases × 3 runs') from evals/RESULTS.md, so the deck always matches the measured results."""
    import re as _re
    text_ = (ROOT / "evals" / "RESULTS.md").read_text()
    m = _re.search(r"(\d+) full runs: (\d+)/(\d+) case runs passed", text_)
    cases = len(_re.findall(r"^\| E\d+ \|", text_, _re.M))
    return (f"{m.group(2)}/{m.group(3)} passed", f"{cases} cases × {m.group(1)} runs") if m else ("see RESULTS.md", "")


def _unit_tests() -> str:
    out = subprocess.run(["python", "-m", "pytest", "-m", "not live", "-q", "--collect-only", "-p", "no:cacheprovider"],
                         cwd=ROOT, capture_output=True, text=True).stdout
    import re as _re
    m = _re.search(r"(\d+)/\d+ tests collected|(\d+) tests? collected", out)
    return (m.group(1) or m.group(2)) if m else "?"


def s_performance(s):
    evals, runs = _eval_numbers()
    q = [["Quality (real Gemini, 10–11 Oct 2026)", "Result"],
         [f"Agent evals: {runs} (listing, Tamil, blocking, scams, reused photos, prompt injection, no medicine advice, "
          "roles, verification, visits, care companion)", [(evals, {"bold": True, "color": GREEN})]],
         ["Protected species blocked from the photo alone", [("8/8", {"bold": True, "color": GREEN})]],
         ["Ordinary pets wrongly flagged as protected", [("0/37", {"bold": True, "color": GREEN})]],
         ["All photo checks: species, dye, blur, no animal, watermark, screenshot", [("202/202*", {"bold": True})]],
         ["Accessibility: axe-core, WCAG 2.2 AA, light + dark, 320–1280 px, all screens", [("0 problems", {"bold": True, "color": GREEN})]],
         ["Unit tests in CI · live smoke test", [(f"{_unit_tests()} · 17/17", {"bold": True})]]]
    table(s, X0, Y0, 5.75, q, [4.55, 1.2], size=8.2, row_h=0.4)
    p = [["Speed (live)", "Time"],
         ["List a pet: upload, AI fill, publish with trust check", "17–27 s"],
         ["Check a pasted post", "5–7 s"],
         ["Web app load (Firebase CDN)", "≈ 0.7 s"],
         ["Gemini: read a certificate · scan a message", "≈ 4.5 s · ≈ 2 s"],
         ["Gemini: symptom urgency · daily-log feedback", "≈ 8 s"]]
    table(s, X0 + 5.95, Y0, W - 5.95, p, [2.45, 0.9], size=8.2, row_h=0.4)
    text(s, X0 + 5.95, Y0 + 2.55, W - 5.95, 1.2, [
        ("How we test", {"bold": True, "size": 9.5, "after": 2}),
        ("Gemini isn’t deterministic, so each eval runs three times and we report the count. Decisions (trust, "
         "verification, match %, urgency floor) are made by tested code.", {"size": 8.5})])
    footnote(s, ["*Test photos are AI-generated and the screening prompt was tuned on them (first run 196/202), "
                 "so treat this as an upper bound", "Reproduce: scripts/run_evals.sh 3 · scripts/vision_accuracy.py · "
                 "pytest -m ui tests/ui", "evals/RESULTS.md, evals/VISION_RESULTS.md"])


def s_future(s):
    cw = (W - 0.3) / 2
    card(s, X0, Y0, cw, 3.6, "Roadmap (not in the prototype)", [
        "Pilot with real breeders in Coimbatore and Tiruppur, from the founder’s network",
        "Real SMS and email delivery for one-time codes",
        "List by sending a WhatsApp message (WhatsApp Business Platform)",
        "Live State Animal Welfare Board and PARIVESH registry checks; the platform registrations India’s "
        "pet-trade rules require",
        "Chat history in Agent Engine sessions, so Cloud Run can scale past one instance",
        "Breeder ratings from buyers’ care-companion outcomes; vet and pet-pharmacy partners; more languages",
    ], fill=BLUE_BG, title_color=BLUE, size=10.4, title_size=12.5)
    card(s, X0 + cw + 0.3, Y0, cw, 3.6, "Responsible by design (already built)", [
        "Protected species blocked in code, whatever the model says",
        "No medicine names or doses: checked on every AI reply, even while streaming",
        "Verification without ID documents or selfies; photos deleted once read",
        "Codes shown on screen only open new or demo accounts, never someone else’s",
        "Symptom checker: red flags are always an emergency; never a diagnosis",
        "Synthetic sample data, clearly labelled; simulated registry numbers start with SIM-",
    ], fill=GREEN_BG, title_color=GREEN, size=10.4, title_size=12.5)


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
    box(s, X0, Y0 - 0.02, W, 0.42, GREEN_BG)
    text(s, X0 + 0.12, Y0 - 0.02, W - 0.24, 0.42, [[
        ("Market: ", {"bold": True, "size": 10.5, "color": GREEN}),
        ("India’s pet care products market is USD 9.2 B in 2026, heading to USD 13.9 B by 2034⁷, with about "
         "39 million pets¹. The animals themselves are still sold with no checks: that is our wedge.", {"size": 10.5})]],
        anchor=MSO_ANCHOR.MIDDLE)
    cw = (W - 0.4) / 3
    card(s, X0, 1.74, cw, 2.42, "Revenue (planned)", [
        "Verified-breeder subscription: badge, dashboard insights, more listings",
        "Featured listings per district",
        "Starter-kit and accessory commerce after every sale (cart already built)",
        "B2B trust-screening API for classifieds and pet shops",
    ], fill=GREEN_BG, title_color=GREEN, size=9.8, title_size=11.5)
    card(s, X0 + cw + 0.2, 1.74, cw, 2.42, "Built to scale", [
        "Trust costs ≈ ₹1.3 per listing (measured) against pets priced ₹400–₹25,000",
        "Serverless Cloud Run + Firestore: near zero when idle, scales out per request",
        "Districts, species, fair prices and protected lists are data, not code: a new district is a data file",
        "Gemini already reads Tamil, English and mixed messages",
    ], fill=BLUE_BG, title_color=BLUE, size=9.8, title_size=11.5)
    card(s, X0 + 2 * (cw + 0.2), 1.74, cw, 2.42, "Go-to-market", [
        "1 · Pilot in Coimbatore and Tiruppur with the founder’s breeder network",
        "2 · Tamil Nadu, district by district; list by sending a WhatsApp message",
        "3 · Other states and languages; the trust API for other marketplaces",
        "Buyers arrive through “Is this post safe?” links shared in the same groups",
    ], fill=AMBER_BG, title_color=AMBER, size=9.8, title_size=11.5)
    box(s, X0, 4.24, W, 0.82, GREY_BG)
    text(s, X0 + 0.12, 4.26, W - 0.24, 0.8, [
        [("Growth loop: ", {"bold": True, "size": 10, "color": GREEN}),
         ("verified breeders → trusted listings → more buyers → more sales and care data → sharper fair prices and trust "
          "scores → more breeders join.", {"size": 10})],
        [("Impact we measure, live in the app: ", {"bold": True, "size": 10, "color": GREEN}),
         ("listings checked before going live · protected animals stopped · scam warnings raised · verified breeders. "
          "Every warning can be shared back to the group it came from, and protected species come with a way to report them.",
          {"size": 10})],
    ])
    footnote(s, ["Revenue lines and rollout are plans, not results", "¹ Euromonitor 2025",
                 "⁷ IMARC Group, India Pet Care Products Market (2026)", "Cost: docs/submission/05-deck-sources.md"])


def duplicate_slide(prs, src):
    """A copy of a template slide with its branding (header band, logos), placed at the end."""
    dup = prs.slides.add_slide(src.slide_layout)
    for ph in list(dup.placeholders):
        ph._element.getparent().remove(ph._element)
    rid_map = {rel.rId: dup.part.relate_to(rel._target, rel.reltype)
               for rel in src.part.rels.values() if "notesSlide" not in rel.reltype and "slideLayout" not in rel.reltype}
    for shape in src.shapes:
        el = copy.deepcopy(shape._element)
        for node in el.iter():
            for attr in (qn("r:embed"), qn("r:link"), qn("r:id")):
                if node.get(attr) in rid_map:
                    node.set(attr, rid_map[node.get(attr)])
        dup.shapes._spTree.append(el)
    return dup


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
            "Snapshots of the prototype": s_snapshots,     # the optional cost slide is left blank on purpose
            "Prototype Performance report/Benchmarking": s_performance,
            "Additional Details/Future Development (if any)": s_future, "Provide links to your:": s_links}
    for title, fn in fill.items():
        fn(by_title[title])
    blank = slides[14]                     # the template's spare content slide: business case and the journey
    journey = duplicate_slide(prs, blank)
    add_slide_title(blank, "Business case, scale and go-to-market", by_title["Snapshots of the prototype"])
    s_business(blank)
    add_slide_title(journey, "From pain to product: the whole journey, end to end", by_title["Snapshots of the prototype"])
    s_journey(journey)
    delete_slide(prs, 1)                   # the template's "how to download" note
    move_after(prs, blank, by_title["Estimated implementation cost (optional)"])
    move_after(prs, journey, by_title["Brief about the idea"])
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
