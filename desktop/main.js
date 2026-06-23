const { app, BrowserWindow, shell, ipcMain } = require('electron');
const path = require('path');
const { execFile } = require('child_process');

// Note: the AppImage sandbox flag is handled at BUILD time, not here — Chromium's setuid
// sandbox aborts before this JS runs, so --no-sandbox must reach the binary from the AppImage
// launcher (AppRun). See desktop/scripts/patch-appimage.sh. The .deb keeps its real sandbox.

// FORGE terminal: run a command on a cluster machine over SSH (non-interactive).
ipcMain.handle('forge:run', (_e, { host, user, cmd }) => new Promise((resolve) => {
  if (!host || !cmd) return resolve({ out: '', err: 'host and command required', code: 1 });
  const target = user ? `${user}@${host}` : host;
  execFile('ssh',
    ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', '-o', 'StrictHostKeyChecking=accept-new', target, cmd],
    { timeout: 30000, maxBuffer: 1024 * 1024 },
    (err, stdout, stderr) => resolve({ out: stdout || '', err: stderr || '', code: err ? (err.code || 1) : 0 }));
}));

function createWindow() {
  const win = new BrowserWindow({
    width: 1180, height: 820, minWidth: 900, minHeight: 600,
    backgroundColor: '#f5f8f6',
    icon: path.join(__dirname, 'build', 'icon.png'),
    autoHideMenuBar: true, titleBarStyle: 'hiddenInset',
    webPreferences: { contextIsolation: true, preload: path.join(__dirname, 'preload.js') },
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
