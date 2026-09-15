"""
Wrappers around pymobiledevice3.

Each function here becomes an RPC method. The device connection lives in
`_Connection` and stays open between calls — reconnecting per request is slow.

Note: nothing in this layer needs root. The iOS 17+ tunnel (sudo) is only
required for developer/remote services, which are out of scope for v1.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import urllib.request
from typing import Any, Callable

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.usbmux import list_devices
from pymobiledevice3.services.installation_proxy import InstallationProxyService
from pymobiledevice3.services.afc import AfcService
from pymobiledevice3.services.springboard import SpringBoardServicesService
from pymobiledevice3.services.mobilebackup2 import Mobilebackup2Service


# lockdown reports a board identifier (iPhone17,5); people know the retail
# name. Only the models likely to show up are listed — unknown ones fall back
# to the identifier rather than guessing.
_MARKETING = {
    "iPhone17,5": "iPhone 16e",
    "iPhone17,3": "iPhone 16",
    "iPhone17,4": "iPhone 16 Plus",
    "iPhone17,1": "iPhone 16 Pro",
    "iPhone17,2": "iPhone 16 Pro Max",
    "iPhone16,1": "iPhone 15 Pro",
    "iPhone16,2": "iPhone 15 Pro Max",
    "iPhone15,4": "iPhone 15",
    "iPhone15,5": "iPhone 15 Plus",
    "iPhone14,7": "iPhone 14",
    "iPhone14,8": "iPhone 14 Plus",
    "iPhone15,2": "iPhone 14 Pro",
    "iPhone15,3": "iPhone 14 Pro Max",
}


class ElmaError(Exception):
    """A user-facing error. `kind` drives how the UI reacts."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


class _Connection:
    """Holds one open lockdown connection to a device."""

    def __init__(self) -> None:
        self._lockdown = None
        self._udid: str | None = None

    async def get(self, udid: str | None = None):
        if self._lockdown is not None and (udid is None or udid == self._udid):
            return self._lockdown
        try:
            self._lockdown = await create_using_usbmux(serial=udid)
            self._udid = self._lockdown.udid
        except Exception as e:
            raise ElmaError("device_not_found", f"could not connect: {e}") from e
        return self._lockdown

    async def close(self) -> None:
        if self._lockdown is not None:
            try:
                await self._lockdown.close()
            except Exception:
                pass
        self._lockdown = None
        self._udid = None


def build_registry(emit: Callable[[str, Any], None]) -> dict[str, Callable]:
    """Builds the RPC method name -> coroutine mapping."""
    conn = _Connection()

    # --- device --------------------------------------------------------

    async def device_list() -> list[dict]:
        """Connected devices. The same device can appear over both USB and
        network, so we merge on UDID and keep the transports as a list.

        usbmux only reports the serial and transport; name/model/version
        require a lockdown handshake, so we do one short-lived connection
        per device and tolerate failures (a locked or untrusted device
        still belongs in the list).
        """
        seen: dict[str, dict] = {}
        for d in await list_devices():
            udid = d.serial
            if udid is None:
                continue
            transport = d.connection_type or "?"
            existing = seen.get(udid)
            if existing is not None:
                if transport not in existing["transports"]:
                    existing["transports"].append(transport)
                continue

            entry = {
                "udid": udid,
                "name": None,
                "model": None,
                "version": None,
                "build": None,
                "transports": [transport],
                "paired": False,
            }
            try:
                ld = await create_using_usbmux(serial=udid)
                v = await ld.get_value()
                entry.update({
                    "name": v.get("DeviceName"),
                    "model": v.get("ProductType"),
                    "version": v.get("ProductVersion"),
                    "build": v.get("BuildVersion"),
                    "paired": True,
                })
                await ld.close()
            except Exception:
                # Not paired, locked, or busy — report what usbmux gave us.
                pass
            seen[udid] = entry
        return list(seen.values())

    async def device_info(udid: str | None = None) -> dict:
        """Detailed device info. The raw lockdown payload is huge, so we
        pick the fields the UI actually renders.

        Storage and battery live in their own domains and are queried
        separately; a device can refuse either without the rest failing.
        """
        ld = await conn.get(udid)
        v = await ld.get_value()

        storage: dict = {}
        try:
            d = await ld.get_value(domain="com.apple.disk_usage")
            total = d.get("TotalDiskCapacity")
            free = d.get("AmountDataAvailable")
            if total and free is not None:
                storage = {
                    "total_bytes": total,
                    "free_bytes": free,
                    "used_bytes": total - free,
                }
        except Exception:
            pass

        battery: dict = {}
        try:
            b = await ld.get_value(domain="com.apple.mobile.battery")
            battery = {
                "percent": b.get("BatteryCurrentCapacity"),
                "charging": bool(b.get("BatteryIsCharging")),
                "plugged_in": bool(b.get("ExternalConnected")),
            }
        except Exception:
            pass

        return {
            "udid": v.get("UniqueDeviceID"),
            "name": v.get("DeviceName"),
            "model": v.get("ProductType"),
            "marketing_name": _MARKETING.get(v.get("ProductType", ""), None),
            "version": v.get("ProductVersion"),
            "build": v.get("BuildVersion"),
            "serial": v.get("SerialNumber"),
            "color": v.get("DeviceColor"),
            "activation": v.get("ActivationState"),
            "wifi_mac": v.get("WiFiAddress"),
            "bluetooth_mac": v.get("BluetoothAddress"),
            "storage": storage,
            "battery": battery,
        }

    # --- apps ----------------------------------------------------------

    async def app_list(udid: str | None = None, kind: str = "all") -> list[dict]:
        """Installed apps.

        kind: "user" (App Store + sideloaded), "system" (Apple), "all".
        """
        ld = await conn.get(udid)
        async with InstallationProxyService(lockdown=ld) as ips:
            raw = await ips.get_apps()

        wanted = {"user": "User", "system": "System"}.get(kind)
        out = []
        for bundle_id, v in raw.items():
            app_type = v.get("ApplicationType", "?")
            if wanted is not None and app_type != wanted:
                continue
            out.append({
                "bundle_id": bundle_id,
                "name": v.get("CFBundleDisplayName") or v.get("CFBundleName"),
                "version": v.get("CFBundleShortVersionString"),
                "build": v.get("CFBundleVersion"),
                "type": app_type,
                "size_bytes": v.get("StaticDiskUsage"),
                "min_ios": v.get("MinimumOSVersion"),
                # Sideloaded apps don't come from the App Store; on a
                # rebuild the user has to reinstall those by hand.
                "from_store": "ApplicationDSID" in v,
            })
        out.sort(key=lambda a: (a["name"] or a["bundle_id"]).lower())
        return out

    async def app_icons(bundle_ids: list[str],
                        udid: str | None = None) -> dict[str, str | None]:
        """Icon PNGs for the given bundle ids, as data URLs.

        Called per visible batch rather than for the whole list: icons run
        4-65 KB each, so fetching all of them up front would move tens of
        megabytes for rows nobody scrolled to. A missing icon maps to null so
        the caller can stop asking for it.
        """
        ld = await conn.get(udid)
        out: dict[str, str | None] = {}

        # SpringBoard answers an unknown bundle id with a generic placeholder
        # instead of an error. It's byte-identical every time, so learn its
        # digest once and treat later matches as "no icon".
        placeholder: str | None = None

        async with SpringBoardServicesService(lockdown=ld) as sb:
            try:
                probe = await sb.get_icon_pngdata("elma.icon.probe.invalid")
                placeholder = hashlib.sha256(probe).hexdigest()
            except Exception:
                pass

            for bundle_id in bundle_ids:
                try:
                    png = await sb.get_icon_pngdata(bundle_id)
                except Exception:
                    out[bundle_id] = None
                    continue
                if placeholder and hashlib.sha256(png).hexdigest() == placeholder:
                    out[bundle_id] = None
                    continue
                out[bundle_id] = (
                    "data:image/png;base64,"
                    + base64.b64encode(png).decode("ascii")
                )
        return out

    # --- files ---------------------------------------------------------

    async def file_list(path: str = "/", udid: str | None = None) -> list[dict]:
        """Lists the media domain over AFC (DCIM, Downloads, Books…).
        App sandboxes are a different service and not reachable here."""
        ld = await conn.get(udid)
        async with AfcService(lockdown=ld) as afc:
            entries = []
            for name in await afc.listdir(path):
                full = path.rstrip("/") + "/" + name
                try:
                    st = await afc.stat(full)
                except Exception:
                    continue  # skip unreadable entries rather than fail the listing
                entries.append({
                    "name": name,
                    "path": full,
                    "is_dir": st.get("st_ifmt") == "S_IFDIR",
                    "size_bytes": int(st.get("st_size", 0)),
                    "modified": str(st.get("st_mtime", "")),
                })
        entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
        return entries

    # --- iOS versions --------------------------------------------------

    async def signed_versions(model: str) -> list[dict]:
        """iOS versions Apple currently signs — i.e. what can be installed.
        Signing windows close without notice, so this is never cached."""
        url = f"https://api.ipsw.me/v4/device/{model}?type=ipsw"

        def fetch() -> dict:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.load(r)

        try:
            data = await asyncio.to_thread(fetch)
        except Exception as e:
            raise ElmaError("network_error", f"version lookup failed: {e}") from e

        return [
            {
                "version": f["version"],
                "build": f["buildid"],
                "released": (f.get("releasedate") or "")[:10],
                "size_bytes": f.get("filesize"),
                "url": f.get("url"),
            }
            for f in data.get("firmwares", [])
            if f.get("signed")
        ]

    async def file_pull(remote: str, local_dir: str,
                       udid: str | None = None) -> dict:
        """Copies one file or folder off the device into `local_dir`.

        Folders are pulled recursively. Unreadable entries are skipped rather
        than aborting the whole transfer — a media folder usually has a few
        the device won't hand over.
        """
        ld = await conn.get(udid)
        name = remote.rstrip("/").rsplit("/", 1)[-1] or "device"
        target = os.path.join(local_dir, name)

        async with AfcService(lockdown=ld) as afc:
            try:
                info = await afc.stat(remote)
            except Exception as e:
                raise ElmaError("not_found", f"{remote}: {e}") from e

            is_dir = info.get("st_ifmt") == "S_IFDIR"
            try:
                if is_dir:
                    os.makedirs(target, exist_ok=True)
                    await afc.pull(remote, target, ignore_errors=True,
                                   progress_bar=False)
                else:
                    data = await afc.get_file_contents(remote)
                    os.makedirs(local_dir, exist_ok=True)
                    with open(target, "wb") as f:
                        f.write(data)
            except Exception as e:
                raise ElmaError("pull_failed", str(e)) from e

        return {"path": target, "is_dir": is_dir}

    # --- backup ---------------------------------------------------------

    async def backup_create(directory: str, udid: str | None = None,
                            full: bool = True) -> dict:
        """Backs the device up into `directory`/<udid>.

        Progress is streamed as events rather than returned, because a full
        backup takes minutes and the UI needs to show movement.
        """
        ld = await conn.get(udid)

        def on_progress(percent) -> None:
            try:
                emit("backup.progress", {"percent": float(percent)})
            except (TypeError, ValueError):
                pass  # the callback's payload shape isn't guaranteed

        async with Mobilebackup2Service(lockdown=ld) as svc:
            try:
                await svc.backup(full=full, backup_directory=directory,
                                 progress_callback=on_progress)
            except Exception as e:
                raise ElmaError("backup_failed", str(e)) from e

        return {"directory": directory, "udid": ld.udid}

    async def backup_info(directory: str, udid: str | None = None) -> dict:
        """Reads a backup's metadata without restoring it."""
        ld = await conn.get(udid)
        async with Mobilebackup2Service(lockdown=ld) as svc:
            try:
                return await svc.info(backup_directory=directory)
            except Exception as e:
                raise ElmaError("backup_unreadable", str(e)) from e

    async def backup_encryption(udid: str | None = None) -> dict:
        """Whether the device encrypts its backups.

        This matters before a wipe: an unencrypted backup silently drops
        Health data, saved passwords and Wi-Fi networks.
        """
        ld = await conn.get(udid)
        async with Mobilebackup2Service(lockdown=ld) as svc:
            return {"enabled": bool(await svc.get_will_encrypt())}

    return {
        "device.list": device_list,
        "device.info": device_info,
        "app.list": app_list,
        "app.icons": app_icons,
        "file.list": file_list,
        "ios.signedVersions": signed_versions,
        "file.pull": file_pull,
        "backup.create": backup_create,
        "backup.info": backup_info,
        "backup.encryption": backup_encryption,
    }
