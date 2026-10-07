# guided-pr-review

A Claude Code skill that turns any GitHub pull request into one page you can actually read. Files are
grouped into chapters in reading order, diagrams show what changed, the risky lines are flagged, and you
can ask questions and leave review comments right on the page.

Inspired by [@0xluffy](https://x.com/0xluffy)'s
[Guided Reviews](https://x.com/0xluffy/status/2107593041519501477) at Capy.

## The problem

GitHub shows a big diff in file order. You spend the first half hour jumping between files, working out
what the PR is even trying to do, before you can start reviewing it.

## What you get

Ask Claude to do a "guided review" of a PR. It asks you to confirm, reads the diff, and publishes a
private page on claude.ai with three tabs:

- **Guide**: a plain-words overview and a before/after flow diagram, then one chapter per idea, with
  the core change first. Each chapter has its explanation beside its diffs, a "Reviewed" checkbox, and
  "look closely" flags pinned to exact lines.
- **Diagrams** where a picture is faster than prose: sequences (who calls whom), lifecycles (state
  machines), data shapes (models and fields), and a map of how the changed files import each other.
  They draw themselves in and have a Before/After toggle.
- **Tests and generated files** are kept in their own chapter, with test names listed and diffs
  collapsed. They aren't reviewed, which saves time and tokens.
- **Overview**: a risk verdict, a checklist to finish before approving, the PR description and commits.
- **Diff**: every file in GitHub order, for completeness.

Two things happen on the page itself:

- **Ask**: select lines and choose Explain, or ask anything. Claude answers in the page, reading the
  diffs, whole files and searching the code. File references in answers (`path:line`) are links that
  jump to the line.
- **Review comments**: select lines (or use Comment on a flag) and write a comment. Drafts are saved
  with the page. Open **Review**, add an overall comment, pick Comment / Approve / Request changes and
  submit. Then say **"post my review"** in Claude Code, and it posts everything to GitHub as one review
  with inline comments.

## Install

```
npx degit samyakjain0606/awesome-learning-material/guided-pr-review ~/.claude/skills/guided-pr-review
```

It loads in your next Claude Code session.

## Use

```
do a guided review of PR 123
```

You can also pass a PR link, or `owner/repo#123`. Inside a git repo, a bare number uses that repo.
Outside one, Claude asks which repo you mean.

When you've submitted a review on the page:

```
post my review
```

## Requirements

- Claude Code with a claude.ai account (the page is published as a private claude.ai artifact).
- The GitHub CLI, signed in: `gh auth login`. It reads the PR and posts your review comments, as the
  account you're signed in with.
- Python 3.

## Good to know

- The page holds the PR's diff and the changed files' text, in a private artifact on your claude.ai
  account. Don't run it on code that must not leave your machine.
- The Ask panel uses your own Claude usage and asks for permission the first time.
- GitHub only accepts inline comments on lines in the diff. Comments on other lines go into the
  review's summary as file notes. GitHub also doesn't let you approve your own PR, so the page only
  offers Comment there.
- After new commits, ask for the guided review again. It updates the same page link.

## Files

- `SKILL.md`: the workflow Claude follows.
- `scripts/fetch_pr.py`: pulls the PR, its hunks, the changed files' full text, test names and imports.
- `scripts/pr_diff.py`: prints hunks with real line numbers, skipping tests.
- `scripts/build_review.py`: checks Claude's `guide.json` against the PR and builds the page.
- `scripts/post_review.py`: posts a submitted review to GitHub.
- `references/guide-schema.md`: the guide format and how to write good chapters, flags and diagrams.
- `assets/template.html`: the page.
