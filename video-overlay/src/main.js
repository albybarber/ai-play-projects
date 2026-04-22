const { app, BrowserWindow, ipcMain, dialog } = require('electron')
const path = require('path')
const vc = require('./virtual-camera')
const installer = require('./installer')

let mainWindow

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 720,
    minWidth: 900,
    minHeight: 600,
    backgroundColor: '#0f0f1a',
    titleBarStyle: 'hiddenInset',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  })

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'))
}

app.whenReady().then(() => {
  vc.init()
  createWindow()

  // First-launch: check plugin installation
  if (!installer.isInstalled()) {
    setTimeout(() => {
      if (!mainWindow) return
      mainWindow.webContents.send('plugin:status', { installed: false })
    }, 1500)
  } else {
    setTimeout(() => {
      mainWindow && mainWindow.webContents.send('plugin:status', { installed: true })
    }, 500)
  }
})

app.on('window-all-closed', () => {
  vc.cleanup()
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

// Receive composited RGBA frame from renderer, forward to virtual camera
ipcMain.on('frame', (_event, rgbaBuffer) => {
  vc.sendFrame(rgbaBuffer)
})

// Install plugin on request
ipcMain.handle('plugin:install', async () => {
  const result = installer.install()
  return result
})

// Check plugin status
ipcMain.handle('plugin:check', async () => {
  return { installed: installer.isInstalled() }
})
