<script setup lang="ts">
import { ref, watch } from 'vue'
import { api, type SignedVersion } from '@/api'
import { formatCapacity } from '@/format'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent } from '@/components/ui/card'

const props = defineProps<{ model: string | null; current: string | null }>()

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
  <div class="mx-auto max-w-3xl space-y-5 p-6">
    <header>
      <h1 class="text-lg font-semibold tracking-tight">iOS versions</h1>
      <p class="mt-0.5 text-sm text-muted-foreground">
        What Apple still signs for this device — the only builds a restore can install.
      </p>
    </header>

    <div v-if="loading" class="space-y-2">
      <Skeleton v-for="i in 3" :key="i" class="h-14 w-full" />
    </div>
    <p v-else-if="error" class="text-sm text-destructive">{{ error }}</p>
    <p v-else-if="!versions.length" class="text-sm text-muted-foreground">
      Nothing signed for {{ model }}.
    </p>

    <div v-else class="space-y-2">
      <Card v-for="(v, i) in versions" :key="v.build">
        <CardContent class="flex items-center gap-4 px-4 py-3">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="font-semibold tabular-nums">iOS {{ v.version }}</span>
              <Badge v-if="i === 0" class="text-[10px]">Latest</Badge>
              <Badge v-if="v.version === current" variant="secondary" class="text-[10px]">Installed</Badge>
            </div>
            <p class="mt-0.5 font-mono text-xs text-muted-foreground">
              {{ v.build }} · released {{ v.released }}
            </p>
          </div>
          <span class="shrink-0 text-sm tabular-nums text-muted-foreground">
            {{ formatCapacity(v.size_bytes) }}
          </span>
        </CardContent>
      </Card>
    </div>

    <p class="text-xs leading-relaxed text-muted-foreground">
      Signing windows close without warning, so this is fetched fresh each time.
      elma doesn't restore devices — use Finder or iTunes for that.
    </p>
  </div>
</template>
