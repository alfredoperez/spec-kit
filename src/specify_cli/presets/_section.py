"""Section replacement for the ``replace-section`` template strategy.

A section is an ATX heading line plus the body that follows it, up to the
next heading of the same or higher level (or the end of the text). Heading
lines inside fenced code blocks are not headings.
"""

from __future__ import annotations

import re

from ._manifest import PresetValidationError

_HEADING_RE = re.compile(r"^(#{1,6})(?:[ \t]+(.*))?$")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def _scan_headings(lines: list[str]) -> list[tuple[int, int, str]]:
    """Return ``(line_index, level, title)`` for each heading outside fences."""
    headings: list[tuple[int, int, str]] = []
    fence: str | None = None
    for index, raw in enumerate(lines):
        line = raw.rstrip("\r\n")
        fence_match = _FENCE_RE.match(line)
        if fence is not None:
            if (
                fence_match
                and fence_match.group(1)[0] == fence[0]
                and len(fence_match.group(1)) >= len(fence)
                and not fence_match.group(2).strip()
            ):
                fence = None
            continue
        if fence_match:
            fence = fence_match.group(1)
            continue
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            title = (heading_match.group(2) or "").strip()
            headings.append((index, len(heading_match.group(1)), title))
    return headings


def replace_section(text: str, section: str, body: str, source: str) -> str:
    """Replace the body of the one section titled *section*, keeping its heading.

    Raises ``PresetValidationError`` naming the section and listing the
    template's headings when no heading, or more than one, matches.
    """
    lines = text.splitlines(keepends=True)
    headings = _scan_headings(lines)
    wanted = section.strip()
    matches = [h for h in headings if h[2] == wanted]
    if len(matches) != 1:
        problem = "not found" if not matches else f"matches {len(matches)} headings"
        available = ", ".join(
            f"{'#' * level} {title}" for _, level, title in headings
        ) or "none"
        raise PresetValidationError(
            f"replace-section in '{source}': section '{wanted}' {problem} "
            f"in the template. Headings: {available}"
        )

    index, level, _ = matches[0]
    end = len(lines)
    for later_index, later_level, _ in headings:
        if later_index > index and later_level <= level:
            end = later_index
            break

    head = "".join(lines[: index + 1])
    if not head.endswith("\n"):
        head += "\n"
    new_body = body.strip("\r\n")
    result = head + ("\n" + new_body + "\n" if new_body else "")
    if end < len(lines):
        result += "\n" + "".join(lines[end:])
    return result
