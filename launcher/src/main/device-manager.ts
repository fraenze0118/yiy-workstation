import { execSync } from 'child_process'
import { BrowserWindow } from 'electron'
import type { DeviceStatus } from '../types/app'

const POLL_INTERVAL_MS = 2000

/**
 * Device detection using Python's pyserial (no native Node.js modules needed).
 *
 * Why Python instead of node-serialport:
 *   - serialport requires native rebuild (node-gyp + Visual Studio)
 *   - pyserial is already required for the Python SDK
 *   - Python scripts called via execSync, same pattern as AppRunner
 */
export class DeviceManager {
  private status: DeviceStatus = 'disconnected'
  private port: string | null = null
  private timer: ReturnType<typeof setInterval> | null = null
  private scanning = false

  constructor(private win: BrowserWindow) {}

  getStatus(): DeviceStatus {
    return this.status
  }

  getPort(): string | null {
    return this.port
  }

  /**
   * Scan for ESP32-S3 using Python pyserial:
   *   1. python -c "..." enumerates COM ports, filters VID=0x303A
   *   2. python -c "..." opens port, sends *IDN?, reads VCK: response
   */
  scanNow(): { status: DeviceStatus; port: string | null } {
    if (this.scanning) {
      return { status: this.status, port: this.port }
    }
    this.scanning = true

    try {
      const pythonCmd = this.findPython()
      if (!pythonCmd) {
        this.update('disconnected', null)
        return { status: 'disconnected', port: null }
      }

      // Step 1: enumerate COM ports, find ESP32 by VID
      const listScript = `
import json, sys
try:
    import serial.tools.list_ports
    ports = []
    for p in serial.tools.list_ports.comports():
        if p.vid is None:
            continue
        ports.append({"port": p.device, "vid": f"{p.vid:04X}", "pid": f"{p.pid:04X}"})
    print(json.dumps(ports))
except Exception as e:
    print(json.dumps({"error": str(e)}))
`
      const raw = execSync(`"${pythonCmd}" -c "${listScript.replace(/"/g, '\\"')}"`, {
        stdio: 'pipe',
        timeout: 5000,
        windowsHide: true,
      }).toString().trim()

      const result = JSON.parse(raw)
      if (result.error || !Array.isArray(result)) {
        this.update('disconnected', null)
        return { status: 'disconnected', port: null }
      }

      const esp32 = result.find((p: { vid: string }) => p.vid === '303A')
      if (!esp32) {
        this.update('disconnected', null)
        return { status: 'disconnected', port: null }
      }

      // Step 2: verify with *IDN?
      const verifyScript = `
import serial, sys, json
try:
    sp = serial.Serial(${JSON.stringify(esp32.port)}, 115200, timeout=0.4)
    sp.write(b"*IDN?\\n")
    resp = sp.readline()
    sp.close()
    print(json.dumps({"ok": b"VCK:" in resp}))
except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}))
`
      const vrf = execSync(`"${pythonCmd}" -c "${verifyScript.replace(/"/g, '\\"')}"`, {
        stdio: 'pipe',
        timeout: 5000,
        windowsHide: true,
      }).toString().trim()

      const vrfResult = JSON.parse(vrf)
      if (vrfResult.ok) {
        this.update('connected', esp32.port)
      } else {
        // Port exists but can't talk → in use by app
        this.update('busy', esp32.port)
      }

      return { status: this.status, port: this.port }
    } catch {
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
      if (this.status !== 'busy') {
        this.scanNow()
      }
    }, POLL_INTERVAL_MS)
  }

  stopPolling(): void {
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
  }

  markBusy(): void {
    this.update('busy', this.port)
  }

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
    const candidates =
      process.platform === 'win32'
        ? ['python', 'python3', 'py']
        : ['python3', 'python']
    for (const cmd of candidates) {
      try {
        execSync(`"${cmd}" --version`, { stdio: 'ignore', timeout: 3000, windowsHide: true })
        return cmd
      } catch {
        continue
      }
    }
    return null
  }
}
