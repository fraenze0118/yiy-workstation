import type { DeviceStatus, AppDefinition, RunnerStatus } from '../types/app'

export interface ElectronAPI {
  // Window
  minimizeWindow(): Promise<void>
  maximizeWindow(): Promise<void>
  closeWindow(): Promise<void>
  isMaximized(): Promise<boolean>

  // Device
  scanDevice(): Promise<{ status: DeviceStatus; port: string | null }>
  getDeviceStatus(): Promise<DeviceStatus>
  getDevicePort(): Promise<string | null>

  // Apps
  getAllApps(): Promise<AppDefinition[]>
  launchApp(id: string): Promise<boolean>
  stopApp(): Promise<void>
  getAppStatus(): Promise<RunnerStatus>

  // Events (returns unsubscribe)
  onDeviceChanged(cb: (data: { status: DeviceStatus; port: string | null }) => void): () => void
  onAppExited(cb: (data: { appId: string; code: number | null }) => void): () => void
  onAppError(cb: (msg: string) => void): () => void
}

declare global {
  interface Window {
    electronAPI: ElectronAPI
  }
}
