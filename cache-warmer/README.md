# cache-warmer

A Claude Code mod that keeps an idle session's prompt cache warm, then compacts large sessions once
while the cache is still warm. Fewer cold returns, fewer "re-send 400k tokens at full price" moments,
more of your rate limit left for real work.

## The problem

Every message you send re-sends the whole conversation. That is cheap while the conversation is
cached (a cache read costs about a tenth of a fresh read), but the cache only lives for a limited time
(one hour on most accounts). Leave a session idle past that, and your next message re-sends the
entire context uncached. On a 1M-context model that is easily 400k to 500k tokens, billed in full and
counted against your 5-hour and weekly limits. Claude Code warns you with
`new task? /clear to save 230.6k tokens`, but by then the only way to avoid the cost is to throw the
conversation away.

## What the mod does

- After each turn, if the session is above 100k tokens, it arms a 50-minute timer. Your next prompt
  cancels it.
- While you are idle, it sends one silent fork request every 50 minutes with a one-word prompt. The
  request shares the session's prefix, so it is served from cache and refreshes the cache's timer.
  Nothing is added to your transcript.
- After 10 idle hours it stops pinging. If the session is above 500k tokens it compacts once, while
  the cache is still warm, with instructions to keep the task, plan, files touched and open items.
  Smaller sessions are simply left to cool.
- It never pings a cache that has already lapsed (laptop asleep, timer late), stops if a ping finds
  the cache cold, and keeps a daily keep-alive budget shared across all your sessions.

The status line under the prompt shows what it is doing:

```
⚠ cache-warmer: warm · 3 pings · next 16:16 · 225k
⚠ cache-warmer: compacted · 02:40 · 225k → 30k while warm
```

## Install

```
npx degit samyakjain0606/awesome-learning-material/cache-warmer ~/.claude/skills/cache-warmer
```

Plugins in `~/.claude/skills/<name>` load automatically on your next Claude Code session. To try it
in a single session instead: `claude --plugin-dir ~/.claude/skills/cache-warmer`.

Requires a Claude Code build with function-hook mods (2.1.287 or newer).

## Commands

| Command | Does |
| --- | --- |
| `/warm` | status: phase, context size, pings this idle period, today's spend, settings |
| `/warm pause` / `/warm resume` | pause or resume for this session (resume also lifts `off`) |
| `/warm off` | off for the rest of today, in every session |
| `/warm now` | ping right now |

## Settings

All in `/config` (or `pluginConfigs.cache-warmer.options` in settings.json):

| Setting | Default | Meaning |
| --- | --- | --- |
| Ping interval | 50 min | keep it under the cache lifetime |
| Cache lifetime | 60 min | your account's prompt-cache TTL |
| Warm window | 10 h | how long to keep pinging while idle |
| Minimum context to ping | 100k | smaller sessions are left alone |
| Minimum context to compact | 500k | above this, compact once when the warm window ends |
| Daily budget | 2000k | keep-alive spend across all sessions, in full-price token equivalents |

## The honest cost line

A ping reads the whole context from cache, about a tenth of a cold re-send. Twelve pings on a 500k
session cost roughly 1.2 cold returns at the base rate, or about 0.6 if the re-cache is billed at the
one-hour cache-write rate. The win is every time you return inside the window, which is most
workdays. Overnight is roughly break-even, and the 10-hour knob is where you tune it.

## Files

- `hooks/register.ts` — the hooks module
- `types/index.d.ts` — the state contract
- `hooks/warm.test.ts` — tests for `claude plugin test`
- `.claude-plugin/plugin.json` — manifest and settings

MIT.
