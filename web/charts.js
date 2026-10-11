"use strict";

/* Small SVG charts for the seller dashboard: no library, theme colours from CSS, a hover value on every bar
   (<title>), and a "View as table" fallback for screen readers. Loaded before app.js; uses its h() at call time. */

const SVG_NS = "http://www.w3.org/2000/svg";
function svgEl(tag, attrs = {}, ...kids) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null) el.setAttribute(k, v);
  for (const kid of kids.flat()) if (kid != null) el.append(typeof kid === "string" ? document.createTextNode(kid) : kid);
  return el;
}

// Axis maximum in four equal steps of 1, 2 or 5 × 10^n.
function niceMax(value) {
  if (value <= 0) return 4;
  const raw = value / 4;
  const pow = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map((m) => m * pow).find((s) => s >= raw);
  return step * 4;
}

const fmtNum = (n) => (n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : String(n));

// series: [{ name, values, color }] grouped by labels. color is a CSS colour or var().
function barChart({ title, labels, series, format = fmtNum, unit = "", height = 170 }) {
  const W = 420, H = height, padL = 36, padB = 24, padT = 10;
  const max = niceMax(Math.max(0, ...series.flatMap((s) => s.values)));
  const groupW = (W - padL - 8) / labels.length;
  const barW = Math.min(18, (groupW - 8) / series.length);
  const y = (v) => padT + (H - padT - padB) * (1 - v / max);
  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img",
    "aria-label": `${title}: ${series.map((s) => `${s.name} ${s.values.reduce((a, b) => a + b, 0)}${unit} in total`).join(", ")}` });
  for (let i = 0; i <= 4; i++) {
    const v = (max / 4) * i;
    svg.append(svgEl("line", { x1: padL, x2: W - 4, y1: y(v), y2: y(v), class: "grid" }),
      svgEl("text", { x: padL - 6, y: y(v) + 4, class: "axis", "text-anchor": "end" }, format(v)));
  }
  labels.forEach((label, gi) => {
    const gx = padL + gi * groupW + (groupW - barW * series.length) / 2;
    series.forEach((s, si) => {
      const v = s.values[gi] || 0;
      svg.append(svgEl("rect", { x: gx + si * barW, y: y(v), width: Math.max(2, barW - 3), height: Math.max(0, y(0) - y(v)),
        rx: 3, style: `fill:${s.color}` }, svgEl("title", {}, `${label} · ${s.name}: ${format(v)}${unit}`)));
    });
    svg.append(svgEl("text", { x: padL + gi * groupW + groupW / 2, y: H - 8, class: "axis", "text-anchor": "middle" }, label));
  });
  return chartCard(title, svg, series.length > 1 ? series : null, ["Week", ...series.map((s) => s.name)],
    labels.map((l, i) => [l, ...series.map((s) => `${format(s.values[i] || 0)}${unit}`)]));
}

// rows: [{ label, value }] as horizontal bars, with each bar's share of the first one.
function funnelChart({ title, rows }) {
  const top = Math.max(1, rows[0]?.value || 1);
  const body = h("div", { class: "funnel" }, rows.map((r) => h("div", { class: "funnel-row" },
    h("span", { class: "funnel-label" }, r.label),
    h("span", { class: "funnel-track", "aria-hidden": "true" }, h("span", { class: "funnel-bar", style: `width:${Math.max(2, (100 * r.value) / top)}%` })),
    h("span", { class: "funnel-value" }, `${r.value}${r === rows[0] ? "" : ` · ${Math.round((100 * r.value) / top)}%`}`))));
  return chartCard(title, body, null, ["Stage", "Count"], rows.map((r) => [r.label, String(r.value)]));
}

function chartCard(title, chart, legendSeries, head, rows) {
  const table = h("table", { class: "chart-table" }, h("thead", {}, h("tr", {}, head.map((c) => h("th", { scope: "col" }, c)))),
    h("tbody", {}, rows.map((r) => h("tr", {}, r.map((c, i) => (i ? h("td", {}, c) : h("th", { scope: "row" }, c)))))));
  return h("div", { class: "card chart-card" },
    h("div", { class: "chart-head" }, h("b", {}, title),
      legendSeries ? h("span", { class: "legend" }, legendSeries.map((s) => h("span", {}, h("i", { style: `background:${s.color}`, "aria-hidden": "true" }), s.name))) : null),
    chart, h("details", { class: "chart-details" }, h("summary", {}, "View as table"), table));
}
