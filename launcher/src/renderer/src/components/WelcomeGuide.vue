<script setup lang="ts">
/**
 * WelcomeGuide — shown on first successful device connection.
 * Introduces Yiy-Workstation and previews available apps.
 * Dismissed by clicking "Get Started" or any app card.
 */
import { ref, onMounted } from 'vue'
import { Monitor, MicVocal, Gamepad2, Swords } from 'lucide-vue-next'
import { useDeviceStore } from '../stores/device'

const deviceStore = useDeviceStore()
const visible = ref(false)
const dismissed = ref(false)

const WELCOME_KEY = 'vckb-welcome-seen'

onMounted(() => {
  const seen = localStorage.getItem(WELCOME_KEY)
  if (!seen && deviceStore.status === 'connected') {
    visible.value = true
  } else {
    dismissed.value = true
  }
})

function onDismiss(): void {
  localStorage.setItem(WELCOME_KEY, '1')
  visible.value = false
  dismissed.value = true
}

defineExpose({ dismissed })
</script>

<template>
  <Transition name="welcome">
    <div
      v-if="visible"
      class="absolute inset-0 z-30 flex items-center justify-center
             bg-slate-50/90 dark:bg-slate-950/90 backdrop-blur-sm"
      @click.self="onDismiss"
    >
      <div class="w-full max-w-sm mx-6 text-center p-8 rounded-2xl
                  bg-white dark:bg-slate-800
                  shadow-xl dark:shadow-2xl
                  border border-slate-200 dark:border-slate-700">
        <!-- Brand -->
        <div class="mb-5">
          <h1 class="text-xl font-bold text-blue-600 dark:text-blue-400 mb-1">
            Yiy-Workstation
          </h1>
          <p class="text-sm text-slate-500 dark:text-slate-400">
            Your ESP32-S3 Desktop Companion
          </p>
        </div>

        <!-- Device status -->
        <div class="inline-flex items-center gap-2 px-3 py-1.5 mb-6 rounded-full
                    bg-green-50 dark:bg-green-900/30
                    text-green-700 dark:text-green-400 text-sm font-medium">
          <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          Device Ready — {{ deviceStore.port }}
        </div>

        <!-- App previews -->
        <p class="text-xs text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3">
          Try an app to get started
        </p>
        <div class="grid grid-cols-4 gap-3 mb-6">
          <div class="flex flex-col items-center gap-1 text-slate-400 dark:text-slate-500">
            <Monitor :size="22" :stroke-width="1.5" />
            <span class="text-[10px]">Mirror</span>
          </div>
          <div class="flex flex-col items-center gap-1 text-slate-400 dark:text-slate-500">
            <MicVocal :size="22" :stroke-width="1.5" />
            <span class="text-[10px]">Voice</span>
          </div>
          <div class="flex flex-col items-center gap-1 text-slate-400 dark:text-slate-500">
            <Gamepad2 :size="22" :stroke-width="1.5" />
            <span class="text-[10px]">Breakout</span>
          </div>
          <div class="flex flex-col items-center gap-1 text-slate-400 dark:text-slate-500">
            <Swords :size="22" :stroke-width="1.5" />
            <span class="text-[10px]">Tank</span>
          </div>
        </div>

        <!-- CTA -->
        <button
          @click="onDismiss"
          class="w-full px-6 py-2.5 rounded-xl
                 bg-blue-500 hover:bg-blue-600 active:bg-blue-700
                 text-white font-semibold text-sm
                 transition-colors duration-150
                 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2
                 dark:focus-visible:ring-offset-slate-800"
        >
          Get Started
        </button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.welcome-enter-active {
  transition: opacity 0.4s ease-out;
}
.welcome-enter-active > div {
  transition: transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.4s ease-out;
}
.welcome-leave-active {
  transition: opacity 0.25s ease-in;
}
.welcome-enter-from {
  opacity: 0;
}
.welcome-enter-from > div {
  opacity: 0;
  transform: scale(0.9) translateY(20px);
}
.welcome-leave-to {
  opacity: 0;
}
</style>
