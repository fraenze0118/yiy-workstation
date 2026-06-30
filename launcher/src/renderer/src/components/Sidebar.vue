<script setup lang="ts">
import { useDeviceStore } from '../stores/device'
import { useAppRunnerStore } from '../stores/app-runner'
import { computed } from 'vue'

const props = defineProps<{
  selectedCategory: string | null   // null = show all
}>()

const emit = defineEmits<{
  'update:selectedCategory': [value: string | null]
}>()

const device = useDeviceStore()
const runner = useAppRunnerStore()

const statusLabel: Record<string, string> = {
  connected: 'Connected',
  busy: 'In Use',
  disconnected: 'Disconnected',
}

const CATEGORIES = [
  { key: null,  label: 'All Apps' },
  { key: 'tool', label: 'Tools' },
  { key: 'game', label: 'Games' },
  { key: 'test', label: 'Tests' },
]

const isRunning = computed(() => runner.status === 'running')
</script>

<template>
  <aside
    class="flex flex-col w-44 flex-shrink-0 h-full
           bg-slate-100 dark:bg-slate-900
           border-r border-slate-200 dark:border-slate-800
           select-none"
  >
    <!-- Brand -->
    <div class="px-4 pt-4 pb-3">
      <h1 class="text-sm font-bold text-blue-600 dark:text-blue-400 leading-tight">
        Yiy-Workstation
      </h1>
      <p class="text-[11px] text-slate-400 dark:text-slate-600 mt-0.5">
        ESP32-S3 Desktop
      </p>
    </div>

    <!-- Device status -->
    <div class="px-4 py-2.5 mx-3 rounded-lg"
         :class="{
           'bg-blue-50 dark:bg-blue-950/30': device.status === 'connected',
           'bg-slate-200/50 dark:bg-slate-800/50': device.status !== 'connected',
         }">
      <div class="flex items-center gap-2">
        <span class="relative flex h-2 w-2 flex-shrink-0" aria-hidden="true">
          <span class="absolute inline-flex h-full w-full rounded-full"
                :class="{
                  'bg-green-500': device.status === 'connected',
                  'bg-yellow-500': device.status === 'busy',
                  'bg-red-400': device.status === 'disconnected',
                }" />
          <span
            v-if="device.status === 'connected'"
            class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"
          />
        </span>
        <span class="text-xs text-slate-600 dark:text-slate-400 truncate">
          {{ device.status === 'connected' ? device.port : statusLabel[device.status] }}
        </span>
      </div>
      <!-- Scan button -->
      <button
        v-if="device.status !== 'busy'"
        @click="device.scan()"
        :disabled="device.scanning"
        class="w-full mt-1.5 text-[11px] py-1 rounded-md
               text-blue-600 dark:text-blue-400
               hover:bg-blue-100 dark:hover:bg-blue-900/40
               disabled:opacity-40 disabled:cursor-not-allowed
               transition-colors
               focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
        aria-label="Scan for device"
      >
        {{ device.scanning ? 'Scanning…' : 'Refresh' }}
      </button>
    </div>

    <!-- Divider -->
    <div class="mx-4 my-3 h-px bg-slate-200 dark:bg-slate-800" />

    <!-- Category filter -->
    <nav class="flex-1 px-2 space-y-0.5">
      <p class="px-2 mb-1 text-[10px] font-semibold text-slate-400 dark:text-slate-600
                uppercase tracking-wider">
        Apps
      </p>
      <button
        v-for="cat in CATEGORIES"
        :key="cat.key ?? '__all'"
        @click="emit('update:selectedCategory', cat.key)"
        class="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left text-xs
               transition-colors"
        :class="props.selectedCategory === cat.key
          ? 'bg-white dark:bg-slate-800 text-blue-600 dark:text-blue-400 font-medium shadow-sm'
          : 'text-slate-600 dark:text-slate-400 hover:bg-slate-200/50 dark:hover:bg-slate-800/50'"
      >
        <span class="w-4 text-center text-[11px]">
          {{ cat.key === null ? '●' : ['', '🔧', '🎮', '🧪'][['tool','game','test'].indexOf(cat.key ?? '') + 1] || '●' }}
        </span>
        {{ cat.label }}
      </button>
    </nav>

    <!-- Running indicator -->
    <div
      v-if="isRunning"
      class="mx-3 mb-2 px-3 py-1.5 rounded-lg bg-green-50 dark:bg-green-900/20
             text-xs text-green-700 dark:text-green-400 flex items-center gap-2"
    >
      <span class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse flex-shrink-0" />
      <span class="truncate">{{ runner.runningApp?.name }} running</span>
    </div>

    <!-- Footer -->
    <div class="px-4 py-3 border-t border-slate-200 dark:border-slate-800">
      <span class="text-[10px] text-slate-400 dark:text-slate-600">v0.3.1</span>
    </div>
  </aside>
</template>
