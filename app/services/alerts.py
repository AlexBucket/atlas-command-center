"""Aggregate service health alerts.

Checks:
- Containers not running (from docker service)
- Disk > 85% usage (from system)
- NZBGet paused or failing (from nzbget)
- Proxmox node offline (from proxmox)
- Hermes offline (from hermes)
"""

from . import system, docker, nzbget, proxmox, hermes


async def get_alerts() -> list[dict]:
    """Aggregate health alerts from all monitored services."""
    alerts = []

    # --- Docker: containers not running ---
    try:
        dkr = await docker.container_stats()
        if isinstance(dkr, dict) and "error" not in dkr:
            containers = dkr.get("containers", [])
            if isinstance(containers, list):
                for c in containers:
                    if c.get("state") not in ("running", "exited"):
                        alerts.append({
                            "severity": "warning",
                            "title": f"Container: {c['name']}",
                            "detail": f"State is '{c['state']}' — not running or cleanly stopped.",
                            "service": "docker",
                        })
    except Exception as e:
        alerts.append({
            "severity": "critical",
            "title": "Docker service unreachable",
            "detail": str(e),
            "service": "docker",
        })

    # --- System: disk > 85% ---
    try:
        sys_stats = system.get_system_stats()
        disk = sys_stats.get("disk", {})
        disk_pct = disk.get("percent", 0)
        if disk_pct > 85:
            alerts.append({
                "severity": "warning" if disk_pct < 95 else "critical",
                "title": f"Disk usage at {disk_pct}%",
                "detail": f"{disk.get('used_gb', '?')} GB used of {disk.get('total_gb', '?')} GB",
                "service": "system",
            })
    except Exception as e:
        alerts.append({
            "severity": "warning",
            "title": "Cannot read system disk stats",
            "detail": str(e),
            "service": "system",
        })

    # --- NZBGet: paused or failing ---
    try:
        nz = await nzbget.nzbget_stats()
        if isinstance(nz, dict) and "error" not in nz:
            status = nz.get("status", "")
            if status == "PAUSED" or status.startswith("SLEEP"):
                alerts.append({
                    "severity": "info",
                    "title": "NZBGet is paused",
                    "detail": f"Status: {status}",
                    "service": "nzbget",
                })
            elif status not in ("RUNNING", "UNKNOWN", ""):
                alerts.append({
                    "severity": "warning",
                    "title": f"NZBGet status: {status}",
                    "detail": "Downloader may need attention.",
                    "service": "nzbget",
                })
    except Exception as e:
        alerts.append({
            "severity": "warning",
            "title": "Cannot reach NZBGet",
            "detail": str(e),
            "service": "nzbget",
        })

    # --- Proxmox: node offline ---
    try:
        px = await proxmox.proxmox_stats()
        if isinstance(px, dict) and "error" not in px:
            if not px.get("configured", True):
                pass  # not configured, skip
            node = px.get("node", {})
            if node.get("uptime", 1) <= 0:
                alerts.append({
                    "severity": "critical",
                    "title": "Proxmox node appears offline",
                    "detail": "Node uptime is 0 or negative.",
                    "service": "proxmox",
                })
            # Check for stopped VMs/containers
            for vm in px.get("vms", []):
                if vm.get("status") not in ("running",):
                    alerts.append({
                        "severity": "info",
                        "title": f"VM {vm.get('vmid')} ({vm.get('name')}) is {vm.get('status')}",
                        "detail": f"Status: {vm.get('status')}",
                        "service": "proxmox",
                    })
    except Exception as e:
        alerts.append({
            "severity": "warning",
            "title": "Cannot reach Proxmox API",
            "detail": str(e),
            "service": "proxmox",
        })

    # --- Hermes: offline ---
    try:
        hm = await hermes.hermes_stats()
        if isinstance(hm, dict) and "error" not in hm:
            if not hm.get("running", True):
                alerts.append({
                    "severity": "warning",
                    "title": "Hermes Agent is not running",
                    "detail": "The Hermes process has no PID on this host.",
                    "service": "hermes",
                })
    except Exception as e:
        alerts.append({
            "severity": "info",
            "title": "Cannot check Hermes status",
            "detail": str(e),
            "service": "hermes",
        })

    return alerts