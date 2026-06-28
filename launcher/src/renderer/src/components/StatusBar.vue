<script setup lang="ts">
import { useDeviceStore } from '../stores/device'
import { useAppRunnerStore } from '../stores/app-runner'
import { computed } from 'vue'

const deviceStore = useDeviceStore()
const runner = useAppRunnerStore()

const statusText = computed(() => {
  if (runner.status === 'running') return `App running — ${runner.elapsed}`
  if (runner.status === 'stopping') return 'Stopping app...'
  if (runner.status === 'launching') return 'Launching...'
  if (deviceStore.status === 'disconnected') return 'No device'
  if (deviceStore.status === 'busy') return 'Device busy'
  return 'Ready'
})

const statusColor = computed(() => {
  if (runner.status === 'running') return 'text-green-600 dark:text-green-400'
  if (runner.status === 'stopping') return 'text-yellow-600 dark:text-yellow-400'
  if (runner.status === 'launching') return 'text-blue-600 dark:text-blue-400'
  if (deviceStore.status === 'disconnected') return 'text-red-500 dark:text-red-400'
  return 'text-gray-500 dark:text-gray-500'
})
</script>

<template>
  <footer
    class="flex items-center justify-between h-6 px-3
           bg-gray-100 dark:bg-gray-900
           border-t border-gray-200 dark:border-gray-800
           text-[10px]"
  >
    <div class="flex items-center gap-2">
      <span class="w-1.5 h-1.5 rounded-full"
            :class="{
              'bg-green-500': deviceStore.status === 'connected',
              'bg-yellow-500': deviceStore.status === 'busy',
              'bg-red-400': deviceStore.status === 'disconnected',
            }" />
      <span :class="statusColor">{{ statusText }}</span>
    </div>
    <span class="text-gray-400 dark:text-gray-600">v0.2.0</span>
  </footer>
</template>
