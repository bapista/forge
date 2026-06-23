const { app, BrowserWindow, shell } = require('electron');
const path = require('path');
function createWindow() {
  const win = new BrowserWindow({
    width: 1180, height: 820, minWidth: 900, minHeight: 600,
    backgroundColor: '#f5f8f6',
    icon: path.join(__dirname, 'build', 'icon.png'),
    autoHideMenuBar: true, titleBarStyle: 'hiddenInset',
    webPreferences: { contextIsolation: true },
  });
  // open external links (e.g. collab-foundry.com.au) in the default browser, not in-app
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
  win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
}
app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
