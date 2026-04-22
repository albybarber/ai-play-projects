const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const http = require('http')

const MJPEG_PORT = 7654
const clients = new Set()
let latestJpeg = null

const VIEWER_HTML = `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #000; width: 100vw; height: 100vh; overflow: hidden; display: flex; align-items: center; justify-content: center; }
  img { width: 100%; height: 100%; object-fit: contain; display: block; }
</style>
</head>
<body>
  <img src="/stream" />
</body>
</html>`

function startMjpegServer() {
  const server = http.createServer((req, res) => {
    if (req.url === '/health') {
      res.writeHead(200)
      res.end('ok')
      return
    }
    if (req.url === '/stream') {
      res.writeHead(200, {
        'Content-Type': 'multipart/x-mixed-replace; boundary=mjpeg_boundary',
        'Cache-Control': 'no-cache, no-store',
        'Connection': 'close',
        'Access-Control-Allow-Origin': '*',
      })
      if (latestJpeg) pushToClient(res, latestJpeg)
      clients.add(res)
      req.on('close', () => clients.delete(res))
      return
    }
    // Viewer page — used by OBS Browser Source
    res.writeHead(200, { 'Content-Type': 'text/html' })
    res.end(VIEWER_HTML)
  })
  server.listen(MJPEG_PORT)
  return server
}

function pushToClient(res, jpeg) {
  try {
    res.write(
      `--mjpeg_boundary\r\nContent-Type: image/jpeg\r\nContent-Length: ${jpeg.length}\r\n\r\n`
    )
    res.write(jpeg)
    res.write('\r\n')
  } catch (_) {
    clients.delete(res)
  }
}

function broadcastFrame(jpegBuffer) {
  latestJpeg = jpegBuffer
  for (const client of clients) pushToClient(client, jpegBuffer)
}

let mainWindow

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 720,
    minWidth: 900,
    minHeight: 600,
    backgroundColor: '#0f0f1a',
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 14, y: 14 },
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  })

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'))
}

app.whenReady().then(() => {
  startMjpegServer()
  createWindow()

  setTimeout(() => {
    mainWindow && mainWindow.webContents.send('stream:ready', {
      url: `http://localhost:${MJPEG_PORT}`,
      port: MJPEG_PORT,
    })
  }, 500)
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

// Receive JPEG frame from renderer, broadcast to all MJPEG clients
ipcMain.on('frame:jpeg', (_event, jpegArrayBuffer) => {
  broadcastFrame(Buffer.from(jpegArrayBuffer))
})
