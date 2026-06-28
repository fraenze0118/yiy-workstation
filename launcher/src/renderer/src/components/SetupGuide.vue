<script setup lang="ts">
/**
 * Setup guide overlay — shown when Python or vckb SDK is not installed.
 * Guides the user through installing prerequisites.
 */
defineProps<{
  system: {
    python: { found: boolean; version: string; path: string }
    vckb: { found: boolean; path: string }
    localSdk: string
    requiredPkgs: { name: string; found: boolean }[]
  }
}>()

const emit = defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="absolute inset-0 z-20 flex items-center justify-center
              bg-gray-100/95 dark:bg-gray-950/95 backdrop-blur-sm">
    <div class="w-full max-w-md mx-4 p-8 rounded-2xl
                bg-white dark:bg-gray-800
                shadow-xl border border-gray-200 dark:border-gray-700">
      <!-- Header -->
      <div class="text-center mb-6">
        <span class="text-5xl block mb-3">⚙️</span>
        <h2 class="text-xl font-bold text-gray-900 dark:text-white">
          Setup Required
        </h2>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Install the following to use Yiy-Workstation
        </p>
      </div>

      <!-- Checklist -->
      <div class="space-y-3 mb-6">
        <!-- Python -->
        <div class="flex items-center gap-3 p-3 rounded-lg"
             :class="system.python.found
               ? 'bg-green-50 dark:bg-green-900/20'
               : 'bg-red-50 dark:bg-red-900/20'">
          <span class="text-lg">{{ system.python.found ? '✅' : '❌' }}</span>
          <div class="flex-1">
            <p class="text-sm font-medium text-gray-800 dark:text-gray-200">Python 3.10+</p>
            <p class="text-xs text-gray-500 dark:text-gray-400">
              {{ system.python.found ? system.python.version : 'Download from python.org' }}
            </p>
          </div>
        </div>

        <!-- vckb SDK -->
        <div class="flex items-center gap-3 p-3 rounded-lg"
             :class="system.vckb.found
               ? 'bg-green-50 dark:bg-green-900/20'
               : 'bg-yellow-50 dark:bg-yellow-900/20'">
          <span class="text-lg">{{ system.vckb.found ? '✅' : '⚠️' }}</span>
          <div class="flex-1">
            <p class="text-sm font-medium text-gray-800 dark:text-gray-200">vckb SDK</p>
            <p class="text-xs text-gray-500 dark:text-gray-400">
              {{ system.vckb.found
                ? `SDK found — ${system.vckb.path}`
                : 'Launcher auto-adds sdk/python/ to PYTHONPATH' }}
            </p>
          </div>
        </div>

        <!-- Optional packages -->
        <div
          v-for="pkg in system.requiredPkgs"
          :key="pkg.name"
          class="flex items-center gap-3 p-3 rounded-lg"
          :class="pkg.found
            ? 'bg-green-50 dark:bg-green-900/20'
            : 'bg-gray-50 dark:bg-gray-900/30'">
          <span class="text-lg">{{ pkg.found ? '✅' : '⬜' }}</span>
          <div class="flex-1">
            <p class="text-sm font-medium text-gray-800 dark:text-gray-200">
              {{ pkg.name }}
              <span class="text-xs text-gray-400 font-normal">
                {{ pkg.found ? '' : '(optional — needed for some apps)' }}
              </span>
            </p>
          </div>
        </div>
      </div>

      <!-- Auto PYTHONPATH hint -->
      <p class="text-[10px] text-gray-400 dark:text-gray-600 text-center mb-4">
        PYTHONPATH auto-set to: {{ system.localSdk }}
      </p>

      <!-- Action -->
      <button
        @click="emit('retry')"
        class="w-full px-6 py-2.5 rounded-xl
               bg-blue-500 hover:bg-blue-600 active:bg-blue-700
               text-white font-semibold text-sm
               transition-colors duration-150
               focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2
               dark:focus:ring-offset-gray-800"
      >
        {{ system.python.found && system.vckb.found ? 'Continue' : 'Check Again' }}
      </button>
    </div>
  </div>
</template>
