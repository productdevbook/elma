<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { api, type Device } from './api'
import AppsView from './views/AppsView.vue'
import FilesView from './views/FilesView.vue'
import InfoView from './views/InfoView.vue'
import VersionsView from './views/VersionsView.vue'
import BackupView from './views/BackupView.vue'

type Tab = 'info' | 'apps' | 'files' | 'backup' | 'versions'

const devices = ref<Device[]>([])
const selected = ref<Device | null>(null)
const tab = ref<Tab>('info')
const error = ref<string | null>(null)
const loading = ref(false)

const tabs: { id: Tab; label: string }[] = [
  { id: 'info', label: 'Device' },
  { id: 'apps', label: 'Apps' },
  { id: 'files', label: 'Files' },
  { id: 'backup', label: 'Backup' },
  { id: 'versions', label: 'iOS versions' },
]

async function refresh() {
  loading.value = true
  error.value = null
  try {
    devices.value = await api.deviceList()
    // Keep the current selection if it's still plugged in.
    const keep = devices.value.find(d => d.udid === selected.value?.udid)
    selected.value = keep ?? devices.value[0] ?? null
  } catch (e: any) {
    error.value = e?.message ?? String(e)
  } finally {
    loading.value = false
  }
}

const unpaired = computed(() => selected.value && !selected.value.paired)

onMounted(refresh)
</script>

<template>
  <div class="shell">
    <header>
      <div class="brand">elma</div>
      <select
        v-if="devices.length"
        :value="selected?.udid"
        @change="selected = devices.find(d => d.udid === ($event.target as HTMLSelectElement).value) ?? null"
      >
        <option v-for="d in devices" :key="d.udid" :value="d.udid">
          {{ d.name ?? d.udid }} — {{ d.model ?? '?' }}
        </option>
      </select>
      <button :disabled="loading" @click="refresh">
        {{ loading ? 'Scanning…' : 'Refresh' }}
      </button>
    </header>

    <p v-if="error" class="notice danger">{{ error }}</p>

    <div v-else-if="!devices.length" class="empty">
      <p>No device found.</p>
      <p class="muted">Connect an iPhone or iPad over USB and unlock it.</p>
    </div>

    <template v-else-if="selected">
      <p v-if="unpaired" class="notice">
        This device isn't paired yet. Unlock it and tap <strong>Trust</strong>, then refresh.
      </p>

      <nav>
        <button
          v-for="t in tabs"
          :key="t.id"
          :class="{ primary: tab === t.id }"
          @click="tab = t.id"
        >{{ t.label }}</button>
      </nav>

      <main>
        <InfoView v-if="tab === 'info'" :udid="selected.udid" />
        <AppsView v-else-if="tab === 'apps'" :udid="selected.udid" />
        <FilesView v-else-if="tab === 'files'" :udid="selected.udid" />
        <BackupView v-else-if="tab === 'backup'" :udid="selected.udid" />
        <VersionsView v-else :model="selected.model" />
      </main>
    </template>
  </div>
</template>

<style scoped>
.shell { max-width: 1100px; margin: 0 auto; padding: 16px; }

header {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.brand { font-weight: 600; font-size: 17px; margin-right: auto; }

select {
  font: inherit;
  color: inherit;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 10px;
  max-width: 320px;
}

nav { display: flex; gap: 6px; flex-wrap: wrap; margin: 14px 0; }
main { min-height: 300px; }

.empty { text-align: center; padding: 64px 16px; }
.empty p { margin: 4px 0; }

.notice {
  background: var(--panel);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
  padding: 10px 12px;
  margin: 14px 0;
}
.notice.danger { border-left-color: var(--danger); }
</style>
