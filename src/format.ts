/** Human-readable byte size. Returns an em dash for null so tables stay aligned. */
export function formatBytes(n: number | null | undefined): string {
  if (n == null) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let v = n
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

/** Storage vendors count in powers of ten, so a "128 GB" phone reports
 *  128000000000 bytes. Dividing by 1024³ would show 119 GB and look wrong. */
export function formatCapacity(n: number | null | undefined): string {
  if (n == null) return '—'
  return `${Math.round(n / 1e9)} GB`
}

/** "4m 20s" / "1h 05m". Returns null when there's nothing meaningful to show. */
export function formatDuration(seconds: number | null | undefined): string | null {
  if (seconds == null || seconds < 0) return null
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  if (m < 60) return `${m}m ${String(s).padStart(2, '0')}s`
  const h = Math.floor(m / 60)
  return `${h}h ${String(m % 60).padStart(2, '0')}m`
}
