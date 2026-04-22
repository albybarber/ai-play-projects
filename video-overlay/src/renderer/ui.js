// Wires the config panel DOM to the compositor state.
export function initUI(compositor) {
  const timer = compositor.timer

  // --- Camera selector ---
  const cameraSelect = document.getElementById('camera-select')
  navigator.mediaDevices.enumerateDevices().then(devices => {
    const cams = devices.filter(d => d.kind === 'videoinput')
    cameraSelect.innerHTML = ''
    cams.forEach(cam => {
      const opt = document.createElement('option')
      opt.value = cam.deviceId
      opt.textContent = cam.label || `Camera ${cam.deviceId.slice(0, 8)}`
      cameraSelect.appendChild(opt)
    })
  })

  cameraSelect.addEventListener('change', () => {
    window._startCamera(cameraSelect.value)
  })

  // --- Timer duration input ---
  const durationInput = document.getElementById('timer-duration')
  durationInput.addEventListener('change', () => {
    const parts = durationInput.value.split(':').map(Number)
    const minutes = parts[0] || 0
    const seconds = parts[1] || 0
    timer.setDuration(minutes, seconds)
    updateTimerDisplay()
  })

  // --- Timer controls ---
  document.getElementById('btn-start').addEventListener('click', () => {
    if (timer.state === 'idle' || timer.state === 'paused') {
      timer.start()
    }
    compositor.siren.deactivate()
    updateTimerDisplay()
  })

  document.getElementById('btn-pause').addEventListener('click', () => {
    timer.pause()
    updateTimerDisplay()
  })

  document.getElementById('btn-reset').addEventListener('click', () => {
    timer.reset()
    compositor.siren.deactivate()
    updateTimerDisplay()
  })

  // --- On-expire options ---
  document.getElementById('chk-siren').addEventListener('change', e => {
    compositor.sirenOnExpire = e.target.checked
  })

  document.getElementById('chk-show-timer').addEventListener('change', e => {
    compositor.showTimer = e.target.checked
  })

  // Update timer display every 200ms
  setInterval(updateTimerDisplay, 200)

  function updateTimerDisplay() {
    const el = document.getElementById('timer-display')
    if (el) el.textContent = timer.displayString
    const btn = document.getElementById('btn-start')
    if (btn) {
      btn.textContent = timer.state === 'paused' ? '▶ Resume' : '▶ Start'
      btn.disabled = timer.state === 'running' || timer.state === 'expired'
    }
    const pauseBtn = document.getElementById('btn-pause')
    if (pauseBtn) pauseBtn.disabled = timer.state !== 'running'
    const stateEl = document.getElementById('timer-state')
    if (stateEl) {
      stateEl.textContent = timer.state.toUpperCase()
      stateEl.className = 'timer-state ' + timer.state
    }
  }

  // --- Overlays: Add image/video ---
  document.getElementById('btn-add-overlay').addEventListener('click', async () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*,video/*'
    input.onchange = () => {
      const file = input.files[0]
      if (!file) return
      const src = URL.createObjectURL(file)
      const type = file.type.startsWith('video') ? 'video' : 'image'
      compositor.overlays.add({ type, src, label: file.name })
      renderOverlayList()
    }
    input.click()
  })

  function renderOverlayList() {
    const list = document.getElementById('overlay-list')
    list.innerHTML = ''
    for (const o of compositor.overlays.getAll()) {
      const item = document.createElement('div')
      item.className = 'overlay-item'
      item.innerHTML = `
        <span class="overlay-icon">${o.type === 'video' ? '🎬' : '🖼'}</span>
        <span class="overlay-label" title="${o.label}">${truncate(o.label, 20)}</span>
        <button class="btn-remove" data-id="${o.id}">✕</button>
      `
      item.querySelector('.btn-remove').addEventListener('click', () => {
        compositor.overlays.remove(o.id)
        renderOverlayList()
      })
      list.appendChild(item)
    }
  }

  function truncate(str, n) {
    return str.length > n ? str.slice(0, n - 1) + '…' : str
  }

  // --- Stream ready banner ---
  window.bridge.onStreamReady(({ url }) => {
    const banner = document.getElementById('plugin-banner')
    if (!banner) return
    banner.className = 'plugin-banner ok'
    banner.innerHTML = `
      <span>🎥 Stream live —</span>
      <code id="stream-url" style="
        background:#0a2a0a; padding:2px 8px; border-radius:4px;
        font-family:monospace; font-size:12px; cursor:pointer; user-select:all;
      " title="Click to copy">${url}</code>
      <span style="color:#6b7280; font-size:11px;">In OBS: add Browser Source → Start Virtual Camera</span>
    `
    document.getElementById('stream-url').addEventListener('click', () => {
      navigator.clipboard.writeText(url)
    })
  })

  // Initial state
  updateTimerDisplay()
}
