---
name: guided-pr-review
description: Visual, guided review of a GitHub pull request. Builds a private claude.ai page with an Overview / Guide / Diff layout, a before/after flow diagram, files grouped into plain-English chapters in reading order (core change first, tests and generated files last), "look closely" flags on exact lines, and a live Ask panel where Claude answers questions inside the page by reading diffs, whole files and searching the code. Reviewers can also draft line comments in the page and submit a review, which Claude Code posts to GitHub. Use when the user wants to review, understand or walk through a PR ("review PR 956", "help me review this PR", a github.com/.../pull/N link); ALWAYS ask the user to confirm before starting a new guided review. Also use, with no confirmation, when the user says "post my review" (or "post my review for #N") to send a review submitted on a guided review page to GitHub.
---

# Guided PR Review

A big diff shown in file order makes the reviewer spend the first half hour working out what the PR does. This skill does that work up front and hands the reviewer a page that reads in the right order, with Claude available inside the page for follow-up questions.

Output: one private artifact per PR with three tabs.
- **Guide** (default): overview plus diagrams, then one chapter per idea. The top diagrams are the before/after flow, any extra overview diagrams, and an automatic map of how the changed files import each other. Each chapter has the explanation on the left (sticky), its own diagrams and diffs on the right, "Reviewed" checkboxes, "look closely" flags pinned to lines, and suggested questions. Test files sit in a kept "Tests" chapter at the end: listed with their test names, diffs collapsed, not reviewed.
- **Overview**: verdict, the checklist to finish before approving, the PR description, where the lines went, and the commits.
- **Diff**: every file in GitHub order, for completeness.
- **Ask panel** (`/` or the Ask button): Claude answers in the page, with page tools `read_diff`, `read_file` (before or after the PR) and `search`. `path:line` citations in answers jump to the line. Click a line number (shift-click for a range) to ask about that code.
- **Review comments**: select lines (or use Comment on a "Look closely" flag) and choose **Comment**. Drafts are saved in the artifact's database and show inline. The **Review** panel lists them, takes an overall comment and Comment / Approve / Request changes, and **Submit review** queues it. Claude Code posts it to GitHub when the user says "post my review" (see "Posting review comments" below).

## 0. Ask first (required)

Do this before fetching anything.

1. Work out the repo: the PR link if one was given, else the current directory's `origin` if it is a git repo, else ask the user which repo (`owner/name`).
2. If the user didn't name a PR, find candidates and ask which one:
   `gh pr list -R <repo> --search "review-requested:@me" --limit 8 --json number,title,author,additions,deletions,changedFiles`
   (no results: drop the `--search` to list recent open PRs).
3. Confirm with AskUserQuestion. Header "PR review". Question: "Start a guided visual review of #N: <title> (+A −D, F files)?" Options:
   - "Yes, guided review (Recommended)": build the page.
   - "Quick text review instead": run the `code-review` skill on the PR and stop here.
   - "Not now": stop.

Continue only on yes.

## 1. Fetch

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/fetch_pr.py <number|url|owner/name#n> [--repo owner/name]
```

This writes `~/.claude/guided-reviews/<owner>-<name>-<n>/pr.json` (call that folder `DIR`) and prints every file with its status, kind (core, config, test, docs, migration, generated) and +/−. It embeds the full before/after text of changed files, up to a 6 MB budget (`--budget-mb`), so the page can expand unchanged lines and in-page Claude can read whole files. Generated files are never embedded. It also records the test names in each test file and the imports between changed files, which the page draws as a file map.

## 2. Read the PR (skip the tests)

- Description: `python3 -c "import json;print(json.load(open('DIR/pr.json'))['body'])"`
- Diffs with real line numbers: `python3 ${CLAUDE_SKILL_DIR}/scripts/pr_diff.py DIR/pr.json [path-substring ...] [--max-lines N]`. It skips test and generated files by default.
- **Don't read test files.** The build puts every test file you leave out of the guide into a kept "Tests" chapter. That chapter lists each file's test names, collapses its diffs and leaves it out of the review progress. The reviewer can still ask about tests in the Ask panel. Look at the test names fetch printed only when you need to judge coverage for the verdict.
- Read every core file's diff in full. For long docs files, skim the headings. Don't read generated or lock files past their header.
- Before you flag anything, read the code around it (`files[].newText` / `oldText` in pr.json, or the local clone) and confirm it is real. A wrong flag costs the reviewer more than a missing one.
- Large PRs (over about 3,000 changed lines outside generated files): give each area to a subagent (Explore or general-purpose). Each one returns chapter proposals and verified flags with `path:line`, and you merge them.

## 3. Write `DIR/guide.json`

Follow `references/guide-schema.md` for the shape and the writing rules. The short version:

- **Chapters** (usually 3 to 8): one idea each, titled as plain-words actions ("Stage and upload shared files"). Put them in reading order: the core change first, then supporting code and wiring, then data/migrations last. Every changed non-test file goes in exactly one chapter. Leave test files out; the build adds them.
- **Flow**: 5 to 12 nodes showing the runtime path the PR creates or changes. Mark each node `added`, `changed`, `removed` or `same`, and link it to its chapter.
- **Diagrams**: give a chapter a diagram whenever a picture explains it faster than prose. Use `state` for a lifecycle or status field, `sequence` for calls between components, an approval loop or a retry protocol, `schema` for new or changed models, request/response bodies or tables, and `flow` for a pipeline inside one chapter. Aim for one to three diagrams across a mid-size PR. Only draw what the code really does; check the names and order you use.
- **Look closely**: only concrete, verified items, each pinned to `path` + after-PR `line`. Use `risk` for likely bugs, `question` for things the reviewer should ask the author, and `nit` for small stuff. Leave it empty rather than pad it.
- **Ask**: 1 to 3 questions per chapter that a sharp reviewer would really ask.
- **context_files**: up to about 15 unchanged files that answers will need (callers, base classes, schemas, enums), found with `rg` in the local clone.

## 4. Build

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/build_review.py DIR
```

This writes `DIR/review.html`. It stops with ✗ lines when guide.json doesn't fit the PR (an unknown path or a bad flow edge); fix those and rerun. ! lines are warnings: files left out of every chapter go into "Everything else", so fix them when they matter.

## 5. Publish

Before your first publish this session, load the `artifact-design` skill (the template already follows it, so only the page contract matters). Then call the Artifact tool:

- `file_path`: `DIR/review.html`
- `capabilities`: `{"sample": {}, "db": {}, "user": {}}`. `sample` runs the Ask panel; `db` and `user` hold review comments.
- `icon`: `"code"` (first publish of this PR only)
- `description`: one sentence, e.g. "Guided review of acme/api#412: failed payments retry with backoff instead of failing the order."

Re-reviews keep the same link:
- Same session: publish the same `file_path` again.
- Later session: if `DIR/artifact_url.txt` exists, `Artifact read` that URL first, then publish with `url` set to it.
- After any publish, write the URL to `DIR/artifact_url.txt`.

## 6. Hand over

Reply in a few lines:
- the link
- the risk level
- the one to three most important "look closely" items
- that the first Ask question shows a permission prompt and uses their own Claude usage

Don't paste the guide into the terminal.

## Posting review comments

Use this when the user says "post my review" (optionally "for #N"). Submitting in the page only queues the review; this step sends it to GitHub. The user's request is the go-ahead, so don't ask again.

1. Find `DIR` for the PR and read `DIR/artifact_url.txt`. If several reviews exist and no PR was named, query each one and post every queued submission.
2. Query the artifact's database with `ArtifactData` (load it with ToolSearch first): collection `review_submissions`, `status == "queued"`. None queued: say so and stop.
3. For each submission, oldest first:
   - Update it to `{"status": "posting"}`.
   - Read its comments: `review_comments` docs whose ids are in `commentIds`.
   - Write `DIR/submission-<id>.json` as `{"event", "body", "comments": [{path, line, startLine, side, body, fileLevel}]}`.
   - Run `python3 ${CLAUDE_SKILL_DIR}/scripts/post_review.py DIR DIR/submission-<id>.json`. It posts one review with `gh`, pinned to the head commit the page was built from. Inline comments must be on diff lines; anything else becomes a file note in the review body.
   - On success: update the submission to `{"status": "posted", "url", "reviewId", "postedAt"}` and each of its comments to `{"status": "posted"}`, in one `batch`.
   - On failure: update the submission to `{"status": "failed", "error": "<GitHub's message>"}` and put its comments back to `{"status": "draft", "submission": null}` so the user can fix and resubmit.
4. Reply with the review link and the counts (inline comments, file notes). If the PR has new commits since the page was built, say that the comments are pinned to the older commit, so GitHub may show some as outdated.

Comments post as the account `gh` is logged in with (the page shows it). GitHub refuses Approve and Request changes on your own PR, and the page disables them in that case.

## Updating after new commits

Rerun `fetch_pr.py` (same DIR), update guide.json for the files that changed, rebuild, and republish to the same URL. Reviewed checkmarks are stored per head SHA in the viewer's browser, so they reset when the PR moves.

## Notes

- The page holds the PR's diff and changed-file text inside a private artifact on the user's claude.ai account. If the user says a repo's code must not leave the machine, don't publish. Offer `DIR/review.html` as a local file instead; it works without Ask.
- The Ask panel only works on claude.ai. Opened as a local file, the rest of the page still works.
