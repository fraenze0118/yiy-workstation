import { ChildProcess, spawn, execSync } from 'child_process'
import { BrowserWindow } from 'electron'
import { join, resolve } from 'path'
import { tmpdir } from 'os'
import { writeFileSync, unlinkSync, existsSync } from 'fs'
import type { AppDefinition, RunnerStatus } from '../types/app'

// Path to the local Python SDK, relative to the built main process.
// __dirname = launcher/out/main/  →  ../../../sdk/python  →  vc-keyboard/sdk/python
const LOCAL_SDK_PATH = resolve(__dirname, '../../../sdk/python')

/**
 * Three-tier stop strategy for Python subprocess:
 *
 *   L1 (0s):  Write "stop" to signal file → Python poll loop detects, cleans up, exits
 *   L2 (3s):  SIGTERM → graceful shutdown
 *   L3 (5s):  SIGKILL → force kill (TerminateProcess on Windows)
 *
 * Signal file approach is the most reliable cross-platform method:
 *   - Launcher sets VCKB_STOP_SIGNAL env var to a temp file path
 *   - Python app checks os.path.exists(stop_signal) in its poll loop
 *   - On detection, app cleans up (clear screen, stop mic) and exits
 */
export class AppRunner {
  private proc: ChildProcess | null = null
  private app: AppDefinition | null = null
  private status: RunnerStatus = 'idle'
  private sigFile: string | null = null
  private timerL2: ReturnType<typeof setTimeout> | null = null
  private timerL3: ReturnType<typeof setTimeout> | null = null

  private onAppExited: (() => void) | null = null

  constructor(
    private win: BrowserWindow,
    onAppExited?: () => void,
  ) {
    this.onAppExited = onAppExited ?? null
  }

  getStatus(): RunnerStatus {
    return this.status
  }

  getRunningApp(): AppDefinition | null {
    return this.app
  }

  /**
   * Launch a Python app as a child process.
   *
   * Command: python -c "from vckb.apps.<module> import main; main()"
   * Env:      VCKB_STOP_SIGNAL=<tempfile>
   */
  launch(app: AppDefinition): boolean {
    if (this.proc) {
      console.warn('[AppRunner] App already running, stop it first')
      return false
    }

    // Check Python availability
    const pythonCmd = this.findPython()
    if (!pythonCmd) {
      this.win.webContents.send('app-error', 'Python not found. Please install Python 3.10+.')
      return false
    }

    // Check app dependencies
    if (app.requires.length > 0) {
      for (const pkg of app.requires) {
        if (!this.checkPythonPkg(pythonCmd, pkg)) {
          this.win.webContents.send(
            'app-error',
            `Missing Python package: ${pkg}. Run: pip install ${pkg}`,
          )
          return false
        }
      }
    }

    // Create stop signal file path
    this.sigFile = join(tmpdir(), `vckb_stop_${app.id}`)
    // Ensure clean state
    if (existsSync(this.sigFile)) {
      try { unlinkSync(this.sigFile) } catch { /* ignore */ }
    }

    // Build Python code to execute
    const code = `from ${app.module} import main; main()`

    this.status = 'launching'
    this.app = app

    try {
      // Build PYTHONPATH: local SDK takes priority, then existing PYTHONPATH
      const sep = process.platform === 'win32' ? ';' : ':'
      const pythonPath = [LOCAL_SDK_PATH, process.env.PYTHONPATH]
        .filter(Boolean)
        .join(sep)

      this.proc = spawn(pythonCmd, ['-c', code], {
        env: {
          ...process.env,
          PYTHONPATH: pythonPath,
          VCKB_STOP_SIGNAL: this.sigFile,
          PYTHONUNBUFFERED: '1',
        },
        stdio: ['ignore', 'pipe', 'pipe'],
        windowsHide: true,
      })

      // Forward stdout/stderr for debugging
      this.proc.stdout?.on('data', (data: Buffer) => {
        console.log(`[${app.id}] ${data.toString().trim()}`)
      })
      this.proc.stderr?.on('data', (data: Buffer) => {
        console.error(`[${app.id}] ${data.toString().trim()}`)
      })

      this.proc.on('spawn', () => {
        this.status = 'running'
      })

      this.proc.on('error', (err) => {
        console.error(`[AppRunner] spawn error: ${err.message}`)
        this.cleanup()
        this.status = 'idle'
        this.win.webContents.send('app-error', `Failed to launch: ${err.message}`)
      })

      this.proc.on('exit', (code, signal) => {
        console.log(`[AppRunner] ${app.id} exited: code=${code} signal=${signal}`)
        this.cleanup()
        this.status = 'idle'
        const exitedApp = this.app
        this.app = null
        this.win.webContents.send('app-exited', {
          appId: exitedApp?.id ?? 'unknown',
          code: code,
        })
        this.onAppExited?.()
      })

      return true
    } catch (err) {
      console.error('[AppRunner] launch error:', err)
      this.cleanup()
      this.status = 'idle'
      return false
    }
  }

  /**
   * Stop the running app with three-tier cascade.
   */
  stop(): void {
    if (!this.proc || this.status === 'idle') return

    this.status = 'stopping'

    // L1: Write signal file immediately
    if (this.sigFile) {
      try {
        writeFileSync(this.sigFile, 'stop')
        console.log('[AppRunner] L1: signal file written')
      } catch (err) {
        console.error('[AppRunner] L1 failed:', err)
      }
    }

    // L2: SIGTERM after 3 seconds
    this.timerL2 = setTimeout(() => {
      if (this.proc && this.status === 'stopping') {
        console.log('[AppRunner] L2: sending SIGTERM')
        this.proc.kill('SIGTERM')
      }
    }, 3000)

    // L3: SIGKILL after 5 seconds
    this.timerL3 = setTimeout(() => {
      if (this.proc && this.status === 'stopping') {
        console.log('[AppRunner] L3: sending SIGKILL')
        this.proc.kill('SIGKILL')
      }
    }, 5000)
  }

  /** Clean up timers and signal file */
  private cleanup(): void {
    if (this.timerL2) { clearTimeout(this.timerL2); this.timerL2 = null }
    if (this.timerL3) { clearTimeout(this.timerL3); this.timerL3 = null }
    if (this.sigFile && existsSync(this.sigFile)) {
      try { unlinkSync(this.sigFile) } catch { /* ignore */ }
      this.sigFile = null
    }
    this.proc = null
  }

  /** Find Python executable in PATH */
  private findPython(): string | null {
    const candidates =
      process.platform === 'win32'
        ? ['python', 'python3', 'py']
        : ['python3', 'python']

    for (const cmd of candidates) {
      try {
        execSync(`"${cmd}" --version`, { stdio: 'ignore', timeout: 3000 })
        return cmd
      } catch {
        continue
      }
    }
    return null
  }

  /** Check if a Python package is importable */
  // pip package name → Python import name (only where they differ)
  private static IMPORT_NAME: Record<string, string> = {
    pillow: 'PIL',
  }

  private checkPythonPkg(pythonCmd: string, pkg: string): boolean {
    const importName = AppRunner.IMPORT_NAME[pkg] ?? pkg
    const sep = process.platform === 'win32' ? ';' : ':'
    const pythonPath = [LOCAL_SDK_PATH, process.env.PYTHONPATH]
      .filter(Boolean)
      .join(sep)
    try {
      execSync(`"${pythonCmd}" -c "import ${importName}"`, {
        stdio: 'ignore',
        timeout: 5000,
        env: { ...process.env, PYTHONPATH: pythonPath },
      })
      return true
    } catch {
      return false
    }
  }
}
