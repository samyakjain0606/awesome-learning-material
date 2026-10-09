# plan.json

The reader decides from this page whether to build the plan. They should come away knowing what is broken, what will change, what could go wrong and what is theirs to decide, without reading a diff. No code changes are shown. Use diagrams, examples and real numbers.

`example-plan.json` next to this file is a complete plan (4 chapters, 2 decisions). Copy its shape.

## Shape

```json
{
  "name": "Payment Retry Plan",
  "title": "Retry declined card payments instead of cancelling the order",
  "repo": "acme/shop",
  "ref": "main",
  "sha": "3f9c2e1…",
  "ticket": {"id": "SHOP-412", "url": "https://example.com/issues/SHOP-412"},
  "author": "you",
  "root": "~/code/shop",
  "context_files": ["src/payments/checkout.py"],

  "overview": {"summary": ["…"], "steps": ["…"]},
  "flow": {"caption": "…", "direction": "LR", "nodes": [], "edges": []},
  "diagrams": [],
  "chapters": [{
    "title": "Retry soft declines on a backoff schedule",
    "tier": "core",
    "explain": ["…", "…"],
    "touches": ["src/payments/checkout.py:88 · branch on `classify_decline()`"],
    "diagrams": [],
    "examples": [],
    "decisions": [],
    "watch": [{"level": "risk", "path": "src/payments/checkout.py", "line": 88, "text": "…"}],
    "ask": ["…"]
  }],
  "verdict": {"risk": "medium", "summary": "…", "checks": ["…"]},
  "scope": ["What is not changing, one item per line."],
  "ask": ["2-3 starter questions about the whole plan."]
}
```

Header fields:
- `name`: 2 to 4 words, used as the browser tab title ("Payment Retry Plan").
- `title`: the goal as a plain sentence, used as the page heading.
- `ref` / `sha`: the branch and commit the plan is written against. When `root` is a git checkout, the build fills both from it if they are left out. Otherwise set them.
- `ticket`: optional. Adds a link in the header and labels the response with its `id`.
- `root`: the checkout that `context_files` are read from (default: the current directory). It must be at `ref`, because every `path:line` in the plan is a line in these files.
- `context_files`: every file the plan cites, plus the callers and types that answers in the Ask panel will need. Keep it to about 15. The build fails if a `watch` cites a file that is not listed, or a line past the end of the file.

Inline `code` and `**bold**` render in every text field. `path:line` in any text becomes a link that opens the code at that line.

## Overview and flow

- `overview.summary`: 1 or 2 short paragraphs on what is broken and what the plan does. Put the headline number in bold.
- `overview.steps`: 3 to 5 numbered steps, each naming its chapter ("… (chapter 2)").
- `flow`: the runtime path the plan changes, drawn with Before/After. It uses the same shape as the flow in guided-pr-review's `references/guide-schema.md` (the sibling skill folder), section "Flow". Mark nodes and edges `added`, `changed`, `removed` or `same`, and link changed nodes to their chapter. A `removed` edge and an `added` edge from the same node show a path being replaced ("any decline → cancel" becomes "declined → classify").
- `diagrams` (top level): extra overview pictures, rarely needed.

## Chapters

One idea per chapter, in this order:

1. **problem** (usually one): the evidence that the bug or need is real. Use a `stats` example with the headline numbers, a `compare` of what the system sees or does today, and a `chat` or `code` example from a real case. Cite log, trace or ticket IDs in the caption.
2. **core**: the changes that fix it, most important first.
3. **supporting / wiring / data / guard**: changes that the core ones depend on.
4. **rollout** (last): the order of work as a `flow` diagram, the switches, and a `stats` example with the numbers to watch after release (today → target).

Title each chapter as an action in plain words, describing what the system will do: "Retry soft declines on a backoff schedule", "Make every charge idempotent".

Fields:
- `tier`: `problem`, `core`, `supporting`, `wiring`, `data`, `guard`, `rollout` or `docs`.
- `explain`: two short paragraphs at most, 25 to 60 words each. Say what will happen at runtime and why. Name the current functions it changes. Mark proposed names as proposed.
- `touches`: the places in the current code that change, each as `path:line · what changes there`. Use real line numbers at `ref`.
- `diagrams`: `flow`, `state`, `sequence` or `schema`, with the same shapes as guided-pr-review's `references/guide-schema.md`, section "Diagrams". Use `state` for a lifecycle or a failure loop, `schema` for what gets stored, and `sequence` for calls across components. Statuses drive the Before/After toggle.
- `examples`: see below. Each one shows something a paragraph cannot.
- `decisions`: see below.
- `watch`: risks and open questions, pinned to current code. `level` is `risk`, `question` or `nit`. Each one names when it bites and what to do about it. Leave it empty rather than pad it.
- `ask`: 1 to 3 questions a sharp reader would ask about this chapter.

## Examples

Four kinds. `title` names the example, and an optional one-line `caption` says what to notice.

**stats**: headline numbers, which fade in one by one. `tone` is `bad`, `good` or omitted.
```json
{"kind": "stats", "title": "March, all card orders", "items": [
  {"v": "1,240", "l": "orders cancelled on a soft decline", "s": "of 3,100 declines", "tone": "bad"}]}
```

**compare**: today and after the plan, side by side, as text lines. Start a line with `+` for added, `-` for removed, `>` for the current line (bold), or `#` for a dimmed comment.
```json
{"kind": "compare", "title": "The charge request",
 "before": {"label": "today", "lines": ["POST /v1/charges", "amount: 4999"]},
 "after":  {"label": "after the plan", "lines": ["POST /v1/charges", "+Idempotency-Key: ord_1042-attempt_2", "amount: 4999"]}}
```

**chat**: a conversation that plays in turn by turn. `who` is `user`, `bot`, `tool` or `note`. `tone` (`bad` or `good`) colours a bot turn, and `tag` adds a small label. Use real wording from logs or tickets, shortened with "…".
```json
{"kind": "chat", "title": "A support ticket from March", "caption": "Ticket 88213, shortened.", "turns": [
  {"who": "user", "text": "My order got cancelled but my card works fine?"},
  {"who": "bot", "tone": "bad", "text": "Your payment was declined, so the order was cancelled.", "tag": "soft decline"}]}
```

**code**: a short snippet in `text`, highlighted by `lang`. Use it only for a config value, a payload, or a sketch of a key rule, and say "sketch" in the title. The page shows no diffs.
```json
{"kind": "code", "title": "Sketch: retry schedule", "lang": "python", "text": "RETRY_DELAYS = [60, 600, 3600]  # seconds"}
```

## Decisions

Ask only about forks that change what gets built: 2 to 5 for the whole plan. Each one sits on the chapter it changes and also appears on the Decisions tab.

```json
{"id": "schedule", "q": "When does the worker retry?",
 "why": "The gateway says 80% of soft declines that pass do so within one hour.",
 "options": [
   {"value": "1m-10m-1h", "label": "1 min, 10 min, 1 h", "note": "catches timeouts fast; done within the hour", "rec": true},
   {"value": "5m-30m-6h", "label": "5 min, 30 min, 6 h", "note": "catches more insufficient funds; order waits longer"},
   {"value": "once-15m", "label": "Once, after 15 min", "note": "simplest; misses roughly a third of the passes"}]}
```

- `id` is unique across the plan. Exactly one option has `"rec": true`, which is the option the plan assumes.
- `why` gives the fact that decides it, with a number when there is one.
- `note` (12 words at most) says what the option costs or gives. If an option removes a chapter or a step, say so.

## Before we build (verdict) and scope

- `verdict.risk`: `low`, `medium` or `high`. `summary`: one or two sentences on the risk and the one unknown that could change the design.
- `verdict.checks`: things to do or confirm before building: a replay, a config to confirm in production, a manual test with real inputs. The reader ticks them, and the ticked ones go into the response. End with "Pick the N decisions, or keep the suggested ones."
- `scope`: what is not changing, including things that were dropped from the plan and work that gets its own ticket.

## Writing

- Plain words, short sentences, real names from the code. No praise and no filler.
- Every number has a source: logs, traces, a query, the code. Put the IDs in captions.
- Separate today from the plan. "`checkout()` cancels on any decline" is current; "the worker will retry soft declines" is proposed.
- Read every line you cite. A wrong `path:line` costs the reader more than a missing one.
