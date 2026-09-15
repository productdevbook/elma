<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'
import { open } from '@tauri-apps/plugin-dialog'
import { api } from '../api'

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
    encrypted.value = null // not fatal; the backup can still run
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
  <p v-if="encrypted === false" class="notice">
    <strong>Backup encryption is off.</strong>
    An unencrypted backup leaves out saved passwords, Wi-Fi networks and Health
    data. Turn it on in Finder — or on the device under Settings — before
    relying on this backup to restore a wiped phone.
  </p>
  <p v-else-if="encrypted === true" class="notice ok">
    Backup encryption is on — passwords and Health data will be included.
  </p>

  <div class="row">
    <button :disabled="running" @click="pickDirectory">Choose folder…</button>
    <code v-if="directory" class="mono">{{ directory }}</code>
    <span v-else class="muted">No folder chosen</span>
  </div>

  <div class="row">
    <button class="primary" :disabled="!directory || running" @click="start">
      {{ running ? 'Backing up…' : 'Start backup' }}
    </button>
    <template v-if="running">
      <progress :value="percent" max="100" />
      <span class="muted">{{ percent.toFixed(0) }}%</span>
    </template>
  </div>

  <p v-if="result" class="notice ok">Backup written to <code class="mono">{{ result }}</code></p>
  <p v-if="error" class="notice danger">{{ error }}</p>

  <p class="muted note">
    A full backup can take a while and the device must stay connected and
    unlocked throughout.
  </p>
</template>

<style scoped>
.row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin: 12px 0; }
progress { flex: 1; min-width: 160px; height: 6px; }
.notice {
  background: var(--panel);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
  padding: 10px 12px;
  margin: 12px 0;
  max-width: 68ch;
}
.notice.ok { border-left-color: #2da44e; }
.notice.danger { border-left-color: var(--danger); }
.note { margin-top: 16px; font-size: 12px; }
</style>
