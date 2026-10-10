"use strict";

const APP = "breedernear";
const MAX_PHOTOS = 4;
const AGENTS = {
  breedernear_concierge: "Concierge", listing_agent: "Listing copilot", trust_agent: "Trust checker",
  match_agent: "Buyer guide", care_agent: "Care guide",
};
const LOADING = {
  transfer_to_agent: "Passing you to the right assistant…",
  extract_listing: "Reading your photos and message…",
  update_draft: "Updating your draft…",
  publish_listing: "Running trust checks…",
  check_external_listing: "Running trust checks…",
  recommend_species: "Matching pets to your home…",
  search_listings: "Finding trusted listings near you…",
  get_listing: "Opening the listing…",
  create_enquiry: "Sending your enquiry…",
  build_starter_kit: "Building your starter kit…",
  care_plan: "Writing your care plan…",
  add_to_cart: "Adding to your cart…",
};
const MODES = {
  buyer: {
    label: "Buyer", title: "Find your pet",
    text: "Tell me about your home, family, budget and district. I'll suggest suitable pets and trusted breeders nearby.",
    placeholder: "e.g. A pet bird for my daughter, flat in Tiruppur, ₹3000",
    chips: ["Pet bird for my 8-year-old, we live in a flat in Tiruppur, budget ₹3000",
            "Labrador puppy near Coimbatore", "Lovebirds near Erode under ₹2000",
            "I want an Indian parrot that talks"],
  },
  breeder: {
    label: "Breeder", title: "List your animals",
    text: "Send a photo and a quick message, the way you would on WhatsApp, in English or Tamil. I'll build the listing, suggest a fair price and run the trust checks.",
    placeholder: "e.g. 4 jodi lutino lovebird, 5 maasam, jodi 1800 rubai, Kovai",
    chips: ["4 jodi lutino lovebird, 5 maasam, oru jodi 1800 rubai. Saibaba Colony, Kovai",
            "3 budgie pairs, 4 months, ₹600 per pair, Erode", "Show my listings", "Any enquiries for me?"],
  },
  check: {
    label: "Safety check", title: "Is this listing safe?",
    text: "Paste the text of a pet-sale post or upload a screenshot. I'll check it for legality, scam and welfare warning signs. Nothing you check is published.",
    placeholder: "Paste the post text here…",
    chips: ["Lovebirds pair 500 only!! Full advance GPay, courier only, all India delivery. Contact fast",
            "Pachai kili kunju virpanaikku, pesum, 800 rubai",
            "Golden retriever puppies 8000, vaccinated, no visit, parcel only"],
  },
};
const ICON = { pass: "✅", warn: "⚠️", block: "⛔", info: "ℹ️" };
const LEVEL_ICON = { TRUSTED: "✅", CAUTION: "⚠️", BLOCKED: "⛔" };
const FIELD_NAMES = {
  price_inr: "price", age_months: "age", health_notes: "health notes", district: "district",
  sawb_registration_no: "dog-breeder registration (SAWB)", parivesh_registration_id: "PARIVESH registration",
};

// ---------- storage (works even when localStorage is blocked) ----------
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
function guestId() {
  let id = store.get("breedernear_guest_id");
  if (!id || !/^[0-9a-f-]{36}$/i.test(id)) { id = uuid(); store.set("breedernear_guest_id", id); }
  return id;
}
const GUEST = guestId();
const sessionKey = (mode) => `breedernear_session_${mode}`;

// ---------- DOM helpers ----------
const $ = (id) => document.getElementById(id);
function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) if (c != null && c !== false) el.append(c.nodeType ? c : String(c));
  return el;
}
const titleCase = (s) => (s || "").replace(/\b[a-z]/g, (c) => c.toUpperCase());
const inr = (n) => (n == null ? "—" : "₹" + Number(n).toLocaleString("en-IN"));
const escapeHtml = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// Minimal, safe markdown: input is escaped first, then a few inline/block patterns are applied.
function md(text) {
  const inline = (s) => escapeHtml(s)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*(?!\s)(.+?)\*(?!\*)/g, "$1<em>$2</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
  const out = [];
  let list = null, para = [];
  const flushPara = () => { if (para.length) { out.push(`<p>${para.join("<br>")}</p>`); para = []; } };
  const flushList = () => { if (list) { out.push(`<${list.tag}>${list.items.map((i) => `<li>${i}</li>`).join("")}</${list.tag}>`); list = null; } };
  for (const raw of text.split("\n")) {
    const line = raw.trimEnd();
    let m;
    if (!line.trim()) { flushPara(); flushList(); continue; }
    if (/^\s*(---|\*\*\*)\s*$/.test(line)) { flushPara(); flushList(); continue; }
    if ((m = line.match(/^\s*#{1,6}\s+(.*)$/))) { flushPara(); flushList(); out.push(`<h4>${inline(m[1])}</h4>`); continue; }
    if ((m = line.match(/^\s*[-*•]\s+(.*)$/)) || (m = line.match(/^\s*\d+[.)]\s+(.*)$/))) {
      flushPara();
      const tag = /^\s*\d/.test(line) ? "ol" : "ul";
      if (!list || list.tag !== tag) { flushList(); list = { tag, items: [] }; }
      list.items.push(inline(m[1]));
      continue;
    }
    flushList();
    para.push(inline(line));
  }
  flushPara(); flushList();
  return out.join("");
}

function emojiFor(text = "") {
  const t = text.toLowerCase();
  if (/dog|labrador|beagle|shih|puppy|retriever/.test(t)) return "🐕";
  if (/cat|persian|kitten/.test(t)) return "🐈";
  if (/finch|canary/.test(t)) return "🐤";
  if (/budg|lovebird|cockatiel|parakeet|parrot|bird/.test(t)) return "🦜";
  return "🐾";
}
const PRODUCT_EMOJI = { cage: "🏠", food: "🌾", perches: "🪵", feeders: "🥣", mineral: "🦴", carrier: "🧳",
  treat: "🌾", toy: "🧸", bowls: "🥣", bed: "🛏️", collar_leash: "🦮", grooming: "🪮", hygiene: "🧴",
  litter_box: "📦", litter: "🪣", scratching_post: "🪵" };

// ---------- API ----------
async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", "X-Guest-Id": GUEST, ...(options.headers || {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return body;
}

// ---------- app state ----------
let mode = null;
let sessionId = null;
let busy = false;
let pendingFiles = [];

function setMode(next) {
  mode = next;
  store.set("breedernear_mode", next || "");
  const m = MODES[next];
  $("home").hidden = !!next;
  $("chat").hidden = !next;
  $("composer").hidden = !next;
  $("new-btn").hidden = !next;
  $("mode-label").textContent = m ? `· ${m.label}` : "";
  $("cart-btn").hidden = next !== "buyer";
  $("inbox-btn").hidden = next !== "breeder";
  if (!m) return;
  $("input").placeholder = m.placeholder;
  $("attach").hidden = next === "buyer";
  $("intro").replaceChildren(
    h("h2", {}, m.title), h("p", {}, m.text),
    h("div", { class: "chips" }, m.chips.map((c) => h("button", { class: "chip", type: "button", onclick: () => send(c) }, c))),
  );
  refreshCounts();
}

async function createSession() {
  const s = await api(`/apps/${APP}/users/${GUEST}/sessions`, { method: "POST", body: JSON.stringify({ state: { mode } }) });
  sessionId = s.id;
  store.set(sessionKey(mode), sessionId);
  return sessionId;
}

async function openMode(next, { fresh = false } = {}) {
  setMode(next);
  $("log").replaceChildren();
  sessionId = fresh ? null : store.get(sessionKey(next));
  if (fresh) store.del(sessionKey(next));
  if (sessionId) {
    try {
      const s = await api(`/apps/${APP}/users/${GUEST}/sessions/${sessionId}`);
      replay(s.events || []);
    } catch {
      sessionId = null; store.del(sessionKey(next));
    }
  }
  $("input").focus();
}

// ---------- rendering the conversation ----------
function scrollDown() { window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" }); }
function add(node) { $("log").append(node); scrollDown(); return node; }

function stripNote(text) { return text.replace(/\n?\[attachments upload_ids=[^\]]*\]/g, "").trim(); }

function userBubble(text, images = []) {
  const shown = stripNote(text);
  const photos = (text.match(/upload_ids=([^\s\]]+)/)?.[1] || "").split(",").filter(Boolean).length;
  add(h("div", { class: "msg user" }, shown || (photos ? "" : "…"),
    images.length ? h("div", { class: "thumbs" }, images.map((src) => h("img", { src, alt: "Photo you sent" })))
      : photos ? h("div", {}, `📷 ${photos} photo${photos > 1 ? "s" : ""}`) : null));
}

class Turn {
  constructor() {
    this.bubble = null; this.text = ""; this.author = null;
    this.seenCalls = new Set(); this.seenResponses = new Set();
    this.activity = null; this.steps = 0;
    this.typing = null;
  }
  setTyping(label) {
    if (!this.typing) this.typing = add(h("div", { class: "typing", role: "status" }));
    this.typing.textContent = label;
    $("log").append(this.typing);
  }
  done() { this.typing?.remove(); this.typing = null; }
  closeBubble() { this.bubble = null; this.text = ""; }
  log(line) {
    if (!this.activity) {
      this.activityList = h("ol");
      this.activitySummary = h("summary");
      this.activity = add(h("details", { class: "activity" }, this.activitySummary, this.activityList));
    }
    this.steps += 1;
    this.activitySummary.textContent = `What the AI did (${this.steps} step${this.steps > 1 ? "s" : ""})`;
    this.activityList.append(h("li", {}, line));
  }
  writeText(author, text, partial) {
    if (!text) return;
    if (!this.bubble || this.author !== author) {
      this.author = author; this.text = "";
      this.body = h("div");
      this.bubble = add(h("div", { class: "msg bot" }, h("div", { class: "who" }, AGENTS[author] || "Assistant"), this.body));
    }
    this.text = partial ? this.text + text : text;
    this.body.innerHTML = md(this.text);
    if (this.typing) $("log").append(this.typing);
    if (!partial) this.closeBubble();
    scrollDown();
  }
}

function summarise(name, r) {
  if (!r || typeof r !== "object") return "done";
  if (r.status === "error") return `error: ${r.message}`;
  if (r.status === "not_allowed") return "not allowed (protected species)";
  if (r.screening) return `${r.listing_status ? r.listing_status + ", " : ""}${r.screening.trust_level} ${r.screening.trust_score}`;
  if (r.results) return `${r.results.length} result(s) nearby`;
  if (r.options) return `${r.options.length} option(s)`;
  if (r.items) return `${r.items.length} item(s), ${inr(r.total_inr)}`;
  if (r.care_plan) return "care plan ready";
  if (r.draft) return `draft ${r.draft_id}`;
  if (r.enquiry_id) return `enquiry ${r.enquiry_id}`;
  return r.status || "done";
}

function handleEvent(turn, ev) {
  if (ev.error || ev.errorMessage) {
    add(h("div", { class: "msg error", role: "alert" }, "Something went wrong on our side. Please try again."));
    return;
  }
  const author = ev.author;
  for (const part of ev.content?.parts || []) {
    if (part.thought) continue;
    const call = part.functionCall || part.function_call;
    const resp = part.functionResponse || part.function_response;
    if (call) {
      const key = call.id || `${call.name}:${JSON.stringify(call.args)}`;
      if (turn.seenCalls.has(key)) continue;
      turn.seenCalls.add(key);
      turn.closeBubble();
      if (call.name === "transfer_to_agent") {
        turn.log(`${AGENTS[author] || author} → hands over to ${AGENTS[call.args?.agent_name] || call.args?.agent_name}`);
      } else {
        const args = Object.entries(call.args || {}).filter(([k]) => k !== "text")
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.length + " item(s)" : v}`).join(", ");
        turn.log(`${AGENTS[author] || author} → ${call.name}(${args})`);
      }
      turn.setTyping(LOADING[call.name] || "Working…");
    } else if (resp) {
      const key = resp.id || resp.name;
      if (turn.seenResponses.has(key)) continue;
      turn.seenResponses.add(key);
      turn.closeBubble();
      if (resp.name !== "transfer_to_agent") {
        turn.log(`↳ ${resp.name}: ${summarise(resp.name, resp.response)}`);
        renderTool(resp.name, resp.response || {});
      }
      if (turn.typing) turn.setTyping("Thinking…");
    } else if (typeof part.text === "string" && author && author !== "user") {
      turn.writeText(author, part.text, !!ev.partial);
    }
  }
}

function replay(events) {
  let turn = null;
  for (const ev of events) {
    if (ev.author === "user" && ev.content?.parts?.some((p) => typeof p.text === "string")) {
      turn = new Turn();
      userBubble(ev.content.parts.map((p) => p.text || "").join(""));
      continue;
    }
    if (!turn) turn = new Turn();
    handleEvent(turn, ev);
  }
}

// ---------- cards ----------
function badge(level, score) {
  return h("span", { class: `badge ${level}` }, `${LEVEL_ICON[level] || ""} ${level}${score != null ? " · " + score : ""}`);
}
function checksList(checks = []) {
  return h("ul", { class: "checks" }, checks.map((c) => h("li", {}, h("span", { "aria-label": c.result }, ICON[c.result] || "•"), h("span", {}, c.detail))));
}
function questions(qs = []) {
  return qs.length ? h("div", { class: "questions" }, h("b", {}, "Questions to ask the seller"), h("ul", {}, qs.map((q) => h("li", {}, q)))) : null;
}
function rangeBar(price, range) {
  if (!range || !price) return null;
  const [lo, hi] = range, max = hi * 1.6;
  const pct = (v) => Math.max(0, Math.min(100, (v / max) * 100));
  const where = price < lo * 0.5 ? "⚠️ far below the usual range" : price < lo ? "⚠️ below the usual range"
    : price > hi * 1.5 ? "ℹ️ well above the usual range" : "✅ within the usual range";
  return h("div", { class: "range" },
    h("div", { class: "bar", role: "img", "aria-label": `Price ${inr(price)}, usual range ${inr(lo)} to ${inr(hi)}` },
      h("div", { class: "fair", style: `left:${pct(lo)}%;width:${pct(hi) - pct(lo)}%` }),
      h("div", { class: "marker", style: `left:calc(${pct(price)}% - 2px)` })),
    h("div", { class: "label" }, `${where}: ${inr(lo)}–${inr(hi)} (sample market data)`));
}
const unitWord = (unit) => (unit === "pair" ? "pair" : unit === "litter" ? "litter" : "each");

function draftCard(r) {
  const d = r.draft;
  const card = h("div", { class: "card" },
    h("h3", {}, h("span", {}, `${emojiFor(d.species_common)} Draft listing`), h("span", { class: "meta" }, "Not published yet")),
    h("dl", { class: "fields" },
      h("dt", {}, "Species"), h("dd", {}, [d.species_common, d.variety].filter(Boolean).join(" · ")),
      h("dt", {}, "Count"), h("dd", {}, `${d.count} ${d.unit === "pair" ? "pair(s)" : d.unit === "litter" ? "litter" : ""}`.trim()),
      h("dt", {}, "Age"), h("dd", {}, d.age_months != null ? `${d.age_months} months` : "—"),
      h("dt", {}, "Price"), h("dd", {}, d.price_inr ? `${inr(d.price_inr)} / ${unitWord(d.unit)}` : "—"),
      h("dt", {}, "Place"), h("dd", {}, [d.locality, titleCase(d.district)].filter(Boolean).join(", ") || "—"),
      d.health_notes ? [h("dt", {}, "Health"), h("dd", {}, d.health_notes)] : null),
    rangeBar(d.price_inr, r.fair_price_range_inr),
    r.missing_fields?.length ? h("div", { class: "missing" }, "Missing:", r.missing_fields.map((f) => h("span", {}, FIELD_NAMES[f] || f))) : null,
    h("div", { class: "actions" },
      h("button", { class: "btn", type: "button", onclick: (e) => { e.target.disabled = true; send("Publish it"); } }, "Publish"),
      h("button", { class: "btn ghost", type: "button", onclick: () => prefill("Change the price to ") }, "Edit")));
  add(card);
}

function trustCard(screening, { title, status } = {}) {
  add(h("div", { class: "card" },
    h("h3", {}, h("span", {}, title || "Trust check"), badge(screening.trust_level, screening.trust_score)),
    status ? h("div", { class: "meta" }, status) : null,
    checksList(screening.checks),
    questions(screening.questions_to_ask_seller)));
}

function speciesCards(r) {
  add(h("div", { class: "grid" }, r.options.map((o) => h("div", { class: "card" },
    h("h3", {}, h("span", {}, `${emojiFor(o.species)} ${o.species}`)),
    o.typical_price_range_inr ? h("div", { class: "meta" }, `${inr(o.typical_price_range_inr[0])}–${inr(o.typical_price_range_inr[1])} per ${o.price_unit} (sample data)`) : null,
    h("ul", { class: "plain" }, o.why.slice(0, 4).map((w) => h("li", {}, w))),
    o.watch_outs?.length ? h("div", { class: "warn-box" }, "Watch out: ", o.watch_outs.slice(0, 2).join(" ")) : null,
    h("div", { class: "actions" }, h("button", { class: "btn", type: "button", onclick: () => send(`Show me ${o.species} listings near me`) }, "Find nearby"))))));
}

function listingCard(c) {
  const where = [c.locality, titleCase(c.district)].filter(Boolean).join(", ");
  return h("div", { class: "card" },
    h("div", { class: "photo", "aria-hidden": "true" }, emojiFor(c.species)),
    h("h3", {}, h("span", {}, [c.species, c.variety].filter(Boolean).join(" · ")), badge(c.trust_level, c.trust_score)),
    h("div", {}, h("span", { class: "price" }, inr(c.price_inr)), ` / ${unitWord(c.unit)} · `, h("span", { class: "meta" }, c.price_position)),
    h("div", { class: "meta" }, `${c.count} ${c.unit === "pair" ? "pair(s)" : "available"} · ${c.age_months ?? "?"} months`),
    h("div", { class: "meta" }, `📍 ${where}${c.distance ? " · " + c.distance : ""}`),
    h("div", { class: "meta" }, `🏡 ${c.breeder}${c.sample_data ? " (sample breeder)" : ""}`),
    c.warnings?.length ? h("div", { class: "warn-box" }, c.warnings.map((w) => h("div", {}, `⚠️ ${w}`))) : null,
    h("div", { class: "actions" },
      h("button", { class: "btn", type: "button", onclick: () => send(`I'd like to contact the breeder of ${c.listing_id}`) }, "Contact"),
      h("button", { class: "btn ghost", type: "button", onclick: () => send(`Tell me more about ${c.listing_id}`) }, "Details"),
      h("button", { class: "btn ghost", type: "button", onclick: () => send(`What do I need for ${c.unit === "pair" ? "a pair of " : "a "}${c.species}?`) }, "Starter kit")));
}

function listingsCards(r) {
  if (r.results?.length) add(h("div", { class: "grid" }, r.results.map(listingCard)));
  else add(h("div", { class: "card" }, h("h3", {}, "No listings nearby"), h("div", { class: "meta" }, "Try a wider search or another species.")));
  if (r.further_away?.length) {
    add(h("div", { class: "meta" }, "Further away:"));
    add(h("div", { class: "grid" }, r.further_away.map(listingCard)));
  }
  if (r.note) add(h("div", { class: "note" }, r.note));
}

function listingDetail(r) {
  const c = r.listing;
  add(h("div", { class: "card" },
    h("h3", {}, h("span", {}, `${emojiFor(c.species)} ${[c.species, c.variety].filter(Boolean).join(" · ")}`), badge(c.trust_level, c.trust_score)),
    r.description ? h("p", {}, r.description) : null,
    r.health_notes ? h("div", { class: "meta" }, `Health: ${r.health_notes}`) : null,
    r.breeder ? h("div", { class: "meta" }, `🏡 ${r.breeder.name}, ${r.breeder.locality} · ${r.breeder.years_experience} years breeding (sample breeder)`) : null,
    checksList(r.checks), questions(r.questions_to_ask_seller)));
}

function kitCard(r) {
  const addBtn = (item) => h("button", { class: "btn ghost", type: "button", "aria-label": `Add ${item.name} to cart`,
    onclick: async (e) => { e.target.disabled = true; await addToCart([item.product_id]); e.target.textContent = "Added ✓"; } }, "Add");
  add(h("div", { class: "card" },
    h("h3", {}, h("span", {}, `🧺 Starter kit: ${r.count} × ${r.species}`)),
    r.min_cage_cm ? h("div", { class: "meta" }, `Minimum cage for welfare: ${r.min_cage_cm.join(" × ")} cm`) : null,
    r.welfare_note ? h("div", { class: "warn-box" }, `⚠️ ${r.welfare_note}`) : null,
    r.items.map((i) => h("div", { class: "product" },
      h("div", { class: "pic", "aria-hidden": "true" }, PRODUCT_EMOJI[i.category] || "📦"),
      h("div", { class: "body" }, h("b", {}, i.name), h("small", {}, `${i.brand} · ${i.why}`)),
      h("div", { class: "right" }, h("span", {}, inr(i.price_inr)), addBtn(i)))),
    h("div", { class: "total" }, h("span", {}, "Total"), h("span", {}, inr(r.total_inr))),
    h("div", { class: "actions" }, h("button", { class: "btn", type: "button",
      onclick: async (e) => { e.target.disabled = true; await addToCart(r.items.map((i) => i.product_id)); e.target.textContent = "Kit added ✓"; } }, "Add whole kit to cart")),
    h("div", { class: "note" }, r.note)));
}

function careCard(r) {
  const p = r.care_plan;
  add(h("div", { class: "card" },
    h("h3", {}, h("span", {}, `📋 First 14 days: ${p.species}`)),
    p.phases.map((ph) => h("div", { class: "phase" }, h("b", {}, ph.title), h("ul", {}, ph.steps.map((s) => h("li", {}, s))))),
    h("div", { class: "phase" }, h("b", {}, "Diet"), h("ul", {}, p.diet.map((s) => h("li", {}, s)))),
    h("div", { class: "phase" }, h("b", {}, "Daily routine"), h("ul", {}, p.daily_routine.map((s) => h("li", {}, s)))),
    h("div", { class: "vet" }, h("b", {}, "🩺 See a vet if"), h("ul", {}, p.see_vet_if.map((s) => h("li", {}, s)))),
    h("div", { class: "note" }, p.disclaimer)));
}

function renderTool(name, r) {
  if (r.status === "not_allowed") {
    add(h("div", { class: "card blocked-box" }, h("b", {}, "⛔ Not allowed"), h("div", {}, r.message),
      r.legal_alternatives ? h("div", { class: "chips" }, r.legal_alternatives.map((a) => h("button", { class: "chip", type: "button", onclick: () => send(`Tell me about ${a} as a pet`) }, a))) : null));
    return;
  }
  if (r.status !== "ok") return;
  switch (name) {
    case "extract_listing": case "update_draft": draftCard(r); break;
    case "publish_listing":
      trustCard(r.screening, { title: r.listing_status === "BLOCKED" ? "⛔ Not published" : "🎉 Published",
        status: r.listing_status === "BLOCKED" ? "This listing can't be published." : "Visible only to you in this demo (sandboxed)." });
      refreshCounts(); break;
    case "check_external_listing": trustCard(r.screening, { title: "🔍 Post check", status: "Nothing was published or stored." }); break;
    case "recommend_species": if (r.options?.length) speciesCards(r); break;
    case "search_listings": listingsCards(r); break;
    case "get_listing": listingDetail(r); break;
    case "create_enquiry": add(h("div", { class: "card" }, h("h3", {}, "✉️ Enquiry sent"), h("div", { class: "meta" }, r.note))); break;
    case "build_starter_kit": kitCard(r); break;
    case "care_plan": careCard(r); break;
    case "add_to_cart": case "view_cart": updateCartCount(r); break;
    default: break;
  }
}

// ---------- cart, inbox ----------
function updateCartCount(cart) {
  const n = (cart.items || []).reduce((s, i) => s + i.quantity, 0);
  $("cart-count").textContent = n;
  if (n && mode !== "breeder") $("cart-btn").hidden = false;
}
async function addToCart(ids) {
  try {
    let cart;
    for (const id of ids) cart = await api("/api/cart/items", { method: "POST", body: JSON.stringify({ product_id: id }) });
    updateCartCount(cart);
  } catch (e) { add(h("div", { class: "msg error", role: "alert" }, e.message)); }
}
async function refreshCounts() {
  try { updateCartCount(await api("/api/cart")); } catch { /* not critical */ }
  if (mode === "breeder") {
    try { $("inbox-count").textContent = (await api("/api/breeder/enquiries")).enquiries.length; } catch { /* not critical */ }
  }
}
function openDrawer(title, nodes) {
  $("drawer-title").textContent = title;
  $("drawer-body").replaceChildren(...nodes);
  if (!$("drawer").open) $("drawer").showModal();
}
async function showCart() {
  const cart = await api("/api/cart").catch(() => ({ items: [], total_inr: 0, note: "" }));
  const rows = cart.items.map((i) => h("div", { class: "product" },
    h("div", { class: "body" }, h("b", {}, i.name), h("small", {}, `${i.brand} · ${i.quantity} × ${inr(i.price_inr)}`)),
    h("div", { class: "right" }, h("span", {}, inr(i.line_total_inr)),
      h("button", { class: "btn ghost", type: "button", "aria-label": `Remove ${i.name}`, onclick: async () => {
        updateCartCount(await api(`/api/cart/items/${encodeURIComponent(i.product_id)}`, { method: "DELETE" })); showCart();
      } }, "Remove"))));
  openDrawer("Demo cart", rows.length
    ? [...rows, h("div", { class: "total" }, h("span", {}, "Total"), h("span", {}, inr(cart.total_inr))), h("div", { class: "note" }, cart.note)]
    : [h("p", { class: "meta" }, "Your cart is empty. Ask for a starter kit to fill it.")]);
}
async function showInbox() {
  const [inbox, mine] = await Promise.all([api("/api/breeder/enquiries").catch(() => ({ enquiries: [] })),
    api("/api/breeder/listings").catch(() => ({ listings: [] }))]);
  openDrawer("Inbox and listings", [
    h("h3", {}, "Enquiries from buyers"),
    inbox.enquiries.length ? h("ul", { class: "plain" }, inbox.enquiries.map((e) => h("li", {}, `${e.listing_id}: “${e.message}”`)))
      : h("p", { class: "meta" }, "No enquiries yet. Tip: publish a listing, then search for it as a buyer and send an enquiry."),
    h("h3", {}, "My listings"),
    mine.listings.length ? h("ul", { class: "plain" }, mine.listings.map((l) => h("li", {},
      `${[l.species, l.variety].filter(Boolean).join(" · ")}, ${inr(l.price_inr)} `, badge(l.trust_level, l.trust_score))))
      : h("p", { class: "meta" }, "No listings yet."),
    h("p", { class: "note" }, "Listings you create are visible only to you in this demo."),
  ]);
}

// ---------- photos ----------
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
function renderPreviews() {
  $("previews").replaceChildren(...pendingFiles.map((p, i) => h("figure", {},
    h("img", { src: p.url, alt: `Photo ${i + 1} to send` }),
    h("button", { type: "button", "aria-label": `Remove photo ${i + 1}`, onclick: () => { URL.revokeObjectURL(p.url); pendingFiles.splice(i, 1); renderPreviews(); } }, "✕"))));
}
async function uploadAll(files) {
  const kind = mode === "check" ? "external_listing" : "listing_photo";
  const ids = [];
  for (const { file } of files) {
    const form = new FormData();
    form.append("file", await shrink(file));
    form.append("kind", kind);
    const res = await fetch("/api/uploads", { method: "POST", headers: { "X-Guest-Id": GUEST }, body: form });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || "Couldn't upload the photo.");
    ids.push(body.upload_id);
  }
  return { ids, kind };
}

// ---------- sending ----------
function prefill(text) { const i = $("input"); i.value = text; i.focus(); autoGrow(); }

async function runSse(text, turn) {
  const res = await fetch("/run_sse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ app_name: APP, user_id: GUEST, session_id: sessionId, streaming: true,
      new_message: { role: "user", parts: [{ text }] } }),
  });
  if (!res.ok) { const e = new Error(`run ${res.status}`); e.status = res.status; throw e; }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const chunk = buffer.slice(0, cut); buffer = buffer.slice(cut + 2);
      const data = chunk.split("\n").filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trim()).join("");
      if (!data) continue;
      try { handleEvent(turn, JSON.parse(data)); } catch (err) { console.error(err); }
    }
  }
}

async function send(text) {
  text = (text || "").trim();
  if (busy || (!text && !pendingFiles.length)) return;
  busy = true; $("send").disabled = true;
  const files = pendingFiles; pendingFiles = []; renderPreviews();
  $("input").value = ""; autoGrow();
  userBubble(text, files.map((f) => f.url));
  const turn = new Turn();
  turn.setTyping(files.length ? "Uploading photos…" : "Thinking…");
  try {
    let message = text;
    if (files.length) {
      const { ids, kind } = await uploadAll(files);
      message = `${text}\n[attachments upload_ids=${ids.join(",")} kind=${kind}]`;
    }
    if (!sessionId) await createSession();
    try {
      await runSse(message, turn);
    } catch (e) {
      if (e.status !== 404) throw e;
      await createSession();                // session expired (e.g. server restarted): start a new one
      await runSse(message, turn);
    }
  } catch (e) {
    console.error(e);
    const msg = e.status === 429 ? "You've sent a lot of messages. Please wait a few minutes and try again."
      : e.message && !/^run \d+/.test(e.message) && !/fetch/i.test(e.message) ? e.message
      : "Couldn't reach BreederNear right now. Please try again in a moment.";
    add(h("div", { class: "msg error", role: "alert" }, msg));
  } finally {
    turn.done();
    busy = false; $("send").disabled = false;
    refreshCounts();
  }
}

function autoGrow() { const i = $("input"); i.style.height = "auto"; i.style.height = Math.min(i.scrollHeight, 140) + "px"; }

// ---------- wiring ----------
document.querySelectorAll(".choice").forEach((b) => b.addEventListener("click", () => openMode(b.dataset.mode)));
$("demo-priya").addEventListener("click", async () => {
  await openMode("buyer", { fresh: true });
  send("Hi, I'm Priya from Tiruppur. I'd like a pet bird for my 8-year-old daughter. We live in a flat and our budget is about ₹3000.");
});
$("demo-karthik").addEventListener("click", async () => {
  await openMode("breeder", { fresh: true });
  send("4 jodi lutino lovebird, 5 maasam, oru jodi 1800 rubai. Saibaba Colony, Kovai. Healthy, parents on site.");
});
$("home-btn").addEventListener("click", () => setMode(null));
$("new-btn").addEventListener("click", () => openMode(mode, { fresh: true }));
$("cart-btn").addEventListener("click", showCart);
$("inbox-btn").addEventListener("click", showInbox);
$("drawer-close").addEventListener("click", () => $("drawer").close());
$("drawer").addEventListener("click", (e) => { if (e.target === $("drawer")) $("drawer").close(); });
$("attach").addEventListener("click", () => $("file").click());
$("file").addEventListener("change", (e) => {
  for (const file of e.target.files) {
    if (pendingFiles.length >= MAX_PHOTOS) break;
    if (!file.type.startsWith("image/")) continue;
    pendingFiles.push({ file, url: URL.createObjectURL(file) });
  }
  e.target.value = "";
  renderPreviews();
});
$("form").addEventListener("submit", (e) => { e.preventDefault(); send($("input").value); });
$("input").addEventListener("input", autoGrow);
$("input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send($("input").value); }
});

const savedMode = store.get("breedernear_mode");
if (savedMode && MODES[savedMode]) openMode(savedMode); else setMode(null);
