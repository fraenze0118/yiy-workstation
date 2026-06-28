<script setup lang="ts">
import { onMounted, ref } from 'vue'
import TitleBar from './components/TitleBar.vue'
import DeviceStatus from './components/DeviceStatus.vue'
import AppGrid from './components/AppGrid.vue'
import RunningOverlay from './components/RunningOverlay.vue'
import StatusBar from './components/StatusBar.vue'
import SetupGuide from './components/SetupGuide.vue'
import { useDeviceStore } from './stores/device'

const deviceStore = useDeviceStore()

// ── System check on startup ──
const systemChecked = ref(false)
const systemStatus = ref<any>(null)

async function checkSystem(): Promise<void> {
  try {
    systemStatus.value = await window.electronAPI.checkSystem()
  } catch {
    systemStatus.value = null
  }
  systemChecked.value = true
}

function needsSetup(): boolean {
  if (!systemStatus.value) return false
  const s = systemStatus.value
  return !s.python.found || !s.vckb.found
}

onMounted(() => {
  checkSystem()
  deviceStore.scan()
})
</script>

<template>
  <div
    class="flex flex-col h-screen w-screen select-none
           bg-gray-50 dark:bg-gray-950
           text-gray-900 dark:text-gray-100
           overflow-hidden"
  >
    <TitleBar />
    <DeviceStatus />

    <main class="flex-1 relative min-h-0">
      <!-- Setup guide (shown when Python/vckb missing) -->
      <SetupGuide
        v-if="systemChecked && needsSetup()"
        :system="systemStatus"
        @retry="checkSystem()"
      />

      <!-- App grid (behind setup if both shown) -->
      <AppGrid />

      <!-- Running overlay -->
      <RunningOverlay />
    </main>

    <StatusBar />
  </div>
</template>
