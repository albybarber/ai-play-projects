const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('bridge', {
  sendFrame: (buf) => ipcRenderer.send('frame', buf),
  installPlugin: () => ipcRenderer.invoke('plugin:install'),
  checkPlugin: () => ipcRenderer.invoke('plugin:check'),
  onPluginStatus: (cb) => ipcRenderer.on('plugin:status', (_e, data) => cb(data))
})
