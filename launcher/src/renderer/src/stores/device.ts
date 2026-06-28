import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { DeviceStatus } from '@types/app'

export const useDeviceStore = defineStore('device', () => {
  const status = ref<DeviceStatus>('disconnected')
  const port = ref<string | null>(null)
  const scanning = ref(false)

  let _unsub: (() => void) | null = null

  async function scan(): Promise<void> {
    if (scanning.value) return
    scanning.value = true
    try {
      const result = await window.electronAPI.scanDevice()
      if (result) {
        status.value = result.status
        port.value = result.port
      }
    } catch {
      status.value = 'disconnected'
    } finally {
      scanning.value = false
    }
  }

  function startListening(): void {
    _unsub = window.electronAPI.onDeviceChanged((data) => {
      status.value = data.status
      port.value = data.port
    })
  }

  function stopListening(): void {
    _unsub?.()
    _unsub = null
  }

  // Auto-start
  startListening()

  return { status, port, scanning, scan, stopListening }
})
