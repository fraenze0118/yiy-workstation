import { contextBridge, ipcRenderer } from 'electron'

// ── 暴露给 Renderer 的安全 API ──
contextBridge.exposeInMainWorld('electronAPI', {
  // ── 系统 ──
  checkSystem: (): Promise<unknown> => ipcRenderer.invoke('system:check'),

  // ── 窗口控制 ──
  minimizeWindow: () => ipcRenderer.invoke('window:minimize'),
  maximizeWindow: () => ipcRenderer.invoke('window:maximize'),
  closeWindow: () => ipcRenderer.invoke('window:close'),
  isMaximized: (): Promise<boolean> => ipcRenderer.invoke('window:isMaximized'),

  // ── 设备 ──
  scanDevice: (): Promise<unknown> => ipcRenderer.invoke('device:scan'),
  getDeviceStatus: (): Promise<unknown> => ipcRenderer.invoke('device:getStatus'),
  getDevicePort: (): Promise<unknown> => ipcRenderer.invoke('device:getPort'),

  // ── 应用 ──
  getAllApps: (): Promise<unknown> => ipcRenderer.invoke('app:getAll'),
  launchApp: (id: string): Promise<unknown> => ipcRenderer.invoke('app:launch', id),
  stopApp: (): Promise<unknown> => ipcRenderer.invoke('app:stop'),
  getAppStatus: (): Promise<unknown> => ipcRenderer.invoke('app:getStatus'),

  // ── Main → Renderer 事件推送 ──
  onDeviceChanged: (cb: (data: unknown) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, data: unknown) => cb(data)
    ipcRenderer.on('device-changed', handler)
    return () => ipcRenderer.removeListener('device-changed', handler)
  },
  onAppExited: (cb: (data: unknown) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, data: unknown) => cb(data)
    ipcRenderer.on('app-exited', handler)
    return () => ipcRenderer.removeListener('app-exited', handler)
  },
  onAppError: (cb: (msg: string) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, msg: string) => cb(msg)
    ipcRenderer.on('app-error', handler)
    return () => ipcRenderer.removeListener('app-error', handler)
  },
})
