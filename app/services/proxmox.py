"""Proxmox VE stats via API."""

import httpx
import ssl
from config import config


async def proxmox_stats() -> dict:
    if not config.proxmox_token or not config.proxmox_secret:
        return {
            "configured": False,
            "message": "Proxmox API token not configured. Add to config.py or set env vars.",
        }

    try:
        # Create SSL context that accepts self-signed certs
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        # Proxmox uses PVEAPIToken header format, not BasicAuth
        auth_header = f"PVEAPIToken={config.proxmox_token}={config.proxmox_secret}"

        async with httpx.AsyncClient(timeout=10.0, verify=ssl_ctx) as client:
            # Get node status
            resp = await client.get(
                f"{config.proxmox_url}/api2/json/nodes/pve/status",
                headers={"Authorization": auth_header},
            )
            if resp.status_code != 200:
                return {"error": f"Proxmox HTTP {resp.status_code}"}
            node = resp.json().get("data", {})

            # Get containers
            lxc_resp = await client.get(
                f"{config.proxmox_url}/api2/json/nodes/pve/lxc",
                headers={"Authorization": auth_header},
            )
            lxc_list = lxc_resp.json().get("data", []) if lxc_resp.status_code == 200 else []

            # Get VMs
            vm_resp = await client.get(
                f"{config.proxmox_url}/api2/json/nodes/pve/qemu",
                headers={"Authorization": auth_header},
            )
            vm_list = vm_resp.json().get("data", []) if vm_resp.status_code == 200 else []

            return {
                "configured": True,
                "node": {
                    "cpu_percent": round(node.get("cpu", 0) * 100, 1),
                    "memory_total_gb": round(node.get("memory", {}).get("total", 0) / (1024**3), 1),
                    "memory_used_gb": round(node.get("memory", {}).get("used", 0) / (1024**3), 1),
                    "memory_percent": round(
                        node.get("memory", {}).get("used", 0) / max(node.get("memory", {}).get("total", 1), 1) * 100, 1
                    ),
                    "uptime": node.get("uptime", 0),
                    "kver": node.get("kver", ""),
                },
                "lxc": [
                    {
                        "vmid": vm.get("vmid"),
                        "name": vm.get("name", ""),
                        "status": vm.get("status", ""),
                        "cpu": vm.get("cpu", 0),
                        "mem_pct": vm.get("mem", 0),
                    }
                    for vm in lxc_list
                ],
                "vms": [
                    {
                        "vmid": vm.get("vmid"),
                        "name": vm.get("name", ""),
                        "status": vm.get("status", ""),
                        "cpu": vm.get("cpu", 0),
                        "mem_pct": vm.get("mem", 0),
                    }
                    for vm in vm_list
                ],
            }
    except Exception as e:
        return {"error": str(e)}