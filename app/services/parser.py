"""Universal nutrient parser (FSSAI / US FDA / UK-EU label layouts).

Strategy: lowercase the OCR text, split into lines, find every nutrient *label* on a
line, and give each label the text up to the next label as its "segment". The first
sensible number in that segment is the value; the unit may sit after the number
("12g"), in parentheses before it ("Total Fat (g) : 28.0") or be absent (table header).
"""
import re
from typing import Dict, List, Optional, Tuple

NUTRIENT_KEYS = ["energy_kcal", "energy_kj", "fat", "sat_fat", "carbs", "sugars", "protein", "sodium_mg"]

SALT_TO_SODIUM_MG = 400.0   # 1 g salt ~ 400 mg sodium
KJ_PER_KCAL = 4.184

LABEL_RE = re.compile(
    r"""\b(?:
        (?P<trans>trans[\s\-]*fat(?:ty\s+acids)?)
      | (?P<unsat>(?:mono|poly)?[\s\-]*unsaturated(?:\s+fat)?)
      | (?P<sat>saturated\s+fat(?:ty\s+acids)?|saturates|saturated|sat\.?\s*fat)
      | (?P<fat>total\s+fat|fat)
      | (?P<sugars>total\s+sugars?|sugars?)
      | (?P<carbs>total\s+carbohydrates?|carbohydrates?|carbs?)
      | (?P<protein>proteins?)
      | (?P<sodium>sodium)
      | (?P<salt>salt)
      | (?P<energy>energy|calories)
      | (?P<fiber>dietary\s+fib(?:re|er)|fib(?:re|er))
      | (?P<chol>cholesterol)
    )(?![a-z])""",
    re.X,
)

NUM_RE = re.compile(
    r"(?<![\w.])(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>kcal|cal|kj|mg|grams?|gms?|g)?(?![a-z])\s*(?P<pct>%)?"
)
PAREN_UNIT_RE = re.compile(r"\(\s*(kcal|cal|kj|mg|g|gm|grams?)\s*\)")
CAL_FROM_FAT_RE = re.compile(r"calories\s+from\s+fat\s*[\d.]*")

GRAM_KEYS = {"fat", "sat", "sugars", "carbs", "protein"}
MAX_VALUE = {"fat": 100, "sat": 100, "sugars": 100, "carbs": 100, "protein": 100,
             "sodium": 50000, "salt": 100, "energy": 4000}
MAX_GAP = 40   # max characters allowed between a label and its number


def normalize_text(raw: str) -> str:
    text = raw.lower().replace("\u00a0", " ").replace("|", " ").replace("\t", " ").replace("µ", "u")
    text = re.sub(r"(?<=\d),(?=\d{1,2}(?!\d))", ".", text)   # 12,5 -> 12.5
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)      # 1,250 -> 1250
    text = re.sub(r"[._]{2,}", " ", text)                    # dot leaders "Fat ....... 14"
    return text


def _unit(u: Optional[str]) -> Optional[str]:
    if not u:
        return None
    if u in ("cal",):
        return "kcal"
    if u.startswith("g"):
        return "g"
    return u


def _numbers(segment: str, limit: int = 3) -> List[Tuple[float, Optional[str], int]]:
    """Return [(value, unit, start)] skipping percentages and 'per 100 g' style references."""
    out = []
    for m in NUM_RE.finditer(segment):
        if m.group("pct"):
            continue
        before = segment[max(0, m.start() - 8):m.start()]
        if re.search(r"per\s*$", before) or re.search(r"serving\s*$", before):
            continue
        out.append((float(m.group("num")), _unit(m.group("unit")), m.start()))
        if len(out) >= limit:
            break
    return out


def _label_segments(line: str):
    line = CAL_FROM_FAT_RE.sub("", line)
    line = re.split(r"\bincludes\b|\badded\s+sugars?", line, maxsplit=1)[0]
    matches = list(LABEL_RE.finditer(line))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
        yield m.lastgroup, line[m.end():end], i + 1 == len(matches)


def _resolve(key: str, segment: str) -> Optional[float]:
    """Turn a segment into a canonical value: energy -> handled separately, others -> g / mg."""
    nums = _numbers(segment)
    if not nums or nums[0][2] > MAX_GAP:
        return None
    paren = PAREN_UNIT_RE.search(segment[:nums[0][2]])
    paren_unit = _unit(paren.group(1)) if paren else None

    for value, unit, _ in nums:
        unit = unit or paren_unit
        if key in GRAM_KEYS:
            if unit in ("kcal", "kj"):
                continue
            val = value / 1000.0 if unit == "mg" else value
            if val <= MAX_VALUE[key]:
                return val
        elif key == "sodium":
            if unit in ("kcal", "kj"):
                continue
            if unit == "g":
                val = value * 1000.0
            elif unit == "mg":
                val = value
            else:  # unit absent: small decimals look like grams, everything else mg
                val = value * 1000.0 if (value < 5 and "." in str(value) and value != int(value)) else value
            if val <= MAX_VALUE["sodium"]:
                return val
        elif key == "salt":
            if unit in ("kcal", "kj"):
                continue
            val = value / 1000.0 if unit == "mg" else value
            if val <= MAX_VALUE["salt"]:
                return val
    return None


def _resolve_energy(segment: str) -> Dict[str, float]:
    nums = _numbers(segment, limit=4)
    res: Dict[str, float] = {}
    if not nums or nums[0][2] > MAX_GAP:
        return res
    paren = PAREN_UNIT_RE.search(segment[:nums[0][2]])
    paren_unit = _unit(paren.group(1)) if paren else None
    for idx, (value, unit, _) in enumerate(nums):
        unit = unit or (paren_unit if idx == 0 else None)
        if unit is None:
            unit = "kj" if value > 1000 else "kcal"
        if unit in ("kcal", "kj") and unit not in res and value <= MAX_VALUE["energy"] * (4.2 if unit == "kj" else 1):
            res[unit] = value
    return res


def parse_nutrients(raw_text: str) -> Dict[str, Optional[float]]:
    """Return the normalised nutrient dict (values None when not found)."""
    lines = normalize_text(raw_text).splitlines()
    found: Dict[str, float] = {}
    salt_g: Optional[float] = None

    for idx, line in enumerate(lines):
        for key, segment, is_last in _label_segments(line):
            if key not in GRAM_KEYS | {"sodium", "salt", "energy"}:
                continue
            # OCR often splits "Protein" and its number onto two lines
            if is_last and not _numbers(segment) and idx + 1 < len(lines):
                nxt = lines[idx + 1]
                if not LABEL_RE.search(nxt) and re.match(r"^\s*[\(\[]?\s*\d", nxt):
                    segment = segment + " " + nxt

            if key == "energy":
                for unit, val in _resolve_energy(segment).items():
                    found.setdefault("energy_" + unit, val)
                continue
            val = _resolve(key, segment)
            if val is None:
                continue
            if key == "salt":
                salt_g = salt_g if salt_g is not None else val
            else:
                name = {"sat": "sat_fat", "sodium": "sodium_mg"}.get(key, key)
                found.setdefault(name, val)

    if "sodium_mg" not in found and salt_g is not None:
        found["sodium_mg"] = salt_g * SALT_TO_SODIUM_MG
    if "energy_kcal" not in found and "energy_kj" in found:
        found["energy_kcal"] = found["energy_kj"] / KJ_PER_KCAL
    if "energy_kj" not in found and "energy_kcal" in found:
        found["energy_kj"] = found["energy_kcal"] * KJ_PER_KCAL

    return {k: (round(found[k], 2) if k in found else None) for k in NUTRIENT_KEYS}


def count_found(nutrients: Dict[str, Optional[float]]) -> int:
    return sum(1 for k in ("energy_kcal", "fat", "sat_fat", "carbs", "sugars", "protein", "sodium_mg")
               if nutrients.get(k) is not None)
