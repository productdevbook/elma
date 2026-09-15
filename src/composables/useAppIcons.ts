import { api } from '@/api'

/**
 * Batches icon requests.
 *
 * Rows scroll into view a handful at a time, and each one asking on its own
 * would open a SpringBoard session per icon. Requests made within one frame
 * are collected and sent together; results are cached per device so
 * re-filtering the list doesn't refetch.
 */
const cache = new Map<string, string | null>()
const pending = new Map<string, Array<(url: string | null) => void>>()
let queue: string[] = []
let timer: ReturnType<typeof setTimeout> | null = null
let queueUdid: string | null = null

const MAX_BATCH = 24

async function flush() {
  timer = null
  const ids = queue
  const udid = queueUdid
  queue = []
  queueUdid = null
  if (!ids.length || !udid) return

  for (let i = 0; i < ids.length; i += MAX_BATCH) {
    const chunk = ids.slice(i, i + MAX_BATCH)
    let result: Record<string, string | null> = {}
    try {
      result = await api.appIcons(chunk, udid)
    } catch {
      // Leave them uncached: a later scroll past the same row retries.
      for (const id of chunk) pending.get(`${udid}:${id}`)?.forEach(fn => fn(null))
      for (const id of chunk) pending.delete(`${udid}:${id}`)
      continue
    }
    for (const id of chunk) {
      const key = `${udid}:${id}`
      const url = result[id] ?? null
      cache.set(key, url)
      pending.get(key)?.forEach(fn => fn(url))
      pending.delete(key)
    }
  }
}

export function requestIcon(udid: string, bundleId: string): Promise<string | null> {
  const key = `${udid}:${bundleId}`
  const cached = cache.get(key)
  if (cached !== undefined) return Promise.resolve(cached)

  return new Promise(resolve => {
    const waiting = pending.get(key)
    if (waiting) {
      waiting.push(resolve)
      return
    }
    pending.set(key, [resolve])

    // A device switch mid-batch would mix ids across devices; send what's
    // queued before starting a new one.
    if (queueUdid && queueUdid !== udid && timer) {
      clearTimeout(timer)
      flush()
    }
    queueUdid = udid
    queue.push(bundleId)
    timer ??= setTimeout(flush, 50)
  })
}
