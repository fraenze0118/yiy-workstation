import { execSync, spawnSync } from 'child_process'
import { BrowserWindow } from 'electron'
import type { DeviceStatus } from '../types/app'

const POLL_INTERVAL_MS = 2000

/**
 * Device detection using Python pyserial — no native Node.js modules.
 *
 * Uses spawnSync to pass arguments directly (no shell quoting issues).
 * Output format is simple line-based text, not JSON, to avoid escaping hell.
 */
export class DeviceManager {
  private status: DeviceStatus = 'disconnected'
  private port: string | null = null
  private timer: ReturnType<typeof setInterval> | null = null
  private scanning = false

  constructor(private win: BrowserWindow) {}

  getStatus(): DeviceStatus { return this.status }
  getPort(): string | null { return this.port }

  scanNow(): { status: DeviceStatus; port: string | null } {
    if (this.scanning) return { status: this.status, port: this.port }
    this.scanning = true

    try {
      const pythonCmd = this.findPython()
      if (!pythonCmd) {
        this.update('disconnected', null)
        return { status: 'disconnected', port: null }
      }

      // Step 1: enumerate COM ports, output one line per port: PORT|VID|PID
      const listScript = [
        'import serial.tools.list_ports',
        'for p in serial.tools.list_ports.comports():',
        '    if p.vid is not None:',
        '        print(f"{p.device}|{p.vid:04X}|{p.pid:04X}")',
      ].join('\n')

      const listRes = spawnSync(pythonCmd, ['-c', listScript], {
        stdio: 'pipe',
        timeout: 5000,
        windowsHide: true,
      })
      const listOut = listRes.stdout.toString().trim()
      const listErr = listRes.stderr.toString().trim()
      if (listErr) console.error('[DeviceManager] list stderr:', listErr)
      console.log('[DeviceManager] COM ports found:', listOut || '(none)')

      let esp32Port: string | null = null
      for (const line of listOut.split('\n')) {
        const parts = line.trim().split('|')
        if (parts.length === 3 && parts[1] === '303A') {
          esp32Port = parts[0]
          break
        }
      }

      if (!esp32Port) {
        this.update('disconnected', null)
        return { status: 'disconnected', port: null }
      }

      // Step 2: verify with *IDN? — print "OK" or "FAIL"
      const verifyScript = [
        'import serial, sys',
        `port = ${JSON.stringify(esp32Port)}`,
        'try:',
        '    sp = serial.Serial(port, 115200, timeout=0.4)',
        '    sp.write(b"*IDN?\\n")',
        '    resp = sp.readline()',
        '    sp.close()',
        '    print("OK" if b"VCK:" in resp else "FAIL")',
        'except Exception as e:',
        '    print(f"FAIL:{e}")',
      ].join('\n')

      const vrfRes = spawnSync(pythonCmd, ['-c', verifyScript], {
        stdio: 'pipe',
        timeout: 5000,
        windowsHide: true,
      })
      const vrfOut = vrfRes.stdout.toString().trim()
      const vrfErr = vrfRes.stderr.toString().trim()
      console.log('[DeviceManager] verify', esp32Port, '→', vrfOut)
      if (vrfErr) console.error('[DeviceManager] verify stderr:', vrfErr)

      if (vrfOut.startsWith('OK')) {
        this.update('connected', esp32Port)
      } else {
        this.update('busy', esp32Port)
      }

      return { status: this.status, port: this.port }
    } catch (err) {
      console.error('[DeviceManager] scan error:', err)
      this.update('disconnected', null)
      return { status: 'disconnected', port: null }
    } finally {
      this.scanning = false
    }
  }

  startPolling(): void {
    this.stopPolling()
    this.scanNow()
    this.timer = setInterval(() => {
      if (this.status !== 'busy') this.scanNow()
    }, POLL_INTERVAL_MS)
  }

  stopPolling(): void {
    if (this.timer) { clearInterval(this.timer); this.timer = null }
  }

  markBusy(): void { this.update('busy', this.port) }

  markAppExited(): void {
    this.status = 'disconnected'
    this.scanNow()
  }

  private update(status: DeviceStatus, port: string | null): void {
    const changed = this.status !== status || this.port !== port
    this.status = status
    this.port = port
    if (changed) {
      this.win.webContents.send('device-changed', { status, port })
    }
  }

  private findPython(): string | null {
    const candidates = process.platform === 'win32'
      ? ['python', 'python3', 'py']
      : ['python3', 'python']
    for (const cmd of candidates) {
      try {
        execSync(`"${cmd}" --version`, { stdio: 'ignore', timeout: 3000, windowsHide: true })
        return cmd
      } catch { continue }
    }
    return null
  }
}
