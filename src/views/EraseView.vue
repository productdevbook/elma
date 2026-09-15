<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import {
  AlertTriangle, ArrowRight, Check, CircleAlert, KeyRound,
  Lock, RotateCcw, ShieldAlert,
} from 'lucide-vue-next'
import { api, type Device, type DeviceInfo, type App, type SignedVersion } from '@/api'
import { dfuGuideFor, type DfuStep } from '@/lib/dfu'
import { formatCapacity } from '@/format'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import PhoneButtons from '@/components/PhoneButtons.vue'

const props = defineProps<{ device: Device; info: DeviceInfo | null }>()
const emit = defineEmits<{ navigate: [tab: string] }>()

const guide = computed(() => dfuGuideFor(props.device.model))

/* ---- preflight ------------------------------------------------------- */

const sideloaded = ref<App[] | null>(null)
const encrypted = ref<boolean | null>(null)
const versions = ref<SignedVersion[] | null>(null)
const backupConfirmed = ref(false)
const authConfirmed = ref(false)
const findMyConfirmed = ref(false)

async function loadChecks() {
  try {
    sideloaded.value = (await api.appList('user', props.device.udid))
      .filter(a => !a.from_store)
  } catch { sideloaded.value = null }
  try {
    encrypted.value = (await api.backupEncryption(props.device.udid)).enabled
  } catch { encrypted.value = null }
  try {
    if (props.device.model) versions.value = await api.signedVersions(props.device.model)
  } catch { versions.value = null }
}

const target = computed(() => versions.value?.[0] ?? null)

/** Every box has to be ticked before the walkthrough unlocks. These aren't
 *  formalities: each one is unrecoverable if skipped. */
const ready = computed(() =>
  backupConfirmed.value && authConfirmed.value && findMyConfirmed.value)

/* ---- walkthrough ----------------------------------------------------- */

const started = ref(false)
const stepIndex = ref(0)
const remaining = ref(0)
let ticker: ReturnType<typeof setInterval> | null = null

const step = computed<DfuStep | null>(() => guide.value.steps[stepIndex.value] ?? null)

/** Which buttons the diagram highlights, per step of each sequence. */
const highlight = computed<('volUp' | 'volDown' | 'side' | 'home')[]>(() => {
  const i = stepIndex.value
  if (guide.value.family === 'faceid') {
    return [['volUp'], ['volDown'], ['side'], ['side', 'volDown'], ['volDown']][i] ?? []
  }
  if (guide.value.family === 'iphone7') {
    return [['side', 'volDown'], ['volDown']][i] ?? []
  }
  return [['home', 'side'], ['home']][i] ?? []
})

function stop() {
  if (ticker) clearInterval(ticker)
  ticker = null
}

function advance() {
  stop()
  if (stepIndex.value >= guide.value.steps.length - 1) {
    stepIndex.value = guide.value.steps.length
    return
  }
  stepIndex.value += 1
  beginStep()
}

function beginStep() {
  const s = step.value
  if (!s?.hold) return
  remaining.value = s.hold
  ticker = setInterval(() => {
    remaining.value -= 1
    if (remaining.value <= 0) advance()
  }, 1000)
}

function start() {
  started.value = true
  stepIndex.value = 0
  beginStep()
}

function reset() {
  stop()
  started.value = false
  stepIndex.value = 0
  remaining.value = 0
}

const done = computed(() => started.value && stepIndex.value >= guide.value.steps.length)

onUnmounted(stop)
watch(() => props.device.udid, () => { reset(); loadChecks() }, { immediate: true })
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-5 p-6">
    <header>
      <h1 class="text-lg font-semibold tracking-tight">Erase &amp; reinstall iOS</h1>
      <p class="mt-0.5 text-sm text-muted-foreground">
        A DFU restore wipes the device and reinstalls iOS from scratch — deeper
        than Settings → Reset, because it rewrites the bootloader too.
      </p>
    </header>

    <!-- What you'll end up on -->
    <Card v-if="target">
      <CardContent class="flex items-center gap-4 px-4 py-3.5">
        <div class="min-w-0 flex-1">
          <p class="text-sm">
            You'll end up on <strong>iOS {{ target.version }}</strong>
            <span class="text-muted-foreground"> ({{ target.build }})</span>
          </p>
          <p class="mt-0.5 text-xs text-muted-foreground">
            Currently on {{ device.version }}. Apple no longer signs it, so this
            is one-way — you can't go back afterwards.
          </p>
        </div>
        <span class="shrink-0 text-xs tabular-nums text-muted-foreground">
          {{ formatCapacity(target.size_bytes) }}
        </span>
      </CardContent>
    </Card>

    <!-- Preflight -->
    <section class="space-y-2.5">
      <h2 class="text-sm font-medium">Before you start</h2>

      <Card :class="!backupConfirmed && 'border-amber-500/40'">
        <CardContent class="flex gap-3 px-4 py-3.5">
          <button
            class="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded border"
            :class="backupConfirmed ? 'border-primary bg-primary text-primary-foreground' : 'border-muted-foreground/40'"
            @click="backupConfirmed = !backupConfirmed"
          >
            <Check v-if="backupConfirmed" class="size-3" />
          </button>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium">I have a backup</p>
            <p class="mt-0.5 text-xs leading-relaxed text-muted-foreground">
              Everything on the device is erased.
              <template v-if="encrypted === false">
                Backup encryption is <strong>off</strong>, so a backup taken now
                would silently drop saved passwords, Wi-Fi networks and Health
                data — turn it on in Finder first.
              </template>
            </p>
          </div>
          <Button size="sm" variant="outline" class="shrink-0" @click="emit('navigate', 'backup')">
            Back up
          </Button>
        </CardContent>
      </Card>

      <Card :class="!authConfirmed && 'border-amber-500/40'">
        <CardContent class="flex gap-3 px-4 py-3.5">
          <button
            class="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded border"
            :class="authConfirmed ? 'border-primary bg-primary text-primary-foreground' : 'border-muted-foreground/40'"
            @click="authConfirmed = !authConfirmed"
          >
            <Check v-if="authConfirmed" class="size-3" />
          </button>
          <div class="min-w-0 flex-1">
            <p class="flex items-center gap-1.5 text-sm font-medium">
              <KeyRound class="size-3.5" /> My two-factor codes are transferred
            </p>
            <p class="mt-0.5 text-xs leading-relaxed text-muted-foreground">
              Authenticator apps keep their secrets on the device and a backup
              does not always carry them. Export or enable cloud sync in each
              one first, or save the recovery codes for those accounts —
              otherwise you lose access to them, not just the app.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card :class="!findMyConfirmed && 'border-amber-500/40'">
        <CardContent class="flex gap-3 px-4 py-3.5">
          <button
            class="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded border"
            :class="findMyConfirmed ? 'border-primary bg-primary text-primary-foreground' : 'border-muted-foreground/40'"
            @click="findMyConfirmed = !findMyConfirmed"
          >
            <Check v-if="findMyConfirmed" class="size-3" />
          </button>
          <div class="min-w-0 flex-1">
            <p class="flex items-center gap-1.5 text-sm font-medium">
              <Lock class="size-3.5" /> Find My is off, or I know the Apple ID password
            </p>
            <p class="mt-0.5 text-xs leading-relaxed text-muted-foreground">
              Activation Lock survives a DFU restore. Without the password the
              device is unusable afterwards. Turn it off in Settings → your name
              → Find My → Find My iPhone.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card v-if="sideloaded?.length" class="border-amber-500/40">
        <CardContent class="flex gap-3 px-4 py-3.5">
          <AlertTriangle class="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-500" />
          <div class="min-w-0">
            <p class="text-sm font-medium">
              {{ sideloaded.length }} sideloaded app{{ sideloaded.length === 1 ? '' : 's' }}
              won't come back
            </p>
            <div class="mt-1.5 flex flex-wrap gap-1">
              <span
                v-for="a in sideloaded" :key="a.bundle_id"
                class="rounded bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground"
              >{{ a.name ?? a.bundle_id }}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </section>

    <!-- Walkthrough -->
    <section class="space-y-2.5">
      <h2 class="text-sm font-medium">Put the device in DFU mode</h2>

      <Card>
        <CardContent class="px-4 py-4">
          <div v-if="!started" class="space-y-3">
            <div class="flex items-center gap-2">
              <Badge variant="secondary" class="text-[11px]">{{ guide.label }}</Badge>
              <span class="text-xs text-muted-foreground">
                {{ info?.marketing_name ?? device.model }}
              </span>
            </div>
            <p class="text-xs leading-relaxed text-muted-foreground">
              The timing is the hard part, so the steps are walked through one at
              a time. Keep the cable connected the whole way.
            </p>
            <Button class="w-full" :disabled="!ready" @click="start">
              {{ ready ? 'Start the sequence' : 'Tick the boxes above first' }}
            </Button>
          </div>

          <div v-else-if="done" class="space-y-3 text-center">
            <p class="text-sm font-medium">Screen fully black?</p>
            <p class="text-xs leading-relaxed text-muted-foreground">
              Then the device is in DFU and Finder will offer
              <strong>Restore iPhone</strong>. If you see an Apple logo or a
              cable, it went into Recovery instead — start over.
            </p>
            <p class="text-xs leading-relaxed text-muted-foreground">
              elma doesn't perform the restore: Finder is Apple's own tool for
              it and handles a failure mid-flash better than we could.
            </p>
            <Button variant="outline" class="w-full" @click="reset">
              <RotateCcw class="size-3.5" /> Run it again
            </Button>
          </div>

          <div v-else class="flex items-center gap-5">
            <PhoneButtons :family="guide.family" :active="highlight" />
            <div class="min-w-0 flex-1 space-y-2">
              <p class="text-xs text-muted-foreground">
                Step {{ stepIndex + 1 }} of {{ guide.steps.length }}
              </p>
              <p class="text-sm font-medium leading-snug">{{ step?.text }}</p>
              <p v-if="step?.hold" class="text-3xl font-semibold tabular-nums">
                {{ remaining }}<span class="text-base font-normal text-muted-foreground">s</span>
              </p>
              <Button v-else size="sm" @click="advance">
                Done <ArrowRight class="size-3.5" />
              </Button>
              <button class="block text-xs text-muted-foreground underline" @click="reset">
                Start over
              </button>
            </div>
          </div>
        </CardContent>
      </Card>
    </section>

    <p class="flex items-start gap-2 text-xs leading-relaxed text-muted-foreground">
      <CircleAlert class="mt-0.5 size-3.5 shrink-0" />
      <span>
        A DFU restore can't permanently break the device — the bootrom always
        recovers — but an interrupted one leaves it stuck in Recovery until you
        restore again, with the data already gone.
      </span>
    </p>
  </div>
</template>
