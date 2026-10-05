import { atom, read, update } from 'claude-code'
import type { EngineInterface, PluginOptions, Register, Timer } from 'claude-code'

import type { WarmPhase, WarmState } from '../types'

// cache-warmer
//
// After each main-thread turn the session's prompt cache is warm. If the
// person goes idle, this mod touches that cache with a silent fork request
// every `pingIntervalMinutes` (under the cache lifetime), so returning inside
// the warm window costs a cache read, not a full re-send. Once the idle time
// passes `warmHours`, pinging stops: a session above `minCompactContextK` is
// compacted once while still warm, a smaller one is simply left to cool.
//
// It never pings a cache that has already lapsed (laptop asleep, timer late),
// and it stops for the day once `dailyBudgetK` keep-alive spend is reached
// across every session, counted in full-price token equivalents.

type Engine = EngineInterface

type Config = {
  pingIntervalMs: number
  cacheTtlMs: number
  warmWindowMs: number
  minPingTokens: number
  minCompactTokens: number
  dailyBudget: number
}

const INITIAL: WarmState = {
  phase: 'idle',
  lastActivityAt: 0,
  lastPingAt: 0,
  nextPingAt: 0,
  pings: 0,
  pingTokens: 0,
  contextTokens: 0,
  errors: 0,
  note: '',
}

const warm = atom({ plugin: 'cache-warmer', key: 'warm' } as const, INITIAL)

const PING_PROMPT = 'Reply with the single word: ok'

const COMPACT_INSTRUCTIONS =
  'The user is resuming this session after a long break. Keep: the current task and its goal, ' +
  'the plan and exactly where it stands, every file touched and what changed in each, decisions ' +
  'made and why, open items and next steps, and any commands, paths or URLs needed to continue.'

// Full-price token equivalents per token, by kind (base input price = 1).
const WEIGHT = { input: 1, cacheWrite: 1.25, cacheRead: 0.1, output: 5 }

const RETRY_MS = 5 * 60_000
const MAX_ERRORS = 3

// Module state: set once per load by register(), read by the functions below.
// A hot reload starts a fresh environment, so the pending timer is dropped
// with it; session.start re-arms from $.state, which the host keeps.
let cfg: Config = configFrom({})
let timer: Timer | null = null

function num(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : fallback
}

function configFrom(options: PluginOptions): Config {
  return {
    pingIntervalMs: num(options.pingIntervalMinutes, 50) * 60_000,
    cacheTtlMs: num(options.cacheTtlMinutes, 60) * 60_000,
    warmWindowMs: num(options.warmHours, 10) * 3_600_000,
    minPingTokens: num(options.minPingContextK, 100) * 1000,
    minCompactTokens: num(options.minCompactContextK, 500) * 1000,
    dailyBudget: num(options.dailyBudgetK, 2000) * 1000,
  }
}

function pad(n: number): string {
  return String(n).padStart(2, '0')
}

function hhmm(ms: number): string {
  const d = new Date(ms)
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function dateKey(ms: number): string {
  const d = new Date(ms)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function k(n: number): string {
  return `${Math.round(n / 1000)}k`
}

function span(ms: number): string {
  const m = Math.max(0, Math.round(ms / 60_000))
  return m < 60 ? `${m}m` : `${Math.floor(m / 60)}h${pad(m % 60)}`
}

function budgetKey(ms: number): string {
  return `budget:${dateKey(ms)}`
}

function offKey(ms: number): string {
  return `off:${dateKey(ms)}`
}

function cancel(): void {
  timer?.cancel()
  timer = null
}

function paint($: Engine, s: WarmState): void {
  switch (s.phase) {
    case 'warming':
      $.ui.status(
        `warm · ${s.pings} ping${s.pings === 1 ? '' : 's'} · next ${hhmm(s.nextPingAt)} · ${k(s.contextTokens)}`,
      )
      break
    case 'compacted':
      $.ui.status(`compacted · ${s.note}`)
      break
    case 'cold':
      $.ui.status(`cold · ${s.note}`)
      break
    case 'paused':
      $.ui.status('warm off for this session · /warm on')
      break
    case 'stopped':
      $.ui.status(`warm stopped · ${s.note}`)
      break
    default:
      $.ui.status(undefined)
  }
}

async function setPhase($: Engine, phase: WarmPhase, note = ''): Promise<WarmState> {
  const s = await update($, warm, (prev): WarmState => ({ ...prev, phase, note, nextPingAt: 0 }))
  paint($, s)
  return s
}

function log($: Engine, text: string): void {
  $.ui.log(`cache-warmer: ${text}`, { to: 'debug' })
}

async function spentToday($: Engine, now: number): Promise<number> {
  return Number((await $.store.get(budgetKey(now))) ?? 0)
}

async function addSpend($: Engine, now: number, equivalents: number): Promise<number> {
  const total = (await spentToday($, now)) + equivalents
  await $.store.set(budgetKey(now), Math.round(total))
  return total
}

async function isOffToday($: Engine, now: number): Promise<boolean> {
  return (await $.store.get(offKey(now))) === true
}

async function schedule($: Engine, delayMs: number): Promise<void> {
  cancel()
  const now = await $.clock.now()
  const wait = Math.max(0, delayMs)
  const s = await update($, warm, (prev): WarmState => ({ ...prev, phase: 'warming', nextPingAt: now + wait }))
  timer = $.clock.after(wait, () => {
    void tick($)
  })
  paint($, s)
}

// Arm the first ping relative to the last time the cache was touched.
async function armFrom($: Engine, touchedAt: number): Promise<void> {
  const now = await $.clock.now()
  const sinceTouch = now - touchedAt
  if (sinceTouch >= cfg.cacheTtlMs) {
    await setPhase($, 'cold', `cache lapsed ${span(sinceTouch - cfg.cacheTtlMs)} ago, nothing to keep warm`)
    return
  }
  await schedule($, cfg.pingIntervalMs - sinceTouch)
}

async function compactWarm($: Engine, s: WarmState): Promise<void> {
  try {
    const r = await $.session.compact({ instructions: COMPACT_INSTRUCTIONS })
    if (r.skip !== undefined) {
      await setPhase($, 'stopped', `compaction skipped: ${r.skip}`)
      return
    }
    const before = r.tokensBefore ?? s.contextTokens
    const after = r.tokensAfter
    const now = await $.clock.now()
    const note = `${hhmm(now)} · ${k(before)}${after !== undefined ? ` → ${k(after)}` : ''} while warm`
    await setPhase($, 'compacted', note)
    $.ui.toast(`cache-warmer: compacted the session while its cache was warm (${k(before)})`)
  } catch (error) {
    await setPhase($, 'stopped', `compaction failed: ${error instanceof Error ? error.message : String(error)}`)
  }
}

async function tick($: Engine): Promise<void> {
  timer = null
  try {
    const s = await read($, warm)
    if (s.phase !== 'warming') return

    const now = await $.clock.now()
    const idleFor = now - s.lastActivityAt
    const sinceTouch = now - Math.max(s.lastActivityAt, s.lastPingAt)

    // 1. The cache has already lapsed (the machine slept, the timer ran late).
    //    Pinging now would pay full price to warm a cache nobody is using.
    if (sinceTouch >= cfg.cacheTtlMs) {
      await setPhase($, 'cold', `cache lapsed after ${span(sinceTouch)} untouched, not re-warmed`)
      return
    }

    // 2. The warm window is over: compact a large session once, let a small one cool.
    if (idleFor >= cfg.warmWindowMs) {
      if (s.contextTokens >= cfg.minCompactTokens) {
        await compactWarm($, s)
      } else {
        await setPhase(
          $,
          'stopped',
          `${span(idleFor)} idle, ${k(s.contextTokens)} under the ${k(cfg.minCompactTokens)} compact line, left to cool`,
        )
      }
      return
    }

    // 3. Switched off for the day, or the shared daily budget is spent.
    if (await isOffToday($, now)) {
      await setPhase($, 'stopped', 'off in every session for today (/warm off all)')
      return
    }
    const spent = await spentToday($, now)
    if (spent >= cfg.dailyBudget) {
      await setPhase($, 'stopped', `daily keep-alive budget reached (${k(spent)} of ${k(cfg.dailyBudget)})`)
      $.ui.toast('cache-warmer: daily keep-alive budget reached, pinging stopped for today')
      return
    }

    // 4. Touch the cache: one tool-less request over the session's own prefix.
    const r = await $.model.fork({ prompt: PING_PROMPT })
    if (!r.isAnswered && r.reason === 'nothing-to-fork') {
      await setPhase($, 'stopped', 'nothing to keep warm yet')
      return
    }
    const u = r.usage
    const equivalents =
      u.input_tokens * WEIGHT.input +
      u.cache_creation_input_tokens * WEIGHT.cacheWrite +
      u.cache_read_input_tokens * WEIGHT.cacheRead +
      u.output_tokens * WEIGHT.output
    if (equivalents > 0) await addSpend($, now, equivalents)

    if (!r.isAnswered) {
      const errors = s.errors + 1
      await update($, warm, (prev): WarmState => ({ ...prev, errors }))
      log($, `ping failed (${r.reason}), attempt ${errors}`)
      if (errors >= MAX_ERRORS) {
        await setPhase($, 'stopped', `${errors} pings failed in a row (${r.reason})`)
        return
      }
      await schedule($, RETRY_MS)
      return
    }

    const total = u.input_tokens + u.cache_read_input_tokens + u.cache_creation_input_tokens
    const hit = total > 0 ? u.cache_read_input_tokens / total : 0

    // 5. The ping found the cache cold: paid once, stop here.
    if (hit < 0.5) {
      await setPhase($, 'cold', `ping at ${hhmm(now)} found the cache cold (${Math.round(hit * 100)}% served), stopped`)
      $.ui.toast('cache-warmer: the cache was already cold, keep-alive stopped for this idle period')
      return
    }

    await update($, warm, (prev): WarmState => ({
      ...prev,
      pings: prev.pings + 1,
      pingTokens: prev.pingTokens + u.cache_read_input_tokens,
      lastPingAt: now,
      contextTokens: total > 0 ? total : prev.contextTokens,
      errors: 0,
    }))
    log($, `ping ${s.pings + 1}: ${k(u.cache_read_input_tokens)} served from cache, ${Math.round(hit * 100)}% hit`)
    await schedule($, cfg.pingIntervalMs)
  } catch (error) {
    log($, `tick failed: ${error instanceof Error ? error.message : String(error)}`)
  }
}

async function statusText($: Engine): Promise<string> {
  const s = await read($, warm)
  const now = await $.clock.now()
  const spent = await spentToday($, now)
  const off = await isOffToday($, now)
  const lines: (string | null)[] = [
    `cache-warmer · ${s.phase}${s.note ? ` · ${s.note}` : ''}`,
    `  context: ${k(s.contextTokens)} tokens`,
    s.lastActivityAt > 0
      ? `  last activity: ${hhmm(s.lastActivityAt)} (${span(now - s.lastActivityAt)} ago)`
      : '  last activity: none yet',
    `  pings this idle period: ${s.pings} (${k(s.pingTokens)} served from cache)`,
    s.phase === 'warming' ? `  next ping: ${hhmm(s.nextPingAt)}` : null,
    `  today's keep-alive spend: ${k(spent)} of ${k(cfg.dailyBudget)} equivalents${off ? ' · off in every session today' : ''}`,
    `  settings: ping every ${span(cfg.pingIntervalMs)} · cache lifetime ${span(cfg.cacheTtlMs)} · warm window ${span(cfg.warmWindowMs)} · ping ≥ ${k(cfg.minPingTokens)} · compact ≥ ${k(cfg.minCompactTokens)}`,
    '  commands: /warm · /warm off · /warm on · /warm off all · /warm on all · /warm now',
  ]
  return lines.filter((line): line is string => line !== null).join('\n')
}

async function onSessionStart($: Engine): Promise<void> {
  await $.command.register({
    name: 'warm',
    description: 'Cache warmer: status, off/on for this session, off all/on all (every session, today), now (ping)',
    argumentHint: '[off|on|off all|on all|now]',
  })

  // After a hot reload or a restart: pick the schedule back up from state.
  const s = await read($, warm)
  if (s.phase === 'warming' && s.lastActivityAt > 0) {
    await armFrom($, Math.max(s.lastActivityAt, s.lastPingAt))
  } else {
    paint($, s)
  }
}

async function onPromptSubmit($: Engine): Promise<void> {
  cancel()
  const s = await update($, warm, (prev): WarmState => ({
    ...prev,
    phase: prev.phase === 'paused' ? 'paused' : 'active',
    nextPingAt: 0,
    note: '',
  }))
  paint($, s)
}

async function onTurnComplete($: Engine): Promise<void> {
  const now = await $.clock.now()
  const { context } = await $.session.usage()
  const tokens = context.tokens ?? 0

  const s = await update($, warm, (prev): WarmState => ({
    ...prev,
    lastActivityAt: now,
    lastPingAt: 0,
    nextPingAt: 0,
    pings: 0,
    pingTokens: 0,
    errors: 0,
    contextTokens: tokens,
    note: '',
    phase: prev.phase === 'paused' ? 'paused' : tokens >= cfg.minPingTokens ? 'warming' : 'small',
  }))

  if (s.phase === 'warming') {
    await schedule($, cfg.pingIntervalMs)
  } else {
    paint($, s)
  }
}

async function resumeHere($: Engine): Promise<string> {
  const s = await update($, warm, (prev): WarmState => ({ ...prev, note: '' })) // drop the "off" note
  if (s.lastActivityAt === 0) {
    await setPhase($, 'idle')
    return 'cache-warmer is on for this session. It arms after the next turn.'
  }
  const { context } = await $.session.usage()
  const tokens = context.tokens ?? s.contextTokens
  await update($, warm, (prev): WarmState => ({ ...prev, contextTokens: tokens }))
  if (tokens < cfg.minPingTokens) {
    await setPhase($, 'small')
    return `cache-warmer is on for this session. Context is ${k(tokens)}, under the ${k(cfg.minPingTokens)} ping line, so nothing to do yet.`
  }
  await armFrom($, Math.max(s.lastActivityAt, s.lastPingAt))
  return statusText($)
}

async function onWarmCommand($: Engine, args: string): Promise<string> {
  const arg = args.trim().toLowerCase().replace(/\s+/g, ' ')
  const now = await $.clock.now()

  // This session only. 'paused' survives later turns, so it stays off until /warm on.
  if (arg === 'off' || arg === 'pause') {
    cancel()
    await setPhase($, 'paused', 'off for this session (/warm off)')
    return 'cache-warmer is off for this session only. Other sessions keep warming. /warm on turns it back on here.'
  }

  if (arg === 'on' || arg === 'resume') {
    const note = (await isOffToday($, now))
      ? ` Note: /warm off all is still in effect for every session today, so nothing will ping until /warm on all.`
      : ''
    return (await resumeHere($)) + note
  }

  // Every session, for the rest of today.
  if (arg === 'off all') {
    cancel()
    await $.store.set(offKey(now), true)
    await setPhase($, 'stopped', 'off in every session for today (/warm off all)')
    return `cache-warmer is off in every session for the rest of ${dateKey(now)}. /warm on all lifts it.`
  }

  if (arg === 'on all') {
    await $.store.delete(offKey(now))
    return `Lifted /warm off all: every session can warm again.\n${await resumeHere($)}`
  }

  if (arg === 'now') {
    const s = await read($, warm)
    if (s.lastActivityAt === 0) return 'Nothing to ping yet: no turn has completed in this session.'
    await update($, warm, (prev): WarmState => ({ ...prev, phase: 'warming' }))
    await tick($)
    return statusText($)
  }

  return statusText($)
}

export const register: Register = (on, options) => {
  cfg = configFrom(options)

  on('session.start', async ($, e, next) => {
    await onSessionStart($)
    return next(e)
  })

  on('prompt.submit', async ($, e, next) => {
    await onPromptSubmit($)
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    if (e.agentId === undefined) await onTurnComplete($) // a subagent's turn leaves the main cache as it was
    return done
  })

  on('session.end', ($, e, next) => {
    cancel()
    return next(e)
  })

  on('command.run', { command: 'warm' }, async ($, e) => ({ text: await onWarmCommand($, e.args) }))
}
