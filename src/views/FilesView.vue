<script setup lang="ts">
import { ref, watch } from 'vue'
import { api, type FileEntry } from '../api'
import { formatBytes } from '../format'

const props = defineProps<{ udid: string }>()

const path = ref('/')
const entries = ref<FileEntry[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

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
  if (path.value === '/') return
  const parts = path.value.split('/').filter(Boolean)
  parts.pop()
  load('/' + parts.join('/'))
}

watch(() => props.udid, () => load('/'), { immediate: true })
</script>

<template>
  <div class="bar">
    <button :disabled="path === '/'" @click="up">↑ Up</button>
    <code class="mono path">{{ path }}</code>
  </div>

  <p v-if="loading" class="muted">Loading…</p>
  <p v-else-if="error" class="muted">{{ error }}</p>

  <table v-else>
    <thead>
      <tr><th>Name</th><th>Size</th><th>Modified</th></tr>
    </thead>
    <tbody>
      <tr
        v-for="e in entries"
        :key="e.path"
        :class="{ dir: e.is_dir }"
        @click="e.is_dir && load(e.path)"
      >
        <td>{{ e.is_dir ? '📁' : '📄' }} {{ e.name }}</td>
        <td>{{ e.is_dir ? '—' : formatBytes(e.size_bytes) }}</td>
        <td class="muted">{{ e.modified.slice(0, 19) }}</td>
      </tr>
    </tbody>
  </table>

  <p class="muted note">
    This is the media area only — app sandboxes aren't reachable over AFC.
  </p>
</template>

<style scoped>
.bar { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.path { color: var(--muted); }
tr.dir { cursor: pointer; }
.note { margin-top: 12px; font-size: 12px; }
</style>
