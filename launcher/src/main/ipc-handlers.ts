import { ipcMain, BrowserWindow } from 'electron'
import { execSync } from 'child_process'
import { existsSync } from 'fs'
import { join, resolve } from 'path'
import { DeviceManager } from './device-manager'
import { AppRunner } from './app-runner'
import { APP_REGISTRY, getAppById } from './app-registry'

// Local SDK path (same logic as app-runner.ts)
// __dirname = launcher/out/main/  →  ../../../sdk/python  →  repo/sdk/python
const LOCAL_SDK_PATH = resolve(__dirname, '../../../sdk/python')
const PYTHONPATH_SEP = process.platform === 'win32' ? ';' : ':'

/** Build PYTHONPATH env string: local SDK + existing PYTHONPATH */
function buildPythonPath(): string {
  return [LOCAL_SDK_PATH, process.env.PYTHONPATH].filter(Boolean).join(PYTHONPATH_SEP)
}

// ── Environment Detection ────────────────────────────

interface SystemStatus {
  python: { found: boolean; version: string; path: string }
  vckb: { found: boolean; path: string }
  localSdk: string
  requiredPkgs: { name: string; found: boolean }[]
}

function findPython(): { found: boolean; version: string; path: string } {
  const candidates =
    process.platform === 'win32'
      ? ['python', 'python3', 'py']
      : ['python3', 'python']
  for (const cmd of candidates) {
    try {
      const version = execSync(`"${cmd}" --version`, {
        stdio: 'pipe',
        timeout: 5000,
      })
        .toString()
        .trim()
      return { found: true, version, path: cmd }
    } catch {
      continue
    }
  }
  return { found: false, version: '', path: '' }
}

function checkVckb(pythonCmd: string, pythonPath: string): { found: boolean; path: string } {
  console.log('[SystemCheck] Checking vckb with PYTHONPATH:', pythonPath)
  try {
    const result = execSync(
      `"${pythonCmd}" -c "import vckb; print(vckb.__file__)"`,
      {
        stdio: 'pipe',
        timeout: 5000,
        env: { ...process.env, PYTHONPATH: pythonPath },
      },
    )
      .toString()
      .trim()
    console.log('[SystemCheck] vckb found at:', result)
    return { found: true, path: result }
  } catch (err: any) {
    console.error('[SystemCheck] vckb NOT found:', err.message)
    return { found: false, path: '' }
  }
}

function checkEnvironment(): SystemStatus {
  const python = findPython()
  const pythonPath = buildPythonPath()

  const vckb = python.found
    ? checkVckb(python.path, pythonPath)
    : { found: false, path: '' }

  // pip package name → Python import name (only where they differ)
  const importName: Record<string, string> = { pillow: 'PIL' }

  const requiredPkgs = [
    { name: 'numpy', found: false },
    { name: 'pillow', found: false },
  ]

  if (python.found) {
    for (const pkg of requiredPkgs) {
      const modName = importName[pkg.name] ?? pkg.name
      try {
        execSync(`"${python.path}" -c "import ${modName}"`, {
          stdio: 'ignore',
          timeout: 5000,
          env: { ...process.env, PYTHONPATH: pythonPath },
        })
        pkg.found = true
      } catch {
        pkg.found = false
      }
    }
  }

  return { python, vckb, localSdk: LOCAL_SDK_PATH, requiredPkgs }
}

/**
 * Register all IPC handlers for Renderer ↔ Main communication.
 */
export function registerIpcHandlers(
  win: BrowserWindow,
  deviceMgr: DeviceManager,
  appRunner: AppRunner,
): void {
  // ── System Check ────────────────────────────────────

  ipcMain.handle('system:check', () => {
    return checkEnvironment()
  })

  // ── Window Controls ──────────────────────────────────

  ipcMain.handle('window:minimize', () => win.minimize())
  ipcMain.handle('window:maximize', () => {
    if (win.isMaximized()) win.unmaximize()
    else win.maximize()
  })
  ipcMain.handle('window:close', () => win.close())
  ipcMain.handle('window:isMaximized', () => win.isMaximized())

  // ── Device ────────────────────────────────────────────

  ipcMain.handle('device:scan', async () => {
    return deviceMgr.scanNow()
  })

  ipcMain.handle('device:getStatus', () => {
    return deviceMgr.getStatus()
  })

  ipcMain.handle('device:getPort', () => {
    return deviceMgr.getPort()
  })

  // ── Apps ──────────────────────────────────────────────

  ipcMain.handle('app:getAll', () => {
    return APP_REGISTRY
  })

  ipcMain.handle('app:launch', (_event, id: string) => {
    const app = getAppById(id)
    if (!app) {
      console.error(`[IPC] Unknown app: ${id}`)
      return false
    }

    deviceMgr.markBusy()

    const ok = appRunner.launch(app)
    if (!ok) {
      deviceMgr.markAppExited()
    }
    return ok
  })

  ipcMain.handle('app:stop', () => {
    appRunner.stop()
  })

  ipcMain.handle('app:getStatus', () => {
    return appRunner.getStatus()
  })
}
