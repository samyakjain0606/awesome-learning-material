import { expect, mock, test } from 'claude-code/testing'

const MIN = 60_000
const HOUR = 60 * MIN

type Usage = {
  input_tokens: number
  output_tokens: number
  cache_read_input_tokens: number
  cache_creation_input_tokens: number
}

const hit = (context: number): Usage => ({
  input_tokens: 12,
  output_tokens: 1,
  cache_read_input_tokens: context,
  cache_creation_input_tokens: 0,
})

const miss = (context: number): Usage => ({
  input_tokens: context,
  output_tokens: 1,
  cache_read_input_tokens: 0,
  cache_creation_input_tokens: 0,
})

// The world beneath the plugin: a mocked clock and store, a session of
// `context` tokens, a model whose fork answers from `answers` in order.
const world = ($: any, on: any, context: number, answers: Usage[]) => {
  const clock = mock.clock(on, { now: Date.UTC(2026, 9, 4, 9, 0, 0) })
  mock.store(on)
  const seen = { forks: 0, compacts: 0, status: [] as (string | undefined)[] }
  on('session.start', (_$: any, e: any) => ({ cwd: e.cwd }))
  on('turn.complete', () => ({ text: '' }))
  on('prompt.submit', (_$: any, e: any) => ({ text: e.text }))
  on('command.register', (_$: any, e: any) => ({ command: e.name }))
  on('session.usage', () => ({
    startedAt: 0,
    context: { tokens: context, window: 1_000_000, percent: Math.round(context / 10_000) },
    rateLimits: [],
  }))
  on('model.fork', () => {
    const usage = answers[Math.min(seen.forks, answers.length - 1)] ?? hit(context)
    seen.forks += 1
    return { isAnswered: true, text: 'ok', usage }
  })
  on('session.compact', () => {
    seen.compacts += 1
    return { messages: [], tokensBefore: context, tokensAfter: 30_000 }
  })
  on('ui.status', (_$: any, e: any) => {
    seen.status.push(e.text)
    return {}
  })
  on('ui.toast', () => ({}))
  on('ui.log', () => ({}))
  const start = () => $.session.start({ cwd: '/tmp', surface: 'terminal', isInteractive: true })
  const turn = () =>
    $.turn.complete({ answer: 'done', durationMs: 1000, isAborted: false, turnId: 't1', reason: 'answer' })
  return { clock, seen, start, turn }
}

test('a large idle session is pinged every 50 minutes', async ($, on) => {
  const w = world($, on, 600_000, [hit(600_000)])
  await w.start()
  await w.turn()
  await w.clock.advance(49 * MIN)
  expect(w.seen.forks).toBe(0)
  await w.clock.advance(2 * MIN)
  expect(w.seen.forks).toBe(1)
  await w.clock.advance(50 * MIN)
  expect(w.seen.forks).toBe(2)
  expect(w.seen.status.at(-1)).toMatch(/^warm · 2 pings · next \d\d:\d\d · 600k$/)
})

test('a new prompt cancels the pending ping', async ($, on) => {
  const w = world($, on, 600_000, [hit(600_000)])
  await w.start()
  await w.turn()
  await w.clock.advance(40 * MIN)
  await $.prompt.submit({ text: 'back', wait: false, origin: { kind: 'composer' } })
  await w.clock.advance(30 * MIN)
  expect(w.seen.forks).toBe(0)
})

test('a small session is left alone', async ($, on) => {
  const w = world($, on, 40_000, [hit(40_000)])
  await w.start()
  await w.turn()
  await w.clock.advance(3 * HOUR)
  expect(w.seen.forks).toBe(0)
})

test('a ping that finds the cache cold stops the keep-alive', async ($, on) => {
  const w = world($, on, 600_000, [miss(600_000)])
  await w.start()
  await w.turn()
  await w.clock.advance(50 * MIN)
  expect(w.seen.forks).toBe(1)
  await w.clock.advance(2 * HOUR)
  expect(w.seen.forks).toBe(1)
  expect(w.seen.status.at(-1)).toMatch(/^cold · /)
})

test('after the warm window a session above 500k is compacted once, while warm', async ($, on) => {
  const w = world($, on, 600_000, [hit(600_000)])
  await w.start()
  await w.turn()
  for (let i = 0; i < 12; i += 1) await w.clock.advance(50 * MIN)
  expect(w.seen.forks).toBe(12)
  expect(w.seen.compacts).toBe(0)
  await w.clock.advance(50 * MIN) // idle now past 10 hours
  expect(w.seen.compacts).toBe(1)
  expect(w.seen.forks).toBe(12)
  await w.clock.advance(3 * HOUR)
  expect(w.seen.forks).toBe(12)
  expect(w.seen.status.at(-1)).toMatch(/^compacted · /)
})

test('after the warm window a session under 500k is left to cool', async ($, on) => {
  const w = world($, on, 300_000, [hit(300_000)])
  await w.start()
  await w.turn()
  for (let i = 0; i < 13; i += 1) await w.clock.advance(50 * MIN)
  expect(w.seen.forks).toBe(12)
  expect(w.seen.compacts).toBe(0)
  expect(w.seen.status.at(-1)).toMatch(/^warm stopped · /)
})

test('/warm answers a status, /warm pause stops pings', async ($, on) => {
  const w = world($, on, 600_000, [hit(600_000)])
  await w.start()
  await w.turn()
  const status = await $.command.run({ command: 'warm', args: '' })
  expect(status.text).toMatch(/cache-warmer · warming/)
  await $.command.run({ command: 'warm', args: 'pause' })
  await w.clock.advance(2 * HOUR)
  expect(w.seen.forks).toBe(0)
})
