<script setup lang="ts">
import { useAppRunnerStore } from '../stores/app-runner'
import AppIcon from './AppIcon.vue'

const runner = useAppRunnerStore()
</script>

<template>
  <Transition name="overlay">
    <div
      v-if="runner.runningApp"
      class="absolute inset-0 z-10 flex items-center justify-center
             bg-gray-100/90 dark:bg-gray-950/90 backdrop-blur-sm"
    >
      <div
        class="w-full max-w-xs mx-4 text-center p-8 rounded-2xl
               bg-white dark:bg-gray-800
               shadow-xl dark:shadow-2xl
               border border-gray-200 dark:border-gray-700"
      >
        <!-- App icon -->
        <div class="mb-4">
          <AppIcon :app-id="runner.runningApp.id" :size="48" />
        </div>

        <!-- App name -->
        <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-1">
          {{ runner.runningApp.name }}
        </h2>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-1">
          {{ runner.runningApp.nameZh }}
        </p>

        <!-- Elapsed timer -->
        <div class="flex items-center justify-center gap-1.5 mb-5">
          <span class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
          <span class="font-mono text-sm text-green-600 dark:text-green-400 tabular-nums">
            {{ runner.elapsed }}
          </span>
        </div>

        <!-- Controls hint -->
        <div
          v-if="Object.keys(runner.runningApp.controls).length"
          class="mb-5 p-3 rounded-lg bg-gray-50 dark:bg-gray-900/50
                 text-left text-xs space-y-1"
        >
          <p class="text-gray-400 dark:text-gray-500 text-xs uppercase tracking-wider mb-2">
            Device Controls
          </p>
          <div
            v-for="(desc, key) in runner.runningApp.controls"
            :key="key"
            class="flex items-center gap-2"
          >
            <code class="bg-gray-200 dark:bg-gray-700 px-1.5 py-0.5 rounded
                         text-xs text-gray-700 dark:text-gray-300
                         font-mono whitespace-nowrap">
              {{ key }}
            </code>
            <span class="text-xs text-gray-500 dark:text-gray-400">{{ desc }}</span>
          </div>
        </div>

        <!-- Stop button -->
        <button
          @click="runner.stop()"
          :disabled="runner.status === 'stopping'"
          class="w-full px-6 py-2.5 rounded-xl
                 bg-red-500 hover:bg-red-600 active:bg-red-700
                 disabled:bg-red-300 dark:disabled:bg-red-900/50
                 disabled:text-red-200 dark:disabled:text-red-400
                 text-white font-semibold text-sm
                 transition-colors duration-150
                 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-2
                 dark:focus-visible:ring-offset-gray-800"
        >
          <span v-if="runner.status === 'stopping'" class="flex items-center justify-center gap-2">
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Stopping...
          </span>
          <span v-else>Stop App</span>
        </button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.overlay-enter-active {
  transition: opacity 0.25s ease-out, transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.overlay-leave-active {
  transition: opacity 0.2s ease-in, transform 0.2s ease-in;
}
.overlay-enter-from {
  opacity: 0;
  transform: scale(0.92);
}
.overlay-leave-to {
  opacity: 0;
  transform: scale(0.96);
}
</style>
