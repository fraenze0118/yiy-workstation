<script setup lang="ts">
import { useDeviceStore } from '../stores/device'

const store = useDeviceStore()

const statusLabel: Record<string, string> = {
  connected: 'Connected',
  busy: 'In Use',
  disconnected: 'Disconnected',
}
</script>

<template>
  <div
    class="flex items-center gap-3 px-4 py-1.5
           border-b border-gray-200 dark:border-gray-800
           transition-colors duration-300"
    :class="{
      'bg-blue-50 dark:bg-blue-950/30': store.status === 'connected',
      'bg-gray-100 dark:bg-gray-900': store.status !== 'connected',
    }"
  >
    <!-- Status dot with pulse animation when connected -->
    <span class="relative flex h-2.5 w-2.5 flex-shrink-0" aria-hidden="true">
      <span
        class="absolute inline-flex h-full w-full rounded-full"
        :class="{
          'bg-green-500': store.status === 'connected',
          'bg-yellow-500': store.status === 'busy',
          'bg-red-400': store.status === 'disconnected',
        }"
      />
      <span
        v-if="store.status === 'connected'"
        class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"
      />
    </span>

    <!-- Status text -->
    <span class="text-xs text-gray-600 dark:text-gray-400 flex-1">
      <template v-if="store.status === 'connected'">
        Device {{ statusLabel[store.status] }} — <span class="font-mono text-gray-700 dark:text-gray-300">{{ store.port }}</span>
      </template>
      <template v-else-if="store.status === 'busy'">
        <span class="font-mono text-gray-700 dark:text-gray-300">{{ store.port }}</span> is in use — app running
      </template>
      <template v-else>
        Device not connected — insert ESP32-S3 via USB
      </template>
    </span>

    <!-- Refresh / Scan button -->
    <button
      @click="store.scan()"
      :disabled="store.scanning || store.status === 'busy'"
      class="flex items-center gap-1 text-xs px-2.5 py-1 rounded-md
             bg-blue-50 hover:bg-blue-100
             dark:bg-blue-900/30 dark:hover:bg-blue-900/50
             text-blue-600 dark:text-blue-400
             disabled:opacity-40 disabled:cursor-not-allowed
             transition-colors
             focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-1"
      aria-label="Scan for device"
    >
      <svg
        class="w-3 h-3"
        :class="{ 'animate-spin': store.scanning }"
        fill="none" stroke="currentColor" viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
      {{ store.scanning ? 'Scanning' : 'Refresh' }}
    </button>
  </div>
</template>
