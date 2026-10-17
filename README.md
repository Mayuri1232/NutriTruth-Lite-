# 🥗 NutriTruth Lite

Food-label scanner & nutritional assessment web app.
**FastAPI** · **OpenCV** · **Tesseract OCR** · **Bootstrap 5** · vanilla JS

Upload (or photograph) a nutrition table / ingredient list and get:
UK FSA traffic lights, an official-style Nutri-Score (A–E), additive (INS / E-number) risk ratings,
side-by-side product comparison and a local scan history. Parses FSSAI, US FDA and UK/EU label layouts.

## 1. Install Tesseract (system binary – required)

| OS | Command |
|----|---------|
| Windows | Installer from <https://github.com/UB-Mannheim/tesseract/wiki> (default path is auto-detected) |
| macOS | `brew install tesseract` |
| Ubuntu / Debian | `sudo apt-get install tesseract-ocr` |
| Fedora | `sudo dnf install tesseract` |

Non-standard location? Set `TESSERACT_CMD` to the full path of the binary.

## 2. Run

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                      # or: uvicorn app.main:app --reload
```
Open <http://127.0.0.1:8000> and click **Try Sample Label** for an instant demo.
The console prints `Tesseract binary resolved to: ...` at startup.

## 3. Tests

```bash
pytest -q
```

## Layout

```
app/main.py              entry point, CORS, static mount, global JSON error handler
app/config.py            Tesseract discovery, limits (1600 px, 10 s OCR timeout)
app/services/ocr.py      OpenCV resize + bilateral filter, 2-pass Tesseract (grayscale, then Otsu fallback)
app/services/parser.py   label-agnostic nutrient parser
app/services/scoring.py  FSA traffic lights, Nutri-Score, additives knowledge base
app/routes/api.py        GET /api/health, POST /api/analyze  (sync def -> runs in worker thread-pool)
templates/index.html     Jinja2 page
static/js/*.js           ES-module client (api, sample, render, history, compare, main)
static/vendor/           Bootstrap 5.3.3 bundled locally (works offline)
```

## Notes
* Nutri-Score uses the simplified formula from the spec: `N (energy, sat. fat, sugars, sodium) − P (protein)`.
* Low protein is shown grey (informational) rather than red.
* Salt → sodium uses 400 mg sodium per 1 g salt.
* Educational tool, not medical advice. OCR can misread labels.
