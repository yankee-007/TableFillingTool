"""Adapted from StudentManagement contact_match; has no source-project dependency."""
from __future__ import annotations

from .data import Sheet


def _word_character(character: str) -> bool:
    return character.isalnum() or "\u3400" <= character <= "\u9fff"


def name_in_title(name: str, title: str) -> bool:
    name, title = str(name or "").strip(), str(title or "").strip()
    if not name or title.casefold() in ("企业微信", "wecom", "wxwork"):
        return False
    # Chinese names must not match part of another name; Latin names also need boundaries.
    start = 0
    while (index := title.casefold().find(name.casefold(), start)) != -1:
        end = index + len(name)
        left = title[index - 1] if index else ""
        right = title[end] if end < len(title) else ""
        han_name = any("\u3400" <= ch <= "\u9fff" for ch in name)
        if han_name:
            blocked = (left and "\u3400" <= left <= "\u9fff") or (right and "\u3400" <= right <= "\u9fff")
        else:
            blocked = (left and _word_character(left)) or (right and _word_character(right))
        if not blocked:
            return True
        start = index + 1
    return False


def candidates(sheets: list[Sheet], title: str, scope: str = "") -> list[tuple[str, str]]:
    if not title or title.casefold() in ("企业微信", "wecom", "wxwork"):
        return []
    precise, fallback = [], []
    compact_title = "".join(title.split())
    for sheet in sheets:
        if scope and sheet.id != scope:
            continue
        for row in sheet.rows:
            name = sheet.name(row)
            remark = row.cells.get(sheet.settings.get("remark_column", ""), "").strip()
            prefix = sheet.settings.get("prefix", "").strip() if sheet.settings.get("use_prefix", True) else ""
            key = (sheet.id, row.id)
            if (remark and name_in_title("".join(remark.split()), compact_title)) or (
                name and prefix and name_in_title("".join((prefix + name).split()), compact_title)
            ):
                precise.append(key)
            elif name and name_in_title(name, title):
                fallback.append(key)
    return precise or fallback
