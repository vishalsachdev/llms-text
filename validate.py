#!/usr/bin/env python3
"""
validate.py — sanity-check llms.txt files against the llmstxt.org spec.

Checks:
  - File starts with a single H1 title (`# Name`).
  - An H1 is followed (after blank lines) by a blockquote summary (`> ...`).
  - Section headings are H2 (`## ...`); no H3+ used as section headers in llms.txt
    (llms-full.txt is allowed deeper headings since it embeds page content).
  - Link list items look like `- [text](http...)` (optionally `: description`).
  - No stray Markdown code fences.

Exit code 0 if all files pass, 1 otherwise.

Usage: ./validate.py [llms.txt llms-full.txt ...]   (defaults to both if present)
"""

import re
import sys
from pathlib import Path

H1_RE = re.compile(r"^#\s+\S")
H2_RE = re.compile(r"^##\s+\S")
HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
BLOCKQUOTE_RE = re.compile(r"^>\s*\S")
LINK_ITEM_RE = re.compile(r"^[-*]\s+\[[^\]]+\]\((https?://[^)]+)\)\s*(:\s*.+)?$")
LIST_ITEM_RE = re.compile(r"^[-*]\s+")


def validate(path, strict_headings):
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()
    errors = []

    def err(lineno, msg):
        errors.append(f"{path}:{lineno}: {msg}")

    if "```" in text:
        for i, ln in enumerate(lines, 1):
            if ln.lstrip().startswith("```"):
                err(i, "code fence found; llms.txt files should be plain markdown")

    # First non-blank line must be the H1.
    first_idx = next((i for i, ln in enumerate(lines) if ln.strip()), None)
    if first_idx is None:
        err(1, "file is empty")
        return errors
    if not H1_RE.match(lines[first_idx]):
        err(first_idx + 1, "file must start with an H1 title: `# Name`")

    h1_count = sum(1 for ln in lines if H1_RE.match(ln))
    if h1_count != 1:
        err(1, f"expected exactly one H1 title, found {h1_count}")

    # Blockquote summary should appear before the first H2.
    seen_blockquote = False
    for i, ln in enumerate(lines):
        if H2_RE.match(ln):
            break
        if BLOCKQUOTE_RE.match(ln):
            seen_blockquote = True
            break
    if not seen_blockquote:
        err(first_idx + 1, "missing blockquote summary (`> ...`) after the H1 title")

    # Heading-depth and link-format checks.
    for i, ln in enumerate(lines, 1):
        m = HEADING_RE.match(ln)
        if m and strict_headings and len(m.group(1)) >= 3:
            err(i, f"H{len(m.group(1))} heading in llms.txt; section headings must be H2")
        if LIST_ITEM_RE.match(ln) and "](" in ln and not LINK_ITEM_RE.match(ln.rstrip()):
            err(i, "list item with a link does not match `- [text](http...): description`")

    return errors


def main():
    args = sys.argv[1:]
    if not args:
        args = [p for p in ("llms.txt", "llms-full.txt") if Path(p).exists()]
    if not args:
        print("No files to validate (pass paths, or run where llms.txt lives).")
        sys.exit(1)

    all_errors = []
    for path in args:
        if not Path(path).exists():
            all_errors.append(f"{path}: not found")
            continue
        strict = Path(path).name == "llms.txt"
        file_errors = validate(path, strict_headings=strict)
        if file_errors:
            all_errors.extend(file_errors)
        else:
            print(f"✅ {path}: OK")

    if all_errors:
        print("\n".join(f"❌ {e}" for e in all_errors))
        sys.exit(1)
    print("All files valid.")


if __name__ == "__main__":
    main()
