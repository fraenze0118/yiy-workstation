<script setup lang="ts">
import type { AppDefinition } from '@types/app'
import { computed } from 'vue'
import { useAppRunnerStore } from '../stores/app-runner'
import { useDeviceStore } from '../stores/device'
import AppIcon from './AppIcon.vue'

const props = defineProps<{ app: AppDefinition }>()
const emit = defineEmits<{ select: [] }>()

const runner = useAppRunnerStore()

const isRunning = computed(() =>
  runner.runningApp?.id === props.app.id && runner.status === 'running'
)

function onClick(): void {
  emit('select')
}
</script>

<template>
  <button
    @click="onClick"
    class="group relative flex flex-col items-start gap-1.5 p-4 rounded-xl text-left w-full
           bg-white dark:bg-slate-800
           border border-slate-200 dark:border-slate-700
           hover:border-slate-300 dark:hover:border-slate-600
           hover:shadow-md dark:hover:shadow-slate-900/30
           active:scale-[0.98]
           transition-all duration-200 ease-out
           focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2
           dark:focus-visible:ring-offset-slate-950"
  >
    <!-- Top row: icon + name + arrow + running dot -->
    <div class="flex items-center gap-2.5 w-full">
      <span class="flex-shrink-0 transition-transform duration-200
                   group-hover:scale-110 group-active:scale-95"
            aria-hidden="true">
        <AppIcon :app-id="app.id" :size="22" />
      </span>
      <div class="flex-1 min-w-0">
        <h3 class="font-semibold text-sm text-slate-900 dark:text-white leading-tight">
          {{ app.name }}
        </h3>
        <p class="text-xs text-slate-400 dark:text-slate-500 truncate">
          {{ app.nameZh }}
        </p>
      </div>
      <!-- Running dot -->
      <span
        v-if="isRunning"
        class="flex-shrink-0 w-2 h-2 rounded-full bg-green-500 animate-pulse"
        aria-label="App running"
      />
      <!-- Arrow -->
      <svg
        v-else
        class="w-4 h-4 text-slate-300 dark:text-slate-600 flex-shrink-0
               group-hover:translate-x-0.5 transition-transform duration-200"
        fill="none" stroke="currentColor" viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
      </svg>
    </div>

    <!-- Description (1 line) -->
    <p class="text-xs text-slate-400 dark:text-slate-500 leading-snug line-clamp-1 pl-8">
      {{ app.description }}
    </p>

    <!-- Requirements tag -->
    <div
      v-if="app.requires.length"
      class="pl-8 text-xs text-slate-300 dark:text-slate-600"
    >
      {{ app.requires.join(', ') }}
    </div>
  </button>
</template>
