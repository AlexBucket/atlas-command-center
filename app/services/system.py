"""System-level stats from the host machine (CPU, RAM, Disk, Uptime)."""

import psutil
import time
import os


def get_system_stats():
    """Get core system stats from the host."""
    boot_ts = psutil.boot_time()
    uptime_seconds = time.time() - boot_ts
    uptime_str = format_uptime(uptime_seconds)

    cpu_percent = psutil.cpu_percent(interval=0.3)
    cpu_count = psutil.cpu_count()

    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    load_avg = psutil.getloadavg()

    return {
        "cpu": {
            "percent": round(cpu_percent, 1),
            "cores": cpu_count,
            "load_1m": round(load_avg[0], 2),
            "load_5m": round(load_avg[1], 2),
            "load_15m": round(load_avg[2], 2),
        },
        "memory": {
            "total_gb": round(mem.total / (1024**3), 1),
            "used_gb": round(mem.used / (1024**3), 1),
            "free_gb": round(mem.available / (1024**3), 1),
            "percent": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 1),
            "used_gb": round(disk.used / (1024**3), 1),
            "free_gb": round(disk.free / (1024**3), 1),
            "percent": disk.percent,
        },
        "uptime": uptime_str,
        "uptime_seconds": int(uptime_seconds),
        "hostname": os.uname().nodename,
    }


def format_uptime(seconds: float) -> str:
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    mins = int((seconds % 3600) // 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    parts.append(f"{mins}m")
    return " ".join(parts)