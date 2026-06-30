<script setup lang="ts">
import { onMounted, ref } from 'vue'
import TitleBar from './components/TitleBar.vue'
import Sidebar from './components/Sidebar.vue'
import AppGrid from './components/AppGrid.vue'
import RunningOverlay from './components/RunningOverlay.vue'
import SetupGuide from './components/SetupGuide.vue'
import WelcomeGuide from './components/WelcomeGuide.vue'
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

// ── Category filter ──
const selectedCategory = ref<string | null>(null)  // null = all

onMounted(() => {
  checkSystem()
  deviceStore.scan()
})
</script>

<template>
  <div
    class="flex flex-col h-screen w-screen select-none
           text-slate-900 dark:text-slate-100
           overflow-hidden
           bg-slate-50 dark:bg-slate-950"
    style="background-image: radial-gradient(circle, #cbd5e1 0.5px, transparent 0.5px); background-size: 20px 20px;"
  >
    <TitleBar />

    <div class="flex flex-1 min-h-0">
      <!-- Sidebar -->
      <Sidebar
        :selected-category="selectedCategory"
        @update:selected-category="selectedCategory = $event"
      />

      <!-- Main content -->
      <main class="flex-1 relative min-h-0">
        <!-- Setup guide -->
        <SetupGuide
          v-if="systemChecked && needsSetup()"
          :system="systemStatus"
          @retry="checkSystem()"
        />

        <!-- Welcome guide (first connection only) -->
        <WelcomeGuide />

        <!-- App grid -->
        <AppGrid :selected-category="selectedCategory" />

        <!-- Running overlay -->
        <RunningOverlay />
      </main>
    </div>
  </div>
</template>
