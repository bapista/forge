// Secure bridge: lets the FORGE UI run a command on a cluster machine over SSH,
// without exposing Node to the renderer (contextIsolation stays on).
const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('forge', {
  run: (host, user, cmd) => ipcRenderer.invoke('forge:run', { host, user, cmd }),
});
