/** 设备连接状态 */
export type DeviceStatus = 'disconnected' | 'connected' | 'busy'

/** 应用运行状态 */
export type RunnerStatus = 'idle' | 'launching' | 'running' | 'stopping'

/** 应用定义 — 与 Python vckb/apps/base.py AppDefinition 对应 */
export interface AppDefinition {
  id: string              // "tomato"
  name: string            // "Tomato"
  nameZh: string          // "番茄钟"
  description: string     // 简短描述
  icon: string            // emoji "🍅"
  category: 'tool' | 'test' | 'game' | 'demo'

  controls: Record<string, string>
  // { "KEY1": "Start/Pause", "KEY5": "Reset", "Encoder": "Adjust time" }

  module: string          // "vckb.apps.tomato" (Python import path)
  requires: string[]      // ["numpy", "pillow"] 或 []
}
