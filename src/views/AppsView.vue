<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api, type App } from '../api'
import { formatBytes } from '../format'

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
    (a.name ?? '').toLowerCase().includes(q) ||
    a.bundle_id.toLowerCase().includes(q))
})

/** Sideloaded apps won't come back from the App Store after a wipe, so they
 *  are the ones worth flagging before a restore. */
const sideloaded = computed(() => apps.value.filter(a => !a.from_store).length)

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
    a.name ?? '', a.bundle_id, a.version ?? '', a.build ?? '', a.type,
    a.from_store ? 'yes' : 'no',
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
  <div class="bar">
    <select v-model="kind">
      <option value="user">User apps</option>
      <option value="system">System apps</option>
      <option value="all">All</option>
    </select>
    <input v-model="query" type="search" placeholder="Filter by name or bundle id" />
    <span class="muted">{{ shown.length }} shown</span>
    <span v-if="sideloaded" class="muted">· {{ sideloaded }} sideloaded</span>
    <button :disabled="!shown.length" @click="exportCsv">Export CSV</button>
  </div>

  <p v-if="loading" class="muted">Loading…</p>
  <p v-else-if="error" class="muted">{{ error }}</p>

  <table v-else>
    <thead>
      <tr>
        <th>Name</th><th>Bundle id</th><th>Version</th><th>Size</th><th>Source</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="a in shown" :key="a.bundle_id">
        <td>{{ a.name ?? '—' }}</td>
        <td class="mono">{{ a.bundle_id }}</td>
        <td>{{ a.version ?? '—' }}</td>
        <td>{{ formatBytes(a.size_bytes) }}</td>
        <td>{{ a.from_store ? 'App Store' : 'Sideloaded' }}</td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.bar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }
select {
  font: inherit; color: inherit; background: var(--panel);
  border: 1px solid var(--border); border-radius: 6px; padding: 6px 10px;
}
</style>
