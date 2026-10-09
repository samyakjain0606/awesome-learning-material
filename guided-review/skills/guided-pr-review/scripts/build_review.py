#!/usr/bin/env python3
"""Build the guided review page from pr.json + guide.json.

Usage:
  build_review.py REVIEW_DIR

Reads REVIEW_DIR/pr.json and REVIEW_DIR/guide.json, fetches any
guide.context_files at the PR head, and writes REVIEW_DIR/review.html.
Exits non-zero with a list of problems when guide.json doesn't fit the PR.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_pr import Source, lang_for  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "template.html")
TIERS = {"core", "supporting", "wiring", "data", "tests", "generated", "docs"}
CONTEXT_BUDGET = 2_000_000
MAX_PAGE = 15_000_000


KINDS = {"flow", "state", "sequence", "schema"}
STATUSES = {None, "same", "added", "changed", "removed"}


def diagrams_of(c):
    d = c.get("diagrams")
    if d is None and c.get("diagram"):
        d = c["diagram"]
    if isinstance(d, dict):
        d = [d]
    c["diagrams"] = d or []
    c.pop("diagram", None)
    return c["diagrams"]


def check_diagram(dg, where, n_chapters, errors, warns):
    kind = dg.get("kind")
    if kind not in KINDS:
        errors.append(f"{where}: kind must be one of {sorted(KINDS)}, got {kind!r}")
        return

    def chapter_ok(item, label):
        ch = item.get("chapter")
        if ch is not None and not (isinstance(ch, int) and 1 <= ch <= n_chapters):
            warns.append(f"{where}: {label} points at chapter {ch!r}, which doesn't exist")
            item.pop("chapter", None)
        if item.get("status") not in STATUSES:
            warns.append(f"{where}: {label} status {item.get('status')!r} should be added, changed, removed or same")

    if kind in ("flow", "state"):
        ids = [n.get("id") for n in dg.get("nodes", [])]
        if not ids:
            errors.append(f"{where}: no nodes")
        if len(ids) != len(set(ids)):
            errors.append(f"{where}: node ids must be unique")
        for n in dg.get("nodes", []):
            chapter_ok(n, f"node {n.get('id')!r}")
        for e in dg.get("edges", []):
            if e.get("from") not in ids or e.get("to") not in ids:
                errors.append(f"{where}: edge {e.get('from')!r} -> {e.get('to')!r} uses an unknown node id")
        if kind == "state" and dg.get("start") and dg["start"] not in ids:
            errors.append(f"{where}: start {dg['start']!r} is not a node id")
    elif kind == "sequence":
        ids = [a.get("id") for a in dg.get("actors", [])]
        if len(ids) < 2:
            errors.append(f"{where}: a sequence needs at least two actors")
        for a in dg.get("actors", []):
            chapter_ok(a, f"actor {a.get('id')!r}")
        for k, s in enumerate(dg.get("steps", []), 1):
            if "from" in s or "to" in s:
                if s.get("from") not in ids or s.get("to") not in ids:
                    errors.append(f"{where}: step {k} uses an unknown actor ({s.get('from')!r} -> {s.get('to')!r})")
                chapter_ok(s, f"step {k}")
            elif "note" in s:
                if any(x not in ids for x in s.get("over", [])):
                    errors.append(f"{where}: note in step {k} is over an unknown actor")
            elif "divider" not in s:
                errors.append(f"{where}: step {k} needs from/to, note or divider")
    elif kind == "schema":
        names = [e.get("name") for e in dg.get("entities", [])]
        if not names:
            errors.append(f"{where}: no entities")
        for e in dg.get("entities", []):
            chapter_ok(e, f"entity {e.get('name')!r}")
            for fld in e.get("fields", []):
                if fld.get("status") not in STATUSES:
                    warns.append(f"{where}: field {e.get('name')}.{fld.get('name')} has unknown status")
        for l in dg.get("links", []):
            if l.get("from") not in names or l.get("to") not in names:
                errors.append(f"{where}: link {l.get('from')!r} -> {l.get('to')!r} uses an unknown entity")


def test_note(f):
    names = f.get("tests") or []
    if not names:
        return None
    shown = ", ".join(f"`{n}`" for n in names[:5])
    return f"{len(names)} tests: {shown}" + (f" and {len(names) - 5} more" if len(names) > 5 else "")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    d = sys.argv[1]
    pr = json.load(open(os.path.join(d, "pr.json")))
    guide = json.load(open(os.path.join(d, "guide.json")))
    paths = {f["path"] for f in pr["files"]}
    errors, warns = [], []

    chapters = guide.get("chapters") or []
    if not chapters:
        errors.append("guide.chapters is empty")
    seen = {}
    for i, c in enumerate(chapters, 1):
        if not c.get("title"):
            errors.append(f"chapter {i} has no title")
        if c.get("tier") and c["tier"] not in TIERS:
            warns.append(f"chapter {i}: unknown tier {c['tier']!r} (use one of {sorted(TIERS)})")
        if isinstance(c.get("explain"), str):
            c["explain"] = [c["explain"]]
        files = []
        for cf in c.get("files") or []:
            cf = {"path": cf} if isinstance(cf, str) else cf
            p = cf.get("path")
            if p not in paths:
                errors.append(f"chapter {i}: {p!r} is not a file in this PR")
                continue
            if p in seen:
                warns.append(f"{p} is in chapters {seen[p]} and {i}; keeping it in {seen[p]}")
                continue
            seen[p] = i
            files.append(cf)
        c["files"] = files
        for w in c.get("watch") or []:
            if w.get("path") and w["path"] not in paths:
                warns.append(f"chapter {i}: watch item points at {w['path']!r}, which isn't in the PR")
                w.pop("line", None)
            if w.get("level") not in (None, "risk", "question", "nit"):
                warns.append(f"chapter {i}: watch level {w.get('level')!r} should be risk, question or nit")

    for i, c in enumerate(chapters, 1):
        for j, dg in enumerate(diagrams_of(c), 1):
            check_diagram(dg, f"chapter {i} diagram {j}", len(chapters), errors, warns)
    for j, dg in enumerate(guide.get("diagrams") or [], 1):
        check_diagram(dg, f"diagrams[{j}]", len(chapters), errors, warns)

    # Tests and generated files are kept on the page but not reviewed: they get
    # their own chapters at the end unless the guide placed them already.
    by_path = {f["path"]: f for f in pr["files"]}
    left = [f for f in pr["files"] if f["path"] not in seen]
    tests = [f for f in left if f["kind"] == "test"]
    generated = [f for f in left if f["kind"] == "generated"]
    other = [f for f in left if f["kind"] not in ("test", "generated")]
    if other:
        warns.append(f"{len(other)} files not in any chapter, added to 'Everything else': "
                     + ", ".join(f["path"] for f in other[:8]) + (" …" if len(other) > 8 else ""))
        chapters.append({
            "title": "Everything else",
            "tier": "wiring",
            "explain": ["Files the guide didn't place in a chapter."],
            "files": [{"path": f["path"]} for f in other],
        })
    if tests:
        n_cases = sum(len(f.get("tests") or []) for f in tests)
        chapters.append({
            "title": "Tests",
            "tier": "tests",
            "kept": True,
            "explain": [
                f"{len(tests)} test files, {n_cases} test cases, +{sum(f['add'] for f in tests)} "
                f"−{sum(f['del'] for f in tests)} lines. Kept here for completeness and not reviewed in this guide.",
                "Ask about them if you want to know what a case covers or what's missing.",
            ],
            "files": [{"path": f["path"], "note": test_note(f)} for f in tests],
            "ask": ["What do these tests cover, and which behaviour in the core chapters has no test?"],
        })
    if generated:
        chapters.append({
            "title": "Generated files",
            "tier": "generated",
            "kept": True,
            "explain": ["Lock files, snapshots and other generated output. Kept for completeness and not reviewed; review whatever produces them instead."],
            "files": [{"path": f["path"]} for f in generated],
        })
    for c in chapters:
        if c.get("tier") in ("tests", "generated") and all(by_path[cf["path"]]["kind"] in ("test", "generated") for cf in c["files"]):
            c["kept"] = True
    guide["chapters"] = chapters

    flow = guide.get("flow")
    if flow:
        ids = [n.get("id") for n in flow.get("nodes", [])]
        if len(ids) != len(set(ids)):
            errors.append("flow node ids must be unique")
        for n in flow.get("nodes", []):
            ch = n.get("chapter")
            if ch is not None and not (isinstance(ch, int) and 1 <= ch <= len(chapters)):
                warns.append(f"flow node {n.get('id')!r} points at chapter {ch!r}, which doesn't exist")
                n.pop("chapter", None)
        for e in flow.get("edges", []):
            if e.get("from") not in ids or e.get("to") not in ids:
                errors.append(f"flow edge {e.get('from')!r} -> {e.get('to')!r} uses an unknown node id")

    if errors:
        print("guide.json doesn't fit the PR:")
        for e in errors:
            print("  ✗", e)
        for w in warns:
            print("  !", w)
        sys.exit(1)

    # Unchanged files the reviewer (and in-page Claude) may need: callers, base classes, schemas.
    context = []
    ctx_paths = [p for p in guide.get("context_files", []) if p not in paths]
    if ctx_paths:
        src = Source(pr["repo"])
        local = src.has(pr["headSha"])
        used = 0
        for p in ctx_paths:
            text = src.read(pr["headSha"], p, local)
            if text is None:
                warns.append(f"context file {p} not found at head (or binary/too large)")
                continue
            size = len(text.encode("utf-8"))
            if used + size > CONTEXT_BUDGET:
                warns.append(f"context file {p} skipped: context budget full")
                continue
            used += size
            context.append({"path": p, "lang": lang_for(p), "text": text})

    # who Claude Code will post review comments as (gh's logged-in account)
    who = subprocess.run(["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True)
    pr["poster"] = who.stdout.strip() if who.returncode == 0 else None

    data = {"pr": pr, "guide": guide, "context": context}
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    name = guide.get("name") or re.sub(r"^\[[^\]]*\]\s*(\[[^\]]*\]:?\s*)?", "", pr["title"])[:48]
    title = f"#{pr['number']} {name}".replace("<", "").replace("&", "and")

    html = open(TEMPLATE).read()
    html = html.replace("__TITLE__", title, 1).replace("__REVIEW_DATA__", blob, 1)
    out = os.path.join(d, "review.html")
    with open(out, "w") as fh:
        fh.write(html)

    size = len(html.encode("utf-8"))
    for w in warns:
        print("  !", w)
    if size > MAX_PAGE:
        sys.exit(f"review.html is {size/1e6:.1f} MB, over the 15 MB page limit. "
                 f"Re-run fetch_pr.py with a smaller --budget-mb.")
    print(f"wrote {out}  ({size/1e6:.2f} MB, {len(chapters)} chapters, {len(context)} context files)")
    print(f"title: {title}")


if __name__ == "__main__":
    main()
