<script setup lang="ts">
import { computed } from 'vue'
import type { DfuFamily } from '@/lib/dfu'

const props = defineProps<{
  family: DfuFamily
  /** Buttons to light up for the current step. */
  active?: ('volUp' | 'volDown' | 'side' | 'home')[]
}>()

const on = (b: string) => props.active?.includes(b as any) ?? false
const hasHome = computed(() => props.family === 'home')
</script>

<template>
  <!-- A schematic phone: enough to show which edge each button is on, which is
       the part people get wrong. Not meant to resemble a specific model. -->
  <svg viewBox="0 0 120 210" class="h-44 w-auto" role="img"
       :aria-label="`Button positions for ${family}`">
    <rect x="18" y="4" width="84" height="202" rx="14"
          class="fill-card stroke-border" stroke-width="2" />
    <rect x="24" y="12" width="72" height="186" rx="9"
          class="fill-muted/40" />

    <!-- Volume up / down, left edge -->
    <rect x="13" y="46" width="5" height="22" rx="2.5"
          :class="on('volUp') ? 'fill-primary' : 'fill-border'" />
    <rect x="13" y="76" width="5" height="22" rx="2.5"
          :class="on('volDown') ? 'fill-primary' : 'fill-border'" />

    <!-- Side / power, right edge -->
    <rect x="102" y="58" width="5" height="34" rx="2.5"
          :class="on('side') ? 'fill-primary' : 'fill-border'" />

    <!-- Home button, front -->
    <circle v-if="hasHome" cx="60" cy="186" r="9"
            fill="none" stroke-width="2.5"
            :class="on('home') ? 'stroke-primary' : 'stroke-border'" />

    <!-- Notch, on Face ID models only -->
    <rect v-if="family === 'faceid'" x="46" y="12" width="28" height="7" rx="3.5"
          class="fill-border" />
  </svg>
</template>
