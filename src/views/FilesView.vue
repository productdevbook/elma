<script setup lang="ts">
import { ref, watch } from 'vue'
import { ChevronRight, Folder, File as FileIcon, ArrowUp, Download, Check } from 'lucide-vue-next'
import { open } from '@tauri-apps/plugin-dialog'
import { api, type FileEntry } from '@/api'
import { formatBytes } from '@/format'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

const props = defineProps<{ udid: string }>()

const path = ref('/')
const entries = ref<FileEntry[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const segments = () => path.value.split('/').filter(Boolean)

async function load(p: string) {
  loading.value = true
  error.value = null
  try {
    entries.value = await api.fileList(p, props.udid)
    path.value = p
  } catch (e: any) {
    error.value = e?.message ?? String(e)
  } finally {
    loading.value = false
  }
}

function up() {
  const parts = segments()
  parts.pop()
  load('/' + parts.join('/'))
}

function goTo(i: number) {
  load('/' + segments().slice(0, i + 1).join('/'))
}

/** Pulling is per-entry rather than a bulk action: the media area holds tens
 *  of gigabytes, and a stray click on "download everything" is expensive. */
const pulling = ref<string | null>(null)
const pulled = ref<Set<string>>(new Set())
const pullError = ref<string | null>(null)

async function pull(e: FileEntry) {
  const dir = await open({ directory: true, multiple: false })
  if (typeof dir !== 'string') return
  pulling.value = e.path
  pullError.value = null
  try {
    await api.filePull(e.path, dir, props.udid)
    pulled.value = new Set(pulled.value).add(e.path)
  } catch (err: any) {
    pullError.value = err?.message ?? String(err)
  } finally {
    pulling.value = null
  }
}

watch(() => props.udid, () => load('/'), { immediate: true })
</script>

<template>
  <div class="flex h-full flex-col">
    <header class="space-y-3 border-b px-6 py-4">
      <h1 class="text-lg font-semibold tracking-tight">Files</h1>
      <div class="flex items-center gap-1 text-xs">
        <Button variant="ghost" size="icon" class="size-6" :disabled="path === '/'" @click="up">
          <ArrowUp class="size-3.5" />
        </Button>
        <button class="rounded px-1.5 py-0.5 hover:bg-accent" @click="load('/')">Device</button>
        <template v-for="(seg, i) in segments()" :key="i">
          <ChevronRight class="size-3 text-muted-foreground" />
          <button class="rounded px-1.5 py-0.5 hover:bg-accent" @click="goTo(i)">{{ seg }}</button>
        </template>
      </div>
    </header>

    <div class="min-h-0 flex-1 overflow-y-auto">
      <div v-if="loading" class="space-y-2 p-6">
        <Skeleton v-for="i in 6" :key="i" class="h-8 w-full" />
      </div>
      <p v-else-if="error" class="p-6 text-sm text-destructive">{{ error }}</p>
      <p v-else-if="!entries.length" class="p-6 text-sm text-muted-foreground">Empty folder.</p>

      <div v-else class="divide-y divide-border/50">
        <div
          v-for="e in entries" :key="e.path"
          class="group flex items-center gap-3 px-6 py-2 text-sm transition-colors hover:bg-muted/50"
        >
          <button
            class="flex min-w-0 flex-1 items-center gap-3 text-left disabled:cursor-default"
            :disabled="!e.is_dir"
            @click="e.is_dir && load(e.path)"
          >
            <component
              :is="e.is_dir ? Folder : FileIcon"
              class="size-4 shrink-0"
              :class="e.is_dir ? 'text-primary' : 'text-muted-foreground'"
            />
            <span class="min-w-0 flex-1 truncate">{{ e.name }}</span>
          </button>

          <span class="shrink-0 text-xs tabular-nums text-muted-foreground">
            {{ e.is_dir ? '' : formatBytes(e.size_bytes) }}
          </span>
          <span class="hidden w-32 shrink-0 text-right text-xs text-muted-foreground sm:block">
            {{ e.modified.slice(0, 16) }}
          </span>

          <Button
            variant="ghost" size="icon"
            class="size-7 shrink-0 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
            :class="(pulled.has(e.path) || pulling === e.path) && 'opacity-100'"
            :disabled="pulling !== null"
            :title="`Save ${e.name} to this computer`"
            @click="pull(e)"
          >
            <Check v-if="pulled.has(e.path)" class="size-3.5 text-emerald-600 dark:text-emerald-500" />
            <Download v-else :class="['size-3.5', pulling === e.path && 'animate-pulse']" />
          </Button>
        </div>
      </div>
    </div>

    <footer class="border-t px-6 py-2.5">
      <p v-if="pullError" class="mb-1 text-xs text-destructive">{{ pullError }}</p>
      <p class="text-xs text-muted-foreground">
        The media area only — app sandboxes aren't reachable over AFC.
      </p>
    </footer>
  </div>
</template>
