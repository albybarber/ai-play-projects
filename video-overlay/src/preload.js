const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('bridge', {
  sendFrame: (buf) => ipcRenderer.send('frame:jpeg', buf),
  onStreamReady: (cb) => ipcRenderer.on('stream:ready', (_e, data) => cb(data))
})
