import { app, BrowserWindow, shell, nativeImage } from 'electron'
import { join, resolve } from 'path'
import { is } from '@electron-toolkit/utils'
import { DeviceManager } from './device-manager'
import { AppRunner } from './app-runner'
import { registerIpcHandlers } from './ipc-handlers'

// ── Module-level refs for cleanup ──
let deviceMgr: DeviceManager | null = null
let appRunner: AppRunner | null = null

function createWindow(): void {
  const win = new BrowserWindow({
    width: 680,
    height: 520,
    minWidth: 560,
    minHeight: 420,
    title: 'Yiy-Workstation',
    frame: false,
    backgroundColor: '#0f172a',
    icon: resolve(__dirname, '../../../resources/icon.ico'),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })

  // ── Set taskbar + window icon ──
  const iconPath = resolve(__dirname, '../../../resources/icon.ico')
  const icon = nativeImage.createFromPath(iconPath)
  if (!icon.isEmpty()) {
    win.setIcon(icon)
  }

  // ── Windows taskbar identity ──
  if (process.platform === 'win32') {
    app.setAppUserModelId('com.vckb.launcher')
  }

  // Open external links in default browser
  win.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  // ── Debug: log SDK path ──
  const sdkPath = require('path').resolve(__dirname, '../../../sdk/python')
  console.log('[Main] Local SDK path:', sdkPath)
  console.log('[Main] PYTHONPATH will be set to:', sdkPath)

  // ── Core: Device Manager ──
  deviceMgr = new DeviceManager(win)

  // ── Core: App Runner ──
  // When an app exits, re-scan the device port
  appRunner = new AppRunner(win, () => {
    deviceMgr?.markAppExited()
  })

  // ── IPC Handlers ──
  registerIpcHandlers(win, deviceMgr, appRunner)

  // ── Start device polling ──
  deviceMgr.startPolling()

  // DevTools in dev mode
  if (is.dev) {
    win.webContents.openDevTools({ mode: 'detach' })
  }

  // Load renderer
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'))
  }

  // Cleanup on window close
  win.on('closed', () => {
    deviceMgr?.stopPolling()
    deviceMgr = null
    appRunner = null
  })
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  deviceMgr?.stopPolling()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  // Force-stop any running app before quitting
  if (appRunner?.getStatus() === 'running') {
    console.log('[Main] Stopping running app before quit...')
    appRunner.stop()
  }
  deviceMgr?.stopPolling()
})
