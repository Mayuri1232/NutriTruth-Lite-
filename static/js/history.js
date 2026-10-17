// LocalStorage-backed scan history (max 5).
const KEY = "nutritruth_history_v1";
const MAX = 5;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export function loadHistory() {
  try { const v = JSON.parse(localStorage.getItem(KEY) || "[]"); return Array.isArray(v) ? v : []; }
  catch (_) { return []; }
}

function persist(items) {
  try { localStorage.setItem(KEY, JSON.stringify(items)); } catch (_) { /* quota / private mode */ }
}

export function saveToHistory(result) {
  const items = loadHistory();
  items.unshift({ id: Date.now(), ts: new Date().toISOString(), result });
  persist(items.slice(0, MAX));
}

export function removeFromHistory(id) {
  persist(loadHistory().filter(i => i.id !== id));
}

export function renderHistory(handlers) {
  const box = $("historyList");
  if (!box) return;
  const items = loadHistory();
  if (!items.length) {
    box.innerHTML = `<div class="list-group-item text-muted">No saved scans yet. Press “Save to History” after a scan.</div>`;
    return;
  }
  box.innerHTML = items.map(i => {
    const r = i.result || {};
    const grade = (r.nutri_score && r.nutri_score.grade) || "?";
    return `<div class="list-group-item d-flex justify-content-between align-items-center flex-wrap gap-2">
      <div><span class="badge g-${esc(grade)} me-2" style="min-width:1.8rem">${esc(grade)}</span>
        <strong>${esc(r.product_name)}</strong>
        <small class="text-muted ms-2">${new Date(i.ts).toLocaleString()}</small></div>
      <div class="btn-group btn-group-sm">
        <button class="btn btn-outline-success" data-act="restore" data-id="${i.id}">Restore</button>
        <button class="btn btn-outline-primary" data-act="a" data-id="${i.id}">→ A</button>
        <button class="btn btn-outline-primary" data-act="b" data-id="${i.id}">→ B</button>
        <button class="btn btn-outline-danger" data-act="del" data-id="${i.id}">✕</button>
      </div></div>`;
  }).join("");

  box.querySelectorAll("button[data-act]").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = Number(btn.dataset.id);
      const item = loadHistory().find(x => x.id === id);
      if (btn.dataset.act === "del") { removeFromHistory(id); renderHistory(handlers); return; }
      if (item && handlers[btn.dataset.act]) handlers[btn.dataset.act](item.result);
    });
  });
}
