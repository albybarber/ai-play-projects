// Manages a list of image/video overlays on the canvas.
export class OverlayManager {
  constructor() {
    this.overlays = []
    this._nextId = 1
  }

  add({ type, src, label, x = 10, y = 10, width = 200, height = 150, opacity = 1.0 }) {
    const id = this._nextId++
    const overlay = { id, type, src, label: label || src, x, y, width, height, opacity, element: null }
    if (type === 'image') {
      const img = new Image()
      img.src = src
      overlay.element = img
    } else if (type === 'video') {
      const vid = document.createElement('video')
      vid.src = src
      vid.loop = true
      vid.muted = true
      vid.play().catch(() => {})
      overlay.element = vid
    }
    this.overlays.push(overlay)
    return id
  }

  remove(id) {
    const idx = this.overlays.findIndex(o => o.id === id)
    if (idx === -1) return
    const o = this.overlays[idx]
    if (o.type === 'video' && o.element) o.element.pause()
    this.overlays.splice(idx, 1)
  }

  update(id, props) {
    const o = this.overlays.find(o => o.id === id)
    if (o) Object.assign(o, props)
  }

  draw(ctx) {
    for (const o of this.overlays) {
      if (!o.element) continue
      ctx.save()
      ctx.globalAlpha = o.opacity
      try {
        ctx.drawImage(o.element, o.x, o.y, o.width, o.height)
      } catch (_) {}
      ctx.restore()
    }
  }

  getAll() {
    return this.overlays.map(({ id, type, label, x, y, width, height, opacity }) =>
      ({ id, type, label, x, y, width, height, opacity })
    )
  }
}
