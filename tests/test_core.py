import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.main import app
from app.services.parser import parse_nutrients
from app.services.scoring import detect_additives, nutri_score, traffic_lights

client = TestClient(app, raise_server_exceptions=False)


def test_fssai_format():
    n = parse_nutrients("Energy (kcal) : 520\nTotal Fat (g) : 28.0\nProtein (g) : 6.8\nSodium (mg) : 640")
    assert (n["energy_kcal"], n["fat"], n["protein"], n["sodium_mg"]) == (520, 28, 6.8, 640)


def test_fda_format_ignores_percent_and_added_sugars():
    n = parse_nutrients("Calories 250\nTotal Fat 12g 15%\nSodium 470mg 20%\nTotal Sugars 5g\nIncludes 4g Added Sugars 8%")
    assert n["fat"] == 12 and n["sodium_mg"] == 470 and n["sugars"] == 5


def test_uk_inline_saturates_and_commas():
    n = parse_nutrients("Fat: 14g of which saturates 2.5g\nCarbohydrate 45,5g of which sugars 12,5g")
    assert n["fat"] == 14 and n["sat_fat"] == 2.5 and n["carbs"] == 45.5 and n["sugars"] == 12.5


def test_salt_and_sodium_grams_conversion():
    assert parse_nutrients("Salt 1.5g")["sodium_mg"] == 600
    assert parse_nutrients("Sodium 0.5 g")["sodium_mg"] == 500


def test_table_header_units():
    n = parse_nutrients("Total Fat ........ 14\nProtein\n6.2")
    assert n["fat"] == 14 and n["protein"] == 6.2


def test_traffic_lights_boundaries():
    t = traffic_lights({"fat": 3.0, "sat_fat": 5.1, "sugars": 22.5, "sodium_mg": 601, "protein": 10})
    assert [t[k]["color"] for k in ("fat", "sat_fat", "sugars", "sodium", "protein")] == \
        ["green", "red", "amber", "red", "green"]


def test_nutri_score_extremes():
    best = nutri_score({"energy_kj": 100, "sat_fat": 0, "sugars": 0, "sodium_mg": 0, "protein": 10})
    worst = nutri_score({"energy_kj": 4000, "sat_fat": 20, "sugars": 60, "sodium_mg": 1500, "protein": 0})
    assert best["grade"] == "A" and worst["grade"] == "E" and worst["negative_points"] == 40


def test_additives():
    names = {a["name"] for a in detect_additives("Citric Acid (INS 330), E621, Palm Oil, BHT, INS 150d")}
    assert {"Citric Acid", "Palm Oil", "BHA / BHT"} <= names
    assert any("MSG" in n for n in names) and any("Caramel" in n for n in names)


def _png(lines):
    img = Image.new("RGB", (1000, 80 * len(lines) + 80), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 46)
    except OSError:
        font = ImageFont.load_default()
    for i, ln in enumerate(lines):
        d.text((50, 40 + i * 80), ln, fill="black", font=font)
    buf = io.BytesIO(); img.save(buf, "PNG"); return buf.getvalue()


def test_index_and_health():
    assert client.get("/").status_code == 200
    assert "tesseract" in client.get("/api/health").json()


def test_analyze_end_to_end():
    png = _png(["Nutrition Facts", "Energy (kcal) : 520", "Total Fat (g) : 28.0", "Protein (g) : 6.8",
                "Sodium (mg) : 640", "Ingredients: Palm Oil, INS 621"])
    r = client.post("/api/analyze", files={"file": ("l.png", png, "image/png")}, data={"product_name": "T"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["nutrients"]["fat"] == 28 and body["nutri_score"]["grade"] in "ABCDE"
    assert any(a["name"] == "Palm Oil" for a in body["additives"])


def test_422_when_no_nutrients_and_no_mock_values():
    png = _png(["The quick brown fox jumps over", "the lazy dog again and again"])
    r = client.post("/api/analyze", files={"file": ("l.png", png, "image/png")})
    assert r.status_code == 422 and "detail" in r.json()


def test_bad_file_is_clean_json():
    r = client.post("/api/analyze", files={"file": ("x.png", b"not an image", "image/png")})
    assert r.status_code == 400 and "detail" in r.json()


def test_missing_tesseract_returns_json_500(monkeypatch):
    import pytesseract
    from app.services import ocr

    def boom(*a, **k):
        raise pytesseract.TesseractNotFoundError()
    monkeypatch.setattr(ocr.pytesseract, "image_to_string", boom)
    r = client.post("/api/analyze", files={"file": ("l.png", _png(["hello"]), "image/png")})
    assert r.status_code == 500 and "Tesseract" in r.json()["detail"]
