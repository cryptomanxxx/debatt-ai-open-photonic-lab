"""Lightweight offline checks for changed research Markdown documents."""
import argparse
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
# Scope: ordinary inline Markdown links outside fenced code blocks.
LINK = re.compile(r"(?<!!)\[[^\]\n]+\]\(<?([^\s)>]+)>?(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


def validate(path, root=ROOT):
    errors = []
    lines = path.read_text(encoding="utf-8").splitlines()
    if not any(line.strip() for line in lines):
        return ["empty document"]
    fence = None
    heading = False
    for number, line in enumerate(lines, 1):
        m = FENCE.match(line)
        if m:
            marker = m.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence) and not line[m.end():].strip():
                fence = None
            continue
        if fence:
            continue
        if line.startswith("# ") and line[2:].strip():
            heading = True
        # Ignore inline code; only validate local path existence, not remote
        # availability, anchors, or scientific correctness.
        line = re.sub(r"`+[^`]+`+", "", line)
        for match in LINK.finditer(line):
            target = match.group(1)
            try:
                url = urlsplit(target)
            except ValueError:
                errors.append(f"line {number}: invalid link {target}")
                continue
            if url.scheme or url.netloc or not url.path:
                continue
            relative = unquote(url.path)
            dest = ((root / relative.lstrip("/")) if relative.startswith("/")
                    else (path.parent / relative)).resolve()
            if not dest.is_relative_to(root.resolve()) or not dest.exists():
                errors.append(f"line {number}: missing or outside-repository target {target}")
    if fence:
        errors.append("unclosed fenced code block")
    if not heading:
        errors.append("missing top-level heading")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="PR base commit; check added/modified research Markdown only")
    args = parser.parse_args()
    if args.base:
        raw = subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=AM", "--no-renames", "-z",
             args.base + "...HEAD", "--", "research/"], cwd=ROOT)
        paths = [ROOT / p for p in raw.decode("utf-8").split("\0") if p.endswith(".md")]
    else:
        paths = sorted((ROOT / "research").rglob("*.md"))
    failures = 0
    for path in paths:
        for error in validate(path):
            failures += 1
            print(f"{path.relative_to(ROOT)}: {error}")
    print(f"Checked {len(paths)} research documents; {failures} errors")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
