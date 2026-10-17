// Pure DOM rendering of an /api/analyze result. Every selection is null-guarded.
const $ = id => document.getElementById(id);
const setText = (id, text) => { const el = $(id); if (el) el.textContent = text; };
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = v => (v === null || v === undefined ? "—" : Number(v).toFixed(1).replace(/\.0$/, ""));

export function renderResult(r) {
  setText("resProduct", r.product_name);
  setText("resMeta", `OCR pass ${r.ocr_pass}`);

  const n = r.nutrients || {};
  setText("resEnergy", n.energy_kcal != null ? `${fmt(n.energy_kcal)} kcal` : "Energy not found");
  const bits = [];
  if (n.energy_kj != null) bits.push(`${Math.round(n.energy_kj)} kJ`);
  if (n.carbs != null) bits.push(`Carbs ${fmt(n.carbs)} g`);
  if (n.sat_fat != null) bits.push(`Sat. fat ${fmt(n.sat_fat)} g`);
  setText("resEnergySub", bits.join(" · "));

  // Nutri-Score bar
  const bar = $("nutriBar");
  const ns = r.nutri_score || {};
  if (bar) {
    bar.innerHTML = ["A", "B", "C", "D", "E"]
      .map(g => `<div class="grade g-${g}${g === ns.grade ? " active" : ""}">${g}</div>`).join("");
  }
  let note = `Score ${ns.score} (negative ${ns.negative_points} − positive ${ns.positive_points}).`;
  if (ns.incomplete) note += ` Estimated without: ${(ns.missing_inputs || []).join(", ")}.`;
  setText("nutriNote", note);

  // Traffic lights (4 cards)
  const grid = $("lightGrid");
  if (grid) {
    const tl = r.traffic_lights || {};
    grid.innerHTML = ["fat", "sugars", "sodium", "protein"].map(k => {
      const t = tl[k]; if (!t) return "";
      return `<div class="col-6"><div class="card light-card ${t.color} h-100 shadow-sm border-0"><div class="card-body">
        <div class="d-flex justify-content-between align-items-center">
          <span class="fw-semibold">${esc(t.title)}</span>
          <span class="badge badge-${t.color}">${esc(t.label)}</span></div>
        <div class="value">${fmt(t.value)}<small class="fs-6 text-muted"> ${t.value == null ? "" : esc(t.unit)}</small></div>
        <div class="ref">${esc(t.reference)}</div></div></div></div>`;
    }).join("");
  }

  // Additives
  const list = $("additiveList");
  if (list) {
    const adds = r.additives || [];
    list.innerHTML = adds.length ? adds.map(a => {
      const cls = a.tier === "caution" ? "bg-danger" : a.tier === "moderate" ? "bg-warning text-dark" : "bg-success";
      return `<div class="additive ${esc(a.tier)}">
        <div class="d-flex justify-content-between flex-wrap gap-1">
          <strong>${esc(a.name)} <small class="text-muted">${esc(a.code)}</small></strong>
          <span class="badge ${cls}">${esc(a.tier.charAt(0).toUpperCase() + a.tier.slice(1))}</span></div>
        <div class="small text-muted">${esc(a.purpose)}</div>
        <div class="small">${esc(a.explanation)}</div></div>`;
    }).join("") : `<p class="text-muted mb-0">No known additives were detected in the extracted text.</p>`;
  }

  setText("rawText", r.raw_text || "");
}
