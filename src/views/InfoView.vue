<script setup lang="ts">
import { ref, watch } from 'vue'
import { api, type DeviceInfo } from '../api'
import { formatBytes } from '../format'

const props = defineProps<{ udid: string }>()
const info = ref<DeviceInfo | null>(null)
const error = ref<string | null>(null)

async function load() {
  error.value = null
  try {
    info.value = await api.deviceInfo(props.udid)
  } catch (e: any) {
    error.value = e?.message ?? String(e)
  }
}

watch(() => props.udid, load, { immediate: true })
</script>

<template>
  <p v-if="error" class="muted">{{ error }}</p>
  <table v-else-if="info">
    <tbody>
      <tr><th>Name</th><td>{{ info.name }}</td></tr>
      <tr><th>Model</th><td>{{ info.model }}</td></tr>
      <tr><th>iOS</th><td>{{ info.version }} ({{ info.build }})</td></tr>
      <tr><th>Serial</th><td class="mono">{{ info.serial }}</td></tr>
      <tr><th>UDID</th><td class="mono">{{ info.udid }}</td></tr>
      <tr v-if="info.capacity_bytes">
        <th>Capacity</th><td>{{ formatBytes(info.capacity_bytes) }}</td>
      </tr>
      <tr v-if="info.battery_percent != null">
        <th>Battery</th><td>{{ info.battery_percent }}%</td>
      </tr>
      <tr><th>Activation</th><td>{{ info.activation }}</td></tr>
      <tr><th>Wi-Fi</th><td class="mono">{{ info.wifi_mac }}</td></tr>
      <tr><th>Bluetooth</th><td class="mono">{{ info.bluetooth_mac }}</td></tr>
    </tbody>
  </table>
</template>

<style scoped>
th { width: 140px; }
</style>
