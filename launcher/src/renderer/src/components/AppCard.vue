<script setup lang="ts">
import type { AppDefinition } from '@types/app'
import { useAppRunnerStore } from '../stores/app-runner'
import { useDeviceStore } from '../stores/device'

const props = defineProps<{ app: AppDefinition }>()

const runner = useAppRunnerStore()
const device = useDeviceStore()

const disabled = () => device.status === 'disconnected' || runner.status !== 'idle'

function onLaunch(): void {
  if (disabled()) return
  runner.launch(props.app)
}
</script>

<template>
  <button
    @click="onLaunch"
    :disabled="disabled()"
    class="group relative flex flex-col items-center gap-1.5 p-4 rounded-xl
           bg-white dark:bg-gray-800
           border border-gray-200 dark:border-gray-700
           hover:border-blue-300 dark:hover:border-blue-500
           hover:shadow-md dark:hover:shadow-blue-500/5
           active:scale-[0.98]
           transition-all duration-150 ease-out
           disabled:opacity-40 disabled:cursor-not-allowed
           disabled:hover:border-gray-200 dark:disabled:hover:border-gray-700
           disabled:hover:shadow-none disabled:active:scale-100"
  >
    <!-- Icon -->
    <span class="text-[2rem] leading-none transition-transform duration-200
                 group-hover:scale-110 group-active:scale-95
                 group-disabled:group-hover:scale-100">
      {{ app.icon }}
    </span>

    <!-- Name -->
    <h3 class="font-semibold text-sm text-gray-900 dark:text-white leading-tight">
      {{ app.name }}
    </h3>

    <!-- Chinese name -->
    <p class="text-[11px] text-gray-400 dark:text-gray-500">
      {{ app.nameZh }}
    </p>

    <!-- Tooltip overlay on hover -->
    <div
      class="absolute inset-0 flex flex-col items-center justify-center gap-2
             bg-gray-900/85 dark:bg-black/85 rounded-xl
             opacity-0 group-hover:opacity-100
             group-disabled:group-hover:opacity-0
             transition-opacity duration-200 p-3 pointer-events-none"
    >
      <p class="text-white text-[11px] text-center leading-snug max-w-[140px]">
        {{ app.description }}
      </p>
      <div
        v-if="Object.keys(app.controls).length"
        class="text-white/60 text-[10px] space-y-0.5 text-center"
      >
        <div v-for="(desc, key) in app.controls" :key="key">
          <code class="bg-white/20 px-1 py-px rounded text-[9px]">{{ key }}</code>
          &nbsp;{{ desc }}
        </div>
      </div>
      <div v-if="app.requires.length" class="text-white/40 text-[9px] mt-1">
        requires: {{ app.requires.join(', ') }}
      </div>
    </div>
  </button>
</template>
