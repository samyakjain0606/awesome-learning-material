# Running log and final report

## Running log

Keep one Markdown file in a working folder: a session scratchpad, or a path the
user picks. Add a row the moment anything changes. It's the source of truth for the
final report, and it's how a long run resumes after the context resets.

```markdown
# <Product> directory submissions: <date>
Source list: <URL of the list you worked from>
Badge budget agreed: <n>; badges used: <list>
Google account: <account the user named>

| # | Directory | DR | Free-tier link type | Status | Evidence / next step |
|--:|---|--:|---|---|---|
| 1 | Example | 72 | dofollow | SUBMITTED, pending review (stated: 72h) | example.com/listing/slug |
| - | Other | 80 | dofollow w/ badge | BADGE-GATED, code collected | waiting on PR #12 |
| - | Third | 68 | | NEEDS USER: captcha, tab left open | |
| PR | site #12 | | | Footer "Featured on" row | https://github.com/... |
```

Use consistent status words so the report can be built from the log: SUBMITTED,
LIVE, SCHEDULED <date>, DRAFT, BADGE-GATED, NEEDS USER, NEEDS DECISION, PAID-ONLY,
SKIPPED <reason>.

Keep private management links (edit links with hashes, status pages) in the log only.
They give control of a listing, so don't put them in chat or in anything published.

## Final report

Re-check live status before writing. Then use this structure:

```markdown
<One sentence: N submitted, how many live now, how many have launch dates, how many
need the user.>

<One sentence reminder if badges were added: keep them, removing one can get that
listing pulled.>

## Submitted (nothing needed from you)
| # | Directory | DR | Link type | Status | When it goes live |
|--:|---|--:|---|---|---|
<Order: live now, then fixed dates (soonest first), then "in review" with a stated
time, then "in review, no date given".>

## Needs you
| Directory | DR | What you need to do | When it would go live |
<Exact steps: where to click, what to type or post, and what happens after.>

## Needs your decision
| Directory | DR | What the free listing needs |
<Engagement gates, extra badges beyond the budget, profiles to create.>

## Skipped
<Grouped by reason: paid-only, badge-gated beyond budget, captcha, broken or dead,
not relevant. One line per group, naming the directories.>

<Closing line: nothing was paid for and every upsell was declined, if true. Where the
full log lives.>
```

Guidelines:

- Give real dates: today's date plus a stated review time ("72 hours, so by 6 Oct").
  If a directory gave no timeline, write "no date given". Don't estimate.
- Be honest about link types. "dofollow only if top 3 that day" and "nofollow on the
  free tier" matter to someone choosing which badges to keep.
- Flag low-odds submissions, for example a directory that says it rejects most free
  listings.
- Name every directory once, in exactly one section.
