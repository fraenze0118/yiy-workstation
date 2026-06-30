<script setup lang="ts">
import AppCard from './AppCard.vue'
import DetailPanel from './DetailPanel.vue'
import { ref, onMounted, computed } from 'vue'
import type { AppDefinition } from '@types/app'

const props = defineProps<{
  selectedCategory?: string | null
}>()

const apps = ref<AppDefinition[]>([])
const loading = ref(true)
const selectedApp = ref<AppDefinition | null>(null)

const CATEGORY_LABELS: Record<string, string> = {
  tool: 'Tools',
  game: 'Games',
  test: 'Tests',
  demo: 'Demos',
}

const filteredApps = computed(() => {
  if (!props.selectedCategory) return apps.value
  return apps.value.filter(a => a.category === props.selectedCategory)
})

const categories = computed(() => {
  const grouped: Record<string, AppDefinition[]> = {}
  for (const app of filteredApps.value) {
    const label = CATEGORY_LABELS[app.category] ?? app.category
    if (!grouped[label]) grouped[label] = []
    grouped[label].push(app)
  }
  return grouped
})

// Flat index for stagger animation
let cardIndex = 0
function nextStaggerDelay(): string {
  return `${cardIndex++ * 40}ms`
}
function resetStagger(): void {
  cardIndex = 0
}

function onSelect(app: AppDefinition): void {
  selectedApp.value = app
}

function onClosePanel(): void {
  selectedApp.value = null
}

onMounted(async () => {
  try {
    const all = await window.electronAPI.getAllApps()
    if (Array.isArray(all)) {
      apps.value = all as AppDefinition[]
    }
  } catch (err) {
    console.error('Failed to load apps:', err)
  }
  resetStagger()
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
      <div class="flex flex-col items-center gap-3 text-slate-400">
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
      <p class="text-sm text-slate-400 dark:text-slate-600">No apps available</p>
    </div>

    <!-- App list by category -->
    <div v-else class="p-5 space-y-5">
      <template v-for="(groupApps, category) in categories" :key="category">
        <!-- Category heading -->
        <div class="flex items-center gap-2">
          <h3 class="text-xs font-semibold text-slate-400 dark:text-slate-500
                     uppercase tracking-widest">
            {{ category }}
          </h3>
          <div class="flex-1 h-px bg-slate-200 dark:bg-slate-800" />
          <span class="text-xs text-slate-400">{{ groupApps.length }}</span>
        </div>

        <!-- Card list (single column, max-w-xl) -->
        <div class="max-w-xl space-y-2">
          <AppCard
            v-for="app in groupApps"
            :key="app.id"
            :app="app"
            :style="{ animationDelay: nextStaggerDelay() }"
            class="animate-card-enter"
            @select="onSelect(app)"
          />
        </div>
      </template>

      <div class="h-4" />
    </div>

    <!-- Detail panel -->
    <DetailPanel
      v-if="selectedApp"
      :app="selectedApp"
      @close="onClosePanel"
    />
  </div>
</template>
