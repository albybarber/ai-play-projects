import { Compositor } from './compositor.js'
import { initUI } from './ui.js'

const W = 1280
const H = 720

const canvas = document.getElementById('preview-canvas')
const videoEl = document.getElementById('camera-feed')
canvas.width = W
canvas.height = H

const compositor = new Compositor(canvas, videoEl)

// Send frames to main process at compositor rate
compositor.onFrame((buffer) => {
  window.bridge.sendFrame(buffer)
})

compositor.start()
initUI(compositor)

// Start camera
window._startCamera = async (deviceId) => {
  try {
    if (videoEl.srcObject) {
      videoEl.srcObject.getTracks().forEach(t => t.stop())
    }
    const constraints = {
      video: {
        width: { ideal: W },
        height: { ideal: H },
        frameRate: { ideal: 30 },
        ...(deviceId ? { deviceId: { exact: deviceId } } : {})
      }
    }
    const stream = await navigator.mediaDevices.getUserMedia(constraints)
    videoEl.srcObject = stream
    videoEl.play()
  } catch (e) {
    console.error('Camera error:', e)
  }
}

window._startCamera()
