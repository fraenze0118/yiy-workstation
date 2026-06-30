<script setup lang="ts">
/**
 * App icon — maps app ID to Lucide SVG component + per-app theme color.
 * Each app has a distinct color for visual differentiation at a glance.
 */
import { computed } from 'vue'
import {
  Timer, Monitor, MicVocal, Gamepad2, Swords,
  Wrench, Image,
} from 'lucide-vue-next'
import type { Component } from 'vue'

const props = defineProps<{
  appId: string
  size?: number            // default 24
}>()

const iconMap: Record<string, Component> = {
  tomato:        Timer,
  screen_mirror: Monitor,
  voice_meter:   MicVocal,
  breakout:      Gamepad2,
  tank_battle:   Swords,
  self_test:     Wrench,
  image_test:    Image,
}

/** Per-app theme color (Tailwind text classes) */
const COLOR_MAP: Record<string, string> = {
  tomato:        'text-red-500 dark:text-red-400',
  screen_mirror: 'text-cyan-500 dark:text-cyan-400',
  voice_meter:   'text-violet-500 dark:text-violet-400',
  breakout:      'text-amber-500 dark:text-amber-400',
  tank_battle:   'text-emerald-500 dark:text-emerald-400',
  self_test:     'text-slate-500 dark:text-slate-400',
  image_test:    'text-pink-500 dark:text-pink-400',
}

const icon = computed(() => iconMap[props.appId] ?? Wrench)
const sz = computed(() => props.size ?? 24)
const colorClass = computed(() => COLOR_MAP[props.appId] ?? 'text-blue-500 dark:text-blue-400')
</script>

<template>
  <span :class="colorClass">
    <component :is="icon" :size="sz" :stroke-width="1.75" />
  </span>
</template>
