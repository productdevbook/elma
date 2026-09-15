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
