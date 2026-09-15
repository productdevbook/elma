<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Search, Download } from 'lucide-vue-next'
import { api, type App } from '@/api'
import { formatBytes } from '@/format'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps<{ udid: string }>()

const apps = ref<App[]>([])
const kind = ref<'user' | 'system' | 'all'>('user')
const query = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

const shown = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return apps.value
  return apps.value.filter(a =>
    (a.name ?? '').toLowerCase().includes(q) || a.bundle_id.toLowerCase().includes(q))
})

/** Sideloaded apps won't return from the App Store after a wipe, so they're
 *  the ones worth surfacing rather than burying in a column. */
const sideloadedCount = computed(() => apps.value.filter(a => !a.from_store).length)

async function load() {
  loading.value = true
  error.value = null
  try {
    apps.value = await api.appList(kind.value, props.udid)
  } catch (e: any) {
    error.value = e?.message ?? String(e)
  } finally {
    loading.value = false
  }
}

function exportCsv() {
  const head = ['name', 'bundle_id', 'version', 'build', 'type', 'from_store']
  const rows = shown.value.map(a => [
    a.name ?? '', a.bundle_id, a.version ?? '', a.build ?? '', a.type, a.from_store ? 'yes' : 'no',
  ])
  const csv = [head, ...rows]
    .map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
  const a = document.createElement('a')
  a.href = url
  a.download = 'apps.csv'
  a.click()
  URL.revokeObjectURL(url)
}

watch([() => props.udid, kind], load, { immediate: true })
</script>

<template>
  <div class="flex h-full flex-col">
    <header class="space-y-3 border-b px-6 py-4">
      <div class="flex items-baseline justify-between gap-4">
        <h1 class="text-lg font-semibold tracking-tight">Apps</h1>
        <Button variant="outline" size="sm" :disabled="!shown.length" @click="exportCsv">
          <Download class="size-3.5" /> Export CSV
        </Button>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <div class="relative flex-1 sm:max-w-xs">
          <Search class="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input v-model="query" placeholder="Filter apps" class="h-8 pl-8 text-sm" />
        </div>

        <div class="flex rounded-md border p-0.5">
          <button
            v-for="k in (['user', 'system', 'all'] as const)" :key="k"
            class="rounded px-2.5 py-1 text-xs capitalize transition-colors hover:bg-accent"
            :class="kind === k && 'bg-accent font-medium'"
            @click="kind = k"
          >{{ k }}</button>
        </div>

        <span class="text-xs text-muted-foreground tabular-nums">{{ shown.length }} apps</span>
        <Badge v-if="sideloadedCount" variant="secondary" class="text-[11px]">
          {{ sideloadedCount }} sideloaded
        </Badge>
      </div>
    </header>

    <div class="min-h-0 flex-1 overflow-y-auto">
      <div v-if="loading" class="space-y-2 p-6">
        <Skeleton v-for="i in 8" :key="i" class="h-9 w-full" />
      </div>
      <p v-else-if="error" class="p-6 text-sm text-destructive">{{ error }}</p>
      <p v-else-if="!shown.length" class="p-6 text-sm text-muted-foreground">No apps match.</p>

      <table v-else class="w-full text-sm">
        <thead class="sticky top-0 bg-background/95 backdrop-blur">
          <tr class="border-b text-xs text-muted-foreground">
            <th class="px-6 py-2 text-left font-medium">Name</th>
            <th class="hidden w-[30%] px-3 py-2 text-left font-medium lg:table-cell">Bundle id</th>
            <th class="w-20 px-3 py-2 text-right font-medium">Version</th>
            <th class="w-20 px-3 py-2 text-right font-medium">Size</th>
            <th class="w-28 px-6 py-2 text-right font-medium">Source</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="a in shown" :key="a.bundle_id"
            class="border-b border-border/50 transition-colors hover:bg-muted/50"
          >
            <td class="max-w-0 px-6 py-1.5">
              <div class="flex items-center gap-2.5">
                <AppIcon :bundle-id="a.bundle_id" :udid="udid" />
                <span class="truncate font-medium">{{ a.name ?? '—' }}</span>
              </div>
            </td>
            <td class="hidden max-w-0 truncate px-3 py-2 font-mono text-xs text-muted-foreground lg:table-cell">{{ a.bundle_id }}</td>
            <td class="whitespace-nowrap px-3 py-2 text-right text-xs tabular-nums text-muted-foreground">{{ a.version ?? '—' }}</td>
            <td class="whitespace-nowrap px-3 py-2 text-right text-xs tabular-nums text-muted-foreground">{{ formatBytes(a.size_bytes) }}</td>
            <td class="whitespace-nowrap px-6 py-2 text-right">
              <Badge v-if="!a.from_store" variant="secondary" class="text-[10px]">Sideloaded</Badge>
              <span v-else class="text-xs text-muted-foreground">App Store</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
