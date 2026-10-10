"use strict";

/* BreederNear AI web app: three tabs (Pets · Local Breeders + My farm · BreederNear AI).
   The tabs call /api directly; the AI tab talks to the ADK agents. Both use the same service code. */

const APP = "breedernear";
const MAX_PHOTOS = 4;

// ---------------------------------------------------------------- storage & identity
const memory = {};
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return memory[k] ?? null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { memory[k] = v; } },
  del(k) { try { localStorage.removeItem(k); } catch { delete memory[k]; } },
};
function uuid() {
  if (window.crypto?.randomUUID) return crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}
const GUEST = (() => {
  let id = store.get("breedernear_guest_id");
  if (!id || !/^[0-9a-f-]{36}$/i.test(id)) { id = uuid(); store.set("breedernear_guest_id", id); }
  return id;
})();

// ---------------------------------------------------------------- DOM helpers
const $ = (id) => document.getElementById(id);
function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;            // only used with trusted SVG markup or escaped markdown
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat(Infinity)) if (c != null && c !== false) el.append(c.nodeType ? c : String(c));
  return el;
}
const ICONS = {
  paw: '<circle cx="6.5" cy="9.5" r="1.8"/><circle cx="10" cy="5.8" r="1.8"/><circle cx="14" cy="5.8" r="1.8"/><circle cx="17.5" cy="9.5" r="1.8"/><path d="M8 17.2c0-2.6 1.8-5 4-5s4 2.4 4 5c0 1.7-1.6 2.6-4 2.6s-4-.9-4-2.6z"/>',
  barn: '<path d="M3 10.5 12 4l9 6.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  sparkles: '<path d="M11 3.5l1.7 4.6 4.6 1.7-4.6 1.7L11 16.1l-1.7-4.6-4.6-1.7 4.6-1.7z"/><path d="M18.5 14.5l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z"/>',
  bag: '<path d="M5.5 8h13l-1 12.5h-11z"/><path d="M9 8V7a3 3 0 0 1 6 0v1"/>',
  pin: '<path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
  chevR: '<path d="M9 5l7 7-7 7"/>', chevL: '<path d="M15 5l-7 7 7 7"/>', chevD: '<path d="M6 9l6 6 6-6"/>',
  shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8.2-8 9-4.6-.8-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>', warn: '<path d="M12 6.5v7"/><path d="M12 17.5h.01"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>', info: '<path d="M12 11v6"/><path d="M12 7.5h.01"/>',
  camera: '<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
  up: '<path d="M12 19V5M5.5 11.5 12 5l6.5 6.5"/>', plus: '<path d="M12 5v14M5 12h14"/>',
  shop: '<path d="M4 9l1.5-5h13L20 9"/><path d="M4 9v11h16V9"/><path d="M9.5 20v-5.5h5V20"/>',
  mail: '<rect x="3" y="5.5" width="18" height="13" rx="2"/><path d="M3.5 7l8.5 6 8.5-6"/>',
  list: '<path d="M8 6h12M8 12h12M8 18h12"/><path d="M4 6h.01M4 12h.01M4 18h.01"/>',
  chat: '<path d="M4 5h16v11H9l-5 4z"/>', search: '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
};
const icon = (name) => h("span", { html: `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`, style: "display:contents" });
const inr = (n) => (n == null ? "—" : "₹" + Number(n).toLocaleString("en-IN"));
const titleCase = (s) => (s || "").replace(/\b[a-z]/g, (c) => c.toUpperCase());
const sentence = (s) => (s ? s[0].toUpperCase() + s.slice(1) : "");
const escapeHtml = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function toast(text) {
  document.querySelector(".toast")?.remove();
  const t = h("div", { class: "toast", role: "status" }, text);
  document.body.append(t);
  setTimeout(() => t.remove(), 3200);
}

// Minimal, safe markdown for agent replies: HTML is escaped first.
function md(text) {
  const inline = (s) => escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*(?!\s)(.+?)\*(?!\*)/g, "$1<em>$2</em>").replace(/`([^`]+)`/g, "<code>$1</code>");
  const out = []; let list = null, para = [];
  const flushPara = () => { if (para.length) { out.push(`<p>${para.join("<br>")}</p>`); para = []; } };
  const flushList = () => { if (list) { out.push(`<${list.tag}>${list.items.map((i) => `<li>${i}</li>`).join("")}</${list.tag}>`); list = null; } };
  for (const raw of text.split("\n")) {
    const line = raw.trimEnd(); let m;
    if (!line.trim() || /^\s*(---|\*\*\*)\s*$/.test(line)) { flushPara(); flushList(); continue; }
    if ((m = line.match(/^\s*#{1,6}\s+(.*)$/))) { flushPara(); flushList(); out.push(`<h4>${inline(m[1])}</h4>`); continue; }
    if ((m = line.match(/^\s*[-*•]\s+(.*)$/)) || (m = line.match(/^\s*\d+[.)]\s+(.*)$/))) {
      flushPara();
      const tag = /^\s*\d/.test(line) ? "ol" : "ul";
      if (!list || list.tag !== tag) { flushList(); list = { tag, items: [] }; }
      list.items.push(inline(m[1])); continue;
    }
    flushList(); para.push(inline(line));
  }
  flushPara(); flushList();
  return out.join("");
}

// ---------------------------------------------------------------- API
async function api(path, options = {}) {
  const res = await fetch(path, { ...options, headers: { "Content-Type": "application/json", "X-Guest-Id": GUEST, ...(options.headers || {}) } });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(typeof body.detail === "string" ? body.detail : "Something went wrong. Please try again.");
    err.status = res.status; throw err;
  }
  return body;
}
const qs = (params) => new URLSearchParams(Object.entries(params).filter(([, v]) => v != null && v !== "")).toString();

async function shrink(file) {
  // Phone photos are often over the 5 MB limit: resize to 1600 px JPEG in the browser.
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
    const canvas = Object.assign(document.createElement("canvas"), { width: Math.round(bitmap.width * scale), height: Math.round(bitmap.height * scale) });
    canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    return blob ? new File([blob], "photo.jpg", { type: "image/jpeg" }) : file;
  } catch { return file; }
}
async function uploadPhotos(photos, kind) {
  const ids = [];
  for (const { file } of photos) {
    const form = new FormData();
    form.append("file", await shrink(file)); form.append("kind", kind);
    const res = await fetch("/api/uploads", { method: "POST", headers: { "X-Guest-Id": GUEST }, body: form });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || "Couldn't upload the photo.");
    ids.push(body.upload_id);
  }
  return ids;
}
function pickPhotos(list, onChange) {
  const input = h("input", { type: "file", accept: "image/*", multiple: true, hidden: true });
  input.addEventListener("change", () => {
    for (const file of input.files) {
      if (list.length >= MAX_PHOTOS) { toast(`Up to ${MAX_PHOTOS} photos`); break; }
      if (file.type.startsWith("image/")) list.push({ file, url: URL.createObjectURL(file) });
    }
    input.remove(); onChange();
  });
  document.body.append(input); input.click();
}
function photoTiles(list, onChange, { addLabel = "Add photo" } = {}) {
  return h("div", { class: "photos" },
    list.map((p, i) => h("div", { class: "photo-tile" }, h("img", { src: p.url, alt: `Photo ${i + 1}` }),
      h("button", { class: "x", type: "button", "aria-label": `Remove photo ${i + 1}`, onclick: () => { URL.revokeObjectURL(p.url); list.splice(i, 1); onChange(); } }, icon("x")))),
    list.length < MAX_PHOTOS ? h("button", { class: "add-photo", type: "button", onclick: () => pickPhotos(list, onChange) }, icon("camera"), addLabel) : null);
}

// ---------------------------------------------------------------- app state
const state = {
  districts: [], district: store.get("breedernear_district") || "coimbatore",
  filters: { species: "all", trusted: false, max: "" },
  cartCount: 0, farmCounts: { listings: 0, enquiries: 0 },
};
const districtName = (key) => state.districts.find((d) => d.key === key)?.name || titleCase(key);
function setDistrict(key) { state.district = key; store.set("breedernear_district", key); renderHeader(); route(); }

const SPECIES_CHIPS = [["all", "All"], ["bird", "Birds"], ["budgie", "Budgies"], ["lovebird", "Lovebirds"], ["cockatiel", "Cockatiels"],
  ["finch", "Finches"], ["canary", "Canaries"], ["dog", "Dogs"], ["cat", "Cats"]];
const PRICE_CAPS = [["", "Any price"], ["1000", "Up to ₹1,000"], ["3000", "Up to ₹3,000"], ["10000", "Up to ₹10,000"], ["30000", "Up to ₹30,000"]];
const LEVEL_WORD = { TRUSTED: "Trusted", CAUTION: "Caution", BLOCKED: "Blocked" };
const LEVEL_ICON = { TRUSTED: "check", CAUTION: "warn", BLOCKED: "x" };
const CHECK_ICON = { pass: "check", warn: "warn", block: "x", info: "info" };
const PRODUCT_EMOJI = { cage: "🏠", food: "🌾", perches: "🪵", feeders: "🥣", mineral: "🦴", carrier: "🧳", treat: "🌾", toy: "🧸",
  bowls: "🥣", bed: "🛏️", collar_leash: "🦮", grooming: "🪮", hygiene: "🧴", litter_box: "📦", litter: "🪣", scratching_post: "🪵" };
const FIELD_NAMES = { price_inr: "price", age_months: "age", health_notes: "health notes", district: "district",
  sawb_registration_no: "dog-breeder registration", parivesh_registration_id: "PARIVESH registration" };

function groupOf(c) {
  const t = `${c.animal_group || ""} ${c.species || c.species_common || ""}`.toLowerCase();
  if (/dog|labrador|beagle|shih|puppy|retriever/.test(t)) return "dog";
  if (/cat|persian|kitten/.test(t)) return "cat";
  if (/bird|budg|lovebird|cockatiel|finch|canary|parakeet|parrot/.test(t)) return "bird";
  return "other";
}
function emojiFor(c) {
  const g = groupOf(c), t = (c.species || c.species_common || "").toLowerCase();
  if (g === "dog") return "🐕"; if (g === "cat") return "🐈";
  if (/finch|canary/.test(t)) return "🐤"; if (g === "bird") return "🦜"; return "🐾";
}
const unitWord = (u) => (u === "pair" ? "pair" : u === "litter" ? "litter" : "each");

// ---------------------------------------------------------------- components
function tag(level, score) {
  return h("span", { class: `tag ${level}` }, icon(LEVEL_ICON[level] || "info"), LEVEL_WORD[level] || level, score != null ? ` ${score}` : "");
}
function media(c, cls = "media") {
  const box = h("div", { class: `${cls} ${groupOf(c)}`, "aria-hidden": "true" }, emojiFor(c));
  if (c.photo) {
    const img = h("img", { src: `/${c.photo}`, alt: "", loading: "lazy" });
    img.addEventListener("error", () => img.remove());
    box.append(img);
  }
  return box;
}
function petCard(c) {
  const m = media(c);
  m.append(h("div", { class: "float" }, tag(c.trust_level), c.is_yours ? h("span", { class: "tag neutral" }, "Yours") : null));
  return h("button", { class: "pet", type: "button", onclick: () => openListing(c.listing_id, c),
    "aria-label": `${c.species} ${c.variety || ""}, ${inr(c.price_inr)} per ${unitWord(c.unit)}, ${LEVEL_WORD[c.trust_level]}` },
    m,
    h("div", { class: "body" },
      h("div", { class: "name" }, [c.species, c.variety].filter(Boolean).join(" · ")),
      h("div", { class: "price" }, inr(c.price_inr), h("small", {}, ` / ${unitWord(c.unit)}`)),
      h("div", { class: "meta" }, c.distance ? sentence(c.distance) : titleCase(c.district)),
      h("div", { class: "meta" }, c.breeder)));
}
const petGrid = (cards) => h("div", { class: "pet-grid" }, cards.map(petCard));

function rangeBar(price, range) {
  if (!range || !price) return null;
  const [lo, hi] = range, max = hi * 1.6;
  const pct = (v) => Math.max(2, Math.min(98, (v / max) * 100));
  const where = price < lo * 0.5 ? ["warn", "Far below the usual price: a common scam sign"] : price < lo ? ["warn", "Below the usual price"]
    : price > hi * 1.5 ? ["info", "Well above the usual price"] : ["check", "Fair price"];
  return h("div", { class: "range" },
    h("div", { class: "track", role: "img", "aria-label": `Price ${inr(price)}; usual range ${inr(lo)} to ${inr(hi)}` },
      h("div", { class: "fair", style: `left:${pct(lo)}%;width:${pct(hi) - pct(lo)}%` }),
      h("div", { class: "knob", style: `left:${pct(price)}%` })),
    h("div", { class: "label" }, icon(where[0]), `${where[1]} · usual ${inr(lo)}–${inr(hi)} (sample market data)`));
}
function checksGroup(checks = []) {
  return h("div", { class: "group" }, checks.map((c) => h("div", { class: "check-row" },
    h("span", { class: `ci ${c.result}`, role: "img", "aria-label": c.result }, icon(CHECK_ICON[c.result] || "info")), h("span", {}, c.detail))));
}
function questionsCallout(qs) {
  return qs?.length ? h("div", { class: "callout info", style: "margin-top:12px" }, h("b", {}, "Ask the seller"), h("ul", {}, qs.map((q) => h("li", {}, q)))) : null;
}
function trustSummary(screening, title, note) {
  return h("div", {},
    h("div", { class: "detail-head" }, h("h3", {}, title), tag(screening.trust_level, screening.trust_score)),
    note ? h("p", { class: "muted", style: "margin:0 0 12px" }, note) : null,
    checksGroup(screening.checks), questionsCallout(screening.questions_to_ask_seller));
}
const AVATAR_GRADIENTS = ["linear-gradient(140deg,#34a36a,#1d6a43)", "linear-gradient(140deg,#e09a3e,#b8641f)", "linear-gradient(140deg,#5b8def,#3557c9)",
  "linear-gradient(140deg,#b06ad8,#7a3fae)", "linear-gradient(140deg,#e2677a,#b23a52)", "linear-gradient(140deg,#3fb2b8,#22777d)"];
function avatar(name, cls = "avatar") {
  const initials = name.split(/\s+/).filter((w) => /^[A-Za-z]/.test(w)).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
  const hash = [...name].reduce((a, ch) => (a * 31 + ch.charCodeAt(0)) >>> 0, 7);
  return h("div", { class: cls, style: `background:${AVATAR_GRADIENTS[hash % AVATAR_GRADIENTS.length]}`, "aria-hidden": "true" }, initials);
}
function regTag(status) {
  if (!status) return null;
  return status === "valid" ? h("span", { class: "tag TRUSTED" }, icon("check"), "Registered dog breeder")
    : h("span", { class: "tag CAUTION" }, icon("warn"), status === "missing" ? "No dog-breeder registration" : "Registration not found");
}
function breederTags(b) {
  return h("div", { class: "tags" },
    b.trust_level === "TRUSTED" ? h("span", { class: "tag TRUSTED" }, icon("check"), "All listings trusted")
      : h("span", { class: "tag CAUTION" }, icon("warn"), `${b.caution_listings} listing${b.caution_listings > 1 ? "s" : ""} need caution`),
    regTag(b.dog_registration));
}
function loading(text) { return h("div", { class: "loading-line" }, h("span", { class: "spinner" }), text); }
function errorCallout(e) { return h("div", { class: "callout bad" }, e.message || "Something went wrong. Please try again."); }
function empty(iconName, title, text, action) {
  return h("div", { class: "empty" }, h("div", { class: "ico green" }, icon(iconName)), h("b", {}, title), h("div", {}, text),
    action ? h("div", { style: "margin-top:14px" }, action) : null);
}
const disclaimer = () => h("p", { class: "disclaimer" }, "Prototype — sample breeders, listings and products. No payments. Not veterinary advice.");

// ---------------------------------------------------------------- sheet
const sheet = $("sheet");
function openSheet(title, content, actions = []) {
  $("sheet-title").textContent = title;
  $("sheet-content").replaceChildren(...[content].flat(Infinity).filter(Boolean));
  $("sheet-content").scrollTop = 0;
  const acts = [actions].flat(Infinity).filter(Boolean);
  $("sheet-actions").replaceChildren(...acts);
  $("sheet-actions").hidden = !acts.length;
  if (!sheet.open) { sheet.showModal(); document.documentElement.style.overflow = "hidden"; }
}
function setSheet(content, actions) { openSheet($("sheet-title").textContent, content, actions); }
function closeSheet() { if (sheet.open) sheet.close(); }
sheet.addEventListener("close", () => { document.documentElement.style.overflow = ""; });
sheet.addEventListener("click", (e) => { if (e.target === sheet) closeSheet(); });
$("sheet-close").append(icon("x"));
$("sheet-close").addEventListener("click", closeSheet);

// listing page
async function openListing(id, card) {
  openSheet("Pet", loading("Opening…"));
  let r;
  try { r = await api(`/api/listings/${encodeURIComponent(id)}`); } catch (e) { setSheet(errorCallout(e)); return; }
  const c = { ...r.listing, distance: card?.distance || r.listing.distance };
  const facts = h("div", { class: "facts" },
    h("div", { class: "fact" }, h("small", {}, "Age"), h("span", {}, c.age_months != null ? `${c.age_months} months` : "—")),
    h("div", { class: "fact" }, h("small", {}, "Available"), h("span", {}, c.unit === "pair" ? `${c.count} pair${c.count > 1 ? "s" : ""}` : `${c.count}`)),
    h("div", { class: "fact" }, h("small", {}, "Where"), h("span", {}, [c.locality, titleCase(c.district)].filter(Boolean).join(", "))),
    c.breeder_id ? h("button", { class: "fact", type: "button", onclick: () => openBreeder(c.breeder_id) }, h("small", {}, "Breeder"), h("span", {}, c.breeder, " ›"))
      : h("div", { class: "fact" }, h("small", {}, "Breeder"), h("span", {}, c.breeder)));
  const content = [
    media(c, "media detail-media"),
    h("div", { class: "detail-head" }, h("h3", {}, [c.species, c.variety].filter(Boolean).join(" · ")), tag(c.trust_level, c.trust_score)),
    h("div", { class: "big-price" }, inr(c.price_inr), h("small", {}, ` / ${unitWord(c.unit)}`)),
    c.distance ? h("div", { class: "muted" }, sentence(c.distance)) : null,
    rangeBar(c.price_inr, c.fair_price_range_inr),
    facts,
    r.description ? h("p", { class: "muted", style: "margin:0" }, r.description) : null,
    r.health_notes ? h("p", { style: "margin:8px 0 0" }, h("b", {}, "Health: "), r.health_notes) : null,
    h("div", { class: "h-sub" }, "Trust checks"), checksGroup(r.checks), questionsCallout(r.questions_to_ask_seller),
    h("p", { class: "disclaimer", style: "margin-top:18px" }, c.sample_data ? "Sample listing from a fictional breeder." : "Your own listing (visible only to you)."),
  ];
  openSheet("Pet", content, [
    h("button", { class: "btn primary block", type: "button", onclick: () => contactView(c, r) }, icon("mail"), "Contact breeder"),
    h("div", { style: "display:grid;grid-template-columns:1fr 1fr;gap:8px" },
      h("button", { class: "btn secondary", type: "button", onclick: () => kitView(c) }, "Starter kit"),
      h("button", { class: "btn secondary", type: "button", onclick: () => askAI(`Tell me about listing ${c.listing_id}. Is it a good choice for a first-time owner?`) }, icon("sparkles"), "Ask AI")),
  ]);
}
function backTo(fn) { return h("button", { class: "btn plain", type: "button", onclick: fn, style: "margin-left:-8px" }, icon("chevL"), "Back"); }

function contactView(c, r) {
  const text = h("textarea", { class: "big-input", rows: 4, maxlength: 500, "aria-label": "Message to the breeder" });
  text.value = `Hello, is your ${[c.variety, c.species].filter(Boolean).join(" ")} still available? Can I visit to see ${c.unit === "pair" ? "them" : "it"} this week?`;
  const send = h("button", { class: "btn primary block", type: "button" }, "Send enquiry");
  send.addEventListener("click", async () => {
    send.disabled = true; send.textContent = "Sending…";
    try {
      await api("/api/enquiries", { method: "POST", body: JSON.stringify({ listing_id: c.listing_id, message: text.value }) });
      setSheet([
        h("div", { class: "success" }, h("div", { class: "ring" }, icon("check")), h("h3", { style: "margin:0" }, "Enquiry sent"),
          h("p", { class: "muted" }, `Saved to ${c.breeder}'s inbox. Demo only: no SMS or WhatsApp is sent.`)),
        h("div", { class: "callout warn" }, h("b", {}, "Stay safe"), "Visit and see the animal before paying. Never pay the full amount in advance."),
      ], [h("button", { class: "btn primary block", type: "button", onclick: closeSheet }, "Done")]);
      refreshFarmCounts();
    } catch (e) { send.disabled = false; send.textContent = "Send enquiry"; toast(e.message); }
  });
  setSheet([backTo(() => openListing(c.listing_id, c)), h("h3", { style: "margin:6px 0 4px;font-size:24px" }, `Message ${c.breeder}`),
    h("p", { class: "muted", style: "margin:0 0 12px" }, "Keep phone numbers and addresses out of the first message."), text], [send]);
}

function productRows(items, { addable = true } = {}) {
  return items.map((i) => h("div", { class: "product" },
    h("div", { class: "pic", "aria-hidden": "true" }, PRODUCT_EMOJI[i.category] || "📦"),
    h("div", { class: "grow" }, h("b", {}, i.name), h("small", {}, `${i.brand} · ${i.why}`)),
    h("div", { class: "end" }, inr(i.price_inr), addable ? h("button", { class: "btn small secondary", type: "button", "aria-label": `Add ${i.name}`,
      onclick: async (e) => { e.currentTarget.disabled = true; await addToCart([i.product_id]); e.currentTarget.textContent = "Added"; } }, "Add") : null)));
}
function kitBlock(kit) {
  return h("div", {},
    kit.min_cage_cm ? h("div", { class: "callout ok", style: "margin-bottom:12px" }, h("b", {}, "Sized for welfare"),
      `The cage meets the minimum ${kit.min_cage_cm.join(" × ")} cm for ${kit.count} ${kit.species}. Smaller cages are never suggested.`) : null,
    kit.welfare_note ? h("div", { class: "callout warn", style: "margin-bottom:12px" }, kit.welfare_note) : null,
    h("div", { class: "group" }, productRows(kit.items), h("div", { class: "total-row" }, h("span", {}, "Total"), h("span", {}, inr(kit.total_inr)))),
    h("p", { class: "disclaimer", style: "margin-top:10px" }, kit.note));
}
function carePlanBlock(p) {
  return h("div", {},
    h("div", { class: "group" }, p.phases.map((ph) => h("div", { class: "phase" }, h("b", {}, ph.title), h("ul", {}, ph.steps.map((s) => h("li", {}, s))))),
      h("div", { class: "phase" }, h("b", {}, "Diet"), h("ul", {}, p.diet.map((s) => h("li", {}, s)))),
      h("div", { class: "phase" }, h("b", {}, "Daily routine"), h("ul", {}, p.daily_routine.map((s) => h("li", {}, s))))),
    h("div", { class: "callout bad", style: "margin-top:12px" }, h("b", {}, "See a vet if"), h("ul", {}, p.see_vet_if.map((s) => h("li", {}, s)))),
    h("p", { class: "disclaimer", style: "margin-top:10px" }, p.disclaimer));
}
async function kitView(c) {
  const count = c.unit === "pair" ? 2 : 1;
  const species = c.species_key || c.species;
  const careBox = h("div", {}, loading("Writing a 14-day care plan with AI…"), h("div", { class: "skeleton", style: "height:180px" }));
  setSheet([backTo(() => openListing(c.listing_id, c)), loading("Building your starter kit…")]);
  let kit;
  try { kit = await api(`/api/starter-kit?${qs({ species, count })}`); } catch (e) { setSheet([backTo(() => openListing(c.listing_id, c)), errorCallout(e)]); return; }
  const addAll = h("button", { class: "btn primary block", type: "button" }, icon("bag"), `Add whole kit · ${inr(kit.total_inr)}`);
  addAll.addEventListener("click", async () => { addAll.disabled = true; await addToCart(kit.items.map((i) => i.product_id)); addAll.textContent = "Kit added to cart"; });
  setSheet([backTo(() => openListing(c.listing_id, c)), h("h3", { style: "margin:6px 0 12px;font-size:24px" }, `Starter kit for ${kit.count} ${kit.species}`),
    kitBlock(kit), h("div", { class: "h-sub" }, "First 14 days · written by AI"), careBox], [addAll]);
  try {
    const r = await api(`/api/care-plan?${qs({ species, age_months: c.age_months })}`);
    careBox.replaceChildren(carePlanBlock(r.care_plan));
  } catch (e) { careBox.replaceChildren(errorCallout(e)); }
}

// breeder page
async function openBreeder(id) {
  openSheet("Breeder", loading("Opening…"));
  try {
    const r = await api(`/api/breeders/${encodeURIComponent(id)}?${qs({ district: state.district })}`);
    const b = r.breeder;
    setSheet([
      h("div", { style: "display:flex;gap:16px;align-items:center;margin:6px 0 4px" }, avatar(b.name, "avatar lg"),
        h("div", {}, h("h3", { style: "margin:0;font-size:24px;letter-spacing:-.02em" }, b.name),
          h("div", { class: "muted" }, `${b.locality}, ${titleCase(b.district)}${b.distance ? " · " + b.distance : ""}`),
          h("div", { class: "muted small" }, `${b.years_experience} years breeding · ${b.species.join(", ")}`))),
      breederTags(b),
      h("div", { class: "callout ok", style: "margin-top:14px" }, h("b", {}, "Direct from the farm"), "Visit, see the parents, and buy at the breeder's own price. No broker in between."),
      h("div", { class: "h-sub" }, `${b.pets_for_sale} pet${b.pets_for_sale > 1 ? "s" : ""} for sale`), petGrid(r.pets),
      h("p", { class: "disclaimer" }, "Fictional sample breeder. Registration status uses a simulated registry."),
    ]);
  } catch (e) { setSheet(errorCallout(e)); }
}

// "Which pet suits me?"
function quizSheet(prefill = {}) {
  const a = { animal_group: "any", home_type: "flat", has_young_children: false, first_time_owner: true, time_per_day_minutes: 30, noise_ok: true, budget_inr: 3000, ...prefill };
  const seg = (label, key, options) => h("div", { style: "margin-bottom:16px" }, h("div", { class: "h-sub", style: "margin:0 0 8px" }, label),
    h("div", { class: "segmented", role: "group", "aria-label": label }, options.map(([v, text]) => h("button", { type: "button", "aria-pressed": String(a[key] === v),
      onclick: (e) => { a[key] = v; e.currentTarget.parentElement.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === e.currentTarget))); } }, text))));
  const go = h("button", { class: "btn primary block", type: "button" }, icon("sparkles"), "Show my matches");
  go.addEventListener("click", async () => {
    go.disabled = true;
    try { showQuizResults(await api("/api/recommend", { method: "POST", body: JSON.stringify(a) }), a); } catch (e) { toast(e.message); go.disabled = false; }
  });
  openSheet("Which pet suits me?", [
    h("p", { class: "muted", style: "margin:0 0 16px" }, "A few taps. Suggestions come from care rules and sample market prices."),
    seg("Kind of pet", "animal_group", [["any", "Not sure"], ["bird", "Bird"], ["dog", "Dog"], ["cat", "Cat"]]),
    seg("Home", "home_type", [["flat", "Flat"], ["house", "House"]]),
    seg("Children under 12 at home", "has_young_children", [[true, "Yes"], [false, "No"]]),
    seg("First pet", "first_time_owner", [[true, "Yes"], [false, "No"]]),
    seg("Time for the pet each day", "time_per_day_minutes", [[15, "15 min"], [30, "30 min"], [60, "1 hour"], [120, "2 hours+"]]),
    seg("Is noise OK?", "noise_ok", [[true, "Yes"], [false, "No"]]),
    seg("Budget for the pet", "budget_inr", [[1000, "₹1k"], [3000, "₹3k"], [10000, "₹10k"], [30000, "₹30k"], [100000, "More"]]),
  ], [go]);
}
function showQuizResults(r, answers) {
  const cards = r.options.map((o, i) => h("div", { class: "card", style: "margin-bottom:12px" },
    h("div", { class: "detail-head", style: "margin:0 0 4px" }, h("h3", { style: "font-size:20px" }, `${i === 0 ? "Best match: " : ""}${o.species}`)),
    o.typical_price_range_inr ? h("div", { class: "muted small" }, `${inr(o.typical_price_range_inr[0])}–${inr(o.typical_price_range_inr[1])} per ${o.price_unit} · lives ${o.lifespan_years[0]}–${o.lifespan_years[1]} years`) : null,
    h("ul", { style: "margin:8px 0;padding-left:18px" }, o.why.map((w) => h("li", {}, w))),
    o.watch_outs?.length ? h("div", { class: "callout warn" }, o.watch_outs.join(" ")) : null,
    h("button", { class: "btn secondary block", type: "button", style: "margin-top:12px",
      onclick: () => { state.filters.species = o.species_key; state.filters.chipLabel = o.species; closeSheet(); go("pets"); toast(`Showing ${o.species} near ${districtName(state.district)}`); } }, `Show ${o.species} near me`)));
  setSheet([
    backTo(() => quizSheet(answers)),
    cards.length ? cards : empty("search", "No match yet", "Try a bigger budget or more time per day."),
    r.excluded?.length ? h("div", { class: "muted small" }, h("b", {}, "Not suggested: "), r.excluded.map((x) => `${x.species} (${x.why_not.join(", ")})`).join("; ")) : null,
    h("p", { class: "disclaimer" }, r.note),
  ], [h("button", { class: "btn plain block", type: "button", onclick: () => askAI("Help me choose a pet. " + describeAnswers(answers)) }, icon("sparkles"), "Talk it through with BreederNear AI")]);
}
function describeAnswers(a) {
  return `I'd like a ${a.animal_group === "any" ? "pet" : a.animal_group}; we live in a ${a.home_type}; ${a.has_young_children ? "we have young children" : "no young children"}; `
    + `${a.first_time_owner ? "first pet" : "we've had pets"}; about ${a.time_per_day_minutes} minutes a day; budget about ₹${a.budget_inr}; district ${districtName(state.district)}.`;
}

// "Is this post safe?"
function checkSheet() {
  const photos = [];
  const text = h("textarea", { class: "big-input", rows: 5, maxlength: 2000, placeholder: "Paste the post text, e.g. “Lovebirds pair 500 only, full advance, courier only”", "aria-label": "Post text" });
  const tiles = h("div");
  const redraw = () => tiles.replaceChildren(photoTiles(photos, redraw, { addLabel: "Screenshot" }));
  redraw();
  const btn = h("button", { class: "btn primary block", type: "button" }, icon("shield"), "Check this post");
  btn.addEventListener("click", async () => {
    if (!text.value.trim() && !photos.length) { toast("Paste the post or add a screenshot"); return; }
    btn.disabled = true;
    setSheet([loading(photos.length ? "Reading the screenshot…" : "Running trust checks…")], []);
    try {
      const ids = await uploadPhotos(photos, "external_listing");
      const r = await api("/api/check", { method: "POST", body: JSON.stringify({ text: text.value, upload_ids: ids }) });
      setSheet([
        trustSummary(r.screening, r.screening.trust_level === "TRUSTED" ? "No warning signs found" : r.screening.trust_level === "BLOCKED" ? "This post can't be trusted" : "This post shows warning signs"),
        h("div", { class: "callout warn", style: "margin-top:12px" }, h("b", {}, "Before you pay"), "See the animal in person. Never pay the full amount in advance or by courier deal."),
        h("p", { class: "disclaimer" }, "Nothing you check is saved or published."),
      ], [h("button", { class: "btn secondary block", type: "button", onclick: checkSheet }, "Check another post"),
        h("button", { class: "btn plain block", type: "button", onclick: () => { state.filters.trusted = true; closeSheet(); go("pets"); } }, "See trusted pets near me instead")]);
    } catch (e) { setSheet([errorCallout(e)], [h("button", { class: "btn secondary block", type: "button", onclick: checkSheet }, "Try again")]); }
  });
  openSheet("Is this post safe?", [
    h("p", { class: "muted", style: "margin:0 0 14px" }, "Saw a pet for sale on WhatsApp, Instagram or Facebook? AI reads it and our rules check it for legality, scam and welfare warning signs."),
    text, h("div", { style: "height:12px" }), tiles,
  ], [btn]);
}

function districtSheet() {
  openSheet("Your district", h("div", { class: "group" }, state.districts.map((d) => h("button", { class: "row", type: "button",
    onclick: () => { setDistrict(d.key); closeSheet(); toast(`Showing pets near ${d.name}`); } },
    h("span", { class: "grow" }, d.name), d.key === state.district ? h("span", { style: "color:var(--accent)" }, icon("check")) : null))));
}

async function cartSheet() {
  openSheet("Cart", loading("Loading…"));
  const cart = await api("/api/cart").catch(() => ({ items: [], total_inr: 0, note: "" }));
  if (!cart.items.length) { setSheet(empty("bag", "Your cart is empty", "Open a pet and tap Starter kit to get everything you need.")); return; }
  setSheet([
    h("div", { class: "group" }, cart.items.map((i) => h("div", { class: "product" },
      h("div", { class: "grow" }, h("b", {}, i.name), h("small", {}, `${i.brand} · ${i.quantity} × ${inr(i.price_inr)}`)),
      h("div", { class: "end" }, inr(i.line_total_inr), h("button", { class: "btn small plain", type: "button", "aria-label": `Remove ${i.name}`,
        onclick: async () => { updateCart(await api(`/api/cart/items/${encodeURIComponent(i.product_id)}`, { method: "DELETE" })); cartSheet(); } }, "Remove")))),
      h("div", { class: "total-row" }, h("span", {}, "Total"), h("span", {}, inr(cart.total_inr)))),
    h("p", { class: "disclaimer" }, cart.note),
  ], [h("button", { class: "btn primary block", type: "button", disabled: true }, "Checkout (not in this demo)")]);
}
function updateCart(cart) {
  state.cartCount = (cart.items || []).reduce((s, i) => s + i.quantity, 0);
  renderHeader();
}
async function addToCart(ids) {
  try {
    let cart;
    for (const id of ids) cart = await api("/api/cart/items", { method: "POST", body: JSON.stringify({ product_id: id }) });
    updateCart(cart); toast(ids.length > 1 ? "Kit added to cart" : "Added to cart");
  } catch (e) { toast(e.message); }
}

// ---------------------------------------------------------------- views
const main = $("main");
const TABS = [["pets", "Pets", "paw"], ["breeders", "Local Breeders", "barn"], ["ai", "BreederNear AI", "sparkles"]];

function hero(eyebrow, title, subtitle) {
  return h("section", { class: "hero" }, h("p", { class: "eyebrow" }, eyebrow), h("h1", { class: "large-title" }, title), h("p", { class: "subtitle" }, subtitle));
}

function welcomeCard() {
  if (store.get("breedernear_welcome_done")) return null;
  const dismiss = () => { store.set("breedernear_welcome_done", "1"); card.remove(); };
  const step = (ico, title, text, onclick) => h("button", { class: "step", type: "button", onclick }, h("span", { class: "ico" }, icon(ico)), h("span", {}, h("b", {}, title), h("span", {}, text)));
  const select = h("select", { class: "select", "aria-label": "Your district" }, state.districts.map((d) => h("option", { value: d.key, selected: d.key === state.district }, d.name)));
  select.addEventListener("change", () => setDistrict(select.value));
  const card = h("section", { class: "welcome", "aria-labelledby": "welcome-title" },
    h("button", { class: "close", type: "button", "aria-label": "Close welcome", onclick: dismiss }, icon("x")),
    h("h2", { id: "welcome-title" }, "Welcome to BreederNear"),
    h("p", { class: "muted", style: "margin:0" }, "Buy pets straight from trusted local breeders, at farm prices. Every listing is checked by AI and clear rules."),
    h("div", { class: "steps" },
      step("paw", "Pets", "Browse healthy, legal pets near you", () => { dismiss(); window.scrollTo({ top: 400, behavior: "smooth" }); }),
      step("barn", "Local Breeders", "Meet breeders, or sell your own pets", () => { dismiss(); go("breeders"); }),
      step("sparkles", "BreederNear AI", "Just ask, in English or Tamil", () => { dismiss(); go("ai"); })),
    h("div", { class: "demo" }, h("span", { class: "muted small" }, "Your district"), select),
    h("div", { class: "demo", style: "margin-top:10px" }, h("span", { class: "muted small" }, "Try the demo:"),
      h("button", { class: "btn small secondary", type: "button", onclick: () => { dismiss(); demoPriya(); } }, "Priya, buyer"),
      h("button", { class: "btn small secondary", type: "button", onclick: () => { dismiss(); demoKarthik(); } }, "Karthik, breeder")));
  return card;
}

async function viewPets() {
  const f = state.filters;
  const chips = [...SPECIES_CHIPS];
  if (!chips.some(([k]) => k === f.species)) chips.push([f.species, f.chipLabel || titleCase(f.species.replace(/_/g, " "))]);
  const grid = h("div", {}, h("div", { class: "pet-grid" }, Array.from({ length: 4 }, () => h("div", { class: "skeleton", style: "aspect-ratio:3/4" }))));
  const count = h("div", { class: "count-line" }, " ");
  const trusted = h("input", { type: "checkbox", checked: f.trusted });
  trusted.addEventListener("change", () => { f.trusted = trusted.checked; load(); });
  const cap = h("select", { class: "select", "aria-label": "Maximum price" }, PRICE_CAPS.map(([v, t]) => h("option", { value: v, selected: v === String(f.max) }, t)));
  cap.addEventListener("change", () => { f.max = cap.value; load(); });
  const chipRow = h("div", { class: "chips", role: "group", "aria-label": "Species" }, chips.map(([k, label]) => h("button", { class: "chip", type: "button", "aria-pressed": String(k === f.species),
    onclick: (e) => { f.species = k; chipRow.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c === e.currentTarget))); load(); } }, label)));
  async function load() {
    try {
      const r = await api(`/api/pets?${qs({ district: state.district, species: f.species, max_price: f.max, trusted_only: f.trusted ? "true" : "" })}`);
      count.textContent = r.total ? `${r.total} pet${r.total > 1 ? "s" : ""} · trusted first, then nearest` : "";
      grid.replaceChildren(r.results.length ? petGrid(r.results)
        : empty("search", "No pets match", "Try another species, a higher price or turn off “Trusted only”."));
    } catch (e) { grid.replaceChildren(errorCallout(e)); }
  }
  main.replaceChildren(h("div", { class: "view" },
    hero(`Near ${districtName(state.district)}`, "Pets", "Healthy, legal pets from trusted breeders near you."),
    welcomeCard(),
    h("div", { class: "tiles" },
      h("button", { class: "tile", type: "button", onclick: () => quizSheet() }, h("span", { class: "ico green" }, icon("sparkles")), h("b", {}, "Which pet suits me?"), h("span", {}, "A few taps. AI-matched to your home.")),
      h("button", { class: "tile", type: "button", onclick: checkSheet }, h("span", { class: "ico blue" }, icon("shield")), h("b", {}, "Is this post safe?"), h("span", {}, "Check a WhatsApp or Instagram post."))),
    chipRow,
    h("div", { class: "controls" }, h("label", { class: "switch" }, trusted, h("span", { class: "track", "aria-hidden": "true" }), "Trusted only"), cap),
    count, grid, disclaimer()));
  load();
}

async function viewBreeders() {
  const list = h("div", { class: "breeders" }, Array.from({ length: 4 }, () => h("div", { class: "skeleton", style: "height:96px" })));
  let species = "all";
  const chipRow = h("div", { class: "chips", role: "group", "aria-label": "Kind of breeder" }, [["all", "All"], ["bird", "Birds"], ["dog", "Dogs"], ["cat", "Cats"]].map(([k, label]) =>
    h("button", { class: "chip", type: "button", "aria-pressed": String(k === species), onclick: (e) => { species = k; chipRow.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c === e.currentTarget))); load(); } }, label)));
  async function load() {
    try {
      const r = await api(`/api/breeders?${qs({ district: state.district, species })}`);
      list.replaceChildren(...(r.breeders.length ? r.breeders.map((b) => h("button", { class: "breeder", type: "button", onclick: () => openBreeder(b.breeder_id) },
        avatar(b.name),
        h("div", { class: "grow" }, h("b", {}, b.name),
          h("div", { class: "meta" }, `${b.locality} · ${b.distance ? sentence(b.distance) : titleCase(b.district)}`),
          h("div", { class: "meta" }, `${b.species.join(", ")} · ${b.pets_for_sale} for sale from ${inr(b.from_price_inr)}`),
          breederTags(b)),
        h("span", { class: "chev", style: "color:var(--label-3)" }, icon("chevR")))) : [empty("barn", "No breeders yet", "Try another kind of pet.")]));
    } catch (e) { list.replaceChildren(errorCallout(e)); }
  }
  main.replaceChildren(h("div", { class: "view" },
    hero("Direct Farm", "Local Breeders", "Buy straight from the breeder. Farm prices, no broker markup."),
    h("button", { class: "seller-banner", type: "button", onclick: () => go("farm") },
      h("span", { class: "ico" }, icon("shop")), h("span", { style: "flex:1" }, h("b", {}, "Are you a breeder?"), h("span", {}, "Open My farm: list your pets in a minute with AI.")), icon("chevR")),
    chipRow, h("div", { style: "height:12px" }), list, disclaimer()));
  load();
}

// ---- My farm (seller side)
const sell = { photos: [], text: "", draftId: null, data: null, busy: "", result: null };
async function refreshFarmCounts() {
  try {
    const [l, e] = await Promise.all([api("/api/breeder/listings"), api("/api/breeder/enquiries")]);
    state.farmCounts = { listings: l.listings.length, enquiries: e.enquiries.length };
  } catch { /* not critical */ }
}
async function viewFarm(sub = "sell") {
  await refreshFarmCounts();
  const pane = h("div");
  const segs = [["sell", "Sell"], ["listings", `Listings${state.farmCounts.listings ? " · " + state.farmCounts.listings : ""}`], ["enquiries", `Enquiries${state.farmCounts.enquiries ? " · " + state.farmCounts.enquiries : ""}`]];
  main.replaceChildren(h("div", { class: "view" },
    h("a", { class: "link", href: "#breeders", style: "margin-top:14px" }, icon("chevL"), "Local Breeders"),
    hero("For breeders", "My farm", "List your pets in a minute. AI fills the form, you check it, and every listing is screened."),
    h("div", { class: "segmented", role: "group", "aria-label": "My farm sections", style: "margin-bottom:6px" },
      segs.map(([k, label]) => h("button", { type: "button", "aria-pressed": String(k === sub), onclick: () => go(k === "sell" ? "farm" : `farm/${k}`) }, label))),
    pane, disclaimer()));
  if (sub === "listings") farmListings(pane); else if (sub === "enquiries") farmEnquiries(pane); else renderSell(pane);
}

function renderSell(pane) {
  const redraw = () => renderSell(pane);
  if (sell.result) { pane.replaceChildren(sellResult()); return; }
  const text = h("textarea", { class: "big-input", rows: 4, maxlength: 2000, "aria-label": "Describe your animals",
    placeholder: "e.g. 4 jodi lutino lovebird, 5 maasam, oru jodi 1800 rubai. Saibaba Colony, Kovai." });
  text.value = sell.text;
  const fill = h("button", { class: "btn primary block", type: "button", disabled: !(sell.text.trim() || sell.photos.length) || !!sell.busy }, icon("sparkles"), sell.draftId ? "Fill again with AI" : "Fill with AI");
  text.addEventListener("input", () => { sell.text = text.value; fill.disabled = !(sell.text.trim() || sell.photos.length); });
  fill.addEventListener("click", async () => {
    sell.busy = "fill"; redraw();
    try {
      const ids = await uploadPhotos(sell.photos, "listing_photo");
      const r = await api("/api/sell/drafts", { method: "POST", body: JSON.stringify({ text: sell.text, upload_ids: ids }) });
      sell.draftId = r.draft_id; sell.data = r;
    } catch (e) { toast(e.message); }
    sell.busy = ""; redraw();
  });
  const tiles = h("div");
  const redrawTiles = () => {
    tiles.replaceChildren(photoTiles(sell.photos, redrawTiles));
    fill.disabled = !(sell.text.trim() || sell.photos.length) || !!sell.busy;
  };
  redrawTiles();
  const parts = [
    h("div", { class: "step-label" }, h("span", { class: "num" }, "1"), "Photos and a quick message"),
    tiles, text,
    h("p", { class: "muted small", style: "margin:8px 2px 12px" }, "Write it like a WhatsApp post, in English, Tamil or both. Include price, age and area if you can."),
    sell.busy === "fill" ? loading(sell.photos.length ? "Reading your photos and message…" : "Reading your message…") : fill,
  ];
  if (sell.data) parts.push(...draftForm(redraw));
  parts.push(h("p", { class: "muted small", style: "text-align:center;margin-top:18px" }, "Prefer to chat? ",
    h("button", { class: "link", type: "button", onclick: () => askAI("I'm a breeder and I want to list my animals for sale.") }, "List with BreederNear AI")));
  pane.replaceChildren(...parts);
}
function draftForm(redraw) {
  const r = sell.data, d = r.draft, missing = new Set(r.missing_fields || []);
  const save = async (field, value) => {
    if (String(d[field] ?? "") === String(value)) return;
    try { sell.data = await api(`/api/sell/drafts/${sell.draftId}`, { method: "PATCH", body: JSON.stringify({ [field]: value }) }); redraw(); }
    catch (e) { toast(e.message); redraw(); }
  };
  const field = (name, label, input, { hint } = {}) => {
    input.id = `f-${name}`;
    input.addEventListener("change", () => save(name, input.value));
    return h("div", { class: `field${missing.has(name) ? " missing" : ""}` }, h("label", { for: input.id }, label), input,
      missing.has(name) ? h("div", { class: "hint" }, hint || "Buyers ask for this") : null);
  };
  const text = (name, label, opts = {}) => field(name, label, h("input", { type: "text", value: d[name] ?? "", placeholder: opts.placeholder || "Add" }), opts);
  const num = (name, label, opts = {}) => field(name, label, h("input", { type: "number", inputmode: "numeric", min: 0, value: d[name] ?? "", placeholder: opts.placeholder || "Add" }), opts);
  const districtSelect = h("select", {}, h("option", { value: "" }, "Choose"), state.districts.map((x) => h("option", { value: x.key, selected: x.key === d.district }, x.name)));
  const unitSeg = h("div", { class: "segmented", role: "group", "aria-label": "Sold per" }, [["single", "Each"], ["pair", "Pair"], ["litter", "Litter"]].map(([v, t]) =>
    h("button", { type: "button", "aria-pressed": String(d.unit === v), onclick: () => save("unit", v) }, t)));
  const publish = h("button", { class: "btn primary block", type: "button", disabled: !!sell.busy }, icon("shield"), "Publish with trust check");
  publish.addEventListener("click", async () => {
    sell.busy = "publish"; redraw();
    try { sell.result = await api(`/api/sell/drafts/${sell.draftId}/publish`, { method: "POST" }); } catch (e) { toast(e.message); }
    sell.busy = ""; redraw();
  });
  return [
    h("div", { class: "step-label" }, h("span", { class: "num" }, "2"), "Check the details"),
    h("p", { class: "muted small", style: "margin:-4px 2px 10px" }, "AI filled these in. Tap any field to change it."),
    h("div", { class: "form-group" },
      text("species_common", "Species"), text("variety", "Variety", { placeholder: "e.g. Lutino" }),
      num("count", "How many"), h("div", { class: "field" }, h("label", {}, "Sold per"), unitSeg),
      num("age_months", "Age (months)"), num("price_inr", "Price ₹", { hint: "Add a price so buyers can compare" }),
      r.fair_price_range_inr && d.price_inr ? h("div", { class: "field", style: "display:block" }, rangeBar(d.price_inr, r.fair_price_range_inr)) : null,
      field("district", "District", districtSelect), text("locality", "Area"),
      field("health_notes", "Health", h("textarea", { rows: 2, placeholder: "e.g. Healthy, dewormed, parents on site" }, d.health_notes || "")),
      d.animal_group === "dog" || missing.has("sawb_registration_no") ? text("sawb_registration_no", "Dog-breeder reg.", { hint: "Required for dog breeders (State Animal Welfare Board)", placeholder: "e.g. SIM-TNAWB-DB-0042" }) : null,
      missing.has("parivesh_registration_id") || d.parivesh_registration_id ? text("parivesh_registration_id", "PARIVESH ID", { hint: "Required for CITES-listed birds" }) : null),
    h("div", { class: "step-label" }, h("span", { class: "num" }, "3"), "Publish"),
    h("p", { class: "muted small", style: "margin:-4px 2px 10px" }, "AI looks at your photos and our rules check the species, price and wording. Listings you create here are visible only to you in this demo."),
    sell.busy === "publish" ? loading("Running trust checks…") : publish,
  ];
}
function sellResult() {
  const r = sell.result, s = r.screening, ok = r.listing_status === "PUBLISHED";
  const again = () => { sell.photos = []; sell.text = ""; sell.draftId = null; sell.data = null; sell.result = null; route(); };
  return h("div", { class: "card", style: "margin-top:16px" },
    h("div", { class: "success" }, h("div", { class: "ring", style: ok ? "" : "background:var(--bad-tint);color:var(--bad)" }, icon(ok ? "check" : "x")),
      h("h3", { style: "margin:0;font-size:22px" }, ok ? "Your listing is live" : "This listing can't be published"),
      h("p", { class: "muted" }, ok ? "Buyers see it with its trust badge. (In this demo, only you can see it.)" : "It was recorded, but buyers will never see it.")),
    trustSummary(s, "Trust check"),
    !ok ? h("div", { class: "callout ok", style: "margin-top:12px" }, "Legal pets you can list instead: budgies, cockatiels, lovebirds, zebra or society finches and canaries.") : null,
    h("div", { style: "display:grid;gap:8px;margin-top:16px" },
      ok ? h("button", { class: "btn primary block", type: "button", onclick: () => { state.filters = { species: "all", trusted: false, max: "" }; go("pets"); } }, "See it in Pets") : null,
      h("button", { class: "btn secondary block", type: "button", onclick: again }, "List another")));
}
async function farmListings(pane) {
  pane.replaceChildren(loading("Loading…"));
  const r = await api("/api/breeder/listings").catch(() => ({ listings: [] }));
  pane.replaceChildren(r.listings.length ? h("div", { class: "group", style: "margin-top:16px" }, r.listings.map((l) => h("div", { class: "list-row" },
    h("div", { class: "grow" }, h("b", {}, [l.species, l.variety].filter(Boolean).join(" · ")),
      h("div", { class: "muted small" }, `${inr(l.price_inr)} · ${l.status === "BLOCKED" ? "Not published" : "Published (visible only to you)"}`)),
    tag(l.trust_level, l.trust_score))))
    : empty("list", "No listings yet", "Your listings and their trust checks show here.", h("button", { class: "btn small primary", type: "button", onclick: () => go("farm") }, "Sell your first pet")));
}
async function farmEnquiries(pane) {
  pane.replaceChildren(loading("Loading…"));
  const r = await api("/api/breeder/enquiries").catch(() => ({ enquiries: [] }));
  pane.replaceChildren(r.enquiries.length ? h("div", { class: "group", style: "margin-top:16px" }, r.enquiries.map((e) => h("div", { class: "list-row" },
    h("span", { class: "ico green", style: "width:36px;height:36px;border-radius:50%;display:grid;place-items:center" }, icon("mail")),
    h("div", { class: "grow" }, h("div", {}, `“${e.message}”`), h("div", { class: "muted small" }, `${e.listing_id} · ${new Date(e.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}`)))))
    : empty("mail", "No enquiries yet", "When buyers contact you about your listings, their messages show here. Demo tip: publish a listing, find it in Pets (tagged “Yours”) and tap Contact."));
}

// ---------------------------------------------------------------- AI tab (ADK agents)
const AGENTS = { breedernear_concierge: "Concierge", listing_agent: "Listing copilot", trust_agent: "Trust checker", match_agent: "Buyer guide", care_agent: "Care guide" };
const LOADING = { transfer_to_agent: "Passing you to the right assistant…", extract_listing: "Reading your photos and message…", update_draft: "Updating your draft…",
  publish_listing: "Running trust checks…", check_external_listing: "Running trust checks…", recommend_species: "Matching pets to your home…",
  search_listings: "Finding trusted pets near you…", get_listing: "Opening the listing…", create_enquiry: "Sending your enquiry…",
  build_starter_kit: "Building your starter kit…", care_plan: "Writing your care plan…", add_to_cart: "Adding to your cart…" };
const chat = { el: null, session: store.get("breedernear_ai_session"), busy: false, photos: [], restored: false };

function viewAI() {
  if (!chat.el) chat.el = h("div", { class: "chat", "aria-live": "polite" });
  const quick = (ico, cls, title, action) => h("button", { type: "button", onclick: action }, h("span", { class: `ico ${cls}`, style: "width:34px;height:34px;border-radius:10px;display:grid;place-items:center" }, icon(ico)), title);
  main.replaceChildren(h("div", { class: "view" },
    hero("Five Gemini agents", "BreederNear AI", "Find a pet, list your animals or check a post. English or Tamil."),
    h("div", { class: "quick" },
      quick("paw", "green", "Find my pet", () => sendChat("Help me find the right pet for my family.")),
      quick("shop", "amber", "List my animals", () => sendChat("I'm a breeder and I want to list my animals for sale.")),
      quick("shield", "blue", "Is this post safe?", () => { prefillChat("Is this post safe? "); })),
    chat.el,
    h("p", { class: "disclaimer" }, "Tap “What the AI did” under a reply to see which agent and tool ran. Prototype: sample data; not veterinary advice.")));
  if (!chat.restored) { chat.restored = true; chat.restoring = restoreChat(); }
  setTimeout(() => window.scrollTo({ top: document.body.scrollHeight }), 50);
}
function prefillChat(text) { const i = $("chat-input"); i.value = text; i.focus(); autoGrow(); }
function askAI(text) { closeSheet(); go("ai"); setTimeout(() => sendChat(text), 60); }
function addChat(node) { chat.el.append(node); window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" }); return node; }
const stripNote = (t) => t.replace(/\n?\[attachments upload_ids=[^\]]*\]/g, "").trim();

function userBubble(text, images = []) {
  const photos = (text.match(/upload_ids=([^\s\]]+)/)?.[1] || "").split(",").filter(Boolean).length;
  addChat(h("div", { class: "bubble me" }, stripNote(text),
    images.length ? h("div", { class: "thumbs" }, images.map((src) => h("img", { src, alt: "Photo you sent" }))) : photos ? h("div", { class: "small" }, `📷 ${photos} photo${photos > 1 ? "s" : ""}`) : null));
}
class Turn {
  constructor() { this.bubble = null; this.text = ""; this.author = null; this.calls = new Set(); this.responses = new Set(); this.activity = null; this.steps = 0; this.typing = null; }
  setTyping(label) { if (!this.typing) this.typing = addChat(h("div", { class: "typing", role: "status" }, h("span", { class: "spinner" }), h("span", {}))); this.typing.lastChild.textContent = label; chat.el.append(this.typing); }
  done() { this.typing?.remove(); this.typing = null; }
  close() { this.bubble = null; this.text = ""; }
  log(line) {
    if (!this.activity) { this.list = h("ol"); this.summary = h("summary"); this.activity = addChat(h("details", { class: "activity" }, this.summary, this.list)); }
    this.steps += 1; this.summary.replaceChildren(icon("sparkles"), `What the AI did · ${this.steps} step${this.steps > 1 ? "s" : ""}`);
    this.list.append(h("li", {}, line));
  }
  write(author, text, partial) {
    if (!text) return;
    if (!this.bubble || this.author !== author) {
      this.author = author; this.text = ""; this.body = h("div");
      this.bubble = addChat(h("div", { class: "bubble ai" }, h("div", { class: "who" }, AGENTS[author] || "BreederNear AI"), this.body));
    }
    this.text = partial ? this.text + text : text;
    this.body.innerHTML = md(this.text);
    if (this.typing) chat.el.append(this.typing);
    if (!partial) this.close();
  }
}
function summarise(r) {
  if (!r || typeof r !== "object") return "done";
  if (r.status === "error") return `error: ${r.message}`;
  if (r.status === "not_allowed") return "not allowed (protected species)";
  if (r.screening) return `${r.listing_status ? r.listing_status + ", " : ""}${r.screening.trust_level} ${r.screening.trust_score}`;
  if (r.results) return `${r.results.length} result(s)`; if (r.options) return `${r.options.length} option(s)`;
  if (r.items) return `${r.items.length} item(s), ${inr(r.total_inr)}`; if (r.care_plan) return "care plan ready";
  if (r.draft) return "draft ready"; if (r.enquiry_id) return "enquiry saved"; return r.status || "done";
}
function handleEvent(turn, ev) {
  if (ev.error || ev.errorMessage) { addChat(h("div", { class: "bubble err", role: "alert" }, "Something went wrong on our side. Please try again.")); return; }
  const author = ev.author;
  for (const part of ev.content?.parts || []) {
    if (part.thought) continue;
    const call = part.functionCall || part.function_call, resp = part.functionResponse || part.function_response;
    if (call) {
      const key = call.id || `${call.name}:${JSON.stringify(call.args)}`;
      if (turn.calls.has(key)) continue;
      turn.calls.add(key); turn.close();
      if (call.name === "transfer_to_agent") turn.log(`${AGENTS[author] || author} → hands over to ${AGENTS[call.args?.agent_name] || call.args?.agent_name}`);
      else turn.log(`${AGENTS[author] || author} → ${call.name}(${Object.entries(call.args || {}).filter(([k]) => k !== "text").map(([k, v]) => `${k}: ${Array.isArray(v) ? v.length + " item(s)" : v}`).join(", ")})`);
      turn.setTyping(LOADING[call.name] || "Working…");
    } else if (resp) {
      const key = resp.id || resp.name;
      if (turn.responses.has(key)) continue;
      turn.responses.add(key); turn.close();
      if (resp.name !== "transfer_to_agent") { turn.log(`↳ ${resp.name}: ${summarise(resp.response)}`); chatCard(resp.name, resp.response || {}); }
      if (turn.typing) turn.setTyping("Thinking…");
    } else if (typeof part.text === "string" && author && author !== "user") {
      turn.write(author, part.text, !!ev.partial);
    }
  }
}
function chatCard(name, r) {
  if (r.status === "not_allowed") {
    addChat(h("div", { class: "callout bad inline" }, h("b", {}, "Not allowed"), r.message, r.legal_alternatives ? h("div", { style: "margin-top:6px" }, "Legal alternatives: " + r.legal_alternatives.join(", ")) : null));
    return;
  }
  if (r.status !== "ok") return;
  const card = (...kids) => addChat(h("div", { class: "card inline" }, ...kids));
  switch (name) {
    case "extract_listing": case "update_draft": {
      const d = r.draft;
      card(h("div", { class: "detail-head", style: "margin:0 0 6px" }, h("h3", { style: "font-size:19px" }, `${emojiFor(d)} Draft: ${[d.species_common, d.variety].filter(Boolean).join(" · ")}`), h("span", { class: "tag neutral" }, "Not published")),
        h("div", { class: "muted" }, `${d.count} ${d.unit === "pair" ? "pair(s)" : d.unit === "litter" ? "litter" : ""} · ${d.age_months ?? "?"} months · ${inr(d.price_inr)} / ${unitWord(d.unit)} · ${titleCase(d.district || "")}`),
        rangeBar(d.price_inr, r.fair_price_range_inr),
        r.missing_fields?.length ? h("div", { class: "callout warn", style: "margin-top:10px" }, "Missing: " + r.missing_fields.map((f) => FIELD_NAMES[f] || f).join(", ")) : null,
        h("button", { class: "btn primary", type: "button", style: "margin-top:12px", onclick: (e) => { e.currentTarget.disabled = true; sendChat("Publish it"); } }, "Publish"));
      break;
    }
    case "publish_listing": card(trustSummary(r.screening, r.listing_status === "BLOCKED" ? "Not published" : "Published", r.listing_status === "BLOCKED" ? "This listing can't be published." : "Visible only to you in this demo.")); refreshFarmCounts(); break;
    case "check_external_listing": card(trustSummary(r.screening, "Post check", "Nothing was published or stored.")); break;
    case "recommend_species":
      if (r.options?.length) card(h("h3", { style: "margin:0 0 8px;font-size:19px" }, "Suggested pets"), h("div", { class: "group" }, r.options.map((o) => h("button", { class: "row", type: "button",
        onclick: () => { state.filters.species = o.species_key; state.filters.chipLabel = o.species; go("pets"); } },
        h("div", { class: "grow" }, h("b", {}, o.species), h("div", { class: "muted small" }, o.why.slice(0, 3).join(" · "))), h("span", { class: "chev" }, icon("chevR"))))));
      break;
    case "search_listings":
      if (r.results?.length) addChat(petGrid(r.results));
      if (r.further_away?.length) { addChat(h("div", { class: "muted small" }, "Further away")); addChat(petGrid(r.further_away)); }
      break;
    case "get_listing": card(h("div", { class: "detail-head", style: "margin:0 0 8px" }, h("h3", { style: "font-size:19px" }, [r.listing.species, r.listing.variety].filter(Boolean).join(" · ")), tag(r.listing.trust_level, r.listing.trust_score)),
      h("button", { class: "btn secondary", type: "button", onclick: () => openListing(r.listing.listing_id, r.listing) }, "Open listing")); break;
    case "create_enquiry": card(h("b", {}, "Enquiry sent"), h("div", { class: "muted small" }, r.note)); refreshFarmCounts(); break;
    case "build_starter_kit": card(h("h3", { style: "margin:0 0 10px;font-size:19px" }, `Starter kit: ${r.count} ${r.species}`), kitBlock(r),
      h("button", { class: "btn primary", type: "button", onclick: (e) => { e.currentTarget.disabled = true; addToCart(r.items.map((i) => i.product_id)); } }, "Add whole kit")); break;
    case "care_plan": card(h("h3", { style: "margin:0 0 10px;font-size:19px" }, `First 14 days: ${r.care_plan.species}`), carePlanBlock(r.care_plan)); break;
    case "add_to_cart": case "view_cart": updateCart(r); break;
    default: break;
  }
}
async function restoreChat() {
  if (!chat.session) return;
  try {
    const s = await api(`/apps/${APP}/users/${GUEST}/sessions/${chat.session}`);
    let turn = null;
    for (const ev of s.events || []) {
      if (ev.author === "user" && ev.content?.parts?.some((p) => typeof p.text === "string")) { turn = new Turn(); userBubble(ev.content.parts.map((p) => p.text || "").join("")); continue; }
      handleEvent(turn || (turn = new Turn()), ev);
    }
  } catch { chat.session = null; store.del("breedernear_ai_session"); }
}
async function createSession() {
  const s = await api(`/apps/${APP}/users/${GUEST}/sessions`, { method: "POST", body: JSON.stringify({ state: { mode: "" } }) });
  chat.session = s.id; store.set("breedernear_ai_session", s.id);
}
async function runSse(text, turn) {
  const res = await fetch("/run_sse", { method: "POST", headers: { "Content-Type": "application/json", "X-Guest-Id": GUEST },
    body: JSON.stringify({ app_name: APP, user_id: GUEST, session_id: chat.session, streaming: true, new_message: { role: "user", parts: [{ text }] } }) });
  if (!res.ok) { const e = new Error(`run ${res.status}`); e.status = res.status; throw e; }
  const reader = res.body.getReader(), decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const chunk = buffer.slice(0, cut); buffer = buffer.slice(cut + 2);
      const data = chunk.split("\n").filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trim()).join("");
      if (data) { try { handleEvent(turn, JSON.parse(data)); } catch (err) { console.error(err); } }
    }
  }
}
async function sendChat(text) {
  text = (text || "").trim();
  if (chat.busy || (!text && !chat.photos.length)) return;
  if (!chat.el) viewAI();
  chat.busy = true; $("chat-send").disabled = true;
  if (chat.restoring) { await chat.restoring; chat.restoring = null; }
  const photos = chat.photos; chat.photos = []; renderChatPreviews();
  $("chat-input").value = ""; autoGrow();
  userBubble(text, photos.map((p) => p.url));
  const turn = new Turn();
  turn.setTyping(photos.length ? "Uploading photos…" : "Thinking…");
  try {
    let message = text;
    if (photos.length) message = `${text}\n[attachments upload_ids=${(await uploadPhotos(photos, "listing_photo")).join(",")} kind=listing_photo]`;
    if (!chat.session) await createSession();
    try { await runSse(message, turn); } catch (e) {
      if (e.status !== 404) throw e;
      await createSession(); await runSse(message, turn);          // session expired after a restart
    }
  } catch (e) {
    console.error(e);
    addChat(h("div", { class: "bubble err", role: "alert" }, e.status === 429 ? "You've used BreederNear a lot in the last hour. Please wait a few minutes and try again."
      : e.message && !/^run \d+/.test(e.message) && !/fetch/i.test(e.message) ? e.message : "Couldn't reach BreederNear right now. Please try again in a moment."));
  } finally { turn.done(); chat.busy = false; $("chat-send").disabled = false; }
}
function renderChatPreviews() {
  $("previews").replaceChildren(...chat.photos.map((p, i) => h("div", { class: "photo-tile" }, h("img", { src: p.url, alt: `Photo ${i + 1} to send` }),
    h("button", { class: "x", type: "button", "aria-label": `Remove photo ${i + 1}`, onclick: () => { URL.revokeObjectURL(p.url); chat.photos.splice(i, 1); renderChatPreviews(); } }, icon("x")))));
}
function autoGrow() { const i = $("chat-input"); i.style.height = "auto"; i.style.height = Math.min(i.scrollHeight, 140) + "px"; }
$("chat-attach").append(icon("camera"));
$("chat-send").append(icon("up"));
$("chat-attach").addEventListener("click", () => pickPhotos(chat.photos, renderChatPreviews));
$("chat-form").addEventListener("submit", (e) => { e.preventDefault(); sendChat($("chat-input").value); });
$("chat-input").addEventListener("input", autoGrow);
$("chat-input").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendChat($("chat-input").value); } });

// ---------------------------------------------------------------- shell, routing, demos
function renderHeader() {
  $("brand-mark").replaceChildren(icon("paw"));
  $("district-btn").replaceChildren(icon("pin"), h("span", {}, districtName(state.district)));
  $("cart-btn").replaceChildren(...[icon("bag"), state.cartCount ? h("span", { class: "badge-dot" }, state.cartCount) : null].filter(Boolean));
  $("cart-btn").setAttribute("aria-label", `Cart, ${state.cartCount} item${state.cartCount === 1 ? "" : "s"}`);
}
function renderTabs(active) {
  const make = () => TABS.map(([key, label, ico]) => h("a", { class: "tab", href: `#${key}`, "aria-current": key === active ? "page" : null }, icon(ico), h("span", {}, label)));
  $("tabbar").replaceChildren(...make());
  $("top-tabs").replaceChildren(...make());
}
function go(path) { if (location.hash === `#${path}`) route(); else location.hash = path; }
function route() {
  const path = location.hash.replace(/^#\/?/, "") || "pets";
  const [page, sub] = path.split("/");
  const tab = page === "farm" ? "breeders" : TABS.some(([k]) => k === page) ? page : "pets";
  store.set("breedernear_tab", path);
  renderTabs(tab);
  $("composer").hidden = page !== "ai";
  main.classList.toggle("ai-main", page === "ai");
  if (page !== "ai") window.scrollTo({ top: 0 });
  if (page === "breeders") viewBreeders();
  else if (page === "farm") viewFarm(sub || "sell");
  else if (page === "ai") viewAI();
  else viewPets();
}
function demoPriya() {
  setDistrict("tiruppur");
  state.filters = { species: "bird", trusted: false, max: "" };
  go("pets");
  setTimeout(() => quizSheet({ animal_group: "bird", home_type: "flat", has_young_children: true, first_time_owner: true, time_per_day_minutes: 30, noise_ok: true, budget_inr: 3000 }), 250);
}
function demoKarthik() {
  setDistrict("coimbatore");
  Object.assign(sell, { photos: [], draftId: null, data: null, result: null,
    text: "4 jodi lutino lovebird, 5 maasam, oru jodi 1800 rubai. Saibaba Colony, Kovai. Healthy, parents on site." });
  go("farm");
  setTimeout(() => toast("Add photos if you like, then tap Fill with AI"), 400);
}
window.addEventListener("hashchange", route);
$("district-btn").addEventListener("click", districtSheet);
$("cart-btn").addEventListener("click", cartSheet);

(async function init() {
  renderHeader();
  try { const m = await api("/api/meta"); state.districts = m.districts; } catch { state.districts = [{ key: "coimbatore", name: "Coimbatore" }]; }
  if (!state.districts.some((d) => d.key === state.district)) state.district = "coimbatore";
  renderHeader();
  if (!location.hash) { const last = store.get("breedernear_tab"); if (last) { history.replaceState(null, "", `#${last}`); } }
  route();
  api("/api/cart").then(updateCart).catch(() => {});
})();
