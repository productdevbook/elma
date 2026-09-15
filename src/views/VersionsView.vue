<script setup lang="ts">
import { ref, watch } from 'vue'
import { api, type SignedVersion } from '../api'
import { formatBytes } from '../format'

const props = defineProps<{ model: string | null }>()

const versions = ref<SignedVersion[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

async function load() {
  if (!props.model) return
  loading.value = true
  error.value = null
  try {
    versions.value = await api.signedVersions(props.model)
  } catch (e: any) {
    error.value = e?.message ?? String(e)
  } finally {
    loading.value = false
  }
}

watch(() => props.model, load, { immediate: true })
</script>

<template>
  <p v-if="loading" class="muted">Checking with Apple…</p>
  <p v-else-if="error" class="muted">{{ error }}</p>
  <p v-else-if="!versions.length" class="muted">No signed version found.</p>

  <template v-else>
    <table>
      <thead>
        <tr><th>iOS</th><th>Build</th><th>Released</th><th>Size</th></tr>
      </thead>
      <tbody>
        <tr v-for="v in versions" :key="v.build">
          <td><strong>{{ v.version }}</strong></td>
          <td class="mono">{{ v.build }}</td>
          <td>{{ v.released }}</td>
          <td>{{ formatBytes(v.size_bytes) }}</td>
        </tr>
      </tbody>
    </table>

    <p class="muted note">
      These are the versions Apple still signs, so they're the only ones a
      restore can install. Signing windows close without warning. elma doesn't
      restore devices — use Finder or iTunes for that.
    </p>
  </template>
</template>

<style scoped>
.note { margin-top: 12px; font-size: 12px; max-width: 60ch; }
</style>
