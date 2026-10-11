"use strict";

/* Buyer journey and care companion screens (docs/product/04-feature-spec-oct.md): profile and match %,
   AI first message, visits and "I bought this pet", My pets (daily log, growth, health calendar, symptom
   checker), and the seller's visit requests and scam warnings. Loaded before app.js and uses its helpers
   (h, api, icon, openSheet, toast, …) at call time. */

const fmtDay = (iso) => new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });

// ---------------------------------------------------------------- profile and match %
const compat = { loaded: false, byKey: {}, hasProfile: false };
async function loadCompat(force = false) {
  if (!auth.user || isSeller() || (compat.loaded && !force)) return compat;
  try {
    const r = await api("/api/buyer/compatibility");
    compat.byKey = Object.fromEntries(r.species.map((s) => [s.species_key, s]));
    compat.hasProfile = r.species.length > 0;
  } catch { compat.byKey = {}; }
  compat.loaded = true;
  return compat;
}
function resetCompat() { compat.loaded = false; compat.byKey = {}; compat.hasProfile = false; }

function matchChip(c) {
  const m = compat.byKey[c.species_key];
  if (!m) return null;
  const cls = m.percent >= 75 ? "TRUSTED" : m.percent >= 40 ? "CAUTION" : "neutral";
  return h("span", { class: `tag ${cls}`, title: "How well this pet suits your home" }, `${m.percent}% match`);
}

function profileBanner() {
  if (compat.hasProfile) return null;
  return h("button", { class: "callout info inline profile-banner", type: "button", onclick: profileSheet },
    h("b", {}, "See your match %"), "Tell us about your home in a sentence, in English or Tamil, and every pet shows how well it suits you.");
}

async function profileSheet() {
  openSheet("Your home and family", loading("Loading…"));
  const current = await api("/api/buyer/profile").catch(() => ({}));
  const words = h("textarea", { class: "big-input", rows: 4, maxlength: 1000, "aria-label": "About your home and family",
    placeholder: "e.g. 2BHK flat in Tiruppur, 8-year-old daughter, first pet, about 30 minutes a day, budget 3000" });
  words.value = current.words || "";
  const save = h("button", { class: "btn primary block", type: "button" }, icon("sparkles"), "Save and show my matches");
  save.addEventListener("click", async () => {
    save.disabled = true; save.replaceChildren(icon("sparkles"), "Reading with AI…");
    try {
      const r = await api("/api/buyer/profile", { method: "POST", body: JSON.stringify({ words: words.value }) });
      await loadCompat(true);
      setSheet([h("div", { class: "h-sub" }, "Best matches for your home"),
        h("div", { class: "group" }, r.compatibility.slice(0, 6).map((s) => h("div", { class: "list-row" },
          h("div", { class: "grow" }, h("b", {}, s.species), h("div", { class: "muted small" }, (s.percent ? s.reasons : s.watch_outs).join(" · "))),
          h("b", {}, `${s.percent}%`)))),
        h("p", { class: "muted small" }, "Calculated by fixed rules from sample care guidance: space, time, noise, family, budget and allergies.")],
        [h("button", { class: "btn primary block", type: "button", onclick: () => { closeSheet(); route(); } }, "See pets with my match %")]);
    } catch (e) { toast(e.message); save.disabled = false; save.replaceChildren(icon("sparkles"), "Save and show my matches"); }
  });
  setSheet([h("p", { class: "muted", style: "margin:0 0 12px" }, "Describe your home, family, time and budget. AI turns it into a profile; the match % is calculated by fixed rules."),
    words, current.profile ? h("p", { class: "muted small" }, "Your profile is saved. Edit the text to update it.") : null], [save]);
}

// ---------------------------------------------------------------- AI first message
function draftOpeningButton(c, textarea) {
  const b = h("button", { class: "btn small secondary", type: "button" }, icon("sparkles"), "Draft with AI");
  b.addEventListener("click", async () => {
    b.disabled = true; b.replaceChildren(icon("sparkles"), "Drafting…");
    try { textarea.value = (await api(`/api/listings/${encodeURIComponent(c.listing_id)}/opening-message`, { method: "POST" })).message; }
    catch (e) { toast(e.message); }
    b.disabled = false; b.replaceChildren(icon("sparkles"), "Draft again with AI");
  });
  return b;
}

function scanBanner(scan, whose) {
  if (!scan || scan.risk === "none") return null;
  return h("div", { class: `callout ${scan.risk === "high" ? "bad" : "warn"} inline`, style: "margin-top:8px" },
    h("b", {}, scan.risk === "high" ? `Warning signs in this ${whose}` : `Check this ${whose}`),
    scan.signals.join("; ") + ". Never pay before seeing the animal in person.");
}

// ---------------------------------------------------------------- visits and purchase
const SLOT_WORDS = [["morning", "Morning"], ["afternoon", "Afternoon"], ["evening", "Evening"]];
const VISIT_TAG = { requested: ["CAUTION", "Waiting for the breeder"], confirmed: ["TRUSTED", "Confirmed"], declined: ["BLOCKED", "Declined"] };
const isoDay = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);

function visitSheet(c) {
  const today = new Date();
  const min = isoDay(new Date(today.getTime() + 86400000)), max = isoDay(new Date(today.getTime() + 30 * 86400000));
  const date = h("input", { class: "input", type: "date", min, max, value: isoDay(new Date(today.getTime() + 2 * 86400000)), "aria-label": "Visit date", style: "width:100%" });
  let slot = "morning";
  const seg = h("div", { class: "segmented", role: "group", "aria-label": "Time" }, SLOT_WORDS.map(([v, t]) => h("button", { type: "button", "aria-pressed": String(v === slot),
    onclick: (e) => { slot = v; seg.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === e.currentTarget))); } }, t)));
  const note = h("textarea", { class: "big-input", rows: 2, maxlength: 300, "aria-label": "Note for the breeder", placeholder: "Optional, e.g. we'd like to see the parents" });
  const send = h("button", { class: "btn primary block", type: "button" }, "Request visit");
  send.addEventListener("click", async () => {
    send.disabled = true;
    try {
      const r = await api("/api/visits", { method: "POST", body: JSON.stringify({ listing_id: c.listing_id, date: date.value, slot, note: note.value }) });
      setSheet([h("div", { class: "success" }, h("div", { class: "ring" }, icon("check")), h("h3", { style: "margin:0" }, r.visit.status === "confirmed" ? "Visit confirmed" : "Visit requested"),
        h("p", { class: "muted" }, `${fmtDay(r.visit.date)} · ${r.visit.slot_label}. ${r.note}`)),
        h("div", { class: "callout warn" }, h("b", {}, "At the visit"), "See the animal and its parents. Pay only in person, never in advance.")],
        [h("button", { class: "btn primary block", type: "button", onclick: () => { closeSheet(); go("account"); } }, "See my visits")]);
    } catch (e) { toast(e.message); send.disabled = false; }
  });
  setSheet([backTo(() => openListing(c.listing_id, c)), h("h3", { style: "margin:6px 0 10px;font-size:24px" }, `Visit ${c.breeder}`),
    h("div", { class: "h-sub" }, "Day"), date, h("div", { class: "h-sub" }, "Time"), seg, h("div", { class: "h-sub" }, "Note"), note,
    h("p", { class: "muted small" }, "No delivery and no payment in the app: you see the pet in person first.")], [send]);
}

function visitsSection() {
  const box = h("div", {}, loading("Loading…"));
  api("/api/visits").then((r) => {
    box.replaceChildren(r.visits.length ? h("div", { class: "group" }, r.visits.map((v) => {
      const t = VISIT_TAG[v.status] || ["neutral", v.status];
      const buy = h("button", { class: "btn small primary", type: "button" }, "I bought this pet");
      buy.addEventListener("click", () => purchaseSheet(v));
      return h("div", { class: "list-row" }, h("div", { class: "grow" },
        h("div", { style: "display:flex;gap:8px;align-items:center;flex-wrap:wrap" }, h("b", {}, `${v.species} · ${v.breeder}`), h("span", { class: `tag ${t[0]}` }, t[1])),
        h("div", { class: "muted small" }, `${fmtDay(v.date)} · ${v.slot_label}${v.sample_breeder ? " · sample breeder" : ""}`),
        v.seller_note ? h("div", { class: "small" }, `Breeder: “${v.seller_note}”`) : null,
        v.purchased ? h("button", { class: "btn small secondary", type: "button", style: "margin-top:8px", onclick: () => go(`mypets/${v.pet_id}`) }, "Open in My pets")
          : v.status === "confirmed" ? h("div", { style: "margin-top:8px" }, buy) : null));
    })) : h("p", { class: "muted" }, "No visits yet. Open a pet and tap Book a visit."));
  }).catch((e) => box.replaceChildren(errorCallout(e)));
  return box;
}

function purchaseSheet(v) {
  const name = h("input", { class: "input", maxlength: 30, placeholder: "e.g. Mango", "aria-label": "Pet name", style: "width:100%" });
  const ok = h("button", { class: "btn primary block", type: "button" }, "Yes, I bought this pet");
  ok.addEventListener("click", async () => {
    ok.disabled = true;
    try {
      const r = await api("/api/purchases", { method: "POST", body: JSON.stringify({ visit_id: v.id, pet_name: name.value }) });
      closeSheet(); toast(`Welcome home, ${r.pet_name}!`); go(`mypets/${r.pet_id}`);
    } catch (e) { toast(e.message); ok.disabled = false; }
  });
  openSheet("Bought after your visit?", [h("p", { class: "muted", style: "margin-top:0" }, `${v.species} from ${v.breeder}. You paid in person; nothing is paid in this app.`),
    h("div", { class: "h-sub" }, "Name your pet"), name, h("p", { class: "muted small" }, "This starts your care companion: a daily log, growth tracker and health calendar.")], [ok]);
}

// ---------------------------------------------------------------- seller: visit requests
function sellerVisitsSection() {
  const box = h("div");
  api("/api/seller/visits").then((r) => {
    const open = r.visits.filter((v) => v.status === "requested");
    const done = r.visits.filter((v) => v.status !== "requested").slice(-4);
    if (!r.visits.length) { box.replaceChildren(); return; }
    const answer = async (v, action) => {
      try { await api(`/api/seller/visits/${encodeURIComponent(v.id)}`, { method: "POST", body: JSON.stringify({ action }) }); toast(action === "confirm" ? "Visit confirmed" : "Visit declined"); box.replaceWith(sellerVisitsSection()); }
      catch (e) { toast(e.message); }
    };
    box.replaceChildren(h("div", { class: "h-sub" }, "Visit requests"), h("div", { class: "group", style: "margin-bottom:16px" },
      [...open, ...done].map((v) => {
        const t = VISIT_TAG[v.status] || ["neutral", v.status];
        return h("div", { class: "list-row" }, h("div", { class: "grow" },
          h("div", { style: "display:flex;gap:8px;align-items:center;flex-wrap:wrap" }, h("b", {}, `${v.species} · ${fmtDay(v.date)}`), h("span", { class: `tag ${t[0]}` }, v.status === "requested" ? "New" : t[1])),
          h("div", { class: "muted small" }, `${v.slot_label}${v.note ? ` · “${v.note}”` : ""}${v.purchased ? " · bought" : ""}`),
          v.status === "requested" ? h("div", { style: "display:flex;gap:8px;margin-top:8px" },
            h("button", { class: "btn small primary", type: "button", onclick: () => answer(v, "confirm") }, "Confirm"),
            h("button", { class: "btn small secondary", type: "button", onclick: () => answer(v, "decline") }, "Decline")) : null));
      })));
  }).catch(() => box.replaceChildren());
  return box;
}

// ---------------------------------------------------------------- My pets (care companion)
const URGENCY = { emergency: ["BLOCKED", "Emergency: go to a vet now"], vet_soon: ["CAUTION", "See a vet soon"], monitor: ["neutral", "Watch at home"] };

async function viewMyPets() {
  const petId = location.hash.split("/")[1];
  if (petId) return petPage(decodeURIComponent(petId));
  const body = h("div", {}, loading("Loading your pets…"));
  main.replaceChildren(h("div", { class: "view" }, hero("Care companion", "My pets", "Daily care, growth and health for the pets you bring home."), body, disclaimer()));
  try {
    const r = await api("/api/companion/pets");
    body.replaceChildren(r.pets.length ? h("div", { class: "group" }, r.pets.map((p) => h("button", { class: "row", type: "button", onclick: () => go(`mypets/${p.pet_id}`) },
      avatar(p.name, "avatar"), h("span", { class: "grow" }, h("b", {}, p.name), h("div", { class: "muted small" },
        `${[p.species, p.variety].filter(Boolean).join(" · ")} · day ${p.days_home + 1} at home${p.streak ? ` · ${p.streak}-day streak` : ""}`)), h("span", { class: "chev" }, icon("chevR")))))
      : empty("heart", "No pets yet", "After a visit, tap “I bought this pet” under Account. Your care companion starts here.",
        h("button", { class: "btn small primary", type: "button", onclick: () => go("pets") }, "Find a pet")));
  } catch (e) { body.replaceChildren(errorCallout(e)); }
}

async function petPage(id) {
  const body = h("div", {}, loading("Loading…"));
  main.replaceChildren(h("div", { class: "view" }, h("a", { class: "link", href: "#mypets", style: "margin-top:14px" }, icon("chevL"), "My pets"), body, disclaimer()));
  let d;
  try { d = await api(`/api/companion/pets/${encodeURIComponent(id)}`); } catch (e) { body.replaceChildren(errorCallout(e)); return; }
  const p = d.pet;
  const reload = () => petPage(id);
  // today's log
  const food = h("input", { class: "input", maxlength: 400, placeholder: "e.g. seed mix and coriander", "aria-label": "Food today", style: "width:100%" });
  const play = h("input", { class: "input", maxlength: 400, placeholder: "e.g. climbed the ladder", "aria-label": "Play today", style: "width:100%" });
  const note = h("input", { class: "input", maxlength: 400, placeholder: "Anything else?", "aria-label": "Note", style: "width:100%" });
  const photos = [];
  const photoBtn = h("button", { class: "btn small secondary", type: "button" }, icon("camera"), "Food photo");
  photoBtn.addEventListener("click", () => pickPhotos(photos, () => { photoBtn.replaceChildren(icon("check"), photos.length ? "Photo added" : "Food photo"); }));
  const feedback = h("div");
  const save = h("button", { class: "btn primary block", type: "button" }, icon("sparkles"), "Save today's log");
  save.addEventListener("click", async () => {
    save.disabled = true; save.replaceChildren(icon("sparkles"), "Checking with AI…");
    try {
      const photo = photos.length ? (await uploadPhotos(photos.slice(-1), "food_photo"))[0] : null;
      const r = await api(`/api/companion/pets/${encodeURIComponent(id)}/log`, { method: "POST", body: JSON.stringify({ food: food.value, play: play.value, note: note.value, photo_upload_id: photo }) });
      feedback.replaceChildren(h("div", { class: `callout ${r.log.food_ok ? "info" : "warn"} inline`, style: "margin-top:10px" },
        h("b", {}, r.log.food_ok ? `Logged · ${r.streak}-day streak` : "Check today's food"), r.log.feedback,
        r.log.suggestions.length ? h("ul", { style: "margin:6px 0 0;padding-left:18px" }, r.log.suggestions.map((s) => h("li", {}, s))) : null));
      food.value = play.value = note.value = ""; photos.length = 0; photoBtn.replaceChildren(icon("camera"), "Food photo");
    } catch (e) { toast(e.message); }
    save.disabled = false; save.replaceChildren(icon("sparkles"), "Save today's log");
  });
  // growth
  const tw = d.typical_weight;
  const weight = h("input", { class: "input", type: "number", inputmode: "decimal", step: "0.1", min: "0", placeholder: tw ? `in ${tw.unit}` : "weight", "aria-label": "Weight", style: "flex:1;min-width:0" });
  const verdict = h("div");
  const addW = h("button", { class: "btn small secondary", type: "button" }, "Add");
  addW.addEventListener("click", async () => {
    try { const r = await api(`/api/companion/pets/${encodeURIComponent(id)}/weight`, { method: "POST", body: JSON.stringify({ value: Number(weight.value) }) }); toast(r.verdict); reload(); }
    catch (e) { toast(e.message); }
  });
  const growth = d.weights.length ? barChart({ title: `Weight (${d.weights[0].unit})`, labels: d.weights.map((w) => fmtDay(w.day)),
    series: [{ name: "Weight", values: d.weights.map((w) => w.value), color: "var(--accent)" }], format: (v) => String(Math.round(v * 10) / 10), height: 150 }) : null;
  // symptom checker
  const sym = h("textarea", { class: "big-input", rows: 2, maxlength: 400, "aria-label": "What do you notice?", placeholder: "e.g. sneezing and fluffed up since morning" });
  const symOut = h("div");
  const check = h("button", { class: "btn secondary block", type: "button" }, icon("shield"), "Check how urgent this is");
  check.addEventListener("click", async () => {
    check.disabled = true;
    try {
      const r = await api(`/api/companion/pets/${encodeURIComponent(id)}/symptoms`, { method: "POST", body: JSON.stringify({ text: sym.value }) });
      const u = URGENCY[r.urgency];
      symOut.replaceChildren(h("div", { class: "card", style: "margin-top:10px" },
        h("span", { class: `tag ${u[0]}` }, icon(r.urgency === "monitor" ? "info" : "warn"), u[1]),
        h("p", { style: "margin:8px 0 6px" }, h("b", {}, r.first_step)), h("p", { class: "muted", style: "margin:0 0 6px" }, r.possible_meaning),
        r.do_now.length ? [h("div", { class: "h-sub" }, "What to do now"), h("ul", { style: "margin:0;padding-left:18px" }, r.do_now.map((x) => h("li", {}, x)))] : null,
        r.watch_for.length ? [h("div", { class: "h-sub" }, "Go sooner if you see"), h("ul", { style: "margin:0;padding-left:18px" }, r.watch_for.map((x) => h("li", {}, x)))] : null,
        h("p", { class: "disclaimer" }, r.disclaimer)));
    } catch (e) { toast(e.message); }
    check.disabled = false;
  });
  body.replaceChildren(h("div", {},
    h("div", { class: "card", style: "display:flex;gap:14px;align-items:center;margin:8px 0 14px" }, avatar(p.name, "avatar lg"),
      h("div", {}, h("b", { style: "font-size:22px" }, p.name), h("div", { class: "muted small" }, [p.species, p.variety].filter(Boolean).join(" · ")),
        h("div", { class: "small", style: "margin-top:4px" }, `Day ${p.days_home + 1} at home${p.age_months != null ? ` · about ${Math.round(p.age_months)} months old` : ""}${p.streak ? ` · ${p.streak}-day streak` : ""}`))),
    h("div", { class: "callout info inline" }, h("b", {}, "This week"), d.check_in),
    h("div", { class: "h-sub" }, "Today's log"),
    h("div", { class: "card", style: "display:grid;gap:8px" }, food, play, note, h("div", {}, photoBtn), save, feedback),
    d.logs.length ? [h("div", { class: "h-sub" }, "Recent days"), h("div", { class: "group" }, d.logs.slice(0, 5).map((l) => h("div", { class: "list-row" },
      h("div", { class: "grow" }, h("b", {}, fmtDay(l.day)), h("div", { class: "muted small" }, [l.food, l.play, l.note].filter(Boolean).join(" · ") || "Photo only")),
      l.food_ok ? null : h("span", { class: "tag CAUTION" }, icon("warn"), "Food"))))] : null,
    h("div", { class: "h-sub" }, "Growth"),
    tw ? h("p", { class: "muted small", style: "margin:0 0 8px" }, `${tw.label[0].toUpperCase() + tw.label.slice(1)}: ${tw.low}–${tw.high} ${tw.unit} (general guidance)`) : null,
    h("div", { style: "display:flex;gap:8px;margin-bottom:10px" }, weight, addW), verdict, growth,
    h("div", { class: "h-sub" }, "Health calendar"),
    h("div", { class: "group" }, d.calendar.map((c) => h("div", { class: "list-row" }, h("div", { class: "grow" }, c.what,
      c.due ? h("div", { class: "muted small" }, `Around ${fmtDay(c.due)} · ${c.status}`) : null)))),
    h("p", { class: "small" }, h("b", {}, "Deworming: "), d.deworming),
    h("div", { class: "h-sub" }, "Symptom checker"),
    h("p", { class: "muted small", style: "margin:0 0 8px" }, "Not a diagnosis. It tells you how urgently to see a vet; it never suggests medicines or doses."),
    sym, h("div", { style: "height:8px" }), check, symOut,
    h("div", { class: "h-sub" }, "Go to a vet at once if"), h("ul", { class: "small", style: "margin:0;padding-left:18px" }, d.red_flags.map((x) => h("li", {}, x))),
    h("p", { class: "disclaimer" }, d.disclaimer)));
}

// ---------------------------------------------------------------- sell flow: vaccination card
function vaccinationButton(draftId) {
  const files = [];
  const b = h("button", { class: "btn small secondary", type: "button" }, icon("camera"), "Add vaccination card (optional)");
  b.addEventListener("click", () => pickPhotos(files, async () => {
    if (!files.length) return;
    b.disabled = true; b.replaceChildren("Attaching…");
    try {
      const [id] = await uploadPhotos(files.slice(-1), "vaccination");
      await api(`/api/sell/drafts/${encodeURIComponent(draftId)}/vaccination`, { method: "POST", body: JSON.stringify({ upload_id: id }) });
      b.replaceChildren(icon("check"), "Vaccination card attached: read when you publish");
    } catch (e) { toast(e.message); b.disabled = false; b.replaceChildren(icon("camera"), "Add vaccination card (optional)"); }
  }));
  return b;
}

// ---------------------------------------------------------------- sign-in: Google and one-time code (F21)
const FIREBASE_SDK = "https://www.gstatic.com/firebasejs/10.14.1/";
function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
    document.head.append(Object.assign(document.createElement("script"), { src, onload: resolve, onerror: () => reject(new Error("Couldn't load Google sign-in. Check your connection.")) }));
  });
}

// For a first sign-in: buy or sell, name, and the farm name for sellers. Resolves with the details or null.
function newAccountDetails(suggestedName = "") {
  return new Promise((resolve) => {
    let role = "customer";
    const name = h("input", { class: "input", maxlength: 60, value: suggestedName, placeholder: "Your name", "aria-label": "Your name", style: "width:100%" });
    const farm = h("input", { class: "input", maxlength: 80, placeholder: "Farm or kennel name", "aria-label": "Farm or kennel name", style: "width:100%", hidden: true });
    const seg = h("div", { class: "segmented", role: "group", "aria-label": "I want to" }, [["customer", "Buy pets"], ["seller", "Sell pets"]].map(([v, t]) =>
      h("button", { type: "button", "aria-pressed": String(v === role), onclick: (e) => { role = v; farm.hidden = v !== "seller";
        seg.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === e.currentTarget))); } }, t)));
    const go = h("button", { class: "btn primary block", type: "button" }, "Create my account");
    go.addEventListener("click", () => { closeSheet(); resolve({ role, name: name.value, district: state.district, farm: role === "seller" ? { farm_name: farm.value, species: [] } : null }); });
    openSheet("Welcome to BreederNear", [h("p", { class: "muted", style: "margin-top:0" }, "First time here. One account is for buying or for selling."),
      seg, h("div", { style: "height:10px" }), name, h("div", { style: "height:8px" }), farm], [go]);
    $("sheet").addEventListener("close", () => resolve(null), { once: true });
  });
}

async function googleSignIn(remember) {
  const cfg = window.BREEDERNEAR_FIREBASE;
  if (!cfg) { toast("Google sign-in isn't set up yet."); return; }
  try {
    await loadScript(FIREBASE_SDK + "firebase-app-compat.js");
    await loadScript(FIREBASE_SDK + "firebase-auth-compat.js");
    if (!window.firebase.apps.length) window.firebase.initializeApp(cfg);
    const result = await window.firebase.auth().signInWithPopup(new window.firebase.auth.GoogleAuthProvider());
    const idToken = await result.user.getIdToken();
    const send = (extra = {}) => api("/api/auth/google", { method: "POST", body: JSON.stringify({ id_token: idToken, remember, ...extra }) });
    let r;
    try { r = await send(); }
    catch (e) {
      if (e.status !== 422) throw e;
      const details = await newAccountDetails(result.user.displayName || "");
      if (!details) return;
      r = await send(details);
    }
    await window.firebase.auth().signOut();                       // our own session takes over from here
    await finishLogin(r, remember);
  } catch (e) {
    if (e.code === "auth/popup-closed-by-user" || e.code === "auth/cancelled-popup-request") return;
    toast(e.message || "Google sign-in failed. Please try again.");
  }
}

function codeSignInSheet(remember) {
  const login = h("input", { class: "input", inputmode: "email", autocomplete: "username", placeholder: "you@example.com or 98765 43210", "aria-label": "Email or mobile number", style: "width:100%" });
  const step2 = h("div");
  const send = h("button", { class: "btn primary block", type: "button" }, "Send code");
  send.addEventListener("click", async () => {
    send.disabled = true;
    try {
      const r = await api("/api/auth/code/request", { method: "POST", body: JSON.stringify({ login: login.value }) });
      const code = h("input", { class: "input", inputmode: "numeric", maxlength: 6, placeholder: "6-digit code", "aria-label": "Code", style: "width:100%" });
      const verify = h("button", { class: "btn primary block", type: "button" }, r.new_account ? "Verify and create account" : "Verify and log in");
      verify.addEventListener("click", async () => {
        verify.disabled = true;
        try {
          const details = r.new_account ? await newAccountDetails() : {};
          if (details === null) { verify.disabled = false; return; }
          await finishLogin(await api("/api/auth/code/verify", { method: "POST", body: JSON.stringify({ login: login.value, code: code.value, remember, ...details }) }), remember);
          closeSheet();
        } catch (e) { toast(e.message); verify.disabled = false; }
      });
      step2.replaceChildren(h("div", { class: "callout info inline", style: "margin:12px 0 10px" }, h("b", {}, "Demo code"),
        h("div", { class: "demo-code" }, r.demo_code), h("div", { class: "small" }, "Shown here because this demo sends no SMS or email. Valid for 5 minutes.")), code, h("div", { style: "height:10px" }), verify);
      send.hidden = true;
    } catch (e) { toast(e.message); send.disabled = false; }
  });
  openSheet("Log in with a code", [h("p", { class: "muted", style: "margin-top:0" }, "For new accounts and the demo accounts. Existing accounts log in with their password or Google."),
    login, h("div", { style: "height:10px" }), send, step2]);
}

function altLogins(remember) {
  return h("div", {},
    h("div", { style: "display:flex;align-items:center;gap:10px;margin:18px 0 12px;color:var(--label-3);font-size:13px" }, h("span", { style: "flex:1;border-top:.5px solid var(--sep)" }), "OR", h("span", { style: "flex:1;border-top:.5px solid var(--sep)" })),
    h("div", { style: "display:grid;gap:8px" },
      window.BREEDERNEAR_FIREBASE?.googleEnabled ? h("button", { class: "btn secondary block", type: "button", onclick: () => googleSignIn(remember.checked) }, h("span", { class: "g-mark", "aria-hidden": "true" }, "G"), "Continue with Google") : null,
      h("button", { class: "btn secondary block", type: "button", onclick: () => codeSignInSheet(remember.checked) }, icon("mail"), "Use a one-time code")));
}
