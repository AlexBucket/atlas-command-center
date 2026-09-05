"""
Atlas vNext — Service Wrapper Layer.

Provides a clean, consistent async interface over the existing service modules.
Every service returns: {"status": "ok"|"error", "data": {...} | None, "error": str | None}

This is the ONLY layer that touches existing services. Widgets never import them directly.
"""

import asyncio
import time
from datetime import datetime, timezone

from app import services as svc


# ── Timeout per service (seconds) ─────────────────────────────
TIMEOUT = 10


async def _call(method, name: str) -> dict:
    """Call an async service method with timeout + error wrapping."""
    try:
        task = method()
        if asyncio.iscoroutine(task):
            result = await asyncio.wait_for(task, timeout=TIMEOUT)
        else:
            result = task
    except asyncio.TimeoutError:
        return {"status": "error", "data": None, "error": f"{name}: timed out after {TIMEOUT}s"}
    except Exception as e:
        return {"status": "error", "data": None, "error": f"{name}: {e}"}

    # If the service itself returned an error dict, propagate it
    if isinstance(result, dict) and "error" in result and result["error"]:
        return {"status": "error", "data": result, "error": result["error"]}

    return {"status": "ok", "data": result, "error": None}


# ── Normalizers: raw service data → stable widget-ready shape ──


def _normalize_system(raw: dict) -> dict:
    mem = raw.get("memory", {})
    disk_raw = raw.get("disk", {})
    # Pick first real disk
    first_disk = next(
        (info for mp, info in disk_raw.items()
         if mp.startswith("/") and not mp.startswith("/etc/")),
        {}
    )
    uptime_s = raw.get("uptime_seconds", 0)
    days = uptime_s // 86400
    hours = (uptime_s % 86400) // 3600
    return {
        "cpu_percent": raw.get("cpu_percent", 0),
        "memory": {
            "percent": mem.get("percent", 0),
            "used_gb": round(mem.get("used", 0) / 1073741824, 1),
            "total_gb": round(mem.get("total", 0) / 1073741824, 1),
        },
        "disk": {
            "percent": first_disk.get("percent", 0),
            "used_gb": round(first_disk.get("used", 0) / 1073741824, 1),
            "total_gb": round(first_disk.get("total", 0) / 1073741824, 1),
        },
        "uptime": f"{int(days)}d {int(hours)}h" if days else f"{int(hours)}h",
    }


def _normalize_docker(raw: dict) -> dict:
    return {
        "running": raw.get("running", 0),
        "total": raw.get("total", 0),
        "containers": [
            {
                "name": c.get("name", "?"),
                "state": c.get("state", "?"),
                "status": c.get("status", ""),
                "image": c.get("image", ""),
            }
            for c in raw.get("containers", [])
        ],
    }


def _normalize_ha(raw: dict) -> dict:
    return {
        "connected": raw.get("connected", False),
        "version": raw.get("version"),
        "entity_count": raw.get("entity_count", 0),
        "people_home": raw.get("people_home", 0),
        "people": [
            {"name": p.get("name", "?"), "state": p.get("state", "")}
            for p in raw.get("people", [])
        ],
        "temperatures": [
            {"name": t.get("name", "?"), "state": t.get("temperature", t.get("state", ""))}
            for t in raw.get("temperatures", [])
        ],
    }


def _normalize_weather(raw: dict) -> dict:
    return {
        "temp": raw.get("temperature") or raw.get("temp"),
        "feels_like": raw.get("feels_like"),
        "condition": raw.get("condition") or raw.get("weather_description", "Unknown"),
        "humidity": raw.get("humidity"),
        "wind_speed": raw.get("wind_speed"),
        "icon": raw.get("icon") or raw.get("condition_icon", ""),
    }


def _normalize_shift(raw: dict) -> dict:
    today = raw.get("today_shift", raw.get("shift", "Off"))
    alarms = raw.get("alarm_times", raw.get("alarms", []))
    if isinstance(alarms, str):
        alarms = [a.strip() for a in alarms.split(",") if a.strip()]
    detail = raw.get("raw_data", {}).get("detail", today + " Shift") if isinstance(raw.get("raw_data"), dict) else today + " Shift"
    return {
        "shift": today,
        "detail": detail,
        "alarm_time": alarms[0] if alarms else "",
        "alarm_times": alarms,
        "bin_night": raw.get("bin_night", "No"),
        "is_bin_night": str(raw.get("bin_night", "No")).lower() in ("yes", "true", "tonight"),
    }


def _normalize_nzbget(raw: dict) -> dict:
    downloads = [
        {"name": d.get("name", "?"), "progress": d.get("progress", 0)}
        for d in raw.get("active_downloads", [])
    ]
    return {
        "download_rate_human": f"{raw.get('download_rate_mbps', 0)} MB/s" if raw.get('download_rate_mbps') else "0 B/s",
        "queue_size_mb": raw.get("queue_size_mb", 0),
        "active_downloads": downloads,
        "paused": raw.get("paused", False),
    }


def _normalize_media(raw: dict) -> dict:
    return {
        "sonarr": {
            "series_count": raw.get("sonarr", {}).get("series_count", 0),
            "wanted": raw.get("sonarr", {}).get("wanted", 0),
        },
        "radarr": {
            "movie_count": raw.get("radarr", {}).get("movie_count", 0),
            "missing": raw.get("radarr", {}).get("missing", 0),
        },
        "lidarr": {
            "artist_count": raw.get("lidarr", {}).get("artist_count", 0),
        },
        "readarr": {
            "book_count": raw.get("readarr", {}).get("author_count", 0) or raw.get("readarr", {}).get("book_count", 0),
        },
        "prowlarr": {
            "indexer_count": raw.get("prowlarr", {}).get("indexer_count", 0),
        },
    }


def _normalize_hermes(raw: dict) -> dict:
    return {
        "running": raw.get("running", False),
        "skill_count": raw.get("skill_count", 0),
        "cron_count": raw.get("cron_count", 0),
        "plugin_count": raw.get("plugin_count", 0),
    }


def _normalize_amp(raw: dict) -> dict:
    instances = raw.get("instances", [])
    return {
        "connected": raw.get("connected", False),
        "servers": [
            {
                "name": i.get("friendly_name", i.get("name", "?")),
                "id": i.get("id", ""),
                "running": i.get("running", False),
                "module": i.get("module", ""),
                "active_users": i.get("active_users", 0),
            }
            for i in instances
        ],
    }


def _normalize_proxmox(raw: dict) -> dict:
    node = raw.get("node", {})
    return {
        "configured": raw.get("configured", raw.get("available", False)),
        "node": {
            "hostname": node.get("hostname", ""),
            "cpu_percent": node.get("cpu_percent", 0),
            "cpu_count": node.get("cpu_count", 0),
            "memory_percent": node.get("memory_percent", 0),
            "memory_used_gb": node.get("memory_used_gb", 0),
            "memory_total_gb": node.get("memory_total_gb", 0),
            "uptime": node.get("uptime", 0),
        },
        "vms": [
            {"vmid": v.get("vmid", ""), "name": v.get("name", ""), "status": v.get("status", "")}
            for v in raw.get("vms", [])
        ],
        "containers": raw.get("lxc", raw.get("containers", [])),
    }


def _normalize_adguard(raw: dict) -> dict:
    stats = raw.get("stats", {})
    filtering = raw.get("filtering", {})
    return {
        "connected": bool(stats),
        "total_queries": stats.get("total_queries", 0),
        "blocked": stats.get("blocked", 0),
        "blocked_percent": stats.get("blocked_percent", 0),
        "filter_rules_count": filtering.get("rules_count", 0),
        "avg_processing_time": stats.get("avg_processing_time", 0),
        "top_queried": stats.get("top_queried_domains", []),
        "top_blocked": stats.get("top_blocked_domains", []),
    }


# ── Registry ────────────────────────────────────────────────

SERVICE_FUNCS = {
    "system": svc.system.get_system_stats,
    "docker": svc.docker.get_docker_stats,
    "ha": svc.homeassistant.get_ha_stats,
    "weather": svc.weather.get_weather,
    "shift": svc.shift.get_shift_info,
    "nzbget": svc.nzbget.get_nzbget_stats,
    "media": svc.mediaarr.get_arr_stats,
    "hermes": svc.hermes.get_hermes_stats,
    "amp": svc.amp.get_amp_stats,
    "proxmox": svc.proxmox.get_proxmox_stats,
    "adguard": svc.adguard.get_adguard_stats,
}

NORMALIZERS = {
    "system": _normalize_system,
    "docker": _normalize_docker,
    "ha": _normalize_ha,
    "weather": _normalize_weather,
    "shift": _normalize_shift,
    "nzbget": _normalize_nzbget,
    "media": _normalize_media,
    "hermes": _normalize_hermes,
    "amp": _normalize_amp,
    "proxmox": _normalize_proxmox,
    "adguard": _normalize_adguard,
}

SERVICE_NAMES = list(SERVICE_FUNCS.keys())

# Services whose failure is "degraded" vs "critical"
CRITICAL_SERVICES = {"system", "docker", "ha", "shift"}


async def get_all_stats() -> dict:
    """Concurrently fetch all services, returning normalized stats.

    Returns: {name: {"status": "ok"|"error", "data": {...}, "error": str}}
    """
    tasks = {}
    for name in SERVICE_NAMES:
        tasks[name] = _call(SERVICE_FUNCS[name], name)

    results = {}
    for name, task in tasks.items():
        raw = await task
        if raw["status"] == "ok" and raw["data"] is not None:
            normalizer = NORMALIZERS.get(name)
            if normalizer:
                try:
                    normalized = normalizer(raw["data"])
                    results[name] = {"status": "ok", "data": normalized, "error": None}
                except Exception as e:
                    results[name] = {"status": "error", "data": None, "error": f"{name} normalize: {e}"}
            else:
                results[name] = raw
        else:
            results[name] = raw

    return results


def get_overall_health(results: dict) -> dict:
    """Summarize overall health from per-service results."""
    total = len(SERVICE_NAMES)
    ok_count = sum(1 for r in results.values() if r["status"] == "ok")
    error_count = total - ok_count
    critical_failures = sum(
        1 for name in CRITICAL_SERVICES
        if results.get(name, {}).get("status") != "ok"
    )

    if critical_failures > 0:
        level = "critical"
    elif error_count > 0:
        level = "degraded"
    else:
        level = "healthy"

    return {
        "level": level,
        "total": total,
        "ok": ok_count,
        "errors": error_count,
        "critical_failures": critical_failures,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }