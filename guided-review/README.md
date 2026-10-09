# guided-review

A Claude Code plugin with two skills that turn code work into one page you can actually read:

- **guided-pr-review**: any GitHub pull request, grouped into chapters in reading order, with diagrams,
  flags on the risky lines, and Ask plus review comments right on the page.
- **guided-plan**: the same kind of page for a change that is not built yet. Evidence, what will change
  and where, risks, and the few decisions that are yours, with one response you paste back before
  Claude builds anything.

Inspired by [@0xluffy](https://x.com/0xluffy)'s
[Guided Reviews](https://x.com/0xluffy/status/2107593041519501477) at Capy.

## Install

```
/plugin marketplace add samyakjain0606/awesome-learning-material
/plugin install guided-review@awesome-learning-material
```

Or as a skills-folder plugin, loaded in your next session:

```
npx degit samyakjain0606/awesome-learning-material/guided-review ~/.claude/skills/guided-review
```

If you installed the old standalone skill, remove it first so a PR review doesn't trigger two skills:
`rm -rf ~/.claude/skills/guided-pr-review`.

## guided-pr-review

### The problem

GitHub shows a big diff in file order. You spend the first half hour jumping between files, working out
what the PR is even trying to do, before you can start reviewing it.

### What you get

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

### Use

```
do a guided review of PR 123
```

You can also pass a PR link, or `owner/repo#123`. Inside a git repo, a bare number uses that repo.
Outside one, Claude asks which repo you mean. When you've submitted a review on the page, say
`post my review`.

## guided-plan

### The problem

A plan in chat scrolls away, and a plan in a doc hides the decisions in prose. You end up approving a
wall of text, and the forks you cared about get decided for you.

### What you get

Ask Claude for a guided plan. It reads the code first, then publishes a private page with two tabs:

- **Plan**: the goal, the steps, and a before/after flow of the runtime path. Then one chapter per idea:
  a problem chapter with the evidence, the core changes, and a rollout chapter last. Each chapter has
  its explanation, the exact current lines it touches (`path:line`, click to open the code), diagrams,
  examples, risks and open questions, and a note box.
- **Examples** that show what a paragraph can't: number tiles, side-by-side "today / after the plan"
  text, chat transcripts that play in turn by turn, and short sketches.
- **Decisions**: each fork that changes what gets built, with the option Claude would pick marked as
  suggested. Also a "Before we build" checklist and what is not changing.
- **Ask**: Claude answers questions about the plan in the page, reading the code it cites.

Change any decision, write notes, tick checks, then press **Copy response** and paste it back to
Claude. It updates the plan (same link) or confirms the final choices, and builds only when you say so.
No code diffs are shown, because there is no code yet.

### Use

```
make a guided plan for retrying declined payments
```

`skills/guided-plan/references/example-plan.json` is a complete example plan.

## Requirements

- Claude Code with a claude.ai account (the pages are published as private claude.ai artifacts).
- Python 3.
- For PR reviews: the GitHub CLI, signed in (`gh auth login`). It reads the PR and posts your review
  comments as the account you're signed in with.

## Good to know

- The pages hold code: the PR's diff and changed files, or the files a plan cites. They live in private
  artifacts on your claude.ai account. Don't run either skill on code that must not leave your machine.
- The Ask panel uses your own Claude usage and asks for permission the first time.
- GitHub only accepts inline comments on lines in the diff. Comments on other lines go into the
  review's summary as file notes. GitHub also doesn't let you approve your own PR, so the page only
  offers Comment there.
- After new commits, ask for the guided review again. It updates the same page link. Plans update the
  same link too.
- guided-plan reuses guided-pr-review's diagram checks and page template, so keep the two skills
  together.

## Files

- `skills/guided-pr-review/SKILL.md`: the review workflow Claude follows.
- `skills/guided-pr-review/scripts/`: `fetch_pr.py` pulls the PR, `pr_diff.py` prints hunks with real
  line numbers, `build_review.py` checks `guide.json` and builds the page, `post_review.py` posts a
  submitted review to GitHub.
- `skills/guided-pr-review/references/guide-schema.md`: the guide format, chapters, flags and diagrams.
- `skills/guided-plan/SKILL.md`: the plan workflow, from reading the code to acting on your response.
- `skills/guided-plan/scripts/build_plan.py`: checks `plan.json` (diagrams, decisions, cited lines) and
  builds the page. `make_template.py` regenerates the plan template from the review template.
- `skills/guided-plan/references/`: `plan-schema.md` (the format and writing rules) and
  `example-plan.json`.
- `skills/*/assets/template.html`: the pages.

## Updating the plan template

`skills/guided-plan/assets/template.html` is generated from the review template by
`skills/guided-plan/scripts/make_template.py`, which removes the Diff tab and the GitHub review panel
and adds touches, examples, decisions, notes and the Decisions tab. After changing the review template:

```
python3 skills/guided-plan/scripts/make_template.py skills/guided-pr-review/assets/template.html skills/guided-plan/assets/template.html
```

If an anchor no longer matches, the script stops with `not found:` and the text it looked for. Update
that anchor in the script.
