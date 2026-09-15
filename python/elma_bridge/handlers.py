"""
Wrappers around pymobiledevice3.

Each function here becomes an RPC method. The device connection lives in
`_Connection` and stays open between calls — reconnecting per request is slow.

Note: nothing in this layer needs root. The iOS 17+ tunnel (sudo) is only
required for developer/remote services, which are out of scope for v1.
"""
from __future__ import annotations

import asyncio
import json
import urllib.request
from typing import Any, Callable

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.usbmux import list_devices
from pymobiledevice3.services.installation_proxy import InstallationProxyService
from pymobiledevice3.services.afc import AfcService


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
        pick the fields the UI actually renders."""
        ld = await conn.get(udid)
        v = await ld.get_value()
        return {
            "udid": v.get("UniqueDeviceID"),
            "name": v.get("DeviceName"),
            "model": v.get("ProductType"),
            "version": v.get("ProductVersion"),
            "build": v.get("BuildVersion"),
            "serial": v.get("SerialNumber"),
            "color": v.get("DeviceColor"),
            "capacity_bytes": v.get("TotalDiskCapacity"),
            "battery_percent": v.get("BatteryCurrentCapacity"),
            "activation": v.get("ActivationState"),
            "wifi_mac": v.get("WiFiAddress"),
            "bluetooth_mac": v.get("BluetoothAddress"),
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

    return {
        "device.list": device_list,
        "device.info": device_info,
        "app.list": app_list,
        "file.list": file_list,
        "ios.signedVersions": signed_versions,
    }
