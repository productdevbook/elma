<script setup lang="ts">
import { onMounted, onUnmounted, ref, useTemplateRef } from 'vue'
import { requestIcon } from '@/composables/useAppIcons'

const props = defineProps<{ bundleId: string; udid: string }>()

const src = ref<string | null>(null)
const root = useTemplateRef<HTMLElement>('root')
let observer: IntersectionObserver | null = null

/** Icons are fetched only once a row scrolls into view — at 4-65 KB each,
 *  loading all of them up front would move tens of megabytes for nothing. */
onMounted(() => {
  observer = new IntersectionObserver(entries => {
    if (!entries.some(e => e.isIntersecting)) return
    observer?.disconnect()
    requestIcon(props.udid, props.bundleId).then(url => { src.value = url })
  }, { rootMargin: '200px' })
  if (root.value) observer.observe(root.value)
})

onUnmounted(() => observer?.disconnect())
</script>

<template>
  <div ref="root" class="size-7 shrink-0 overflow-hidden rounded-[7px] bg-muted">
    <img v-if="src" :src="src" :alt="''" class="size-full object-cover" />
  </div>
</template>
