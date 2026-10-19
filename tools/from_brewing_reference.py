"""Builds teas.json for Tea Timer from the Tea Brewing Reference (Obsidian Markdown).

The reference has one Western and one Gongfu section; each tea has tables per vessel
(1L batch, 350 ml cup, 90 ml gaiwan, 60 ml gaiwan) with min/mid/max times per infusion.
They become:

    type > tea > method ("Gongfu 90 ml", ...) > strength (Light / Medium / Strong)

Medium uses the "Ideal (mid)" time where the reference gives one: the mid times were
rounded to fit a slot timer, which Tea Timer doesn't need.

Usage:
    python tools/from_brewing_reference.py "path/to/Tea Brewing Reference.md" [-o teas.json]
"""

import argparse
import json
import re
from pathlib import Path

METHOD_NAMES = {
    "90 ml gaiwan": "Gongfu 90 ml",
    "60 ml gaiwan": "Gongfu 60 ml",
    "350 ml cup": "Western 350 ml",
    "1L batch": "Western 1 L",
}
METHOD_ORDER = list(METHOD_NAMES.values())

# "**1L batch: 9 tsp (~18 g)** (light 7 / strong 11). Note" or "**60 ml gaiwan**: not recommended. ..."
AMOUNT_RE = re.compile(
    r"^\*\*(?P<vessel>" + "|".join(re.escape(v) for v in METHOD_NAMES) + r")(?::\s*(?P<amount>[^*]+))?\*\*:?\s*(?P<rest>.*)$"
)
LEAF_VARIANTS_RE = re.compile(r"^\((?P<variants>[^)]*)\)\.?\s*(?P<rest>.*)$")
INDEX_LINK_RE = re.compile(r"\[\[#(?P<part>Western|Gongfu)#(?P<section>[^#]+)#(?P<heading>[^\]|\\]+)")
TIME_RE = re.compile(r"^\d+:\d{2}$")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
DERIVED = " (Derived schedule)"


def plain(text: str) -> str:
    """Markdown links -> their text, since the app shows notes as plain text."""
    return MARKDOWN_LINK_RE.sub(r"\1", text).strip()


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_index(lines: list[str]) -> list[dict]:
    """The Index table: type, short tea name and the headings of its Western/Gongfu parts."""
    teas = []
    in_index = False
    for line in lines:
        if line.startswith("## "):
            in_index = line.strip() == "## Index"
            continue
        if not in_index or not line.startswith("|"):
            continue
        row = cells(line)
        if row[0] in ("Type", "---") or len(row) < 4:
            continue
        links = {m["part"]: m["heading"] for m in INDEX_LINK_RE.finditer(line)}
        teas.append({"type": row[0], "name": row[1], "western": links.get("Western"), "gongfu": links.get("Gongfu")})
    return teas


def parse_blocks(lines: list[str]) -> dict:
    """Every "#### tea" block under "## Western" / "## Gongfu", keyed by (part, heading)."""
    blocks = {}
    part = section = None
    current = None
    for line in lines:
        if line.startswith("## "):
            part, section, current = line[3:].strip(), None, None
        elif line.startswith("### "):
            section, current = line[4:].strip(), None
        elif line.startswith("#### ") and part in ("Western", "Gongfu"):
            current = {"section": section, "lines": []}
            blocks[(part, line[5:].strip())] = current
        elif current is not None:
            current["lines"].append(line)
    return blocks


def parse_infusion(row: dict) -> dict:
    times = row["Time (min/mid/max)"].split("/")
    if len(times) != 3 or not all(TIME_RE.match(t) for t in times):
        raise ValueError(f"Unexpected times: {row}")
    light, medium, strong = times
    ideal = row.get("Ideal (mid)", "")
    if TIME_RE.match(ideal):
        medium = ideal
    infusion = {"temp": row["Temp"], "light": light, "medium": medium, "strong": strong}
    if "optional" in row["#"]:
        infusion["optional"] = True
    return infusion


def parse_block(block: dict) -> tuple[str, list[dict]]:
    """A tea block -> (its intro note, its methods)."""
    intro = []
    methods = []
    method = None
    header = None
    for line in block["lines"]:
        stripped = line.strip()
        if match := AMOUNT_RE.match(stripped):
            amount = (match["amount"] or "").strip()
            rest = match["rest"].strip()
            if variants := LEAF_VARIANTS_RE.match(rest):
                amount = f"{amount} · {variants['variants']}"
                rest = variants["rest"]
            method = {"name": METHOD_NAMES[match["vessel"]], "amount": amount, "note": rest.lstrip(". ").strip(), "infusions": []}
            methods.append(method)
            header = None
        elif stripped.startswith("|"):
            row = cells(stripped)
            if header is None:
                header = row
            elif set(stripped) <= set("|- "):
                continue
            elif method is not None:
                method["infusions"].append(parse_infusion(dict(zip(header, row))))
        elif stripped and method is None:
            intro.append(stripped)
    methods = [m for m in methods if m["infusions"]]
    for method in methods:
        method["note"] = plain(method["note"])
    return plain(" ".join(intro)), methods


def build(markdown: str) -> list[dict]:
    lines = markdown.splitlines()
    blocks = parse_blocks(lines)
    teas = []
    for entry in parse_index(lines):
        tea = {"type": entry["type"], "name": entry["name"], "methods": []}
        if entry["western"]:
            note, methods = parse_block(blocks[("Western", entry["western"])])
            if note:
                tea["note"] = note
            tea["methods"] += methods
        if entry["gongfu"]:
            block = blocks[("Gongfu", entry["gongfu"])]
            note, methods = parse_block(block)
            prefix = []
            if entry["gongfu"].endswith(DERIVED):
                prefix.append("Derived schedule, not brewed yet.")
            if block["section"] == "Borderline fits":
                prefix.append("Borderline gongfu fit: western is the better default.")
            for method in methods:
                method["note"] = " ".join(prefix + [note, method["note"]]).strip()
            tea["methods"] += methods
        tea["methods"].sort(key=lambda m: METHOD_ORDER.index(m["name"]))
        for method in tea["methods"]:
            if not method["note"]:
                del method["note"]
            if not method["amount"]:
                del method["amount"]
        teas.append(tea)
    return teas


TEST_TEA = {
    "type": "Test",
    "name": "Quick test",
    "note": "For checking the alarm quickly.",
    "methods": [{
        "name": "5 s steps",
        "infusions": [
            {"temp": "–", "light": "0:05", "medium": "0:05", "strong": "0:05"},
            {"temp": "–", "light": "0:05", "medium": "0:05", "strong": "0:10"},
            {"temp": "–", "light": "0:05", "medium": "0:10", "strong": "0:15", "optional": True},
        ],
    }],
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("reference", type=Path, help="Tea Brewing Reference.md")
    parser.add_argument("-o", "--out", type=Path, default=Path("teas.json"))
    args = parser.parse_args()

    markdown = args.reference.read_text(encoding="utf-8")
    teas = build(markdown)
    teas.append(TEST_TEA)
    stand = re.search(r"^(\w{3} \d{1,2}, \d{4})", markdown, re.MULTILINE)
    data = {"version": 2, "updated": stand[1] if stand else None, "teas": teas}
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    methods = sum(len(t["methods"]) for t in teas)
    print(f"{len(teas)} teas, {methods} methods -> {args.out}")


if __name__ == "__main__":
    main()
