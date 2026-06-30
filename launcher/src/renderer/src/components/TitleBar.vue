<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const darkMode = ref(false)
const isMaximized = ref(false)

// ── Dark mode toggle ──
function toggleDarkMode(): void {
  darkMode.value = !darkMode.value
  document.documentElement.classList.toggle('dark', darkMode.value)
  localStorage.setItem('vckb-dark-mode', String(darkMode.value))
}

// ── Window controls ──
async function onMinimize(): Promise<void> {
  await window.electronAPI.minimizeWindow()
}

async function onMaximize(): Promise<void> {
  await window.electronAPI.maximizeWindow()
  isMaximized.value = !isMaximized.value
}

async function onClose(): Promise<void> {
  await window.electronAPI.closeWindow()
}

onMounted(() => {
  // Restore dark mode preference
  const saved = localStorage.getItem('vckb-dark-mode')
  if (saved === 'true') {
    darkMode.value = true
    document.documentElement.classList.add('dark')
  }
  // Listen for maximize state changes via polling or OS events
  window.electronAPI.isMaximized().then((v) => (isMaximized.value = v))
})
</script>

<template>
  <header
    class="titlebar-drag flex items-center justify-between h-8 pl-3 pr-1
           bg-gray-100 dark:bg-gray-900
           border-b border-gray-200 dark:border-gray-800"
  >
    <!-- App name -->
    <span class="text-xs font-semibold tracking-wide
                 text-blue-600 dark:text-blue-400">
      Yiy-Workstation
    </span>

    <div class="flex items-center gap-1 titlebar-no-drag">
      <!-- Dark mode toggle -->
      <button
        @click="toggleDarkMode"
        class="w-7 h-7 flex items-center justify-center rounded
               hover:bg-gray-200 dark:hover:bg-gray-700
               text-gray-500 dark:text-gray-400
               transition-colors
               focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2
               dark:focus-visible:ring-offset-gray-900"
        :title="darkMode ? 'Light mode' : 'Dark mode'"
        :aria-label="darkMode ? 'Switch to light mode' : 'Switch to dark mode'"
      >
        <svg v-if="darkMode" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="5" />
          <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
        </svg>
        <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      </button>

      <!-- Divider -->
      <div class="w-px h-4 bg-gray-300 dark:bg-gray-700 mx-0.5" />

      <!-- Minimize -->
      <button
        @click="onMinimize"
        class="w-7 h-7 flex items-center justify-center rounded
               hover:bg-gray-200 dark:hover:bg-gray-700
               text-gray-500 dark:text-gray-400 transition-colors
               focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2
               dark:focus-visible:ring-offset-gray-900"
        title="Minimize"
        aria-label="Minimize window"
      >
        <svg class="w-3 h-3" viewBox="0 0 12 12"><rect x="2" y="5.5" width="8" height="1" fill="currentColor" /></svg>
      </button>

      <!-- Maximize / Restore -->
      <button
        @click="onMaximize"
        class="w-7 h-7 flex items-center justify-center rounded
               hover:bg-gray-200 dark:hover:bg-gray-700
               text-gray-500 dark:text-gray-400 transition-colors
               focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2
               dark:focus-visible:ring-offset-gray-900"
        :title="isMaximized ? 'Restore' : 'Maximize'"
        :aria-label="isMaximized ? 'Restore window' : 'Maximize window'"
      >
        <svg v-if="isMaximized" class="w-3 h-3" viewBox="0 0 12 12">
          <rect x="2.5" y="0.5" width="7" height="7" rx="0.5" fill="none" stroke="currentColor" stroke-width="1" />
          <rect x="4" y="2.5" width="7" height="7" rx="0.5" fill="none" stroke="currentColor" stroke-width="1" />
        </svg>
        <svg v-else class="w-3 h-3" viewBox="0 0 12 12">
          <rect x="1.5" y="1.5" width="9" height="9" rx="1" fill="none" stroke="currentColor" stroke-width="1.2" />
        </svg>
      </button>

      <!-- Close -->
      <button
        @click="onClose"
        class="w-7 h-7 flex items-center justify-center rounded
               hover:bg-red-500 hover:text-white
               text-gray-500 dark:text-gray-400 transition-colors
               focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2
               dark:focus-visible:ring-offset-gray-900"
        title="Close"
        aria-label="Close window"
      >
        <svg class="w-3 h-3" viewBox="0 0 12 12">
          <path d="M3 3l6 6M9 3l-6 6" stroke="currentColor" stroke-width="1.3" fill="none" />
        </svg>
      </button>
    </div>
  </header>
</template>
