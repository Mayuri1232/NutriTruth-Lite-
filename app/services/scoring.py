"""UK FSA traffic lights, Nutri-Score and the additives knowledge base."""
import re
from typing import Dict, List, Optional

# --------------------------------------------------------------------------- traffic lights
FSA_THRESHOLDS = {            # (low_max, moderate_max, unit)
    "fat": (3.0, 17.5, "g"),
    "sat_fat": (1.5, 5.0, "g"),
    "sugars": (5.0, 22.5, "g"),
    "sodium": (120.0, 600.0, "mg"),
}
LEVEL_COLOR = {"low": "green", "moderate": "amber", "high": "red", "unknown": "grey"}
TITLES = {"fat": "Total Fat", "sat_fat": "Saturated Fat", "sugars": "Total Sugars",
          "sodium": "Sodium", "protein": "Protein"}


def _light(key: str, value: Optional[float]) -> Dict:
    low, mod, unit = FSA_THRESHOLDS[key]
    ref = f"Low ≤ {low:g}{unit} · Moderate ≤ {mod:g}{unit} · High > {mod:g}{unit}"
    if value is None:
        return {"title": TITLES[key], "value": None, "unit": unit, "level": "unknown",
                "color": "grey", "label": "Not found", "reference": ref}
    level = "low" if value <= low else "moderate" if value <= mod else "high"
    return {"title": TITLES[key], "value": value, "unit": unit, "level": level,
            "color": LEVEL_COLOR[level], "label": level.capitalize(), "reference": ref}


def _protein_light(value: Optional[float]) -> Dict:
    ref = "High/Good ≥ 10g · Moderate 5–9.9g · Low < 5g"
    base = {"title": TITLES["protein"], "unit": "g", "reference": ref}
    if value is None:
        return {**base, "value": None, "level": "unknown", "color": "grey", "label": "Not found"}
    if value >= 10:
        return {**base, "value": value, "level": "high", "color": "green", "label": "High (good)"}
    if value >= 5:
        return {**base, "value": value, "level": "moderate", "color": "amber", "label": "Moderate"}
    # low protein is informational, not "bad" -> neutral grey rather than red
    return {**base, "value": value, "level": "low", "color": "grey", "label": "Low"}


def traffic_lights(n: Dict[str, Optional[float]]) -> Dict[str, Dict]:
    return {
        "fat": _light("fat", n.get("fat")),
        "sat_fat": _light("sat_fat", n.get("sat_fat")),
        "sugars": _light("sugars", n.get("sugars")),
        "sodium": _light("sodium", n.get("sodium_mg")),
        "protein": _protein_light(n.get("protein")),
    }


# --------------------------------------------------------------------------- Nutri-Score
_ENERGY_KJ = [335 * i for i in range(1, 11)]
_SUGARS = [4.5, 9, 13.5, 18, 22.5, 27, 31, 36, 40, 45]
_SAT = [float(i) for i in range(1, 11)]
_SODIUM = [90 * i for i in range(1, 11)]
_PROTEIN = [1.6, 3.2, 4.8, 6.4, 8.0]


def _pts(value: float, steps: List[float]) -> int:
    return sum(1 for s in steps if value > s)


def _grade(score: int) -> str:
    if score <= -1:
        return "A"
    if score <= 2:
        return "B"
    if score <= 10:
        return "C"
    if score <= 18:
        return "D"
    return "E"


def nutri_score(n: Dict[str, Optional[float]]) -> Dict:
    inputs = {"energy_kj": n.get("energy_kj"), "sat_fat": n.get("sat_fat"),
              "sugars": n.get("sugars"), "sodium_mg": n.get("sodium_mg"), "protein": n.get("protein")}
    missing = [k for k, v in inputs.items() if v is None]
    v = {k: (x if x is not None else 0.0) for k, x in inputs.items()}

    breakdown = {
        "energy": _pts(v["energy_kj"], _ENERGY_KJ),
        "sat_fat": _pts(v["sat_fat"], _SAT),
        "sugars": _pts(v["sugars"], _SUGARS),
        "sodium": _pts(v["sodium_mg"], _SODIUM),
    }
    negative = sum(breakdown.values())            # 0..40
    positive = _pts(v["protein"], _PROTEIN)       # 0..5
    score = negative - positive
    return {"grade": _grade(score), "score": score, "negative_points": negative,
            "positive_points": positive, "breakdown": breakdown,
            "missing_inputs": missing, "incomplete": bool(missing)}


# --------------------------------------------------------------------------- additives KB
def _ins(num: str) -> str:
    return rf"\b(?:ins|e)[\s\-\.]*(?:no\.?)?[\s\-]*{num}(?![0-9a-z])"


ADDITIVES = [
    {"code": "INS 621", "name": "Monosodium Glutamate (MSG)", "tier": "moderate",
     "patterns": [_ins("621"), r"\bmsg\b", r"monosodium\s+glutamate"],
     "purpose": "Flavour enhancer",
     "explanation": "Generally recognised as safe, but adds sodium and may cause headaches or flushing in sensitive people."},
    {"code": "INS 330", "name": "Citric Acid", "tier": "safe",
     "patterns": [_ins("330"), r"citric\s+acid"],
     "purpose": "Acidity regulator / preservative",
     "explanation": "Naturally occurring in citrus fruit; considered safe at food-use levels."},
    {"code": "—", "name": "Palm Oil", "tier": "moderate",
     "patterns": [r"palm\s*(?:oil|olein)", r"palmolein"],
     "purpose": "Cooking fat / texture",
     "explanation": "High in saturated fat, which raises LDL cholesterol when eaten often; also an environmental concern."},
    {"code": "INS 1400-1450", "name": "Maltodextrin", "tier": "moderate",
     "patterns": [r"maltodextrin"],
     "purpose": "Bulking agent / thickener",
     "explanation": "Highly processed carbohydrate with a high glycaemic index; can spike blood sugar."},
    {"code": "INS 551", "name": "Silicon Dioxide", "tier": "safe",
     "patterns": [_ins("551"), r"silicon\s+dioxide"],
     "purpose": "Anti-caking agent",
     "explanation": "Inert mineral used to keep powders free-flowing; considered safe at permitted levels."},
    {"code": "INS 150d", "name": "Caramel Colour IV (Sulphite Ammonia)", "tier": "moderate",
     "patterns": [_ins(r"150\s*\(?d\)?"), r"caramel\s+colou?r\s+(?:iv|4)\b"],
     "purpose": "Colour",
     "explanation": "Can contain trace 4-MEI, a by-product that is a potential carcinogen at high exposure; common in colas."},
    {"code": "INS 211", "name": "Sodium Benzoate", "tier": "moderate",
     "patterns": [_ins("211"), r"sodium\s+benzoate"],
     "purpose": "Preservative",
     "explanation": "Effective preservative; with vitamin C it may form traces of benzene, and it is linked to hyperactivity in some children."},
    {"code": "INS 202", "name": "Potassium Sorbate", "tier": "safe",
     "patterns": [_ins("202"), r"potassium\s+sorbate"],
     "purpose": "Preservative",
     "explanation": "One of the better-tolerated preservatives; rare skin or allergy reactions."},
    {"code": "INS 951", "name": "Aspartame", "tier": "caution",
     "patterns": [_ins("951"), r"aspartame"],
     "purpose": "Artificial sweetener",
     "explanation": "Must be avoided by people with phenylketonuria (PKU). Classed 'possibly carcinogenic' (IARC 2B) while staying within the accepted daily intake."},
    {"code": "INS 320 / 321", "name": "BHA / BHT", "tier": "caution",
     "patterns": [_ins("320"), _ins("321"), r"\bbha\b", r"\bbht\b", r"butylated\s+hydroxy(?:anisole|toluene)"],
     "purpose": "Antioxidant preservative",
     "explanation": "Synthetic antioxidants flagged in animal studies (BHA is 'possibly carcinogenic'); intake limits apply."},
    {"code": "INS 102", "name": "Tartrazine", "tier": "caution",
     "patterns": [_ins("102"), r"tartrazine"],
     "purpose": "Yellow synthetic colour",
     "explanation": "Azo dye linked to allergic reactions and hyperactivity in children; requires a warning label in the EU."},
    {"code": "INS 110", "name": "Sunset Yellow FCF", "tier": "caution",
     "patterns": [_ins("110"), r"sunset\s+yellow"],
     "purpose": "Orange synthetic colour",
     "explanation": "Azo dye associated with hyperactivity in children and rare allergic reactions."},
    {"code": "INS 122", "name": "Carmoisine", "tier": "caution",
     "patterns": [_ins("122"), r"carmoisine|azorubine"],
     "purpose": "Red synthetic colour",
     "explanation": "Azo dye linked to hyperactivity in some children; may trigger allergies."},
    {"code": "INS 129", "name": "Allura Red AC", "tier": "caution",
     "patterns": [_ins("129"), r"allura\s+red"],
     "purpose": "Red synthetic colour",
     "explanation": "Azo dye associated with hyperactivity in children."},
    {"code": "INS 950", "name": "Acesulfame Potassium", "tier": "moderate",
     "patterns": [_ins("950"), r"acesulfame"],
     "purpose": "Artificial sweetener",
     "explanation": "Approved sweetener; long-term effects are still debated, usually blended with other sweeteners."},
    {"code": "INS 955", "name": "Sucralose", "tier": "moderate",
     "patterns": [_ins("955"), r"sucralose"],
     "purpose": "Artificial sweetener",
     "explanation": "Approved, calorie-free sweetener; some research suggests effects on gut bacteria."},
    {"code": "INS 627 / 631 / 635", "name": "Ribonucleotides", "tier": "moderate",
     "patterns": [_ins("627"), _ins("631"), _ins("635"), r"ribonucleotides?"],
     "purpose": "Flavour enhancer",
     "explanation": "Taste boosters used with MSG; may aggravate gout in people prone to high uric acid."},
    {"code": "INS 250", "name": "Sodium Nitrite", "tier": "caution",
     "patterns": [_ins("250"), r"sodium\s+nitrite"],
     "purpose": "Curing agent / preservative",
     "explanation": "Can form nitrosamines, which are linked to cancer risk, particularly in processed meats."},
    {"code": "INS 223", "name": "Sodium Metabisulphite", "tier": "moderate",
     "patterns": [_ins("223"), r"sodium\s+meta\s*bisulph?ite"],
     "purpose": "Preservative / antioxidant",
     "explanation": "Sulphite that can trigger asthma and allergic reactions in sensitive people."},
    {"code": "INS 322", "name": "Lecithin", "tier": "safe",
     "patterns": [_ins("322"), r"lecithin"],
     "purpose": "Emulsifier",
     "explanation": "Natural emulsifier from soy or sunflower; considered safe (soy allergens possible)."},
    {"code": "INS 300", "name": "Ascorbic Acid (Vitamin C)", "tier": "safe",
     "patterns": [_ins("300"), r"ascorbic\s+acid"],
     "purpose": "Antioxidant",
     "explanation": "Vitamin C; safe and beneficial at food-use levels."},
    {"code": "INS 500", "name": "Sodium Bicarbonate", "tier": "safe",
     "patterns": [_ins("500"), r"sodium\s+(?:bi)?carbonate|baking\s+soda"],
     "purpose": "Raising agent",
     "explanation": "Baking soda; safe, though it adds a little sodium."},
]

_TIER_ORDER = {"caution": 0, "moderate": 1, "safe": 2}
_COMPILED = [(a, [re.compile(p, re.I) for p in a["patterns"]]) for a in ADDITIVES]


def detect_additives(raw_text: str) -> List[Dict]:
    text = raw_text.lower()
    found = []
    for add, regexes in _COMPILED:
        for rx in regexes:
            m = rx.search(text)
            if m:
                found.append({"code": add["code"], "name": add["name"], "tier": add["tier"],
                              "purpose": add["purpose"], "explanation": add["explanation"],
                              "matched": m.group(0).strip()})
                break
    found.sort(key=lambda a: (_TIER_ORDER[a["tier"]], a["name"]))
    return found
