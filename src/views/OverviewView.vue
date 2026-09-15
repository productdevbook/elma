<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { AlertTriangle, BatteryCharging, Battery, HardDrive, ShieldCheck, ShieldAlert } from 'lucide-vue-next'
import { api, type Device, type DeviceInfo, type App } from '@/api'
import { formatCapacity, formatBytes } from '@/format'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

const props = defineProps<{
  device: Device
  info: DeviceInfo | null
  appCount: number | null
}>()
const emit = defineEmits<{ navigate: [tab: string] }>()

const sideloaded = ref<App[] | null>(null)
const encrypted = ref<boolean | null>(null)

const storage = computed(() => {
  const s = props.info?.storage
  return s && 'total_bytes' in s ? s : null
})
const battery = computed(() => {
  const b = props.info?.battery
  return b && 'percent' in b ? b : null
})
const usedPercent = computed(() =>
  storage.value ? (storage.value.used_bytes / storage.value.total_bytes) * 100 : 0)

async function load() {
  sideloaded.value = null
  encrypted.value = null
  try {
    const apps = await api.appList('user', props.device.udid)
    sideloaded.value = apps.filter(a => !a.from_store)
  } catch { /* the rest of the page still renders */ }
  try {
    encrypted.value = (await api.backupEncryption(props.device.udid)).enabled
  } catch { /* ditto */ }
}

watch(() => props.device.udid, load, { immediate: true })
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-5 p-6">
    <header>
      <h1 class="text-xl font-semibold tracking-tight">{{ device.name ?? 'iPhone' }}</h1>
      <p class="mt-0.5 text-sm text-muted-foreground">
        {{ info?.marketing_name ?? device.model }} · iOS {{ device.version }}
        <span class="text-muted-foreground/60">({{ device.build }})</span>
      </p>
    </header>

    <!-- Stats -->
    <div class="grid gap-3 sm:grid-cols-3">
      <Card>
        <CardContent class="px-4 py-3.5">
          <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
            <HardDrive class="size-3.5" /> Storage
          </div>
          <template v-if="storage">
            <p class="mt-1.5 text-lg font-semibold tabular-nums">
              {{ formatCapacity(storage.free_bytes) }}
              <span class="text-sm font-normal text-muted-foreground">free</span>
            </p>
            <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                class="h-full rounded-full transition-all"
                :class="usedPercent > 90 ? 'bg-destructive' : 'bg-primary'"
                :style="{ width: `${usedPercent}%` }"
              />
            </div>
            <p class="mt-1.5 text-xs text-muted-foreground tabular-nums">
              {{ formatCapacity(storage.used_bytes) }} of {{ formatCapacity(storage.total_bytes) }} used
            </p>
          </template>
          <Skeleton v-else class="mt-2 h-12 w-full" />
        </CardContent>
      </Card>

      <Card>
        <CardContent class="px-4 py-3.5">
          <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
            <component :is="battery?.charging ? BatteryCharging : Battery" class="size-3.5" /> Battery
          </div>
          <template v-if="battery?.percent != null">
            <p class="mt-1.5 text-lg font-semibold tabular-nums">{{ battery.percent }}%</p>
            <p class="mt-1 text-xs text-muted-foreground">
              {{ battery.charging ? 'Charging' : battery.plugged_in ? 'Plugged in' : 'On battery' }}
            </p>
          </template>
          <Skeleton v-else class="mt-2 h-8 w-16" />
        </CardContent>
      </Card>

      <Card>
        <CardContent class="px-4 py-3.5">
          <div class="text-xs text-muted-foreground">Apps</div>
          <template v-if="appCount != null">
            <p class="mt-1.5 text-lg font-semibold tabular-nums">{{ appCount }}</p>
            <p class="mt-1 text-xs text-muted-foreground">installed by you</p>
          </template>
          <Skeleton v-else class="mt-2 h-8 w-12" />
        </CardContent>
      </Card>
    </div>

    <!-- What would be lost -->
    <section v-if="sideloaded?.length || encrypted === false" class="space-y-2.5">
      <h2 class="text-sm font-medium">Before you erase this device</h2>

      <Card v-if="sideloaded?.length" class="border-amber-500/40">
        <CardContent class="flex gap-3 px-4 py-3.5">
          <AlertTriangle class="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-500" />
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium">
              {{ sideloaded.length }} app{{ sideloaded.length === 1 ? '' : 's' }} won't come back
            </p>
            <p class="mt-0.5 text-xs text-muted-foreground">
              These weren't installed from the App Store, so a wipe removes them for good.
              You'll need the original build to put them back.
            </p>
            <div class="mt-2 flex flex-wrap gap-1">
              <span
                v-for="a in sideloaded.slice(0, 8)" :key="a.bundle_id"
                class="rounded bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground"
              >{{ a.name ?? a.bundle_id }}</span>
              <span v-if="sideloaded.length > 8" class="px-1 py-0.5 text-[11px] text-muted-foreground">
                +{{ sideloaded.length - 8 }} more
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card :class="encrypted === false ? 'border-amber-500/40' : ''">
        <CardContent class="flex gap-3 px-4 py-3.5">
          <component
            :is="encrypted ? ShieldCheck : ShieldAlert"
            class="mt-0.5 size-4 shrink-0"
            :class="encrypted ? 'text-emerald-600 dark:text-emerald-500' : 'text-amber-600 dark:text-amber-500'"
          />
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium">
              Backup encryption is {{ encrypted ? 'on' : 'off' }}
            </p>
            <p class="mt-0.5 text-xs text-muted-foreground">
              {{ encrypted
                ? 'Saved passwords, Wi-Fi networks and Health data will be included.'
                : 'An unencrypted backup silently leaves out saved passwords, Wi-Fi networks and Health data. Turn it on in Finder before relying on it.' }}
            </p>
          </div>
          <Button size="sm" variant="outline" class="shrink-0" @click="emit('navigate', 'backup')">
            Back up
          </Button>
        </CardContent>
      </Card>
    </section>

    <!-- Details -->
    <Card>
      <CardContent class="px-4 py-1">
        <dl class="divide-y text-sm">
          <div v-for="row in [
            ['Model', info?.model ?? device.model],
            ['Serial', info?.serial],
            ['UDID', device.udid],
            ['Activation', info?.activation],
            ['Wi-Fi', info?.wifi_mac],
            ['Bluetooth', info?.bluetooth_mac],
            ['Connection', device.transports.join(' + ')],
          ]" :key="row[0]" class="flex items-center gap-4 py-2.5">
            <dt class="w-28 shrink-0 text-xs text-muted-foreground">{{ row[0] }}</dt>
            <dd class="truncate font-mono text-xs">{{ row[1] ?? '—' }}</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  </div>
</template>
