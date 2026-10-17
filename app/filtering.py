"""Column query semantics adapted from StudentManagement's profile table."""
from collections import Counter
import re


def matches(cells, search, rules, skip=None):
    query = search.strip().casefold()
    if query and query not in " ".join(str(value) for value in cells.values()).casefold():
        return False
    for cid, rule in rules.items():
        if cid == skip:
            continue
        raw = cells.get(cid, "")
        text, value = raw.strip().casefold(), rule.get("value", "").strip().casefold()
        mode = rule["mode"]
        if ((mode == "values" and raw not in rule["values"])
                or (mode == "contains" and value not in text)
                or (mode == "exact" and text != value)
                or (mode == "empty" and text)
                or (mode == "notempty" and not text)):
            return False
    return True


def options(sheet, search, rules, cid):
    counts = Counter(row.cells.get(cid, "") for row in sheet.rows
                     if matches(row.cells, search, rules, skip=cid))
    return sorted(counts.items(), key=lambda item: natural_key(item[0]))


def natural_key(text):
    return tuple((0, int(part)) if part.isdigit() else (1, part.casefold())
                 for part in re.split(r"(\d+)", text))


def next_record(visible, old_id, previous):
    if old_id in visible:
        return old_id
    if old_id in previous:
        position = previous.index(old_id)
        for rid in previous[position + 1:] + list(reversed(previous[:position])):
            if rid in visible:
                return rid
    return visible[0] if visible else None
