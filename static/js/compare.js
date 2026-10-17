// Side-by-side comparison of two products.
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const METRICS = [
  { key: "calories", label: "Calories (kcal)", lowerBetter: true },
  { key: "sugar", label: "Sugar (g)", lowerBetter: true },
  { key: "fat", label: "Fat (g)", lowerBetter: true },
  { key: "sodium", label: "Sodium (mg)", lowerBetter: true },
  { key: "protein", label: "Protein (g)", lowerBetter: false },
];

function buildColumn(slot, title) {
  const col = $(slot === 1 ? "colP1" : "colP2");
  if (!col) return;
  col.innerHTML = `<h6>${title}</h6>
    <input class="form-control mb-2" id="p${slot}_name" placeholder="Product name">
    <div class="row g-2">${METRICS.map(m => `
      <div class="col-6"><label class="form-label small mb-0" for="p${slot}_${m.key}">${m.label}</label>
      <input type="number" step="any" min="0" class="form-control form-control-sm" id="p${slot}_${m.key}"></div>`).join("")}
    </div>`;
}

export function setProduct(slot, result) {
  const n = result.nutrients || {};
  const map = { name: result.product_name, calories: n.energy_kcal, sugar: n.sugars, fat: n.fat, sodium: n.sodium_mg, protein: n.protein };
  Object.entries(map).forEach(([k, v]) => {
    const el = $(`p${slot}_${k}`);
    if (el) el.value = v == null ? "" : (typeof v === "number" ? Math.round(v * 10) / 10 : v);
  });
  const sec = $("compareSection");
  if (sec) sec.scrollIntoView({ behavior: "smooth", block: "start" });
}

function readSlot(slot) {
  const num = k => { const el = $(`p${slot}_${k}`); const v = el ? parseFloat(el.value) : NaN; return Number.isFinite(v) ? v : null; };
  const nameEl = $(`p${slot}_name`);
  return { name: (nameEl && nameEl.value.trim()) || `Product ${slot === 1 ? "A" : "B"}`, values: Object.fromEntries(METRICS.map(m => [m.key, num(m.key)])) };
}

function evaluate() {
  const a = readSlot(1), b = readSlot(2);
  let aWins = 0, bWins = 0;
  const rows = METRICS.map(m => {
    const x = a.values[m.key], y = b.values[m.key];
    let winner = "—";
    if (x != null && y != null && x !== y) {
      const aBetter = m.lowerBetter ? x < y : x > y;
      winner = aBetter ? "A" : "B";
      aBetter ? aWins++ : bWins++;
    } else if (x != null && y != null) winner = "Tie";
    const cell = (v, w, me) => `<td class="${winner === me ? "winner" : ""}">${v == null ? "—" : v}</td>`;
    return `<tr><td class="text-start">${m.label}<br><small class="text-muted">${m.lowerBetter ? "lower is better" : "higher is better"}</small></td>
      ${cell(x, winner, "A")}${cell(y, winner, "B")}<td>${winner === "A" ? esc(a.name) : winner === "B" ? esc(b.name) : winner}</td></tr>`;
  });

  const body = $("compareBody"); if (body) body.innerHTML = rows.join("");
  const th1 = $("thP1"), th2 = $("thP2");
  if (th1) th1.textContent = a.name; if (th2) th2.textContent = b.name;

  const verdict = $("compareVerdict");
  if (verdict) {
    verdict.className = "alert mb-0 " + (aWins === bWins ? "alert-secondary" : "alert-success");
    verdict.textContent = aWins === bWins
      ? `It's a draw (${aWins} – ${bWins}). Neither product is clearly healthier on these metrics.`
      : `🏆 ${aWins > bWins ? a.name : b.name} is the healthier choice, winning ${Math.max(aWins, bWins)} of ${METRICS.length} metrics (${aWins} – ${bWins}).`;
  }
  const res = $("compareResult"); if (res) res.classList.remove("d-none");
}

export function initCompare() {
  buildColumn(1, "Product A");
  buildColumn(2, "Product B");
  const btn = $("compareBtn");
  if (btn) btn.addEventListener("click", evaluate);
}
