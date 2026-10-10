"use strict";

/* BreederNear AI web app. Separate customer and seller accounts (one role per account):
   customers get Pets · Local Breeders · BreederNear AI · Account; sellers get Dashboard · Listings ·
   Enquiries · BreederNear AI · Farm. Screens call /api; the AI tab talks to the ADK agents. Both use the
   same service code, and the server checks the role on every call. */

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
// Device ID: identifies this browser for the same-device sandbox (rule R33). Not a login.
const DEVICE = (() => {
  let id = store.get("breedernear_guest_id");
  if (!id || !/^[0-9a-f-]{36}$/i.test(id)) { id = uuid(); store.set("breedernear_guest_id", id); }
  return id;
})();
const auth = { token: null, user: null };
function readToken() {
  try { return localStorage.getItem("breedernear_token") || sessionStorage.getItem("breedernear_token"); }
  catch { return memory.breedernear_token || null; }
}
function saveToken(token, remember) {
  try {
    localStorage.removeItem("breedernear_token"); sessionStorage.removeItem("breedernear_token");
    (remember ? localStorage : sessionStorage).setItem("breedernear_token", token);
  } catch { memory.breedernear_token = token; }
}
function clearToken() {
  try { localStorage.removeItem("breedernear_token"); sessionStorage.removeItem("breedernear_token"); } catch { /* ignore */ }
  delete memory.breedernear_token;
}
const isSeller = () => auth.user?.role === "seller";

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
  chat: '<path d="M4 5h16v11H9l-5 4z"/>',
  user: '<circle cx="12" cy="8.5" r="3.8"/><path d="M4.5 20c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5"/>',
  grid: '<rect x="4" y="4" width="7" height="7" rx="2"/><rect x="13" y="4" width="7" height="7" rx="2"/><rect x="4" y="13" width="7" height="7" rx="2"/><rect x="13" y="13" width="7" height="7" rx="2"/>',
  eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
  logout: '<path d="M15 4h4v16h-4"/><path d="M10 8l-4 4 4 4M6 12h10"/>', search: '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
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
function authHeaders() {
  return { "X-Device-Id": DEVICE, ...(auth.token ? { Authorization: `Bearer ${auth.token}` } : {}) };
}
async function api(path, options = {}) {
  const res = await fetch(path, { ...options, headers: { "Content-Type": "application/json", ...authHeaders(), ...(options.headers || {}) } });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(typeof body.detail === "string" ? body.detail : "Something went wrong. Please try again.");
    err.status = res.status;
    if (res.status === 401 && auth.token && !path.startsWith("/api/auth/")) { signedOut("Your session has ended. Please log in again."); }
    throw err;
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
    const res = await fetch("/api/uploads", { method: "POST", headers: authHeaders(), body: form });
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
const disclaimer = () => h("p", { class: "disclaimer" }, "Prototype — sample breeders, listings and products, with illustrative photos. No payments. Not veterinary advice.");

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
    h("p", { class: "disclaimer", style: "margin-top:18px" }, c.sample_data ? "Sample listing from a fictional breeder. Illustrative photo." : "Your own listing (visible only to you)."),
  ];
  const actions = isSeller()
    ? [c.is_yours ? h("button", { class: "btn secondary block", type: "button", onclick: () => { closeSheet(); go("listings"); } }, "Manage in Listings")
        : h("p", { class: "muted small", style: "text-align:center;margin:0" }, "You're signed in as a seller. Buying uses a customer account.")]
    : [h("button", { class: "btn primary block", type: "button", onclick: () => contactView(c, r) }, icon("mail"), "Contact breeder"),
      h("div", { style: "display:grid;grid-template-columns:1fr 1fr;gap:8px" },
        h("button", { class: "btn secondary", type: "button", onclick: () => kitView(c) }, "Starter kit"),
        h("button", { class: "btn secondary", type: "button", onclick: () => askAI(`Tell me about listing ${c.listing_id}. Is it a good choice for a first-time owner?`) }, icon("sparkles"), "Ask AI"))];
  openSheet("Pet", content, actions);
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
const CUSTOMER_TABS = [["pets", "Pets", "paw"], ["breeders", "Local Breeders", "barn"], ["ai", "BreederNear AI", "sparkles"], ["account", "Account", "user"]];
const SELLER_TABS = [["dashboard", "Dashboard", "grid"], ["listings", "Listings", "list"], ["enquiries", "Enquiries", "mail"], ["ai", "AI", "sparkles"], ["farm", "Farm", "barn"]];
const tabs = () => (isSeller() ? SELLER_TABS : CUSTOMER_TABS);

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
    h("p", { class: "muted", style: "margin:0" }, `Hi ${auth.user?.name || "there"}! Buy pets straight from trusted local breeders, at farm prices. Every listing is checked by AI and clear rules.`),
    h("div", { class: "steps" },
      step("paw", "Pets", "Browse healthy, legal pets near you", () => { dismiss(); window.scrollTo({ top: 400, behavior: "smooth" }); }),
      step("barn", "Local Breeders", "Meet breeders near you, at farm prices", () => { dismiss(); go("breeders"); }),
      step("sparkles", "BreederNear AI", "Just ask, in English or Tamil", () => { dismiss(); go("ai"); })),
    h("div", { class: "demo" }, h("span", { class: "muted small" }, "Your district"), select));
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
  chipRow.querySelector('[aria-pressed="true"]')?.scrollIntoView({ inline: "center", block: "nearest" });
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
    h("button", { class: "seller-banner", type: "button", onclick: becomeSellerSheet },
      h("span", { class: "ico" }, icon("shop")), h("span", { style: "flex:1" }, h("b", {}, "Are you a breeder?"), h("span", {}, "Sell on BreederNear with a seller account. AI writes your listing in a minute.")), icon("chevR")),
    chipRow, h("div", { style: "height:12px" }), list, disclaimer()));
  load();
}

// ---- Seller app: Dashboard · Listings · Enquiries · Farm, and the AI-filled sell form
const sell = { photos: [], text: "", draftId: null, data: null, busy: "", result: null };
const SELLER_TYPES = [["home_breeder", "Home"], ["kennel", "Kennel"], ["farm", "Farm"]];
const FARM_SPECIES = [["budgerigar", "Budgies"], ["lovebird", "Lovebirds"], ["cockatiel", "Cockatiels"], ["finch", "Finches"],
  ["canary", "Canaries"], ["dog", "Dogs"], ["cat", "Cats"]];
const VERIFY = {
  verified: ["TRUSTED", "check", "Verified dog breeder (simulated registry)"],
  missing: ["CAUTION", "warn", "Add your dog-breeder registration"],
  not_found: ["CAUTION", "warn", "Registration not found (simulated registry)"],
  expired: ["CAUTION", "warn", "Registration expired"],
};
function verifyTag(farm) {
  const v = VERIFY[farm?.verification];
  return v ? h("span", { class: `tag ${v[0]}` }, icon(v[1]), v[2]) : null;
}
function greeting() { const hr = new Date().getHours(); return hr < 12 ? "Good morning" : hr < 17 ? "Good afternoon" : "Good evening"; }
function stat(label, value, ico, cls) {
  return h("div", { class: "card", style: "padding:14px" }, h("span", { class: `ico ${cls}`, style: "width:34px;height:34px;border-radius:10px;display:grid;place-items:center;margin-bottom:8px" }, icon(ico)),
    h("div", { style: "font-size:26px;font-weight:700;letter-spacing:-.02em" }, value), h("div", { class: "muted small" }, label));
}
const STATUS_WORD = { PUBLISHED: "Live", PAUSED: "Paused", SOLD: "Sold", BLOCKED: "Blocked" };

async function viewDashboard() {
  const body = h("div", {}, loading("Loading your farm…"));
  main.replaceChildren(h("div", { class: "view" },
    hero(auth.user.farm?.farm_name || "Your farm", `${greeting()}, ${auth.user.name.replace(/ \(demo\)$/, "")}`, "Here's how your farm is doing on BreederNear."),
    body, disclaimer()));
  let d;
  try { d = await api("/api/seller/dashboard"); } catch (e) { body.replaceChildren(errorCallout(e)); return; }
  const c = d.counts;
  body.replaceChildren(...[
    verifyTag(d.farm) ? h("div", { style: "margin:-4px 0 14px" }, verifyTag(d.farm)) : null,
    h("button", { class: "btn primary block", type: "button", onclick: () => go("sell") }, icon("sparkles"), "Sell a pet with AI"),
    h("div", { style: "display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin:16px 0" },
      stat("Live listings", c.active, "list", "green"), stat("Buyer enquiries", c.enquiries, "mail", "blue"),
      stat("Listing views", c.views, "search", "amber"), stat("Trusted & live", d.trusted, "shield", "green")),
    c.blocked ? h("div", { class: "callout bad", style: "margin-bottom:12px" }, `${c.blocked} listing${c.blocked > 1 ? "s were" : " was"} blocked by the trust check (protected species). Buyers never see blocked listings.`) : null,
    d.farm?.verification === "missing" ? h("div", { class: "callout warn", style: "margin-bottom:12px" }, h("b", {}, "Add your registration"),
      "Dog breeders must be registered with the State Animal Welfare Board. Add your number in Farm to earn the verified badge.",
      h("div", { style: "margin-top:8px" }, h("button", { class: "btn small secondary", type: "button", onclick: () => go("farm") }, "Open Farm"))) : null,
    h("div", { class: "h-sub" }, "Recent activity"),
    d.recent_activity.length ? h("div", { class: "group" }, d.recent_activity.map((a) => h("div", { class: "list-row" },
      h("div", { class: "grow" }, a.text), h("span", { class: "muted small" }, new Date(a.at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })))))
      : empty("sparkles", "No activity yet", "List your first pet: add a photo and a quick message, and AI fills the form.",
        h("button", { class: "btn small primary", type: "button", onclick: () => go("sell") }, "Sell a pet")),
    h("div", { class: "callout info", style: "margin-top:16px" }, h("b", {}, "How trust works"),
      "Every listing gets a trust check: AI reads your photos, and fixed rules check the species, price, wording and registrations. Fair prices and clear photos keep you Trusted.")].filter(Boolean));
}

async function viewSellerListings(filter = "all") {
  const pane = h("div", {}, loading("Loading…"));
  const segs = [["all", "All"], ["PUBLISHED", "Live"], ["PAUSED", "Paused"], ["SOLD", "Sold"], ["BLOCKED", "Blocked"]];
  main.replaceChildren(h("div", { class: "view" },
    hero("Your farm", "Listings", "Pause, mark sold or remove a listing anytime."),
    h("button", { class: "btn primary block", type: "button", onclick: () => go("sell"), style: "margin-bottom:14px" }, icon("plus"), "New listing"),
    h("div", { class: "segmented", role: "group", "aria-label": "Filter listings" }, segs.map(([k, label]) =>
      h("button", { type: "button", "aria-pressed": String(k === filter), onclick: () => viewSellerListings(k) }, label))),
    pane, disclaimer()));
  const r = await api("/api/seller/listings").catch((e) => { pane.replaceChildren(errorCallout(e)); return null; });
  if (!r) return;
  const rows = r.listings.filter((l) => filter === "all" || l.status === filter);
  if (!rows.length) { pane.replaceChildren(empty("list", "Nothing here yet", filter === "all" ? "List your first pet with AI." : "No listings with this status.")); return; }
  const act = async (l, status) => {
    try { await api(`/api/seller/listings/${encodeURIComponent(l.listing_id)}`, { method: "PATCH", body: JSON.stringify({ status }) }); toast(status === "SOLD" ? "Marked as sold" : status === "PAUSED" ? "Paused: hidden from buyers" : "Live again"); viewSellerListings(filter); }
    catch (e) { toast(e.message); }
  };
  const remove = async (l) => {
    if (!confirm(`Remove this ${l.species} listing? This can't be undone.`)) return;
    try { await api(`/api/seller/listings/${encodeURIComponent(l.listing_id)}`, { method: "DELETE" }); toast("Listing removed"); viewSellerListings(filter); }
    catch (e) { toast(e.message); }
  };
  pane.replaceChildren(h("div", { class: "group", style: "margin-top:14px" }, rows.map((l) => h("div", { class: "list-row", style: "align-items:flex-start" },
    (() => { const m = media(l); m.style.cssText = "width:64px;height:64px;aspect-ratio:auto;border-radius:12px;font-size:28px;flex:none;overflow:hidden"; return m; })(),
    h("div", { class: "grow" },
      h("b", {}, [l.species, l.variety].filter(Boolean).join(" · ")),
      h("div", { class: "muted small" }, `${inr(l.price_inr)} / ${unitWord(l.unit)} · ${STATUS_WORD[l.status] || l.status} · ${l.views} view${l.views === 1 ? "" : "s"}`),
      h("div", { style: "margin:6px 0" }, tag(l.trust_level, l.trust_score)),
      l.status === "BLOCKED" ? h("div", { class: "muted small" }, "Blocked by the trust check. Buyers never see it.")
        : h("div", { style: "display:flex;gap:6px;flex-wrap:wrap" },
          l.status === "PUBLISHED" ? h("button", { class: "btn small secondary", type: "button", onclick: () => act(l, "PAUSED") }, "Pause")
            : h("button", { class: "btn small secondary", type: "button", onclick: () => act(l, "PUBLISHED") }, l.status === "SOLD" ? "Relist" : "Resume"),
          l.status !== "SOLD" ? h("button", { class: "btn small secondary", type: "button", onclick: () => act(l, "SOLD") }, "Mark sold") : null,
          h("button", { class: "btn small plain", type: "button", onclick: () => openListing(l.listing_id, l) }, "View"),
          l.sample ? null : h("button", { class: "btn small plain", type: "button", style: "color:var(--bad)", onclick: () => remove(l) }, "Remove")))))));
}

async function viewSellerEnquiries() {
  const pane = h("div", {}, loading("Loading…"));
  main.replaceChildren(h("div", { class: "view" }, hero("Your farm", "Enquiries", "Messages from buyers about your listings."), pane, disclaimer()));
  const r = await api("/api/seller/enquiries").catch(() => ({ enquiries: [] }));
  pane.replaceChildren(r.enquiries.length ? h("div", { class: "group" }, r.enquiries.map((e) => h("div", { class: "list-row" },
    h("span", { class: "ico green", style: "width:36px;height:36px;border-radius:50%;display:grid;place-items:center;flex:none" }, icon("mail")),
    h("div", { class: "grow" }, h("div", {}, `“${e.message}”`), h("div", { class: "muted small" }, `${e.listing_id} · ${new Date(e.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}`),
      e.reply ? replyQuote("You replied", e.reply)
        : h("div", { style: "margin-top:8px" }, h("button", { class: "btn small secondary", type: "button", onclick: () => replySheet(e) }, icon("sparkles"), "Reply"))))))
    : empty("mail", "No enquiries yet", "When buyers contact you about a listing, their message shows here. Demo tip: on this device, log in as a demo customer, find your pet in Pets (tagged by your farm) and tap Contact."));
}

function replyQuote(who, reply) {
  return h("div", { class: "callout info inline", style: "margin-top:8px" }, h("b", {}, who), h("div", { style: "white-space:pre-wrap" }, reply.text));
}

function replySheet(e) {
  const text = h("textarea", { class: "big-input", rows: 6, maxlength: 800, "aria-label": "Your reply", placeholder: "Write your reply, or let AI draft it from your listing." });
  const notes = h("div");
  const draft = h("button", { class: "btn secondary block", type: "button" }, icon("sparkles"), "Draft with AI");
  const send = h("button", { class: "btn primary block", type: "button" }, "Send reply");
  draft.addEventListener("click", async () => {
    draft.disabled = true; draft.replaceChildren(icon("sparkles"), "Drafting from your listing…");
    try {
      const r = await api(`/api/seller/enquiries/${encodeURIComponent(e.enquiry_id)}/draft-reply`, { method: "POST" });
      text.value = r.reply;
      notes.replaceChildren(r.needs_seller_input?.length
        ? h("div", { class: "callout warn inline", style: "margin-top:10px" }, h("b", {}, "Only you can answer"), r.needs_seller_input.join(", ") + ". Edit the draft before sending.")
        : h("p", { class: "muted small", style: "margin:8px 0 0" }, "Drafted from your listing only. Check it before sending."));
    } catch (err) { toast(err.message); }
    draft.disabled = false; draft.replaceChildren(icon("sparkles"), "Draft again with AI");
  });
  send.addEventListener("click", async () => {
    send.disabled = true; send.textContent = "Sending…";
    try {
      await api(`/api/seller/enquiries/${encodeURIComponent(e.enquiry_id)}/reply`, { method: "POST", body: JSON.stringify({ text: text.value }) });
      closeSheet(); toast("Reply sent"); viewSellerEnquiries();
    } catch (err) { send.disabled = false; send.textContent = "Send reply"; toast(err.message); }
  });
  openSheet("Reply to buyer", [h("div", { class: "callout inline" }, h("b", {}, `About ${e.listing_id}`), `“${e.message}”`),
    h("div", { style: "height:12px" }), text, notes,
    h("p", { class: "muted small", style: "margin:10px 0 0" }, "Keep phone numbers and addresses out of the first reply. Demo only: no SMS or WhatsApp is sent.")], [draft, send]);
}

function viewSell() {
  const pane = h("div");
  main.replaceChildren(h("div", { class: "view" },
    h("a", { class: "link", href: "#listings", style: "margin-top:14px" }, icon("chevL"), "Listings"),
    hero("Sell with AI", "New listing", "Add photos and a quick message. AI fills the form, you check it, and every listing is screened."),
    pane, disclaimer()));
  renderSell(pane);
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
    h("p", { class: "muted small", style: "margin:-4px 2px 10px" }, "AI looks at your photos and our rules check the species, price and wording. In this demo, your listings are visible to customer accounts on this device only."),
    sell.busy === "publish" ? loading("Running trust checks…") : publish,
  ];
}
function sellResult() {
  const r = sell.result, s = r.screening, ok = r.listing_status === "PUBLISHED";
  const again = () => { sell.photos = []; sell.text = ""; sell.draftId = null; sell.data = null; sell.result = null; route(); };
  return h("div", { class: "card", style: "margin-top:16px" },
    h("div", { class: "success" }, h("div", { class: "ring", style: ok ? "" : "background:var(--bad-tint);color:var(--bad)" }, icon(ok ? "check" : "x")),
      h("h3", { style: "margin:0;font-size:22px" }, ok ? "Your listing is live" : "This listing can't be published"),
      h("p", { class: "muted" }, ok ? "Buyers see it with its trust badge. In this demo, customer accounts on this device can see it." : "It was recorded, but buyers will never see it.")),
    trustSummary(s, "Trust check"),
    !ok ? h("div", { class: "callout ok", style: "margin-top:12px" }, "Legal pets you can list instead: budgies, cockatiels, lovebirds, zebra or society finches and canaries.") : null,
    h("div", { style: "display:grid;gap:8px;margin-top:16px" },
      ok ? h("button", { class: "btn primary block", type: "button", onclick: () => { sell.result = null; go("listings"); } }, "See my listings") : null,
      h("button", { class: "btn secondary block", type: "button", onclick: again }, "List another")));
}

function farmForm(farm, onChange) {
  const f = { farm_name: "", seller_type: "home_breeder", locality: "", species: [], sawb_registration_no: "", ...(farm || {}) };
  const set = (k, v) => { f[k] = v; onChange?.(f); };
  const input = (k, label, attrs = {}) => {
    const el = h("input", { id: `farm-${k}`, value: f[k] || "", ...attrs });
    el.addEventListener("input", () => set(k, el.value));
    return h("div", { class: "field" }, h("label", { for: el.id }, label), el);
  };
  const dogRow = input("sawb_registration_no", "Dog-breeder reg.", { placeholder: "e.g. SIM-TNAWB-DB-0042" });
  dogRow.hidden = !f.species.includes("dog");
  const chips = h("div", { class: "chips", style: "margin:0;padding:0;flex-wrap:wrap" }, FARM_SPECIES.map(([k, label]) => {
    const b = h("button", { class: "chip", type: "button", "aria-pressed": String(f.species.includes(k)) }, label);
    b.addEventListener("click", () => {
      const on = !f.species.includes(k);
      set("species", on ? [...f.species, k] : f.species.filter((s) => s !== k));
      b.setAttribute("aria-pressed", String(on));
      dogRow.hidden = !f.species.includes("dog");
    });
    return b;
  }));
  const typeSeg = h("div", { class: "segmented", role: "group", "aria-label": "Seller type" }, SELLER_TYPES.map(([k, label]) => {
    const b = h("button", { type: "button", "aria-pressed": String(f.seller_type === k) }, label);
    b.addEventListener("click", () => { set("seller_type", k); typeSeg.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); });
    return b;
  }));
  return { values: f, el: h("div", {},
    h("div", { class: "form-group" }, input("farm_name", "Farm name", { placeholder: "e.g. Noyyal Finch House", maxlength: 80 }),
      h("div", { class: "field" }, h("label", {}, "Type"), typeSeg), input("locality", "Area", { placeholder: "e.g. Saibaba Colony", maxlength: 80 }), dogRow),
    h("div", { class: "h-sub" }, "What do you breed?"), chips) };
}

async function viewFarm() {
  const u = auth.user;
  const form = farmForm(u.farm);
  const district = h("select", { class: "select", "aria-label": "District", style: "width:100%" }, state.districts.map((d) => h("option", { value: d.key, selected: d.key === u.district }, d.name)));
  const save = h("button", { class: "btn primary block", type: "button" }, "Save farm profile");
  save.addEventListener("click", async () => {
    save.disabled = true;
    const body = u.default ? { district: district.value } : { farm: form.values, district: district.value };
    try { auth.user = (await api("/api/auth/me", { method: "PATCH", body: JSON.stringify(body) })).user; toast(u.default ? "District saved" : "Farm profile saved"); route(); }
    catch (e) { toast(e.message); save.disabled = false; }
  });
  main.replaceChildren(h("div", { class: "view" },
    hero("Seller account", "Farm", "How buyers see your farm on BreederNear."),
    h("div", { class: "card", style: "display:flex;gap:14px;align-items:center;margin-bottom:16px" }, avatar(u.farm?.farm_name || u.name, "avatar lg"),
      h("div", {}, h("b", { style: "font-size:19px" }, u.farm?.farm_name || "Your farm"), h("div", { class: "muted small" }, `${u.name} · ${u.login || "demo account"}`), h("div", { style: "margin-top:6px" }, verifyTag(u.farm)))),
    u.default ? h("div", { class: "callout info", style: "margin-bottom:12px" }, "This is the shared demo seller. Farm details are fixed; sign up to create your own farm.") : null,
    form.el, h("div", { class: "h-sub" }, "District"), district, h("div", { style: "height:16px" }), save,
    accountActions(), disclaimer()));
}

function accountActions() {
  return h("div", { style: "display:grid;gap:8px;margin-top:22px" },
    h("button", { class: "btn secondary block", type: "button", onclick: () => logout() }, "Log out"),
    auth.user?.default ? h("p", { class: "muted small", style: "text-align:center;margin:0" }, "This shared demo account is reset regularly and can't be deleted.")
      : h("button", { class: "btn plain block", type: "button", style: "color:var(--bad)", onclick: deleteAccount }, "Delete my account"),
    h("p", { class: "muted small", style: "text-align:center;margin:4px 0 0" }, "We store only your name, email or mobile and district. Passwords are stored as secure hashes."));
}

// ---------------------------------------------------------------- AI tab (ADK agents)
const AGENTS = { breedernear_concierge: "Concierge", listing_agent: "Listing assistant", trust_agent: "Trust checker", match_agent: "Buyer guide", care_agent: "Care guide" };
const LOADING = { transfer_to_agent: "Passing you to the right assistant…", extract_listing: "Reading your photos and message…", update_draft: "Updating your draft…",
  publish_listing: "Running trust checks…", check_external_listing: "Running trust checks…", explain_screening: "Reading the trust checks…", draft_enquiry_reply: "Drafting a reply…", recommend_species: "Matching pets to your home…",
  search_listings: "Finding trusted pets near you…", get_listing: "Opening the listing…", create_enquiry: "Sending your enquiry…",
  build_starter_kit: "Building your starter kit…", care_plan: "Writing your care plan…", add_to_cart: "Adding to your cart…" };
const chat = { el: null, session: null, busy: false, photos: [], restored: false };
const chatKey = () => `breedernear_ai_session_${auth.user?.id}`;
function resetChat() { Object.assign(chat, { el: null, session: auth.user ? store.get(chatKey()) : null, busy: false, photos: [], restored: false, restoring: null }); }

function viewAI() {
  if (!chat.el) chat.el = h("div", { class: "chat", "aria-live": "polite" });
  const quick = (ico, cls, title, action) => h("button", { type: "button", onclick: action }, h("span", { class: `ico ${cls}`, style: "width:34px;height:34px;border-radius:10px;display:grid;place-items:center" }, icon(ico)), title);
  main.replaceChildren(h("div", { class: "view" },
    hero("Five Gemini agents", "BreederNear AI", isSeller() ? "List your animals, check a post or ask about your enquiries. English or Tamil." : "Find a pet, check a post or plan the first two weeks. English or Tamil."),
    h("div", { class: "quick" }, isSeller()
      ? [quick("shop", "amber", "List my animals", () => sendChat("I want to list my animals for sale.")),
        quick("mail", "green", "Any enquiries?", () => sendChat("Do I have any enquiries from buyers?")),
        quick("shield", "blue", "Is this post safe?", () => { prefillChat("Is this post safe? "); })]
      : [quick("paw", "green", "Find my pet", () => sendChat("Help me find the right pet for my family.")),
        quick("sparkles", "amber", "First-14-days plan", () => sendChat("What do I need for a pair of budgies, and how do I care for them in the first two weeks?")),
        quick("shield", "blue", "Is this post safe?", () => { prefillChat("Is this post safe? "); })]),
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
    case "publish_listing": card(trustSummary(r.screening, r.listing_status === "BLOCKED" ? "Not published" : "Published", r.listing_status === "BLOCKED" ? "This listing can't be published." : "Visible to customer accounts on this device in this demo.")); break;
    case "check_external_listing": card(trustSummary(r.screening, "Post check", "Nothing was published or stored.")); break;
    case "explain_screening": card(trustSummary(r.screening, `Trust checks: ${r.species}`, `Listing ${r.listing_id}`)); break;
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
    case "create_enquiry": card(h("b", {}, "Enquiry sent"), h("div", { class: "muted small" }, r.note)); break;
    case "draft_enquiry_reply": card(h("b", {}, "Draft reply"), h("p", { style: "margin:6px 0 0;white-space:pre-wrap" }, r.reply),
      r.needs_seller_input?.length ? h("div", { class: "muted small", style: "margin-top:6px" }, "Only you can answer: " + r.needs_seller_input.join(", ")) : null,
      h("button", { class: "btn secondary", type: "button", style: "margin-top:12px", onclick: () => go("enquiries") }, "Edit and send in Enquiries")); break;
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
    const s = await api(`/apps/${APP}/users/${auth.user.id}/sessions/${chat.session}`);
    let turn = null;
    for (const ev of s.events || []) {
      if (ev.author === "user" && ev.content?.parts?.some((p) => typeof p.text === "string")) { turn = new Turn(); userBubble(ev.content.parts.map((p) => p.text || "").join("")); continue; }
      handleEvent(turn || (turn = new Turn()), ev);
    }
  } catch { chat.session = null; store.del(chatKey()); }
}
async function createSession() {
  const s = await api(`/apps/${APP}/users/${auth.user.id}/sessions`, { method: "POST", body: JSON.stringify({ state: {} }) });
  chat.session = s.id; store.set(chatKey(), s.id);
}
async function runSse(text, turn) {
  const res = await fetch("/run_sse", { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ app_name: APP, user_id: auth.user.id, session_id: chat.session, streaming: true, new_message: { role: "user", parts: [{ text }] } }) });
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
    const kind = isSeller() ? "listing_photo" : "external_listing";
    if (photos.length) message = `${text}\n[attachments upload_ids=${(await uploadPhotos(photos, kind)).join(",")} kind=${kind}]`;
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

// ---------------------------------------------------------------- customer account
async function viewAccount() {
  const u = auth.user;
  const list = h("div", {}, loading("Loading…"));
  const district = h("select", { class: "select", "aria-label": "Your district", style: "width:100%" }, state.districts.map((d) => h("option", { value: d.key, selected: d.key === (u.district || state.district) }, d.name)));
  district.addEventListener("change", async () => {
    try { auth.user = (await api("/api/auth/me", { method: "PATCH", body: JSON.stringify({ district: district.value }) })).user; setDistrict(district.value); toast("District saved"); }
    catch (e) { toast(e.message); }
  });
  main.replaceChildren(h("div", { class: "view" },
    hero("Customer account", "Account", "Your enquiries, cart and settings."),
    h("div", { class: "card", style: "display:flex;gap:14px;align-items:center;margin-bottom:16px" }, avatar(u.name, "avatar lg"),
      h("div", {}, h("b", { style: "font-size:19px" }, u.name), h("div", { class: "muted small" }, u.login || "Demo customer account"))),
    h("div", { class: "group" },
      h("button", { class: "row", type: "button", onclick: cartSheet }, h("span", { class: "ico green", style: "width:32px;height:32px;border-radius:9px;display:grid;place-items:center" }, icon("bag")),
        h("span", { class: "grow" }, "Cart"), h("span", { class: "muted", "data-cart-count": "" }, String(state.cartCount)), h("span", { class: "chev" }, icon("chevR"))),
      h("button", { class: "row", type: "button", onclick: () => go("breeders") }, h("span", { class: "ico green", style: "width:32px;height:32px;border-radius:9px;display:grid;place-items:center" }, icon("barn")),
        h("span", { class: "grow" }, "Local Breeders"), h("span", { class: "chev" }, icon("chevR")))),
    h("div", { class: "h-sub" }, "My district"), district,
    h("div", { class: "h-sub" }, "Enquiries I sent"), list,
    h("button", { class: "seller-banner", type: "button", style: "margin-top:20px", onclick: becomeSellerSheet },
      h("span", { class: "ico" }, icon("shop")), h("span", { style: "flex:1" }, h("b", {}, "Want to sell pets?"), h("span", {}, "Breeders use a separate seller account.")), icon("chevR")),
    accountActions(), disclaimer()));
  const r = await api("/api/enquiries/sent").catch(() => ({ enquiries: [] }));
  list.replaceChildren(r.enquiries.length ? h("div", { class: "group" }, r.enquiries.map((e) => h("div", { class: "list-row" },
    h("div", { class: "grow" }, `“${e.message}”`, h("div", { class: "muted small" }, `${e.listing_id} · ${new Date(e.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}`),
      e.reply ? replyQuote("Breeder replied", e.reply) : h("div", { class: "muted small" }, "Waiting for a reply")))))
    : h("p", { class: "muted" }, "No enquiries yet. Open a pet and tap Contact breeder."));
}

function becomeSellerSheet() {
  openSheet("Sell on BreederNear", [
    h("div", { class: "success" }, h("div", { class: "ring" }, icon("shop")), h("h3", { style: "margin:0;font-size:22px" }, "Sellers use a separate account"),
      h("p", { class: "muted" }, "A seller account gets its own dashboard: list pets in a minute with AI, see enquiries and views, and manage listings.")),
    h("div", { class: "callout info" }, "Listings on BreederNear are checked for legality, fair prices and scam signs before buyers see them. Protected native birds can never be listed."),
  ], [h("button", { class: "btn primary block", type: "button", onclick: () => { closeSheet(); logout({ quiet: true, then: () => viewAuth("signup", "seller") }); } }, "Create a seller account"),
    h("button", { class: "btn plain block", type: "button", onclick: () => { closeSheet(); logout({ quiet: true, then: () => demoLogin("seller") }); } }, "Try the demo seller instead")]);
}

// ---------------------------------------------------------------- login & sign-up
function passwordField(id, autocomplete) {
  const input = h("input", { id, type: "password", autocomplete, minlength: 8, required: true, placeholder: "At least 8 characters",
    style: "flex:1;min-width:0;border:0;background:transparent;padding:10px 0;font-size:16px" });
  const toggle = h("button", { class: "icon-btn", type: "button", "aria-label": "Show password", style: "background:none" }, icon("eye"));
  toggle.addEventListener("click", () => { const show = input.type === "password"; input.type = show ? "text" : "password"; toggle.setAttribute("aria-label", show ? "Hide password" : "Show password"); });
  return { input, el: h("div", { style: "display:flex;align-items:center;gap:6px" }, input, toggle) };
}
function authField(label, input, hint) {
  if (input.tagName !== "DIV") input.style.cssText = "width:100%;border:0;background:transparent;padding:10px 0;font-size:16px";
  return h("label", { style: "display:block;padding:6px 16px;border-top:.5px solid var(--sep)" }, h("span", { class: "muted small" }, label), input, hint ? h("span", { class: "muted small", style: "display:block;padding-bottom:6px" }, hint) : null);
}
function viewAuth(mode = "login", role = "customer") {
  document.body.classList.add("signed-out");
  $("composer").hidden = true;
  const card = h("div", { class: "card", style: "max-width:440px;margin:0 auto;padding:24px 20px" });
  const seg = h("div", { class: "segmented", role: "group", "aria-label": "Log in or sign up", style: "margin-bottom:18px" },
    h("button", { type: "button", "aria-pressed": String(mode === "login"), onclick: () => viewAuth("login", role) }, "Log in"),
    h("button", { type: "button", "aria-pressed": String(mode === "signup"), onclick: () => viewAuth("signup", role) }, "Sign up"));
  const error = h("div", { class: "callout bad", role: "alert", hidden: true, style: "margin-bottom:12px" });
  const fail = (e) => { error.textContent = e.message; error.hidden = false; };
  const loginInput = h("input", { id: "auth-login", autocomplete: "username", inputmode: "email", required: true, placeholder: "you@example.com or 98765 43210" });
  const remember = h("input", { type: "checkbox", checked: true, id: "auth-remember" });
  const demo = h("div", {},
    h("div", { style: "display:flex;align-items:center;gap:10px;margin:20px 0 14px;color:var(--label-3);font-size:13px" }, h("span", { style: "flex:1;border-top:.5px solid var(--sep)" }), "OR TRY THE DEMO", h("span", { style: "flex:1;border-top:.5px solid var(--sep)" })),
    h("div", { style: "display:grid;gap:8px" },
      h("button", { class: "btn secondary block", type: "button", onclick: () => demoLogin("customer") }, icon("paw"), "Demo customer · Priya"),
      h("button", { class: "btn secondary block", type: "button", onclick: () => demoLogin("seller") }, icon("shop"), "Demo seller · Karthik")),
    h("div", { class: "callout info", style: "margin-top:12px;font-size:14px" }, h("b", {}, "Demo logins (preloaded data)"),
      h("div", {}, "Customer: priya.customer@example.com"), h("div", {}, "Seller: karthik.seller@example.com"),
      h("div", {}, "Password for both: demo12345")));
  if (mode === "login") {
    const pw = passwordField("auth-password", "current-password");
    const submit = h("button", { class: "btn primary block", type: "submit" }, "Log in");
    const form = h("form", {},
      h("div", { class: "form-group" }, authField("Email or mobile number", loginInput), authField("Password", pw.el)),
      h("div", { style: "display:flex;justify-content:space-between;align-items:center;margin:14px 2px" },
        h("label", { style: "display:flex;gap:8px;align-items:center;font-size:15px" }, remember, "Remember me"),
        h("button", { class: "link", type: "button", onclick: forgotSheet }, "Forgot password?")),
      submit,
      h("p", { class: "muted", style: "text-align:center;margin:14px 0 0;font-size:15px" }, "Don't have an account? ", h("button", { class: "link", type: "button", onclick: () => viewAuth("signup", role) }, "Sign up")));
    form.addEventListener("submit", async (e) => {
      e.preventDefault(); error.hidden = true; submit.disabled = true;
      try { await finishLogin(await api("/api/auth/login", { method: "POST", body: JSON.stringify({ login: loginInput.value, password: pw.input.value, remember: remember.checked }) }), remember.checked); }
      catch (err) { fail(err); submit.disabled = false; }
    });
    card.append(seg, error, form, demo);
  } else {
    let chosen = role, farm = null;
    const roleSeg = h("div", { class: "segmented", role: "group", "aria-label": "I want to" },
      h("button", { type: "button", "aria-pressed": String(chosen === "customer"), onclick: () => viewAuth("signup", "customer") }, "Buy pets"),
      h("button", { type: "button", "aria-pressed": String(chosen === "seller"), onclick: () => viewAuth("signup", "seller") }, "Sell pets"));
    const name = h("input", { id: "auth-name", autocomplete: "name", required: true, maxlength: 60, placeholder: "Your name" });
    const pw = passwordField("auth-new-password", "new-password");
    const district = h("select", { id: "auth-district" }, state.districts.map((d) => h("option", { value: d.key, selected: d.key === state.district }, d.name)));
    const farmBlock = chosen === "seller" ? (farm = farmForm(null), h("div", {}, h("div", { class: "h-sub" }, "Your farm"), farm.el)) : null;
    const submit = h("button", { class: "btn primary block", type: "submit", style: "margin-top:16px" }, chosen === "seller" ? "Create seller account" : "Create account");
    const form = h("form", {},
      h("div", { class: "h-sub", style: "margin-top:0" }, "I want to"), roleSeg, h("div", { style: "height:14px" }),
      h("div", { class: "form-group" }, authField("Name", name), authField("Email or mobile number", loginInput), authField("Password", pw.el, "At least 8 characters. Please don't reuse an important password in this prototype."), authField("District", district)),
      farmBlock,
      h("label", { style: "display:flex;gap:8px;align-items:center;font-size:15px;margin:14px 2px 0" }, remember, "Remember me"),
      submit,
      h("p", { class: "muted small", style: "text-align:center;margin:12px 0 0" }, "We store only your name, email or mobile and district. Passwords are stored as secure hashes."),
      h("p", { class: "muted", style: "text-align:center;margin:10px 0 0;font-size:15px" }, "Already have an account? ", h("button", { class: "link", type: "button", onclick: () => viewAuth("login", role) }, "Log in")));
    form.addEventListener("submit", async (e) => {
      e.preventDefault(); error.hidden = true; submit.disabled = true;
      try {
        await finishLogin(await api("/api/auth/signup", { method: "POST", body: JSON.stringify({ role: chosen, name: name.value, login: loginInput.value,
          password: pw.input.value, district: district.value, remember: remember.checked, farm: farm?.values }) }), remember.checked);
      } catch (err) { fail(err); submit.disabled = false; window.scrollTo({ top: 0, behavior: "smooth" }); }
    });
    card.append(seg, error, form, demo);
  }
  main.classList.remove("ai-main");
  main.replaceChildren(h("div", { class: "view", style: "padding:28px 0 40px" },
    h("div", { style: "text-align:center;margin-bottom:20px" },
      h("div", { class: "mark", style: "width:58px;height:58px;border-radius:17px;background:var(--g-brand);display:grid;place-items:center;color:#fff;margin:0 auto 12px" }, icon("paw")),
      h("h1", { class: "large-title", style: "font-size:30px;margin:0" }, mode === "login" ? "Welcome back" : "Join BreederNear"),
      h("p", { class: "subtitle", style: "font-size:16px" }, mode === "login" ? "Log in to find trusted pets, or to manage your farm." : "Buy pets from trusted local breeders, or sell your own.")),
    card, disclaimer()));
  (mode === "login" ? loginInput : $("auth-name"))?.focus();
}
function forgotSheet() {
  openSheet("Forgot password", [
    h("p", {}, "Password reset needs a verified email or SMS service, which this prototype doesn't have."),
    h("p", { class: "muted" }, "Please create a new account, or try the demo customer or demo seller."),
  ], [h("button", { class: "btn primary block", type: "button", onclick: closeSheet }, "OK")]);
}
async function finishLogin(r, remember) {
  auth.token = r.token; auth.user = r.user;
  saveToken(r.token, remember);
  document.body.classList.remove("signed-out");
  if (r.user.district) { state.district = r.user.district; store.set("breedernear_district", r.user.district); }
  resetChat(); Object.assign(sell, { photos: [], text: "", draftId: null, data: null, busy: "", result: null });
  renderHeader();
  history.replaceState(null, "", isSeller() ? "#dashboard" : "#pets");
  route();
  if (!isSeller()) api("/api/cart").then(updateCart).catch(() => {});
}
async function demoLogin(role) {
  try {
    await finishLogin(await api("/api/auth/demo", { method: "POST", body: JSON.stringify({ role }) }), false);
    if (role === "seller") {
      Object.assign(sell, { text: "4 jodi lutino lovebird, 5 maasam, oru jodi 1800 rubai. Saibaba Colony, Kovai. Healthy, parents on site." });
      toast("Welcome, Karthik! Try “Sell a pet with AI”");
    } else {
      toast("Welcome, Priya! Your cart and enquiries are preloaded");
    }
  } catch (e) { toast(e.message); }
}
function signedOut(message) {
  auth.token = null; auth.user = null; clearToken(); resetChat(); state.cartCount = 0;
  closeSheet(); renderHeader(); viewAuth("login");
  if (message) toast(message);
}
async function logout({ quiet = false, then } = {}) {
  try { await fetch("/api/auth/logout", { method: "POST", headers: authHeaders() }); } catch { /* signing out locally anyway */ }
  signedOut(quiet ? null : "Logged out");
  then?.();
}
async function deleteAccount() {
  if (!confirm("Delete your account? Your profile, sessions and listings will be removed. This can't be undone.")) return;
  try { await api("/api/auth/me", { method: "DELETE" }); signedOut("Your account was deleted"); } catch (e) { toast(e.message); }
}

// ---------------------------------------------------------------- shell & routing
function renderHeader() {
  const signedIn = !!auth.user;
  $("brand-mark").replaceChildren(icon("paw"));
  $("district-btn").hidden = !signedIn || isSeller();
  $("cart-btn").hidden = !signedIn || isSeller();
  $("district-btn").replaceChildren(icon("pin"), h("span", { class: "pill-text" }, districtName(state.district)));
  $("district-btn").setAttribute("aria-label", `District: ${districtName(state.district)}. Change`);
  $("cart-btn").replaceChildren(...[icon("bag"), state.cartCount ? h("span", { class: "badge-dot" }, state.cartCount) : null].filter(Boolean));
  $("cart-btn").setAttribute("aria-label", `Cart, ${state.cartCount} item${state.cartCount === 1 ? "" : "s"}`);
  document.querySelectorAll("[data-cart-count]").forEach((n) => { n.textContent = String(state.cartCount); });  // e.g. Account › Cart
  $("role-pill").hidden = !isSeller();
  $("role-pill").replaceChildren(icon("shop"), h("span", {}, "Seller"));
  $("tabbar").hidden = !signedIn;
  $("top-tabs").hidden = !signedIn;
  $("tabbar").style.gridTemplateColumns = `repeat(${tabs().length}, 1fr)`;
}
function renderTabs(active) {
  const make = () => tabs().map(([key, label, ico]) => h("a", { class: "tab", href: `#${key}`, "aria-current": key === active ? "page" : null }, icon(ico), h("span", {}, label)));
  $("tabbar").replaceChildren(...make());
  $("top-tabs").replaceChildren(...make());
}
function go(path) { if (location.hash === `#${path}`) route(); else location.hash = path; }
function route() {
  if (!auth.user) { viewAuth("login"); return; }
  const fallback = isSeller() ? "dashboard" : "pets";
  const path = location.hash.replace(/^#\/?/, "") || fallback;
  const page = path.split("/")[0];
  const allowed = isSeller() ? ["dashboard", "listings", "enquiries", "sell", "ai", "farm"] : ["pets", "breeders", "ai", "account"];
  const current = allowed.includes(page) ? page : fallback;
  store.set("breedernear_tab", current);
  renderTabs(current === "sell" ? "listings" : current);
  $("composer").hidden = current !== "ai";
  main.classList.toggle("ai-main", current === "ai");
  if (current !== "ai") window.scrollTo({ top: 0 });
  ({ dashboard: viewDashboard, listings: () => viewSellerListings(), enquiries: viewSellerEnquiries, sell: viewSell, farm: viewFarm,
     breeders: viewBreeders, account: viewAccount, ai: viewAI, pets: viewPets })[current]();
}
window.addEventListener("hashchange", route);
$("district-btn").addEventListener("click", districtSheet);
$("cart-btn").addEventListener("click", cartSheet);

(async function init() {
  try { const m = await api("/api/meta"); state.districts = m.districts; } catch { state.districts = [{ key: "coimbatore", name: "Coimbatore" }]; }
  if (!state.districts.some((d) => d.key === state.district)) state.district = "coimbatore";
  auth.token = readToken();
  if (auth.token) {
    try { auth.user = (await api("/api/auth/me")).user; } catch { auth.token = null; clearToken(); }
  }
  resetChat();
  renderHeader();
  route();
  if (auth.user && !isSeller()) api("/api/cart").then(updateCart).catch(() => {});
})();
