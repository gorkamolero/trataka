/* H1B Small-Software-Sponsor Finder — LibreMap (MapLibre GL) viewer.
 *
 * Loads data/leads.geojson and plots companies on a free OpenStreetMap-based
 * vector map. Filters (LLC-only, target band, min filings) drive both the map
 * layer and the sidebar list. No API keys, no tracking.
 */

const STYLE_PRIMARY = "https://tiles.openfreemap.org/styles/liberty";
const STYLE_FALLBACK = "https://demotiles.maplibre.org/style.json";

const state = { all: [], filtered: [] };

const map = new maplibregl.Map({
  container: "map",
  style: STYLE_PRIMARY,
  center: [-94.5, 33.5], // between MO and TX
  zoom: 4.4,
  attributionControl: true,
});
map.addControl(new maplibregl.NavigationControl(), "top-right");

// Fall back to MapLibre's demo tiles if OpenFreeMap can't be reached.
map.on("error", (e) => {
  if (e && e.error && /openfreemap/.test(String(e.error.url || ""))) {
    if (map.getStyle()?.sprite !== STYLE_FALLBACK) map.setStyle(STYLE_FALLBACK);
  }
});

map.on("load", init);

async function init() {
  let fc;
  try {
    const resp = await fetch("data/leads.geojson", { cache: "no-store" });
    fc = await resp.json();
  } catch (err) {
    document.getElementById("stats").textContent = "Could not load leads.geojson";
    return;
  }

  state.all = fc.features || [];
  if (fc.metadata && fc.metadata.sample) {
    document.getElementById("sample-banner").classList.remove("hidden");
  }

  map.addSource("leads", { type: "geojson", data: fc });

  // Color by entity type; radius scales with filing count.
  map.addLayer({
    id: "leads-circles",
    type: "circle",
    source: "leads",
    paint: {
      "circle-radius": [
        "interpolate", ["linear"], ["get", "lca_filing_count"],
        1, 5, 5, 9, 20, 16,
      ],
      "circle-color": [
        "case", ["==", ["get", "entity_type"], "LLC"], "#36c98d", "#f0a35e",
      ],
      "circle-opacity": 0.85,
      "circle-stroke-width": 1,
      "circle-stroke-color": "#0f1419",
    },
  });

  map.on("click", "leads-circles", (e) => showPopup(e.features[0]));
  map.on("mouseenter", "leads-circles", () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", "leads-circles", () => (map.getCanvas().style.cursor = ""));

  wireControls();
  applyFilters();
  fitToData();
}

function currentFilters() {
  return {
    llcOnly: document.getElementById("llc-only").checked,
    bandOnly: document.getElementById("band-only").checked,
    minFilings: parseInt(document.getElementById("min-filings").value, 10),
  };
}

function applyFilters() {
  const f = currentFilters();
  state.filtered = state.all.filter((ft) => {
    const p = ft.properties;
    if (f.llcOnly && p.entity_type !== "LLC") return false;
    if (f.bandOnly && p.in_target_band !== true) return false;
    if ((p.lca_filing_count || 0) < f.minFilings) return false;
    return true;
  });

  map.getSource("leads").setData({
    type: "FeatureCollection",
    features: state.filtered,
  });

  renderList();
  renderStats();
}

function wireControls() {
  document.getElementById("llc-only").addEventListener("change", applyFilters);
  document.getElementById("band-only").addEventListener("change", applyFilters);
  const slider = document.getElementById("min-filings");
  slider.addEventListener("input", () => {
    document.getElementById("minf-val").textContent = slider.value;
    applyFilters();
  });
}

function renderStats() {
  const total = state.filtered.length;
  const llc = state.filtered.filter((f) => f.properties.entity_type === "LLC").length;
  const band = state.filtered.filter((f) => f.properties.in_target_band === true).length;
  document.getElementById("stats").innerHTML =
    `<span><b>${total}</b> companies</span>` +
    `<span><b>${llc}</b> LLC</span>` +
    `<span><b>${band}</b> in band</span>`;
  document.getElementById("count").textContent = `${total} shown`;
}

function renderList() {
  const ul = document.getElementById("list");
  ul.innerHTML = "";
  const sorted = [...state.filtered].sort((a, b) => {
    const al = a.properties.entity_type === "LLC" ? 1 : 0;
    const bl = b.properties.entity_type === "LLC" ? 1 : 0;
    if (al !== bl) return bl - al;
    return (a.properties.lca_filing_count || 0) - (b.properties.lca_filing_count || 0);
  });
  for (const ft of sorted) {
    const p = ft.properties;
    const li = document.createElement("li");
    const tags = [];
    if (p.entity_type === "LLC") tags.push('<span class="tag llc">LLC</span>');
    if (p.review_status === "needs_review") tags.push('<span class="tag review">review</span>');
    li.innerHTML =
      `<div class="name">${escapeHtml(p.name)}</div>` +
      `<div class="meta">` +
      `<span>${escapeHtml(p.city || "?")}, ${escapeHtml(p.state || "?")}</span>` +
      `<span>${p.lca_filing_count} filings</span>` +
      (p.approval_count != null ? `<span>${p.approval_count} approvals</span>` : "") +
      tags.join("") +
      `</div>`;
    li.addEventListener("click", () => {
      map.flyTo({ center: ft.geometry.coordinates, zoom: 9 });
      showPopup(ft);
    });
    ul.appendChild(li);
  }
}

function showPopup(ft) {
  const p = ft.properties;
  const titles = Array.isArray(p.job_titles)
    ? p.job_titles
    : JSON.parse(p.job_titles || "[]");
  const rows = [
    ["Entity", p.entity_type],
    ["NAICS", p.naics_code || "—"],
    ["Location", `${p.city || "?"}, ${p.state || "?"}`],
    ["LCA filings", p.lca_filing_count],
    ["Approvals", p.approval_count != null ? p.approval_count : "—"],
    ["Building score", p.building_score != null ? p.building_score : "—"],
    ["In band (2–10)", p.in_target_band === true ? "yes" : p.in_target_band === false ? "no" : "unknown"],
    ["Size confidence", p.size_confidence],
    ["Headcount", "unknown (proxy only)"],
    ["Geocode", p.geocode_precision],
  ];
  const html =
    `<h3>${escapeHtml(p.name)}</h3>` +
    rows.map(([k, v]) => `<div class="row"><span class="k">${k}</span><span>${escapeHtml(String(v))}</span></div>`).join("") +
    (titles.length ? `<div class="row"><span class="k">Titles</span><span>${escapeHtml(titles.join(", "))}</span></div>` : "");
  new maplibregl.Popup({ closeButton: true })
    .setLngLat(ft.geometry.coordinates)
    .setHTML(html)
    .addTo(map);
}

function fitToData() {
  if (!state.filtered.length) return;
  const b = new maplibregl.LngLatBounds();
  state.filtered.forEach((f) => b.extend(f.geometry.coordinates));
  map.fitBounds(b, { padding: 60, maxZoom: 9 });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
