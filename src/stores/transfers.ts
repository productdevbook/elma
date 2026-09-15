import { computed, reactive, readonly } from 'vue'
import { listen } from '@tauri-apps/api/event'
import { api } from '@/api'

/**
 * Backup and restore progress, held outside the view.
 *
 * These run for minutes. When the state lived in BackupView, switching tabs
 * unmounted the component and took the progress and the event listener with
 * it — the transfer kept running with nothing showing it. The listeners here
 * are registered once for the life of the app instead.
 */

export type TransferKind = 'backup' | 'restore'

interface Transfer {
  kind: TransferKind
  udid: string
  directory: string
  percent: number
  /** Bytes written so far, measured on disk — the device link protocol
   *  carries no byte count of its own. Backups only. */
  bytesDone: number | null
  /** Extrapolated from percent, so it only appears once percent passes 1. */
  bytesTotal: number | null
  etaSeconds: number | null
  elapsedSeconds: number
  startedAt: number
}

interface ProgressPayload {
  percent: number
  bytes_done?: number
  bytes_total_estimate?: number | null
  eta_seconds?: number | null
  elapsed_seconds?: number
}

const state = reactive({
  active: null as Transfer | null,
  lastResult: null as { kind: TransferKind; path: string; bytes?: number } | null,
  lastError: null as { kind: TransferKind; message: string } | null,
})

let wired = false

/** Called once at startup; further calls are no-ops. */
export async function initTransfers() {
  if (wired) return
  wired = true
  const apply = (kind: TransferKind) => (e: { payload: ProgressPayload }) => {
    const t = state.active
    if (t?.kind !== kind) return
    t.percent = e.payload.percent
    if (e.payload.bytes_done != null) t.bytesDone = e.payload.bytes_done
    t.bytesTotal = e.payload.bytes_total_estimate ?? null
    t.etaSeconds = e.payload.eta_seconds ?? null
    if (e.payload.elapsed_seconds != null) t.elapsedSeconds = e.payload.elapsed_seconds
  }
  await listen<ProgressPayload>('backup.progress', apply('backup'))
  await listen<ProgressPayload>('restore.progress', apply('restore'))
}

export async function startBackup(directory: string, udid: string) {
  if (state.active) return
  state.active = {
    kind: 'backup', udid, directory, percent: 0,
    bytesDone: 0, bytesTotal: null, etaSeconds: null, elapsedSeconds: 0,
    startedAt: Date.now(),
  }
  state.lastResult = null
  state.lastError = null
  try {
    const r = await api.backupCreate(directory, udid)
    state.lastResult = { kind: 'backup', path: `${r.directory}/${r.udid}`, bytes: r.bytes }
  } catch (e: any) {
    state.lastError = { kind: 'backup', message: e?.message ?? String(e) }
  } finally {
    state.active = null
  }
}

export async function startRestore(directory: string, udid: string, password: string) {
  if (state.active) return
  state.active = {
    kind: 'restore', udid, directory, percent: 0,
    bytesDone: null, bytesTotal: null, etaSeconds: null, elapsedSeconds: 0,
    startedAt: Date.now(),
  }
  state.lastResult = null
  state.lastError = null
  try {
    await api.backupRestore(directory, udid, password)
    state.lastResult = { kind: 'restore', path: directory }
  } catch (e: any) {
    state.lastError = { kind: 'restore', message: e?.message ?? String(e) }
  } finally {
    state.active = null
  }
}

export function dismissResult() {
  state.lastResult = null
  state.lastError = null
}

export const transfers = readonly(state)
export const isBusy = computed(() => state.active !== null)
