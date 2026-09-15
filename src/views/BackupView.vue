<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'
import { open } from '@tauri-apps/plugin-dialog'
import { FolderOpen, ShieldAlert, ShieldCheck, CheckCircle2 } from 'lucide-vue-next'
import { api } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'

const props = defineProps<{ udid: string }>()

const encrypted = ref<boolean | null>(null)
const directory = ref<string | null>(null)
const running = ref(false)
const percent = ref(0)
const result = ref<string | null>(null)
const error = ref<string | null>(null)

let unlisten: UnlistenFn | null = null

async function loadEncryption() {
  try {
    encrypted.value = (await api.backupEncryption(props.udid)).enabled
  } catch {
    encrypted.value = null // not fatal; a backup can still run
  }
}

async function pickDirectory() {
  const picked = await open({ directory: true, multiple: false })
  if (typeof picked === 'string') directory.value = picked
}

async function start() {
  if (!directory.value) return
  running.value = true
  percent.value = 0
  result.value = null
  error.value = null
  try {
    const r = await api.backupCreate(directory.value, props.udid)
    result.value = `${r.directory}/${r.udid}`
  } catch (e: any) {
    error.value = e?.message ?? String(e)
  } finally {
    running.value = false
  }
}

onMounted(async () => {
  unlisten = await listen<{ percent: number }>('backup.progress', e => {
    percent.value = e.payload.percent
  })
})
onUnmounted(() => unlisten?.())

watch(() => props.udid, loadEncryption, { immediate: true })
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-5 p-6">
    <header>
      <h1 class="text-lg font-semibold tracking-tight">Backup</h1>
      <p class="mt-0.5 text-sm text-muted-foreground">
        A full local backup, written to a folder you choose.
      </p>
    </header>

    <Card v-if="encrypted !== null" :class="encrypted ? '' : 'border-amber-500/40'">
      <CardContent class="flex gap-3 px-4 py-3.5">
        <component
          :is="encrypted ? ShieldCheck : ShieldAlert"
          class="mt-0.5 size-4 shrink-0"
          :class="encrypted ? 'text-emerald-600 dark:text-emerald-500' : 'text-amber-600 dark:text-amber-500'"
        />
        <div>
          <p class="text-sm font-medium">Encryption is {{ encrypted ? 'on' : 'off' }}</p>
          <p class="mt-0.5 text-xs leading-relaxed text-muted-foreground">
            {{ encrypted
              ? 'Saved passwords, Wi-Fi networks and Health data will be included in the backup.'
              : 'An unencrypted backup silently leaves out saved passwords, Wi-Fi networks and Health data. Turn encryption on in Finder before relying on this to restore a wiped phone.' }}
          </p>
        </div>
      </CardContent>
    </Card>

    <Card>
      <CardContent class="space-y-4 px-4 py-4">
        <div class="flex items-center gap-3">
          <Button variant="outline" size="sm" :disabled="running" @click="pickDirectory">
            <FolderOpen class="size-3.5" /> Choose folder
          </Button>
          <span v-if="directory" class="min-w-0 flex-1 truncate font-mono text-xs text-muted-foreground">
            {{ directory }}
          </span>
          <span v-else class="text-xs text-muted-foreground">No folder chosen</span>
        </div>

        <div v-if="running" class="space-y-1.5">
          <Progress :model-value="percent" class="h-1.5" />
          <p class="text-xs tabular-nums text-muted-foreground">{{ percent.toFixed(0) }}% complete</p>
        </div>

        <Button class="w-full" :disabled="!directory || running" @click="start">
          {{ running ? 'Backing up…' : 'Start backup' }}
        </Button>
      </CardContent>
    </Card>

    <Card v-if="result" class="border-emerald-500/40">
      <CardContent class="flex gap-3 px-4 py-3.5">
        <CheckCircle2 class="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-500" />
        <div class="min-w-0">
          <p class="text-sm font-medium">Backup complete</p>
          <p class="mt-0.5 truncate font-mono text-xs text-muted-foreground">{{ result }}</p>
        </div>
      </CardContent>
    </Card>

    <p v-if="error" class="text-sm text-destructive">{{ error }}</p>

    <p class="text-xs text-muted-foreground">
      The device must stay connected and unlocked for the whole backup.
    </p>
  </div>
</template>
