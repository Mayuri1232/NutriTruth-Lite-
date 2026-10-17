// Network layer: 15 s timeout, text-first parsing, readable errors.
const TIMEOUT_MS = 15000;

function messageFrom(data, text, res) {
  if (data && data.detail) {
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) return data.detail.map(d => d.msg || JSON.stringify(d)).join("; ");
  }
  const snippet = (text || "").trim().slice(0, 300);
  return snippet ? `Server error ${res.status}: ${snippet}` : `Server error ${res.status} ${res.statusText}`;
}

export async function analyzeImage(file, productName) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const form = new FormData();
    form.append("file", file, file.name || "label.png");
    form.append("product_name", productName || "");
    const res = await fetch("/api/analyze", { method: "POST", body: form, signal: controller.signal });

    const text = await res.text();               // always read as text first
    let data = null;
    try { data = JSON.parse(text); } catch (_) { /* not JSON */ }

    if (!res.ok) throw new Error(messageFrom(data, text, res));
    if (!data) throw new Error("The server returned a non-JSON response: " + text.slice(0, 200));
    return data;
  } catch (err) {
    if (err && err.name === "AbortError") {
      throw new Error("The request timed out after 15 seconds. Try a smaller or clearer photo.");
    }
    if (err instanceof TypeError) {
      throw new Error("Could not reach the server. Is it still running?");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}
