// Entry point: wires up the UI. All DOM lookups are null-guarded.
import { analyzeImage } from "./api.js";
import { generateSampleLabel } from "./sample.js";
import { renderResult } from "./render.js";
import { saveToHistory, renderHistory } from "./history.js";
import { initCompare, setProduct } from "./compare.js";

const $ = id => document.getElementById(id);
const on = (el, evt, fn) => { if (el) el.addEventListener(evt, fn); };
const show = (el, yes) => { if (el) el.classList.toggle("d-none", !yes); };

let selectedFile = null;
let currentResult = null;
let previewUrl = null;

function showError(msg) {
  const box = $("errorAlert"), txt = $("errorText");
  if (txt) txt.textContent = msg;
  show(box, true);
  if (box) box.scrollIntoView({ behavior: "smooth", block: "nearest" });
}
const hideError = () => show($("errorAlert"), false);

function setFile(file) {
  hideError();
  if (!file) return;
  if (file.type && !file.type.startsWith("image/")) { showError("Please choose an image file (JPG, PNG, WEBP…)."); return; }
  selectedFile = file;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  const img = $("previewImage"); if (img) img.src = previewUrl;
  show($("dropZone"), false);
  show($("previewContainer"), true);
  const btn = $("scanBtn"); if (btn) btn.disabled = false;
}

function clearFile() {
  selectedFile = null;
  if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = null; }
  const img = $("previewImage"); if (img) img.removeAttribute("src");
  const input = $("fileInput"); if (input) input.value = "";
  show($("previewContainer"), false);
  show($("dropZone"), true);
  const btn = $("scanBtn"); if (btn) btn.disabled = true;
}

function setBusy(busy) {
  const btn = $("scanBtn"), label = $("scanLabel");
  if (btn) btn.disabled = busy || !selectedFile;
  show($("scanSpinner"), busy);
  show($("laserScanner"), busy);
  if (label) label.textContent = busy ? "Scanning…" : "Scan Label";
}

async function scan() {
  if (!selectedFile) return;
  hideError();
  setBusy(true);
  try {
    const nameEl = $("productName");
    const name = (nameEl && nameEl.value.trim()) || "";
    const result = await analyzeImage(selectedFile, name);
    currentResult = result;
    renderResult(result);
    show($("welcomePlaceholder"), false);
    show($("resultCard"), true);
  } catch (err) {
    showError(err && err.message ? err.message : "Something went wrong.");
  } finally {
    setBusy(false);          // always reset spinner + laser
  }
}

function showStored(result) {
  currentResult = result;
  renderResult(result);
  show($("welcomePlaceholder"), false);
  show($("resultCard"), true);
  const rc = $("resultCard"); if (rc) rc.scrollIntoView({ behavior: "smooth", block: "start" });
}

function init() {
  const drop = $("dropZone"), input = $("fileInput");

  on($("browseBtn"), "click", e => { e.stopPropagation(); if (input) input.click(); });
  on(drop, "click", () => { if (input) input.click(); });
  on(input, "change", () => setFile(input.files && input.files[0]));

  ["dragenter", "dragover"].forEach(t => on(drop, t, e => { e.preventDefault(); drop.classList.add("dragover"); }));
  ["dragleave", "drop"].forEach(t => on(drop, t, e => { e.preventDefault(); drop.classList.remove("dragover"); }));
  on(drop, "drop", e => setFile(e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]));

  on($("sampleBtn"), "click", async e => {
    e.stopPropagation();
    try {
      const blob = await generateSampleLabel();
      const nameEl = $("productName");
      if (nameEl && !nameEl.value.trim()) nameEl.value = "Sample Masala Chips";
      setFile(new File([blob], "sample-label.png", { type: "image/png" }));
    } catch (err) { showError("Could not generate the sample label: " + err.message); }
  });

  on($("clearBtn"), "click", clearFile);
  on($("scanBtn"), "click", scan);
  on($("errorClose"), "click", hideError);

  on($("saveBtn"), "click", () => {
    if (!currentResult) return;
    saveToHistory(currentResult);
    refreshHistory();
  });
  on($("setABtn"), "click", () => { if (currentResult) setProduct(1, currentResult); });

  initCompare();
  refreshHistory();
}

function refreshHistory() {
  renderHistory({ restore: showStored, a: r => setProduct(1, r), b: r => setProduct(2, r) });
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
else init();
