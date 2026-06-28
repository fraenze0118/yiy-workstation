<script setup lang="ts">
import AppCard from './AppCard.vue'
import { useDeviceStore } from '../stores/device'
import { ref, onMounted, computed } from 'vue'
import type { AppDefinition } from '@types/app'

const deviceStore = useDeviceStore()
const apps = ref<AppDefinition[]>([])
const loading = ref(true)

const categories = computed(() => {
  const grouped: Record<string, AppDefinition[]> = {}
  for (const app of apps.value) {
    const label = app.category === 'tool' ? 'Tools' : 'Tests'
    if (!grouped[label]) grouped[label] = []
    grouped[label].push(app)
  }
  return grouped
})

onMounted(async () => {
  try {
    const all = await window.electronAPI.getAllApps()
    if (Array.isArray(all)) {
      apps.value = all as AppDefinition[]
    }
  } catch (err) {
    console.error('Failed to load apps:', err)
  }
  loading.value = false
})
</script>

<template>
  <div class="h-full overflow-y-auto">
    <!-- Loading state -->
    <div
      v-if="loading"
      class="flex items-center justify-center h-full"
    >
      <div class="flex flex-col items-center gap-3 text-gray-400">
        <svg class="w-8 h-8 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span class="text-sm">Loading apps...</span>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="!apps.length"
      class="flex items-center justify-center h-full"
    >
      <p class="text-sm text-gray-400 dark:text-gray-600">No apps available</p>
    </div>

    <!-- App grid by category -->
    <div v-else class="p-5 space-y-5">
      <template v-for="(groupApps, category) in categories" :key="category">
        <!-- Category heading -->
        <div class="flex items-center gap-2">
          <h3 class="text-[11px] font-semibold text-gray-400 dark:text-gray-500
                     uppercase tracking-widest">
            {{ category }}
          </h3>
          <div class="flex-1 h-px bg-gray-200 dark:bg-gray-800" />
          <span class="text-[10px] text-gray-400">{{ groupApps.length }}</span>
        </div>

        <!-- Card grid -->
        <div class="grid gap-3"
             :class="groupApps.length <= 3
               ? 'grid-cols-3'
               : 'grid-cols-3 sm:grid-cols-4'">
          <AppCard
            v-for="app in groupApps"
            :key="app.id"
            :app="app"
          />
        </div>
      </template>

      <!-- Bottom padding for scroll -->
      <div class="h-4" />
    </div>
  </div>
</template>
