const fs = require('fs')
const path = require('path')

// Shared frame file paths — DAL plugin reads from these
const FRAME_FILE = '/tmp/voc_frame.bgra'
const SEQ_FILE = '/tmp/voc_seq'

const WIDTH = 1280
const HEIGHT = 720
const FRAME_SIZE = WIDTH * HEIGHT * 4  // BGRA

let frameBuffer = null
let seqBuffer = null
let seq = 0

function init() {
  // Pre-allocate a blank frame file so the plugin can mmap it immediately
  frameBuffer = Buffer.alloc(FRAME_SIZE, 0)
  seqBuffer = Buffer.alloc(8, 0)
  try {
    fs.writeFileSync(FRAME_FILE, frameBuffer)
    fs.writeFileSync(SEQ_FILE, seqBuffer)
  } catch (e) {
    console.error('Failed to create frame files:', e.message)
  }
}

function sendFrame(rgbaBuffer) {
  if (!frameBuffer) return
  // Convert RGBA → BGRA (swap R and B channels)
  for (let i = 0; i < FRAME_SIZE; i += 4) {
    frameBuffer[i]     = rgbaBuffer[i + 2]  // B ← R
    frameBuffer[i + 1] = rgbaBuffer[i + 1]  // G
    frameBuffer[i + 2] = rgbaBuffer[i]      // R ← B
    frameBuffer[i + 3] = rgbaBuffer[i + 3]  // A
  }
  try {
    fs.writeFileSync(FRAME_FILE, frameBuffer)
    seq++
    seqBuffer.writeBigUInt64LE(BigInt(seq), 0)
    fs.writeFileSync(SEQ_FILE, seqBuffer)
  } catch (_) {
    // Non-fatal — plugin may not be installed yet
  }
}

function cleanup() {
  try {
    if (fs.existsSync(FRAME_FILE)) fs.unlinkSync(FRAME_FILE)
    if (fs.existsSync(SEQ_FILE)) fs.unlinkSync(SEQ_FILE)
  } catch (_) {}
}

module.exports = { init, sendFrame, cleanup, WIDTH, HEIGHT }
