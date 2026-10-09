#!/usr/bin/env python3
"""Print a PR's hunks from pr.json with real line numbers, for reading before writing guide.json.

Usage:
  pr_diff.py PR_JSON [PATH_SUBSTRING ...] [--max-lines N] [--include-tests]

Each line prints as `<old> <new> <mark> <code>` so you can cite exact new-file
line numbers in guide.json `watch` items. With path filters, only matching files print.
Test and generated files are skipped unless you pass --include-tests or name them
in a path filter: the page keeps them, the guide doesn't review them.
"""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pr_json")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--max-lines", type=int, default=1500, help="per file")
    ap.add_argument("--include-tests", action="store_true")
    a = ap.parse_args()

    pr = json.load(open(a.pr_json))
    skipped = []
    for f in pr["files"]:
        if a.paths and not any(p in f["path"] for p in a.paths):
            continue
        if f["kind"] in ("test", "generated") and not a.include_tests and not a.paths:
            skipped.append(f["path"])
            continue
        head = f"=== {f['path']}  ({f['status']}, {f['kind']}, +{f['add']} -{f['del']})"
        if f.get("prev"):
            head += f"  renamed from {f['prev']}"
        print(head)
        if f["patchMissing"]:
            print("    (no patch from GitHub: binary or too large)\n")
            continue
        shown = 0
        for h in f["hunks"]:
            print(f"  @@ -{h['o']},{h['oc']} +{h['n']},{h['nc']} @@ {h['ctx']}")
            for t, o, n, s in h["lines"]:
                if shown >= a.max_lines:
                    break
                print(f"  {o or '':>5} {n or '':>5} {t} {s}")
                shown += 1
        if shown >= a.max_lines:
            print(f"  … truncated at {a.max_lines} lines")
        print()
    if skipped:
        print(f"(skipped {len(skipped)} test/generated files; they get their own kept chapter automatically)")


if __name__ == "__main__":
    main()
