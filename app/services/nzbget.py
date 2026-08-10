"""NZBGet download status."""

import httpx
from config import config


async def nzbget_stats() -> dict:
    try:
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            # NZBGet uses JSON-RPC
            payload = {
                "method": "status",
                "params": [],
                "id": 1,
            }
            resp = await client.post(
                config.nzbget_url + "/jsonrpc",
                json=payload,
                auth=(config.nzbget_user, config.nzbget_pass),
            )
            if resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code}"}

            data = resp.json().get("result", {})

            # Get queue too
            queue_payload = {
                "method": "listgroups",
                "params": [],
                "id": 2,
            }
            queue_resp = await client.post(
                config.nzbget_url + "/jsonrpc",
                json=queue_payload,
                auth=(config.nzbget_user, config.nzbget_pass),
            )

            queue_data = []
            if queue_resp.status_code == 200:
                queue_data = queue_resp.json().get("result", [])

            download_rate = data.get("DownloadRate", 0)
            download_limit = data.get("DownloadLimit", 0)
            queue_size = data.get("QueueSize", 0)
            remaining_size = data.get("RemainingSize", 0)

            return {
                "download_rate_human": format_speed(download_rate),
                "download_rate_raw": download_rate,
                "download_limit_human": format_speed(download_limit) if download_limit > 0 else "Unlimited",
                "queue_size_human": format_bytes(queue_size),
                "remaining_human": format_bytes(remaining_size),
                "queue_count": data.get("RemainingSizeMB", 0),  # fallback
                "active_downloads": data.get("ActiveDownloads", 0),
                "status": data.get("Status", "UNKNOWN"),
                "uptime": data.get("UpTimeSec", 0),
                "queue_items": len(queue_data),
                "paused_downloads": sum(1 for g in queue_data if g.get("PausedSize")),
                "downloads": [
                    {
                        "name": g.get("NZBNicename", ""),
                        "size_human": format_bytes(g.get("FileSize", 0)),
                        "progress": round(
                            (g.get("FileSizeLo", 0) / max(g.get("FileSize", 1), 1)) * 100
                            if g.get("FileSize", 0) > 0 else 0, 1
                        ) if g.get("FileSize", 0) > 0 else 0,
                        "status": g.get("Status", ""),
                    }
                    for g in queue_data[:10]
                ],
            }
    except Exception as e:
        return {"error": str(e)}


def format_speed(bps: int) -> str:
    if bps < 1024:
        return f"{bps} B/s"
    elif bps < 1024**2:
        return f"{bps / 1024:.1f} KB/s"
    elif bps < 1024**3:
        return f"{bps / 1024**2:.1f} MB/s"
    else:
        return f"{bps / 1024**3:.1f} GB/s"


def format_bytes(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    elif b < 1024**2:
        return f"{b / 1024:.1f} KB"
    elif b < 1024**3:
        return f"{b / 1024**2:.1f} MB"
    else:
        return f"{b / 1024**3:.1f} GB"