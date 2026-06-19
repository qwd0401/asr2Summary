import { app, BrowserWindow, shell } from 'electron';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isDev = !app.isPackaged;

let mainWindow = null;
let flaskProcess = null;

function startFlask() {
  const port = process.env.PORT || 5000;
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  flaskProcess = spawn(pythonCmd, ['app.py'], {
    cwd: isDev ? path.join(__dirname, '..') : path.join(process.resourcesPath, 'app'),
    env: { ...process.env, PORT: String(port), FLASK_ENV: 'production' },
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  flaskProcess.stdout.on('data', (data) => {
    console.log(`[Flask] ${data.toString().trim()}`);
  });

  flaskProcess.stderr.on('data', (data) => {
    console.error(`[Flask] ${data.toString().trim()}`);
  });

  flaskProcess.on('error', (err) => {
    console.error('Failed to start Flask:', err);
  });

  return port;
}

function waitForServer(port, timeout = 15000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const check = () => {
      import('http')
        .then((http) => {
          http
            .get(`http://127.0.0.1:${port}/`, (res) => {
              if (res.statusCode === 200 || res.statusCode === 302) {
                resolve();
              } else {
                setTimeout(check, 300);
              }
            })
            .on('error', () => {
              if (Date.now() - start > timeout) {
                reject(new Error('Flask server timeout'));
              } else {
                setTimeout(check, 300);
              }
            });
        })
        .catch(() => setTimeout(check, 300));
    };
    check();
  });
}

function createWindow(port) {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: 'MeetAssistant',
    icon: path.join(__dirname, '..', 'static', 'icon-512.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.loadURL(`http://127.0.0.1:${port}`);

  // Open external links in system browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http')) shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  const port = startFlask();
  try {
    await waitForServer(port);
    createWindow(port);
  } catch (err) {
    console.error('Server failed to start:', err);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (flaskProcess) {
    flaskProcess.kill();
    flaskProcess = null;
  }
  app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    const port = process.env.PORT || 5000;
    createWindow(port);
  }
});
