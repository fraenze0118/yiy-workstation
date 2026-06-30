<script setup lang="ts">
import type { AppDefinition } from '@types/app'
import { useAppRunnerStore } from '../stores/app-runner'
import { useDeviceStore } from '../stores/device'
import AppIcon from './AppIcon.vue'

const props = defineProps<{ app: AppDefinition }>()
const emit = defineEmits<{ close: [] }>()

const runner = useAppRunnerStore()
const device = useDeviceStore()

const disabled = device.status === 'disconnected' || runner.status !== 'idle'

function onStart(): void {
  if (disabled) return
  runner.launch(props.app)
  emit('close')
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape') emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-40 flex items-center justify-center
             bg-slate-50/80 dark:bg-slate-950/80 backdrop-blur-sm"
      @click.self="emit('close')"
      @keydown="onKeydown"
    >
      <div
        class="w-full max-w-sm mx-4 p-8 rounded-2xl
               bg-white dark:bg-slate-800
               shadow-xl dark:shadow-2xl
               border border-slate-200 dark:border-slate-700
               animate-panel-in"
      >
        <!-- Close button -->
        <button
          @click="emit('close')"
          class="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded-lg
                 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300
                 hover:bg-slate-100 dark:hover:bg-slate-700
                 transition-colors
                 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
          aria-label="Close"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <!-- App icon (large, colored) -->
        <div class="text-center mb-4">
          <AppIcon :app-id="app.id" :size="52" />
        </div>

        <!-- Name -->
        <h2 class="text-lg font-bold text-slate-900 dark:text-white text-center mb-0.5">
          {{ app.name }}
        </h2>
        <p class="text-sm text-slate-500 dark:text-slate-400 text-center mb-4">
          {{ app.nameZh }}
        </p>

        <!-- Description -->
        <p class="text-sm text-slate-600 dark:text-slate-300 text-center leading-snug mb-5">
          {{ app.description }}
        </p>

        <!-- Device Controls -->
        <div
          v-if="Object.keys(app.controls).length"
          class="mb-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-900/50"
        >
          <p class="text-xs text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">
            Device Controls
          </p>
          <div class="space-y-1.5">
            <div
              v-for="(desc, key) in app.controls"
              :key="key"
              class="flex items-center gap-2 text-sm"
            >
              <code class="inline-flex items-center px-2 py-0.5 rounded-md
                           bg-slate-200 dark:bg-slate-700
                           text-xs text-slate-700 dark:text-slate-300
                           font-mono whitespace-nowrap">
                {{ key }}
              </code>
              <span class="text-slate-500 dark:text-slate-400">{{ desc }}</span>
            </div>
          </div>
        </div>

        <!-- Requirements -->
        <div
          v-if="app.requires.length"
          class="mb-5 text-xs text-slate-400 dark:text-slate-500 text-center"
        >
          requires: {{ app.requires.join(', ') }}
        </div>

        <!-- Device disconnected warning -->
        <p
          v-if="device.status === 'disconnected'"
          class="mb-4 text-xs text-amber-600 dark:text-amber-400 text-center"
        >
          Device not connected — insert ESP32-S3 via USB
        </p>

        <!-- Start button -->
        <button
          @click="onStart"
          :disabled="disabled"
          class="w-full px-6 py-3 rounded-xl
                 bg-blue-500 hover:bg-blue-600 active:bg-blue-700
                 disabled:bg-slate-300 dark:disabled:bg-slate-700
                 disabled:text-slate-400 dark:disabled:text-slate-500
                 text-white font-semibold text-sm
                 transition-colors duration-150
                 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2
                 dark:focus-visible:ring-offset-slate-800"
        >
          ▶&nbsp; Start
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
@keyframes panel-in {
  from {
    opacity: 0;
    transform: scale(0.92) translateY(16px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
.animate-panel-in {
  animation: panel-in 280ms cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
</style>
