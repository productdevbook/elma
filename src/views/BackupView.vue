<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { open } from '@tauri-apps/plugin-dialog'
import {
  FolderOpen, ShieldAlert, ShieldCheck, CheckCircle2, Upload, Lock,
} from 'lucide-vue-next'
import { api, type BackupEntry } from '@/api'
import { formatBytes, formatDuration } from '@/format'
import {
  transfers, startBackup, startRestore, dismissResult,
} from '@/stores/transfers'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'

const props = defineProps<{ udid: string }>()

const encrypted = ref<boolean | null>(null)
const directory = ref<string | null>(null)
const error = ref<string | null>(null)

// Progress lives in the store, so it survives leaving this tab mid-transfer.
const active = computed(() => transfers.active)
const backingUp = computed(() => active.value?.kind === 'backup')
const restoring = computed(() => active.value?.kind === 'restore')
const busy = computed(() => active.value !== null)

const result = computed(() => transfers.lastResult)
const storeError = computed(() => transfers.lastError)

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

function start() {
  if (directory.value) startBackup(directory.value, props.udid)
}

/* ---- restore ---------------------------------------------------------- */

const found = ref<BackupEntry[] | null>(null)
const chosen = ref<BackupEntry | null>(null)
const password = ref('')
const confirmed = ref(false)

async function scanForBackups() {
  const dir = await open({ directory: true, multiple: false })
  if (typeof dir !== 'string') return
  chosen.value = null
  confirmed.value = false
  error.value = null
  try {
    found.value = await api.backupScan(dir)
  } catch (e: any) {
    error.value = e?.message ?? String(e)
    found.value = []
  }
}

function runRestore() {
  if (chosen.value) startRestore(chosen.value.path, props.udid, password.value)
}

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
          <Button variant="outline" size="sm" :disabled="busy" @click="pickDirectory">
            <FolderOpen class="size-3.5" /> Choose folder
          </Button>
          <span v-if="directory" class="min-w-0 flex-1 truncate font-mono text-xs text-muted-foreground">
            {{ directory }}
          </span>
          <span v-else class="text-xs text-muted-foreground">No folder chosen</span>
        </div>

        <div v-if="backingUp" class="space-y-2">
          <Progress :model-value="active!.percent" class="h-1.5" />
          <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs tabular-nums text-muted-foreground">
            <span class="font-medium text-foreground">{{ active!.percent.toFixed(0) }}%</span>
            <span v-if="active!.bytesDone">
              {{ formatBytes(active!.bytesDone) }}<template v-if="active!.bytesTotal"> of ~{{ formatBytes(active!.bytesTotal) }}</template>
            </span>
            <span v-if="formatDuration(active!.etaSeconds)">
              ~{{ formatDuration(active!.etaSeconds) }} left
            </span>
            <span v-if="active!.elapsedSeconds > 5" class="ml-auto">
              {{ formatDuration(active!.elapsedSeconds) }} elapsed
            </span>
          </div>
          <p v-if="!active!.bytesTotal" class="text-[11px] text-muted-foreground">
            Sizing the backup — the total appears once it gets going.
          </p>
        </div>

        <Button class="w-full" :disabled="!directory || busy" @click="start">
          {{ backingUp ? 'Backing up…' : 'Start backup' }}
        </Button>
      </CardContent>
    </Card>

    <Card v-if="result?.kind === 'backup'" class="border-emerald-500/40">
      <CardContent class="flex items-start gap-3 px-4 py-3.5">
        <CheckCircle2 class="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-500" />
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium">Backup complete</p>
          <p class="mt-0.5 truncate font-mono text-xs text-muted-foreground">{{ result.path }}</p>
          <p v-if="result.bytes" class="mt-0.5 text-xs text-muted-foreground">
            {{ formatBytes(result.bytes) }} written
          </p>
        </div>
        <button class="shrink-0 text-xs text-muted-foreground underline" @click="dismissResult">
          Dismiss
        </button>
      </CardContent>
    </Card>

    <p v-if="storeError?.kind === 'backup'" class="text-sm text-destructive">
      {{ storeError.message }}
    </p>
    <p v-if="error" class="text-sm text-destructive">{{ error }}</p>

    <p class="text-xs text-muted-foreground">
      The device must stay connected and unlocked for the whole backup. You can
      switch tabs — it keeps running.
    </p>

    <!-- Restore -->
    <section class="space-y-2.5 border-t pt-5">
      <h2 class="text-sm font-medium">Restore a backup</h2>

      <Card>
        <CardContent class="space-y-4 px-4 py-4">
          <div class="flex items-center gap-3">
            <Button variant="outline" size="sm" :disabled="busy" @click="scanForBackups">
              <FolderOpen class="size-3.5" /> Find backups
            </Button>
            <span v-if="found" class="text-xs text-muted-foreground">{{ found.length }} found</span>
          </div>

          <div v-if="found?.length" class="space-y-1.5">
            <button
              v-for="b in found" :key="b.path"
              class="flex w-full items-center gap-3 rounded-md border px-3 py-2 text-left transition-colors hover:bg-muted/50"
              :class="chosen?.path === b.path && 'border-primary bg-muted/50'"
              :disabled="busy"
              @click="chosen = b; confirmed = false"
            >
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium">{{ b.device_name ?? b.udid }}</p>
                <p class="truncate text-xs text-muted-foreground">
                  {{ b.product ?? '—' }}<template v-if="b.ios_version"> · iOS {{ b.ios_version }}</template>
                  <template v-if="b.date"> · {{ b.date.slice(0, 10) }}</template>
                </p>
              </div>
              <Badge v-if="b.encrypted" variant="secondary" class="shrink-0 text-[10px]">
                <Lock class="size-2.5" /> Encrypted
              </Badge>
            </button>
          </div>
          <p v-else-if="found" class="text-xs text-muted-foreground">
            No backups in that folder. Pick the folder containing them, or one
            backup's own folder.
          </p>

          <template v-if="chosen">
            <Input
              v-if="chosen.encrypted"
              v-model="password" type="password"
              placeholder="Backup password" class="h-8 text-sm"
            />

            <label class="flex cursor-pointer items-start gap-2.5">
              <input v-model="confirmed" type="checkbox" class="mt-0.5" :disabled="busy" />
              <span class="text-xs leading-relaxed text-muted-foreground">
                I understand this replaces what's on
                <strong>{{ chosen.device_name ?? 'this device' }}</strong> with
                the backup, and the device restarts when it finishes.
              </span>
            </label>

            <div v-if="restoring" class="space-y-2">
              <Progress :model-value="active!.percent" class="h-1.5" />
              <div class="flex flex-wrap items-baseline gap-x-3 text-xs tabular-nums text-muted-foreground">
                <span class="font-medium text-foreground">{{ active!.percent.toFixed(0) }}%</span>
                <span v-if="formatDuration(active!.etaSeconds)">
                  ~{{ formatDuration(active!.etaSeconds) }} left
                </span>
                <span v-if="active!.elapsedSeconds > 5" class="ml-auto">
                  {{ formatDuration(active!.elapsedSeconds) }} elapsed
                </span>
              </div>
            </div>

            <Button
              class="w-full" variant="destructive"
              :disabled="!confirmed || busy || (chosen.encrypted && !password)"
              @click="runRestore"
            >
              <Upload class="size-3.5" />
              {{ restoring ? 'Restoring…' : 'Restore to this device' }}
            </Button>
          </template>
        </CardContent>
      </Card>

      <Card v-if="result?.kind === 'restore'" class="border-emerald-500/40">
        <CardContent class="flex items-start gap-3 px-4 py-3.5">
          <CheckCircle2 class="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-500" />
          <p class="flex-1 text-sm">Restore finished — the device is restarting.</p>
          <button class="shrink-0 text-xs text-muted-foreground underline" @click="dismissResult">
            Dismiss
          </button>
        </CardContent>
      </Card>

      <p v-if="storeError?.kind === 'restore'" class="text-sm text-destructive">
        {{ storeError.message }}
      </p>
    </section>
  </div>
</template>
