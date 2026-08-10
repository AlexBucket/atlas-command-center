"""AMP (Cubecoders) game server integration."""

import httpx
from config import config


async def _login() -> str | None:
    """Login to AMP and return a Bearer token."""
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.post(
                f"{config.amp_url}/API/Core/Login",
                json={
                    "username": config.amp_user,
                    "password": config.amp_pass,
                    "rememberMe": False,
                    "token": "",
                    "setSession": True,
                },
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    return data.get("sessionID")
        return None
    except Exception:
        return None


async def get_instances() -> list[dict]:
    """Get all AMP game server instances."""
    session = await _login()
    if not session:
        return []

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.post(
                f"{config.amp_url}/API/ADSModule/GetInstances",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {session}",
                },
                json={},
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    instances = data[0].get("AvailableInstances", [])
                    return [
                        {
                            "name": i.get("FriendlyName", i.get("InstanceName", "Unknown")),
                            "id": i.get("InstanceID", ""),
                            "module": i.get("ModuleDisplayName", i.get("Module", "")),
                            "running": i.get("Running", False),
                            "state": i.get("AppState", 0),
                            "cpu_percent": i.get("Metrics", {}).get("CPU Usage", {}).get("Percent", 0),
                            "mem_percent": i.get("Metrics", {}).get("Memory Usage", {}).get("Percent", 0),
                            "mem_raw_mb": i.get("Metrics", {}).get("Memory Usage", {}).get("RawValue", 0),
                            "mem_max_mb": i.get("Metrics", {}).get("Memory Usage", {}).get("MaxValue", 0),
                            "active_users": i.get("Metrics", {}).get("Active Users", {}).get("RawValue", 0),
                            "max_users": i.get("Metrics", {}).get("Active Users", {}).get("MaxValue", 0),
                            "disk_usage_mb": i.get("DiskUsageMB", 0),
                            "endpoints": [
                                {
                                    "name": e.get("DisplayName", ""),
                                    "address": e.get("Endpoint", ""),
                                }
                                for e in i.get("ApplicationEndpoints", [])
                                if "Game" in e.get("DisplayName", "") or "Application" in e.get("DisplayName", "")
                            ][:2],
                            "display_image": i.get("DisplayImageSource", ""),
                        }
                        for i in instances
                        if i.get("Module") != "ADS"  # Filter out the AMP management module itself
                    ]
    except Exception:
        return []

    return []


async def get_status() -> dict:
    """Get quick AMP overview for dashboard."""
    instances = await get_instances()
    total = len(instances)
    running = sum(1 for i in instances if i["running"])
    total_users = sum(i["active_users"] for i in instances)
    return {
        "total_servers": total,
        "running_servers": running,
        "total_players": total_users,
        "servers": instances,
    }


async def send_console_command(instance_id: str, command: str) -> dict:
    """Send a console command to an AMP instance via the instance's own API."""
    session = await _login()
    if not session:
        return {"error": "Failed to authenticate"}
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.post(
                f"{config.amp_url}/API/Core/SendConsoleCommand",
                headers={"Accept": "application/json", "Authorization": f"Bearer {session}"},
                json={"command": command},
            )
            return {"status": resp.status_code, "success": resp.status_code == 200}
    except Exception as e:
        return {"error": str(e)}


async def start_instance(instance_id: str) -> dict:
    """Start an AMP instance."""
    session = await _login()
    if not session:
        return {"error": "Failed to authenticate"}
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.post(
                f"{config.amp_url}/API/ADSModule/StartInstance",
                headers={"Accept": "application/json", "Authorization": f"Bearer {session}"},
                json={"instanceId": instance_id},
            )
            return {"status": resp.status_code, "success": resp.status_code == 200}
    except Exception as e:
        return {"error": str(e)}


async def stop_instance(instance_id: str) -> dict:
    """Stop an AMP instance."""
    session = await _login()
    if not session:
        return {"error": "Failed to authenticate"}
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.post(
                f"{config.amp_url}/API/ADSModule/StopInstance",
                headers={"Accept": "application/json", "Authorization": f"Bearer {session}"},
                json={"instanceId": instance_id},
            )
            return {"status": resp.status_code, "success": resp.status_code == 200}
    except Exception as e:
        return {"error": str(e)}


async def restart_instance(instance_id: str) -> dict:
    """Restart an AMP instance."""
    session = await _login()
    if not session:
        return {"error": "Failed to authenticate"}
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.post(
                f"{config.amp_url}/API/ADSModule/RestartInstance",
                headers={"Accept": "application/json", "Authorization": f"Bearer {session}"},
                json={"instanceId": instance_id},
            )
            return {"status": resp.status_code, "success": resp.status_code == 200}
    except Exception as e:
        return {"error": str(e)}