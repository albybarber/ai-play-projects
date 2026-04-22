// Draws an animated red siren overlay onto a canvas context.
// Call draw() each frame when active.
export class Siren {
  constructor() {
    this.active = false
    this.angle = 0
    this.startedAt = null
  }

  activate() {
    this.active = true
    this.startedAt = performance.now()
    this.angle = 0
  }

  deactivate() {
    this.active = false
  }

  draw(ctx, canvasW, canvasH) {
    if (!this.active) return
    const now = performance.now()
    const elapsed = now - this.startedAt

    // Rotate at 2 revolutions/sec
    this.angle = (elapsed / 1000) * Math.PI * 4

    // Flashing red vignette: toggles every 250ms
    const flashOn = Math.floor(elapsed / 250) % 2 === 0
    if (flashOn) {
      const grad = ctx.createRadialGradient(
        canvasW / 2, canvasH / 2, canvasH * 0.2,
        canvasW / 2, canvasH / 2, canvasH * 0.75
      )
      grad.addColorStop(0, 'rgba(200,0,0,0)')
      grad.addColorStop(1, 'rgba(200,0,0,0.55)')
      ctx.fillStyle = grad
      ctx.fillRect(0, 0, canvasW, canvasH)
    }

    // Siren light in bottom-left corner
    const cx = 60
    const cy = canvasH - 60
    const r = 36

    ctx.save()
    ctx.translate(cx, cy)

    // Base dome
    ctx.beginPath()
    ctx.arc(0, 0, r, 0, Math.PI * 2)
    ctx.fillStyle = flashOn ? '#cc0000' : '#880000'
    ctx.fill()
    ctx.strokeStyle = '#ff4444'
    ctx.lineWidth = 2
    ctx.stroke()

    // Rotating light beam
    ctx.save()
    ctx.rotate(this.angle)
    const beam = ctx.createLinearGradient(0, 0, r * 2.5, 0)
    beam.addColorStop(0, 'rgba(255,80,80,0.9)')
    beam.addColorStop(1, 'rgba(255,80,80,0)')
    ctx.fillStyle = beam
    ctx.beginPath()
    ctx.moveTo(0, 0)
    ctx.arc(0, 0, r * 2.5, -0.25, 0.25)
    ctx.closePath()
    ctx.fill()
    ctx.restore()

    // Central bright spot
    const spot = ctx.createRadialGradient(0, 0, 0, 0, 0, r * 0.5)
    spot.addColorStop(0, 'rgba(255,220,220,0.95)')
    spot.addColorStop(1, 'rgba(255,0,0,0)')
    ctx.beginPath()
    ctx.arc(0, 0, r * 0.5, 0, Math.PI * 2)
    ctx.fillStyle = spot
    ctx.fill()

    ctx.restore()

    // "TIME'S UP!" banner
    if (flashOn) {
      ctx.save()
      ctx.font = 'bold 36px system-ui, sans-serif'
      ctx.textAlign = 'left'
      ctx.textBaseline = 'middle'
      const text = "TIME'S UP!"
      const textX = 110
      const textY = canvasH - 60
      const metrics = ctx.measureText(text)
      const pad = 10
      ctx.fillStyle = 'rgba(0,0,0,0.7)'
      ctx.beginPath()
      ctx.roundRect(textX - pad, textY - 24, metrics.width + pad * 2, 48, 6)
      ctx.fill()
      ctx.fillStyle = '#ff4444'
      ctx.fillText(text, textX, textY)
      ctx.restore()
    }
  }
}
