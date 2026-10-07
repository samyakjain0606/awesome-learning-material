#!/usr/bin/env python3
"""Post a review drafted on the guided review page to GitHub as one PR review.

Usage:
  post_review.py REVIEW_DIR SUBMISSION_JSON [--dry-run]

SUBMISSION_JSON is what the page queued, collected by Claude Code from the
artifact's database:
  {"event": "COMMENT" | "APPROVE" | "REQUEST_CHANGES",
   "body": "overall comment",
   "comments": [{"path": str, "line": int, "startLine": int|null,
                 "side": "RIGHT"|"LEFT", "body": str, "fileLevel": bool}]}

Inline comments must sit on lines that are part of the diff. Any that don't
(or were drafted as file comments) go into the review body as file notes.
Posts with `gh` as whichever account it is logged in as, pinned to the head
commit the review was built from. Prints one JSON line with the result.
"""
import json
import os
import subprocess
import sys


def diff_lines(pr):
    """{path: {"RIGHT": set(new lines), "LEFT": set(old lines)}} for lines GitHub can comment on."""
    out = {}
    for f in pr["files"]:
        right, left = set(), set()
        for h in f["hunks"]:
            for t, o, n, _ in h["lines"]:
                if t in ("+", " ") and n:
                    right.add(n)
                if t in ("-", " ") and o:
                    left.add(o)
        out[f["path"]] = {"RIGHT": right, "LEFT": left}
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    if len(args) != 2:
        sys.exit(__doc__)
    review_dir, sub_path = args
    pr = json.load(open(os.path.join(review_dir, "pr.json")))
    sub = json.load(open(sub_path))
    valid = diff_lines(pr)

    event = sub.get("event") or "COMMENT"
    if event not in ("COMMENT", "APPROVE", "REQUEST_CHANGES"):
        sys.exit(f"unknown event {event!r}")
    inline, notes = [], []
    for c in sub.get("comments") or []:
        body = (c.get("body") or "").strip()
        if not body:
            continue
        path, line, side = c.get("path"), c.get("line"), c.get("side") or "RIGHT"
        start = c.get("startLine")
        ok = (not c.get("fileLevel")) and path in valid and isinstance(line, int) and line in valid[path][side]
        if ok:
            item = {"path": path, "line": line, "side": side, "body": body}
            if isinstance(start, int) and start < line and start in valid[path][side]:
                item["start_line"] = start
                item["start_side"] = side
            inline.append(item)
        else:
            where = f"`{path}`" + (f" L{start}–{line}" if start and line and start < line else f" L{line}" if line else "")
            notes.append(f"**{where}**\n{body}")

    body = (sub.get("body") or "").strip()
    if notes:
        body = (body + "\n\n" if body else "") + "\n\n".join(notes)
    if event == "REQUEST_CHANGES" and not body and not inline:
        sys.exit("Request changes needs a comment.")
    if event == "COMMENT" and not body and not inline:
        sys.exit("Nothing to post: no overall comment and no line comments.")

    payload = {"commit_id": pr["headSha"], "event": event, "body": body, "comments": inline}
    if dry:
        print(json.dumps({"dry_run": True, "repo": pr["repo"], "number": pr["number"], "payload": payload}, indent=1))
        return
    r = subprocess.run(
        ["gh", "api", f"repos/{pr['repo']}/pulls/{pr['number']}/reviews", "--method", "POST", "--input", "-"],
        input=json.dumps(payload), capture_output=True, text=True,
    )
    if r.returncode != 0:
        msg = r.stdout.strip() or r.stderr.strip()
        try:
            msg = json.loads(r.stdout).get("message", msg) + " " + json.dumps(json.loads(r.stdout).get("errors", ""))
        except Exception:
            pass
        print(json.dumps({"ok": False, "error": msg[:600]}))
        sys.exit(1)
    res = json.loads(r.stdout)
    print(json.dumps({"ok": True, "id": res.get("id"), "url": res.get("html_url"), "state": res.get("state"),
                      "inline": len(inline), "fileNotes": len(notes)}))


if __name__ == "__main__":
    main()
