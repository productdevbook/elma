# elma

A cross-platform device manager for iPhone and iPad. Runs on macOS, Windows and Linux.

Apple's own tooling is uneven here: `devicectl` hides most apps behind an
opt-in flag, Finder shows almost nothing, and the third-party options are
either macOS-only or closed source. elma is a small GUI over
[pymobiledevice3](https://github.com/doronz88/pymobiledevice3) that shows what's
actually on the device.

## What it does

- **Apps** — every installed app with version, size and whether it came from
  the App Store. Sideloaded apps are flagged, because those are the ones that
  won't come back on their own after a wipe. Exports to CSV.
- **Files** — browse the media area (DCIM, Downloads, Books) over AFC and
  copy files or whole folders back to your computer.
- **Device** — model, iOS build, serial, capacity, activation state.
- **Backup** — full device backup with live progress, and an upfront warning
  when backup encryption is off, since that silently drops saved passwords,
  Wi-Fi networks and Health data.
- **iOS versions** — which builds Apple currently signs for the connected
  device, fetched live.

None of this needs root. elma does not restore or erase devices; use Finder or
iTunes for that.

## Requirements

An iPhone or iPad, connected over USB and unlocked, paired with this computer.
Release builds carry their own Python, so nothing else is needed to run one.

## Development

```bash
bun install
cd python && pip install -e . && cd ..
bun run app
```

Release builds need the vendored Python runtime built first — it is not
checked in:

```bash
bash scripts/bundle-python.sh
bun run app:build
```

`bun run typecheck` runs TypeScript 7 over the sources. The `typescript`
dependency is pinned to 5.x because `@vue/compiler-sfc` drives the compiler
through its JS API to resolve the prop types shadcn components inherit from
reka-ui, and TypeScript 7 replaced that API with a native binary — it now
exports two symbols. Once Vue supports it, the pin goes away.

The Rust side spawns `python -m elma_bridge` and talks JSON-RPC to it over
stdin/stdout. `ELMA_PYTHON` and `ELMA_BRIDGE_DIR` override the interpreter and
the bridge directory.

## Architecture

```
Vue 3 + Tailwind 4 + shadcn-vue   UI
   ↓ invoke()
Rust (Tauri 2)            command routing, process supervision
   ↓ JSON-RPC over stdio
Python bridge             pymobiledevice3 wrappers
   ↓ usbmux / lockdown
device
```

The bridge is one long-lived process: the lockdown connection stays open
between calls, and requests are matched to responses by id so they can overlap.

## Licence

GPL-3.0. pymobiledevice3 is GPL-3.0 and elma is built around it.
