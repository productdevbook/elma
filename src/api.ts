import { invoke } from '@tauri-apps/api/core'

export interface Device {
  udid: string
  name: string | null
  model: string | null
  version: string | null
  build: string | null
  transports: string[]
  paired: boolean
}

export interface DeviceInfo {
  udid: string
  name: string
  model: string
  version: string
  build: string
  serial: string
  capacity_bytes: number | null
  battery_percent: number | null
  activation: string
  wifi_mac: string
  bluetooth_mac: string
}

export interface App {
  bundle_id: string
  name: string | null
  version: string | null
  build: string | null
  type: string
  size_bytes: number | null
  min_ios: string | null
  from_store: boolean
}

export interface FileEntry {
  name: string
  path: string
  is_dir: boolean
  size_bytes: number
  modified: string
}

export interface SignedVersion {
  version: string
  build: string
  released: string
  size_bytes: number | null
  url: string | null
}

/** A failure the bridge could describe — `kind` is stable, `message` is not. */
export interface BridgeError {
  kind: string
  message: string
}

export interface BackupEncryption {
  enabled: boolean
}

export interface BackupResult {
  directory: string
  udid: string
}

export const api = {
  deviceList: () => invoke<Device[]>('device_list'),
  deviceInfo: (udid?: string) => invoke<DeviceInfo>('device_info', { params: { udid } }),
  appList: (kind: 'all' | 'user' | 'system' = 'user', udid?: string) =>
    invoke<App[]>('app_list', { params: { kind, udid } }),
  fileList: (path = '/', udid?: string) =>
    invoke<FileEntry[]>('file_list', { params: { path, udid } }),
  signedVersions: (model: string) =>
    invoke<SignedVersion[]>('ios_signed_versions', { params: { model } }),
  backupEncryption: (udid?: string) =>
    invoke<BackupEncryption>('backup_encryption', { params: { udid } }),
  backupCreate: (directory: string, udid?: string, full = true) =>
    invoke<BackupResult>('backup_create', { params: { directory, udid, full } }),
}
