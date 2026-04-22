import { OverlayManager } from './overlays.js'
import { Timer } from './timer.js'
import { Siren } from './siren.js'

export class Compositor {
  constructor(canvas, videoEl) {
    this.canvas = canvas
    this.ctx = canvas.getContext('2d', { willReadFrequently: true })
    this.videoEl = videoEl
    this.overlays = new OverlayManager()
    this.siren = new Siren()
    this.showTimer = true
    this.sirenOnExpire = true
    this.timer = new Timer(() => {
      if (this.sirenOnExpire) this.siren.activate()
    })
    this._running = false
    this._frameCallback = null
    this._lastSend = 0
    this.targetFPS = 25
  }

  start() {
    this._running = true
    this._loop()
  }

  stop() {
    this._running = false
  }

  onFrame(cb) {
    this._frameCallback = cb
  }

  _loop() {
    if (!this._running) return
    const now = performance.now()
    const interval = 1000 / this.targetFPS
    if (now - this._lastSend >= interval) {
      this._render()
      this._lastSend = now
    }
    requestAnimationFrame(() => this._loop())
  }

  _render() {
    const ctx = this.ctx
    const { canvas, videoEl } = this
    const W = canvas.width
    const H = canvas.height

    // 1. Camera feed
    if (videoEl.readyState >= 2) {
      ctx.drawImage(videoEl, 0, 0, W, H)
    } else {
      ctx.fillStyle = '#111'
      ctx.fillRect(0, 0, W, H)
      ctx.fillStyle = '#333'
      ctx.font = '20px system-ui'
      ctx.textAlign = 'center'
      ctx.fillText('Camera initializing…', W / 2, H / 2)
    }

    // 2. Image/video overlays
    this.overlays.draw(ctx)

    // 3. Timer overlay (top-right)
    if (this.showTimer && this.timer.state !== 'idle') {
      this._drawTimer(ctx, W, H)
    }

    // 4. Siren (when expired)
    this.siren.draw(ctx, W, H)

    // 5. Send JPEG frame to main process (skip if previous encode still in flight)
    if (this._frameCallback && !this._encoding) {
      this._encoding = true
      this.canvas.toBlob((blob) => {
        this._encoding = false
        if (blob) blob.arrayBuffer().then(buf => this._frameCallback(buf))
      }, 'image/jpeg', 0.85)
    }
  }

  _drawTimer(ctx, W, H) {
    const text = this.timer.displayString
    const isExpired = this.timer.isExpired
    ctx.save()
    ctx.font = 'bold 32px "SF Mono", "Courier New", monospace'
    ctx.textAlign = 'right'
    ctx.textBaseline = 'top'
    const pad = 12
    const metrics = ctx.measureText(text)
    const boxW = metrics.width + pad * 2
    const boxH = 48
    const x = W - 16 - boxW
    const y = 16
    ctx.fillStyle = isExpired ? 'rgba(180,0,0,0.85)' : 'rgba(0,0,0,0.65)'
    ctx.beginPath()
    ctx.roundRect(x, y, boxW, boxH, 8)
    ctx.fill()
    ctx.fillStyle = isExpired ? '#ff8888' : '#ffffff'
    ctx.fillText(text, W - 16 - pad, y + 8)
    ctx.restore()
  }
}
