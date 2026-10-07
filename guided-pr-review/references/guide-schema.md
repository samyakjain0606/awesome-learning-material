# guide.json

The page's whole narrative comes from this file. The reviewer reads it before the code, so every sentence has to earn its place.

## Shape

```json
{
  "name": "Retry Failed Payments",
  "overview": {
    "summary": ["2-3 sentences: what the PR does and why, in plain words."],
    "steps": ["How the change works end to end, 3-5 numbered steps. `code` allowed."]
  },
  "flow": {
    "caption": "One line naming what flows: 'Shared content reaches a thread'",
    "direction": "LR",
    "nodes": [
      {"id": "retry", "label": "retry_payment()", "status": "added", "chapter": 2, "note": "optional tooltip"}
    ],
    "edges": [
      {"from": "checkout", "to": "retry", "label": "card declined", "status": "added"}
    ]
  },
  "chapters": [
    {
      "title": "Retry a declined card with backoff",
      "tier": "core",
      "explain": ["Paragraph 1: what this code does now.", "Paragraph 2: why, edge cases, what it replaces."],
      "files": [
        {"path": "src/payments/retry.py", "note": "Optional one-liner shown above the diff: where to look."}
      ],
      "watch": [
        {"level": "risk", "path": "src/payments/retry.py", "line": 88, "text": "What is wrong or worth checking, and when it bites."}
      ],
      "ask": ["A question a sharp reviewer would ask about this chapter."],
      "diagrams": [{"kind": "sequence", "title": "…", "actors": [], "steps": []}]
    }
  ],
  "diagrams": [
    {"kind": "state", "title": "Proposal lifecycle", "caption": "…", "start": "pending", "nodes": [], "edges": []}
  ],
  "verdict": {
    "risk": "low | medium | high",
    "summary": "One or two sentences on overall risk and why.",
    "checks": ["Concrete things to do or confirm before approving."]
  },
  "ask": ["2-3 starter questions about the whole PR, shown when the Ask panel is empty."],
  "context_files": ["src/payments/gateway.py"]
}
```

Field notes:
- `name`: 2 to 4 words naming the change. It becomes the page title `#412 Retry Failed Payments`.
- `files[]` entries may be plain path strings.
- `tier`: `core`, `supporting`, `wiring`, `data`, `tests`, `generated` or `docs`.
- `line`: the after-PR line number from `pr_diff.py`'s second column. For a removed line, use its old number and add `"side": "old"`.
- `chapter` in a flow node is 1-based.
- `direction`: `LR` or `TB`. The page switches to the other one when the first is much wider than the card.
- Inline `code` and `**bold**` render in every text field. `path:line` in any text becomes a link to that line.

## Chapters

- One idea per chapter. If the explanation needs the word "also", it is probably two chapters.
- Title each one as an action in plain words, describing what the code now does: "Stage and upload shared files", "Gate every query in the builder". Don't use file names or "Changes to X".
- Order is the reading path: the entry point or core behaviour first, then what supports it, then wiring and config, then data and migrations, then tests, then generated files. Within a chapter, list files in the order someone should read them.
- `explain`: two short paragraphs at most, 25 to 60 words each. Say what happens at runtime and why. Don't restate the diff line by line, and don't praise the code.
- Generated files, lock files and snapshots go in their own `generated` chapter near the end. Say what produced them and that the reviewer should review the generator instead.

## Flow

- Show the runtime path the PR creates or changes: entry point → the new or changed functions and components → where data ends up. Use real symbol names as labels (`useShareSend()`, `ShareInbox`, `POST /v1/payments`).
- 5 to 12 nodes. Include unchanged neighbours (`same`) only where they anchor the path.
- `status` drives the Before/After toggle: `added` nodes vanish under Before, `removed` ones are struck through under After.
- Link every added or changed node to the chapter that explains it. Edge labels are short (1 to 3 words) and only where they say what passes along the edge.
- If the PR has no runtime path (docs, config or test-only changes), leave `flow` out.

## Diagrams

Chapters take `diagrams` (a list), and the top level takes `diagrams` for extra overview pictures. The top-level `flow` stays the headline before/after picture. Every diagram has `kind`, an optional `title` and an optional one-line `caption`. Statuses (`added`, `changed`, `removed`, `same`) drive the colours and the Before/After toggle, and `chapter` (1-based) makes an element clickable.

**flow**: same shape as the top-level flow (`nodes`, `edges`, `direction`). Use it for a pipeline inside one chapter.

**state**: a lifecycle. Use it when the PR adds or changes a status field, a proposal/approval loop, retries, or a job's phases.
```json
{"kind": "state", "title": "Payment retry lifecycle", "start": "pending",
 "nodes": [{"id": "pending", "label": "pending", "status": "same"},
           {"id": "retrying", "label": "retrying", "status": "added", "chapter": 2},
           {"id": "paid", "label": "paid", "status": "same", "end": true}],
 "edges": [{"from": "pending", "to": "retrying", "label": "card declined", "status": "added"},
           {"from": "retrying", "to": "paid", "label": "retry succeeds", "status": "added"}]}
```
`start` draws the entry dot and `end: true` draws a terminal state. Label each edge with the event or call that moves the state.

**sequence**: who calls whom, in order. Use it for request flows across modules or services, approval round-trips, streaming and tool-call protocols.
```json
{"kind": "sequence", "title": "Retry a declined card",
 "actors": [{"id": "api", "label": "checkout API"}, {"id": "retry", "label": "RetryWorker", "status": "added", "chapter": 2},
            {"id": "psp", "label": "payment provider"}],
 "steps": [{"from": "api", "to": "psp", "label": "charge card"},
           {"from": "psp", "to": "api", "label": "declined", "reply": true},
           {"from": "api", "to": "retry", "label": "schedule retry", "status": "added"},
           {"note": "Backs off 1 min, 10 min, 1 h before giving up.", "over": ["retry"]},
           {"divider": "after backoff"},
           {"from": "retry", "to": "psp", "label": "charge card again", "status": "added"}]}
```
`reply: true` draws a dashed return arrow. A step whose `from` equals its `to` draws a self-call. Keep labels to 32 characters or fewer and steps to about 14.

**schema**: data shapes. Use it for new or changed models, request/response bodies, DB tables and enums.
```json
{"kind": "schema", "title": "Payment models",
 "entities": [{"name": "PaymentAttempt", "status": "added", "chapter": 3,
               "fields": [{"name": "attempt_no", "type": "int"}, {"name": "next_retry_at", "type": "datetime | None"}]},
              {"name": "Order", "status": "changed",
               "fields": [{"name": "payment_state", "type": "PaymentState", "status": "added"}]}],
 "links": [{"from": "Order", "to": "PaymentAttempt", "label": "attempts"}]}
```
On a changed entity, mark only the fields that changed. Show the fields that matter to the review (up to about 12), not every field.

The page also draws **How the changed files connect** by itself from the imports between changed files. Don't describe that in guide.json.

## Tests

Leave test files out of `chapters`. The build adds a kept "Tests" chapter at the end with each file's test names and collapsed diffs, outside the review progress. Put a test file in a real chapter only when the test itself is the change (a new harness or fixture framework someone must review). Generated files left out are handled the same way.

## Look closely

- Only things you verified by reading the code. Each one names the condition that triggers it ("when the user names two fields…").
- `risk`: a likely bug, a data or security problem, or a deploy-order hazard. `question`: a design choice or gap to raise with the author. `nit`: small and optional.
- Point at the exact line where a reviewer should look. It renders inline in the diff.
- Zero items is fine. Five weak items train the reviewer to ignore the section.

## Verdict checks

Each check is something the reviewer can actually do: a command, a manual test with real inputs, a deploy-order step, or a file to compare. Avoid generic advice like "make sure tests pass".

## Context files

Add the unchanged files that answers will need: the definitions of types and functions the PR calls, the callers of functions it changes, the enums and tables it checks against. Find them with `rg` in the local clone. Keep to about 15 files and skip anything huge. The build fetches them at the PR head.
