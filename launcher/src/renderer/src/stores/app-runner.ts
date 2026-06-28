import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AppDefinition, RunnerStatus } from '@types/app'

export const useAppRunnerStore = defineStore('app-runner', () => {
  const status = ref<RunnerStatus>('idle')
  const runningApp = ref<AppDefinition | null>(null)
  const elapsed = ref('00:00:00')
  const startTime = ref(0)

  let _timer: ReturnType<typeof setInterval> | null = null
  let _unsubExit: (() => void) | null = null
  let _unsubError: (() => void) | null = null

  async function launch(app: AppDefinition): Promise<void> {
    status.value = 'launching'
    try {
      const ok = await window.electronAPI.launchApp(app.id)
      if (ok) {
        runningApp.value = app
        status.value = 'running'
        startTime.value = Date.now()
        _timer = setInterval(() => {
          const s = Math.floor((Date.now() - startTime.value) / 1000)
          elapsed.value = new Date(s * 1000).toISOString().slice(11, 19)
        }, 250)
      } else {
        status.value = 'idle'
      }
    } catch {
      status.value = 'idle'
    }
  }

  async function stop(): Promise<void> {
    status.value = 'stopping'
    try {
      await window.electronAPI.stopApp()
    } catch {
      // Force-idle if IPC fails
    }
  }

  function startListening(): void {
    _unsubExit = window.electronAPI.onAppExited(({ appId: _appId, code: _code }) => {
      if (_timer) { clearInterval(_timer); _timer = null }
      status.value = 'idle'
      runningApp.value = null
    })
    _unsubError = window.electronAPI.onAppError((_msg) => {
      // Could show toast here in future
    })
  }

  function stopListening(): void {
    _unsubExit?.()
    _unsubError?.()
    if (_timer) clearInterval(_timer)
  }

  startListening()

  return { status, runningApp, elapsed, launch, stop, stopListening }
})
