# SPDX-FileCopyrightText: 2026 Ben Balter
# SPDX-License-Identifier: MIT
"""
A searchable catalog of the actions a stock Furby Connect can play.

The catalog is bluefluff's community transcription of each action
(data/actionlist.md, from https://github.com/Jeija/bluefluff, MIT, see
data/BLUEFLUFF-LICENSE.md), read as it is rather than copied into code, so
updating it means replacing that one file. A row whose code lists several
values ("37|0|2,3|0" or "24|7|0|0 - 7") plays a line like it at each of them.
"""

import functools
import itertools
import re
from importlib import resources

WORD = re.compile(r"[a-z0-9']+")


def values_in(cell):
    """The values a code cell lists: "2,3" → [2, 3], "0 - 3" → [0, 1, 2, 3]."""
    values = []
    for part in cell.split(","):
        low, _, high = part.partition("-")
        values.extend(range(int(low), int(high or low) + 1))
    return values


def parse(text):
    """[{"action": [i, x, s, p], "alternatives": [...], "category", "says"}] from actionlist.md."""
    actions, category = [], None
    for line in text.splitlines():
        if line.startswith("## "):
            category = line[3:].strip()
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if category is None or len(cells) != 5 or not cells[0][:1].isdigit():
            continue
        try:
            values = [values_in(cell) for cell in cells[:4]]
        except ValueError:  # "x": bluefluff left it out
            continue
        codes = [list(code) for code in itertools.product(*values)]
        actions.append(
            {
                "action": codes[0],
                "alternatives": codes[1:],
                "category": re.sub(r"^[\d\s,-]+-\s*", "", category),
                "says": cells[4],
            }
        )
    return actions


@functools.cache
def catalog():
    return parse(resources.files(__package__).joinpath("data/actionlist.md").read_text(encoding="utf-8"))


def find(query="", input=None, limit=25):
    """Actions whose category or transcription contain every word of query, best match first."""
    words = WORD.findall(query.lower())
    matches = []
    for entry in catalog():
        if input is not None and entry["action"][0] != input:
            continue
        haystack = f"{entry['category']} {entry['says']}".lower()
        if all(w in haystack for w in words):
            # Rank whole-word hits in what the Furby says above partial ones and category-only ones
            says = set(WORD.findall(entry["says"].lower()))
            matches.append((-sum(w in says for w in words), len(matches), entry))
    matches.sort(key=lambda m: m[:2])
    return [m[2] for m in matches[:limit]], len(matches)


def describe(action):
    """The catalog entry for an action code, or None if bluefluff didn't transcribe it."""
    code = list(action)
    for entry in catalog():
        if entry["action"] == code or code in entry["alternatives"]:
            return entry
    return None
