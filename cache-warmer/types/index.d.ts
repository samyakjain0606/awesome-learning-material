export type WarmPhase =
  | 'idle'
  | 'active'
  | 'small'
  | 'warming'
  | 'compacted'
  | 'cold'
  | 'paused'
  | 'stopped'

export type WarmState = {
  phase: WarmPhase
  lastActivityAt: number
  lastPingAt: number
  nextPingAt: number
  pings: number
  pingTokens: number
  contextTokens: number
  errors: number
  note: string
}

declare module 'claude-code' {
  interface PluginState {
    'cache-warmer': { warm: WarmState }
  }
}
