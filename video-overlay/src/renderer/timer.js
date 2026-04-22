// Timer states: idle | running | paused | expired
export class Timer {
  constructor(onExpire) {
    this.state = 'idle'
    this.totalMs = 5 * 60 * 1000
    this.remainingMs = this.totalMs
    this.startedAt = null
    this.onExpire = onExpire
    this._raf = null
  }

  setDuration(minutes, seconds = 0) {
    this.stop()
    this.totalMs = (minutes * 60 + seconds) * 1000
    this.remainingMs = this.totalMs
    this.state = 'idle'
  }

  start() {
    if (this.state === 'expired') return
    if (this.state === 'running') return
    this.state = 'running'
    this.startedAt = performance.now() - (this.totalMs - this.remainingMs)
    this._tick()
  }

  pause() {
    if (this.state !== 'running') return
    this.state = 'paused'
    this.remainingMs = Math.max(0, this.totalMs - (performance.now() - this.startedAt))
  }

  reset() {
    this.state = 'idle'
    this.remainingMs = this.totalMs
    this.startedAt = null
  }

  stop() {
    this.state = 'idle'
    this.remainingMs = this.totalMs
    this.startedAt = null
  }

  _tick() {
    if (this.state !== 'running') return
    const elapsed = performance.now() - this.startedAt
    this.remainingMs = Math.max(0, this.totalMs - elapsed)
    if (this.remainingMs <= 0) {
      this.remainingMs = 0
      this.state = 'expired'
      this.onExpire && this.onExpire()
      return
    }
    requestAnimationFrame(() => this._tick())
  }

  get displayString() {
    const ms = Math.ceil(this.remainingMs)
    const m = Math.floor(ms / 60000)
    const s = Math.floor((ms % 60000) / 1000)
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }

  get isExpired() { return this.state === 'expired' }
  get isRunning() { return this.state === 'running' }
}
