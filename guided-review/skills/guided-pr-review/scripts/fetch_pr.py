#!/usr/bin/env python3
"""Fetch a GitHub PR into pr.json for the guided review page.

Usage:
  fetch_pr.py <pr> [--repo owner/name] [-o OUT_DIR] [--budget-mb 6]

<pr> is a number, a PR URL, or owner/name#number. Without --repo, a bare
number resolves against the git repo in the current directory.

Writes OUT_DIR/pr.json (default ~/.claude/guided-reviews/<owner>-<name>-<n>/)
and prints a file table to read before writing guide.json.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote

PER_FILE_CAP = 400_000  # bytes of full-file text kept per side
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@ ?(.*)$")

LANGS = {
    "py": "python", "pyi": "python", "ts": "typescript", "tsx": "typescript",
    "js": "javascript", "jsx": "javascript", "mjs": "javascript", "cjs": "javascript",
    "json": "json", "yml": "yaml", "yaml": "yaml", "md": "markdown", "mdx": "markdown",
    "sh": "bash", "bash": "bash", "zsh": "bash", "go": "go", "rs": "rust", "java": "java",
    "kt": "kotlin", "kts": "kotlin", "swift": "swift", "sql": "sql", "toml": "ini",
    "ini": "ini", "cfg": "ini", "html": "xml", "xml": "xml", "svg": "xml", "css": "css",
    "scss": "scss", "less": "less", "rb": "ruby", "c": "c", "h": "c", "cpp": "cpp",
    "hpp": "cpp", "cs": "csharp", "php": "php", "lua": "lua", "graphql": "graphql",
    "gql": "graphql", "r": "r", "pl": "perl", "m": "objectivec",
}
SPECIAL = {"Makefile": "makefile", "Dockerfile": "plaintext", "Jenkinsfile": "plaintext"}

GENERATED = re.compile(
    r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|uv\.lock|Cargo\.lock|"
    r"go\.sum|Gemfile\.lock|composer\.lock|Pipfile\.lock)$|\.min\.(js|css)$|_pb2(_grpc)?\.pyi?$|"
    r"\.pb\.go$|(^|/)(__generated__|generated|gen)/|(^|/)__snapshots__/|\.snap$"
)
TEST = re.compile(
    r"(^|/)(tests?|__tests__|spec|e2e)/|(^|/)test_[^/]+\.py$|_test\.(py|go)$|"
    r"\.(test|spec)\.[jt]sx?$|(^|/)conftest\.py$"
)
MIGRATION = re.compile(r"(^|/)(migrations?|alembic|db/migrate)/|\.sql$")
CONFIG = re.compile(
    r"(^|/)\.github/|(^|/)(Dockerfile|Makefile|Jenkinsfile|docker-compose[^/]*|"
    r"pyproject\.toml|setup\.cfg|setup\.py|requirements[^/]*\.txt|package\.json|tsconfig[^/]*\.json|"
    r"\.env[^/]*|\.pre-commit-config\.yaml|\.gitignore)$|(^|/)(helm|k8s|deploy|infra|charts)/"
)
DOCS = re.compile(r"\.(md|mdx|rst|txt)$|(^|/)docs?/")
KIND_ORDER = {"core": 0, "config": 1, "test": 2, "docs": 3, "migration": 4, "generated": 5}


def run(args, binary=False, check=True):
    r = subprocess.run(args, capture_output=True, text=not binary)
    if check and r.returncode != 0:
        err = r.stderr if not binary else r.stderr.decode("utf-8", "replace")
        raise RuntimeError(f"{' '.join(args[:4])}…: {err.strip()[:400]}")
    return r


def parse_ref(ref, repo):
    m = re.match(r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)", ref)
    if m:
        return m.group(1), int(m.group(2))
    m = re.match(r"^([\w.-]+/[\w.-]+)#(\d+)$", ref)
    if m:
        return m.group(1), int(m.group(2))
    if ref.lstrip("#").isdigit():
        if not repo:
            repo = run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]).stdout.strip()
        return repo, int(ref.lstrip("#"))
    sys.exit(f"Can't read PR reference: {ref!r}. Use a number, URL, or owner/name#123.")


def lang_for(path):
    name = path.rsplit("/", 1)[-1]
    if name in SPECIAL:
        return SPECIAL[name]
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return LANGS.get(ext, "plaintext")


def kind_for(path):
    for kind, rx in (("generated", GENERATED), ("test", TEST), ("migration", MIGRATION),
                     ("config", CONFIG), ("docs", DOCS)):
        if rx.search(path):
            return kind
    return "core"


def parse_patch(patch):
    hunks = []
    cur = None
    o = n = 0
    for raw in patch.rstrip("\n").split("\n"):
        m = HUNK_RE.match(raw)
        if m:
            o, n = int(m[1]), int(m[3])
            cur = {"o": o, "oc": int(m[2]) if m[2] is not None else 1,
                   "n": n, "nc": int(m[4]) if m[4] is not None else 1,
                   "ctx": m[5], "lines": []}
            hunks.append(cur)
            continue
        if cur is None or raw.startswith("\\"):
            continue
        t, s = (raw[:1] or " "), raw[1:]
        if t == "+":
            cur["lines"].append(["+", None, n, s]); n += 1
        elif t == "-":
            cur["lines"].append(["-", o, None, s]); o += 1
        else:
            cur["lines"].append([" ", o, n, s]); o += 1; n += 1
    return hunks


TEST_NAME_RES = [
    re.compile(r"^\s*(?:async\s+)?def\s+(test_\w+)", re.M),
    re.compile(r"""^\s*(?:it|test)(?:\.\w+)?\(\s*['"`]([^'"`]{1,120})""", re.M),
    re.compile(r"^\s*func\s+(Test\w+)\(", re.M),
]


def test_names(text):
    names = []
    for rx in TEST_NAME_RES:
        names += rx.findall(text or "")
    return names[:200]


def import_edges(files):
    """(importer, imported) pairs among the PR's own non-test, non-generated files."""
    pool = {f["path"]: f for f in files if f["kind"] not in ("test", "generated")}
    by_module = {}
    for p in pool:
        if p.endswith(".py"):
            mod = p[:-3].replace("/", ".")
            by_module[mod[:-9] if mod.endswith(".__init__") else mod] = p
    js_exts = ("", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js")
    edges = set()
    for p, f in pool.items():
        text = f["newText"] if f["newText"] is not None else f["oldText"]
        if not text:
            continue
        targets = []
        if p.endswith(".py"):
            pkg = p.rsplit("/", 1)[0].replace("/", ".") if "/" in p else ""
            for m in re.finditer(r"^\s*from\s+(\.*)([\w.]*)\s+import\s+(\([^)]*\)|[^\n]+)", text, re.M):
                dots, mod, names = m.groups()
                if dots:
                    base = pkg.split(".")
                    base = base[: len(base) - (len(dots) - 1)] if len(dots) > 1 else base
                    mod = ".".join([x for x in base + mod.split(".") if x])
                targets.append(mod)
                for n in re.findall(r"\b(\w+)\b", names.replace(" as ", " ")):
                    targets.append(f"{mod}.{n}")
            for m in re.finditer(r"^\s*import\s+([\w.]+)", text, re.M):
                targets.append(m.group(1))
            for t in targets:
                q = by_module.get(t)
                if q and q != p:
                    edges.add((p, q))
        elif re.search(r"\.(m?[jt]sx?)$", p):
            d = p.rsplit("/", 1)[0] if "/" in p else ""
            for m in re.finditer(r"""(?:from\s+|require\(\s*|import\(\s*)['"](\.[^'"]+)['"]""", text):
                parts = (d + "/" + m.group(1)).split("/")
                out = []
                for part in parts:
                    if part in ("", "."):
                        continue
                    if part == "..":
                        out = out[:-1]
                    else:
                        out.append(part)
                base = "/".join(out)
                for ext in js_exts:
                    if base + ext in pool and base + ext != p:
                        edges.add((p, base + ext))
                        break
    return sorted(edges)


class Source:
    """Reads file text at a commit: local git when the commit is present, else the GitHub API."""

    def __init__(self, repo):
        self.repo = repo
        self.local = False
        r = run(["git", "remote", "get-url", "origin"], check=False)
        if r.returncode == 0 and repo.lower() in r.stdout.strip().lower().replace(":", "/"):
            self.local = True

    def has(self, sha):
        if not self.local:
            return False
        return run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], check=False).returncode == 0

    def read(self, sha, path, use_local):
        try:
            if use_local:
                r = run(["git", "show", f"{sha}:{path}"], binary=True, check=False)
                data = r.stdout if r.returncode == 0 else None
            else:
                r = run(["gh", "api", "-H", "Accept: application/vnd.github.raw",
                         f"repos/{self.repo}/contents/{quote(path)}?ref={sha}"], binary=True, check=False)
                data = r.stdout if r.returncode == 0 else None
        except Exception:
            data = None
        if data is None or b"\x00" in data[:8000]:
            return None
        if len(data) > PER_FILE_CAP:
            return None
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pr")
    ap.add_argument("--repo")
    ap.add_argument("-o", "--out")
    ap.add_argument("--budget-mb", type=float, default=6.0,
                    help="cap on full-file text embedded for in-page Q&A")
    a = ap.parse_args()

    repo, num = parse_ref(a.pr, a.repo)
    fields = ("number,title,body,author,url,baseRefName,headRefName,baseRefOid,headRefOid,"
              "additions,deletions,changedFiles,commits,createdAt,isDraft,labels,state,reviewDecision")
    meta = json.loads(run(["gh", "pr", "view", str(num), "-R", repo, "--json", fields]).stdout)

    lines = run(["gh", "api", "--paginate", f"repos/{repo}/pulls/{num}/files?per_page=100",
                 "--jq", ".[] | {filename,status,additions,deletions,patch,previous_filename}"]).stdout
    raw_files = [json.loads(x) for x in lines.splitlines() if x.strip()]

    head = meta["headRefOid"]
    mb = run(["gh", "api", f"repos/{repo}/compare/{meta['baseRefOid']}...{head}",
              "--jq", ".merge_base_commit.sha"], check=False)
    merge_base = mb.stdout.strip() if mb.returncode == 0 and mb.stdout.strip() else meta["baseRefOid"]

    files = []
    for rf in raw_files:
        path = rf["filename"]
        patch = rf.get("patch")
        files.append({
            "path": path,
            "prev": rf.get("previous_filename"),
            "status": rf["status"],  # added | removed | modified | renamed | copied | changed
            "add": rf["additions"],
            "del": rf["deletions"],
            "kind": kind_for(path),
            "lang": lang_for(path),
            "hunks": parse_patch(patch) if patch else [],
            "patchMissing": not patch,
            "newText": None,
            "oldText": None,
        })

    # Full-file text so the page can expand unchanged lines and Claude can read whole files.
    src = Source(repo)
    head_local, base_local = src.has(head), src.has(merge_base)
    order = sorted(range(len(files)), key=lambda i: (KIND_ORDER[files[i]["kind"]], files[i]["add"] + files[i]["del"]))
    budget = int(a.budget_mb * 1_000_000)
    jobs = []
    for i in order:
        f = files[i]
        if f["kind"] == "generated":
            continue
        if f["status"] != "removed":
            jobs.append((i, "newText", head, f["path"], head_local))
        if f["status"] not in ("added",):
            jobs.append((i, "oldText", merge_base, f["prev"] or f["path"], base_local))

    def fetch(job):
        i, side, sha, path, loc = job
        return i, side, src.read(sha, path, loc)

    used = 0
    skipped = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, side, text in pool.map(fetch, jobs):
            if text is None:
                continue
            size = len(text.encode("utf-8"))
            if used + size > budget:
                skipped += 1
                continue
            files[i][side] = text
            used += size

    for f in files:
        if f["kind"] == "test":
            f["tests"] = test_names(f["newText"] or "".join(l[3] + "\n" for h in f["hunks"] for l in h["lines"] if l[0] != "-"))

    pr = {
        "repo": repo,
        "number": meta["number"],
        "title": meta["title"],
        "body": meta.get("body") or "",
        "author": (meta.get("author") or {}).get("login", ""),
        "url": meta["url"],
        "base": meta["baseRefName"],
        "head": meta["headRefName"],
        "baseSha": meta["baseRefOid"],
        "headSha": head,
        "mergeBase": merge_base,
        "additions": meta["additions"],
        "deletions": meta["deletions"],
        "changedFiles": meta["changedFiles"],
        "createdAt": meta["createdAt"],
        "isDraft": meta["isDraft"],
        "state": meta["state"],
        "labels": [l["name"] for l in meta.get("labels", [])],
        "commits": [{"sha": c["oid"][:7], "msg": c["messageHeadline"]} for c in meta.get("commits", [])],
        "files": files,
        "imports": import_edges(files),
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    out = a.out or os.path.expanduser(f"~/.claude/guided-reviews/{repo.replace('/', '-')}-{num}")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "pr.json")
    with open(path, "w") as fh:
        json.dump(pr, fh, ensure_ascii=False)

    print(f"{repo}#{num}  {meta['title']}")
    print(f"@{pr['author']}  {pr['base']} <- {pr['head']}  +{pr['additions']} -{pr['deletions']}  {len(files)} files")
    print(f"full text: {used/1e6:.1f} MB embedded" + (f", {skipped} sides over budget" if skipped else "")
          + f"  (source: {'local git' if head_local else 'GitHub API'})")
    print()
    w = max((len(f["path"]) for f in files), default=10)
    for f in files:
        flag = " [no patch]" if f["patchMissing"] else ""
        if f["kind"] == "test":
            flag += f"  ({len(f.get('tests', []))} tests, kept, not reviewed)"
        print(f"  {f['path']:<{w}}  {f['status']:<8} {f['kind']:<9} +{f['add']:<5} -{f['del']}{flag}")
    review = [f for f in files if f["kind"] not in ("test", "generated")]
    print()
    print(f"to review: {len(review)} files, {sum(f['add'] + f['del'] for f in review)} changed lines "
          f"(tests and generated files are kept on the page but not read)")
    print(f"imports between changed files: {len(pr['imports'])} (drawn as the file map)")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
