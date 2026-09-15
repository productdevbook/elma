<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Smartphone, LayoutGrid, Grid3x3, FolderOpen, Archive, Download, RefreshCw, Eraser } from 'lucide-vue-next'
import { api, type Device, type DeviceInfo } from '@/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

import OverviewView from '@/views/OverviewView.vue'
import AppsView from '@/views/AppsView.vue'
import FilesView from '@/views/FilesView.vue'
import BackupView from '@/views/BackupView.vue'
import VersionsView from '@/views/VersionsView.vue'
import EraseView from '@/views/EraseView.vue'

type Tab = 'overview' | 'apps' | 'files' | 'backup' | 'versions' | 'erase'

const devices = ref<Device[]>([])
const selected = ref<Device | null>(null)
const info = ref<DeviceInfo | null>(null)
const appCount = ref<number | null>(null)
const tab = ref<Tab>('overview')
const loading = ref(false)
const error = ref<string | null>(null)

const nav = [
  { id: 'overview', label: 'Overview', icon: LayoutGrid },
  { id: 'apps', label: 'Apps', icon: Grid3x3 },
  { id: 'files', label: 'Files', icon: FolderOpen },
  { id: 'backup', label: 'Backup', icon: Archive },
  { id: 'versions', label: 'iOS', icon: Download },
  { id: 'erase', label: 'Erase', icon: Eraser },
] as const

async function refresh() {
  loading.value = true
  error.value = null
  try {
    devices.value = await api.deviceList()
    // Keep the current selection if it's still plugged in.
    selected.value = devices.value.find(d => d.udid === selected.value?.udid)
      ?? devices.value[0] ?? null
  } catch (e: any) {
    error.value = e?.message ?? String(e)
  } finally {
    loading.value = false
  }
}

/** Overview and the sidebar badge both need these, so they're fetched once
 *  here rather than twice in two views. */
async function loadDetail() {
  info.value = null
  appCount.value = null
  if (!selected.value?.paired) return
  try {
    info.value = await api.deviceInfo(selected.value.udid)
  } catch { /* the sidebar still works without it */ }
  try {
    appCount.value = (await api.appList('user', selected.value.udid)).length
  } catch { /* count is decoration, not load-bearing */ }
}

const subtitle = computed(() => {
  const d = selected.value
  if (!d) return ''
  const model = info.value?.marketing_name ?? d.model ?? 'Unknown'
  return d.version ? `${model} · iOS ${d.version}` : model
})

watch(selected, loadDetail)
onMounted(refresh)
</script>

<template>
  <div class="flex h-full">
    <!-- Sidebar -->
    <aside class="flex w-56 shrink-0 flex-col border-r bg-sidebar">
      <div class="flex items-center gap-2 px-4 py-3">
        <div class="size-2 rounded-full" :class="selected ? 'bg-emerald-500' : 'bg-muted-foreground/40'" />
        <span class="text-sm font-semibold tracking-tight">elma</span>
        <Button
          variant="ghost" size="icon"
          class="ml-auto size-7"
          :disabled="loading"
          @click="refresh"
        >
          <RefreshCw :class="cn('size-3.5', loading && 'animate-spin')" />
        </Button>
      </div>

      <!-- Device card -->
      <div class="mx-2 mb-2 rounded-lg border bg-card px-3 py-2.5">
        <template v-if="selected">
          <div class="flex items-start gap-2.5">
            <Smartphone class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <div class="min-w-0">
              <p class="truncate text-sm font-medium leading-tight">{{ selected.name ?? 'iPhone' }}</p>
              <p class="mt-0.5 truncate text-xs text-muted-foreground">{{ subtitle }}</p>
            </div>
          </div>
          <Badge v-if="!selected.paired" variant="destructive" class="mt-2 text-[10px]">
            Not paired
          </Badge>
        </template>
        <template v-else-if="loading">
          <Skeleton class="h-4 w-28" />
          <Skeleton class="mt-2 h-3 w-20" />
        </template>
        <p v-else class="text-xs text-muted-foreground">No device</p>
      </div>

      <!-- Device switcher, only when it's an actual choice -->
      <div v-if="devices.length > 1" class="px-2 pb-2">
        <button
          v-for="d in devices" :key="d.udid"
          class="w-full truncate rounded px-2 py-1 text-left text-xs hover:bg-sidebar-accent"
          :class="d.udid === selected?.udid && 'bg-sidebar-accent font-medium'"
          @click="selected = d"
        >{{ d.name ?? d.udid }}</button>
      </div>

      <nav class="flex flex-col gap-0.5 px-2">
        <button
          v-for="n in nav" :key="n.id"
          :disabled="!selected"
          class="flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm transition-colors
                 hover:bg-sidebar-accent disabled:pointer-events-none disabled:opacity-40"
          :class="tab === n.id && 'bg-sidebar-accent font-medium'"
          @click="tab = n.id as Tab"
        >
          <component :is="n.icon" class="size-4 text-muted-foreground" />
          {{ n.label }}
          <span v-if="n.id === 'apps' && appCount != null" class="ml-auto text-xs text-muted-foreground">
            {{ appCount }}
          </span>
        </button>
      </nav>

      <p class="mt-auto px-4 py-3 text-[10px] leading-relaxed text-muted-foreground">
        Erasing and reinstalling iOS is done in Finder — elma walks you through it.
      </p>
    </aside>

    <!-- Content -->
    <main class="min-w-0 flex-1 overflow-y-auto">
      <div v-if="error" class="p-6">
        <p class="text-sm text-destructive">{{ error }}</p>
      </div>

      <div v-else-if="!devices.length && !loading" class="flex h-full flex-col items-center justify-center gap-2 p-6 text-center">
        <Smartphone class="size-8 text-muted-foreground/40" />
        <p class="text-sm font-medium">No device connected</p>
        <p class="max-w-xs text-xs text-muted-foreground">
          Plug in an iPhone or iPad over USB, unlock it, and tap Trust if asked.
        </p>
        <Button variant="outline" size="sm" class="mt-2" @click="refresh">Scan again</Button>
      </div>

      <template v-else-if="selected">
        <OverviewView
          v-if="tab === 'overview'"
          :device="selected" :info="info" :app-count="appCount"
          @navigate="tab = $event as Tab"
        />
        <AppsView v-else-if="tab === 'apps'" :udid="selected.udid" />
        <FilesView v-else-if="tab === 'files'" :udid="selected.udid" />
        <BackupView v-else-if="tab === 'backup'" :udid="selected.udid" />
        <VersionsView v-else-if="tab === 'versions'" :model="selected.model" :current="selected.version" />
        <EraseView v-else :device="selected" :info="info" @navigate="tab = $event as Tab" />
      </template>
    </main>
  </div>
</template>
