import type { AppDefinition } from '../types/app'

/**
 * App Registry — hard-coded list of all available Yiy-Workstation apps.
 *
 * Each entry mirrors the Python AppDefinition in vckb/apps/<id>.py.
 * v0.2.0 uses hard-coded data; v0.3.0 may switch to JSON config.
 */
export const APP_REGISTRY: AppDefinition[] = [
  // ── Tools ──
  {
    id: 'tomato',
    name: 'Tomato',
    nameZh: '番茄钟',
    description: 'Pomodoro timer — 25min focus sessions',
    icon: '🍅',
    category: 'tool',
    controls: {
      KEY1: 'Start / Pause',
      KEY5: 'Reset',
      Encoder: 'Adjust time',
    },
    module: 'vckb.apps.tomato',
    requires: [],
  },
  {
    id: 'screen_mirror',
    name: 'Screen Mirror',
    nameZh: '屏幕镜像',
    description: 'Real-time PC screen mirroring at ~6 FPS',
    icon: '🖥️',
    category: 'tool',
    controls: {
      KEY1: 'Pause / Resume',
      KEY5: 'Exit',
    },
    module: 'vckb.apps.screen_mirror',
    requires: ['numpy', 'pillow'],
  },
  {
    id: 'voice_meter',
    name: 'Voice Meter',
    nameZh: '语音电平表',
    description: 'Real-time audio spectrum & waveform visualization',
    icon: '🎤',
    category: 'tool',
    controls: {
      KEY5: 'Exit',
    },
    module: 'vckb.apps.voice_meter',
    requires: ['numpy'],
  },

  // ── Games ──
  {
    id: 'breakout',
    name: 'Breakout',
    nameZh: '打砖块',
    description: 'Classic brick breaker — 5 levels, encoder paddle control',
    icon: '🧱',
    category: 'game',
    controls: {
      KEY3: 'Move paddle left',
      KEY4: 'Move paddle right',
      KEY1: 'Launch ball / Restart',
      KEY2: 'Pause / Resume',
      KEY5: 'Exit',
    },
    module: 'vckb.apps.breakout',
    requires: [],
  },
  {
    id: 'tank_battle',
    name: 'Tank Battle',
    nameZh: '坦克大战',
    description: 'Classic tank battle — 5 levels, auto-fire, 3 tank types',
    icon: '🔫',
    category: 'game',
    controls: {
      KEY1: '上移 ↑',
      KEY2: '下移 ↓',
      KEY3: '左移 ←',
      KEY4: '右移 →',
      SWITCH: '暂停 / 继续',
      KEY5: '退出',
      Encoder: '选择坦克',
      'Encoder Btn': '确认选择',
    },
    module: 'vckb.apps.tank_battle',
    requires: ['numpy'],
  },

  // ── Tests ──
  {
    id: 'self_test',
    name: 'Self Test',
    nameZh: '外设自检',
    description: 'Test all peripherals — screen, keys, encoder, mic',
    icon: '🔧',
    category: 'test',
    controls: {
      'KEY1~5': 'Press to test',
      Encoder: 'Rotate to test',
      'Encoder Btn': 'Reset counter',
      Switch: 'Toggle to test',
      Mic: 'Speak to test',
    },
    module: 'vckb.apps.self_test',
    requires: [],
  },
  {
    id: 'image_test',
    name: 'Image Test',
    nameZh: '位图传输测试',
    description: '4-stage push_frame validation: gradient, compare, solids, full-screen',
    icon: '🖼️',
    category: 'test',
    controls: {
      KEY5: 'Skip stage / Exit',
    },
    module: 'vckb.apps.image_test',
    requires: ['numpy', 'pillow'],
  },
]

/** Get apps grouped by category (for UI display) */
export function getAppsByCategory(): Record<string, AppDefinition[]> {
  const grouped: Record<string, AppDefinition[]> = {}
  for (const app of APP_REGISTRY) {
    if (!grouped[app.category]) {
      grouped[app.category] = []
    }
    grouped[app.category].push(app)
  }
  return grouped
}

/** Find an app by ID */
export function getAppById(id: string): AppDefinition | undefined {
  return APP_REGISTRY.find((a) => a.id === id)
}
