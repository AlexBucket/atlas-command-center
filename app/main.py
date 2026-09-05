import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import config
from app.services import (
    system, docker, adguard, homeassistant, weather, shift,
    nzbget, amp, mediaarr, hermes, proxmox, alerts, github, intelligence,
)
from app.vnext.router import vnext_router

app = FastAPI(title="Atlas Command Center v3", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(vnext_router)

# Templates — raw Jinja2 to avoid Jinja2Templates cache issue
templates_dir = Path(__file__).parent / "templates"
jinja = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=select_autoescape(["html", "xml"]))

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

def render(name: str, **kw) -> HTMLResponse:
    return HTMLResponse(jinja.get_template(name).render(**kw))


# ── Health check ──────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}


# ── Overview ──────────────────────────────────────────────────

@app.get("/api/overview")
async def overview():
    import asyncio
    tasks = {
        "system": system.get_system_stats(),
        "docker": docker.get_docker_stats(),
        "ha": homeassistant.get_ha_stats(),
        "adguard": adguard.get_adguard_stats(),
        "weather": weather.get_weather(),
        "shift": shift.get_shift_info(),
        "nzbget": nzbget.get_nzbget_stats(),
        "amp": amp.get_amp_stats(),
        "media": mediaarr.get_arr_stats(),
        "hermes": hermes.get_hermes_stats(),
        "proxmox": proxmox.get_proxmox_stats(),
    }
    results = {}
    for name, task in tasks.items():
        try:
            if asyncio.iscoroutine(task):
                results[name] = await task
            else:
                results[name] = task
        except Exception as e:
            results[name] = {"error": str(e)}

    # ── Normalize data shapes for frontend widgets ────────

    # System: flatten cpu percent into {cpu:{percent}}, memory into {percent, used_gb, total_gb},
    # disk into {percent, used_gb, total_gb}, uptime as human string
    sys_raw = results.get("system", {})
    if sys_raw and "error" not in sys_raw:
        mem = sys_raw.get("memory", {})
        # Use first real disk mountpoint (not /etc/*)
        disk_raw = sys_raw.get("disk", {})
        first_disk = None
        for mp, info in disk_raw.items():
            if mp.startswith("/") and not mp.startswith("/etc/"):
                first_disk = info
                break
        if not first_disk:
            first_disk = {}
        uptime_s = sys_raw.get("uptime_seconds", 0)
        days = uptime_s // 86400
        hours = (uptime_s % 86400) // 3600
        uptime_str = f"{int(days)}d {int(hours)}h" if days else f"{int(hours)}h"
        results["system"] = {
            "cpu": {"percent": sys_raw.get("cpu_percent", 0)},
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
            "uptime": uptime_str,
        }

    # Weather: map temperature→temp, condition→weather_description, icon→condition_icon
    wx = results.get("weather", {})
    if wx and "error" not in wx:
        results["weather"] = {
            "temp": wx.get("temperature"),
            "weather_description": wx.get("condition", "Unknown"),
            "humidity": wx.get("humidity"),
            "wind_speed": wx.get("wind_speed"),
            "condition_icon": wx.get("icon", ""),
        }

    # Media: add wanted/missing/book_count fields, use author_count→book_count
    m = results.get("media", {})
    if m and "error" not in m:
        sonarr = m.get("sonarr", {})
        radarr = m.get("radarr", {})
        lidarr = m.get("lidarr", {})
        readarr = m.get("readarr", {})
        prowlarr = m.get("prowlarr", {})
        results["media"] = {
            "sonarr": {
                "series_count": sonarr.get("series_count", 0),
                "wanted": sonarr.get("wanted", 0),
            },
            "radarr": {
                "movie_count": radarr.get("movie_count", 0),
                "missing": radarr.get("missing", 0),
            },
            "lidarr": {
                "artist_count": lidarr.get("artist_count", 0),
            },
            "readarr": {
                "book_count": readarr.get("author_count", 0) or readarr.get("book_count", 0),
            },
            "prowlarr": {
                "indexer_count": prowlarr.get("indexer_count", 0),
            },
        }

    # AMP: alias instances → servers for the games widget
    amp_data = results.get("amp", {})
    if amp_data and "error" not in amp_data:
        amp_data["servers"] = amp_data.get("instances", [])

    return {"data": results}


# ── Individual API endpoints ──────────────────────────────────

@app.get("/api/system")
async def api_system():
    return {"data": system.get_system_stats()}

@app.get("/api/docker")
async def api_docker():
    return {"data": await docker.get_docker_stats()}

@app.get("/api/homeassistant")
async def api_ha():
    return {"data": await homeassistant.get_ha_stats()}

@app.get("/api/adguard")
async def api_adguard():
    return {"data": await adguard.get_adguard_stats()}

@app.get("/api/adguard/recent")
async def api_adguard_recent():
    return {"data": await adguard.get_adguard_recent()}

@app.get("/api/weather")
async def api_weather():
    raw = await weather.get_weather()
    if raw and "error" not in raw:
        return {"data": {
            "temp": raw.get("temperature"),
            "weather_description": raw.get("condition", "Unknown"),
            "humidity": raw.get("humidity"),
            "wind_speed": raw.get("wind_speed"),
            "condition_icon": raw.get("icon", ""),
        }}
    return {"data": raw}

@app.get("/api/shift")
async def api_shift():
    raw = await shift.get_shift_info()
    if raw and "error" not in raw:
        today = raw.get("today_shift", "Off")
        alarms = raw.get("alarm_times", [])
        return {"data": {
            "shift": today,
            "detail": raw.get("raw_data", {}).get("detail", today + " Shift"),
            "shift_start": raw.get("today_shift", ""),
            "alarm_time": alarms[0] if alarms else "",
            "cycle_progress": "",
        }}
    return {"data": raw}

@app.get("/api/nzbget")
async def api_nzbget():
    return {"data": await nzbget.get_nzbget_stats()}

@app.get("/api/amp")
async def api_amp():
    return {"data": await amp.get_amp_stats()}

@app.get("/api/arr")
async def api_arr():
    return {"data": await mediaarr.get_arr_stats()}

@app.get("/api/hermes")
async def api_hermes():
    return {"data": await hermes.get_hermes_stats()}

@app.get("/api/proxmox")
async def api_proxmox():
    return {"data": await proxmox.get_proxmox_stats()}

@app.get("/api/alerts")
async def api_alerts():
    return {"data": await alerts.get_alerts()}


# ── GitHub API endpoints ──────────────────────────────────────

@app.get("/api/github")
async def api_github_overview():
    return await github.get_overview()

@app.get("/api/github/prs")
async def api_github_prs(repo: str = "AlexBucket/atlas-config"):
    return await github.get_prs(repo)

@app.get("/api/github/issues")
async def api_github_issues(repo: str = "AlexBucket/atlas-config"):
    return await github.get_issues(repo)

@app.get("/api/github/commits")
async def api_github_commits(repo: str = "AlexBucket/atlas-config"):
    return await github.get_commits(repo)

@app.get("/api/github/workflows")
async def api_github_workflows(repo: str = "AlexBucket/atlas-config"):
    return await github.get_workflows(repo)

@app.post("/api/github/pr/{repo}/{pr_number}/approve")
async def api_github_approve_pr(repo: str, pr_number: int):
    full_repo = f"AlexBucket/{repo}" if "/" not in repo else repo
    return await github.approve_pr(full_repo, pr_number)

@app.post("/api/github/workflows/{repo}/{run_id}/rerun")
async def api_github_rerun_workflow(repo: str, run_id: int):
    full_repo = f"AlexBucket/{repo}" if "/" not in repo else repo
    return await github.rerun_workflow(full_repo, run_id)


# ── Page routes ───────────────────────────────────────────────

@app.get("/")
async def index():
    return render("index.html")

@app.get("/infra")
async def infra_page():
    return render("infra.html")

@app.get("/media")
async def media_page():
    return render("media.html")

@app.get("/network")
async def network_page():
    return render("network.html")

@app.get("/games")
async def games_page():
    return render("games.html")

@app.get("/github")
async def github_page():
    return render("github.html")


# ── Intelligence API endpoints ────────────────────────────────

@app.get("/api/intelligence")
async def api_intelligence_stats():
    return intelligence.get_stats()

@app.get("/api/intelligence/graph")
async def api_intelligence_graph():
    return intelligence.get_graph()

@app.get("/api/intelligence/tags")
async def api_intelligence_tags():
    return intelligence.get_tags()

@app.get("/api/intelligence/timeline")
async def api_intelligence_timeline():
    return intelligence.get_timeline()

@app.get("/api/intelligence/recent")
async def api_intelligence_recent():
    return intelligence.get_recent()

@app.get("/api/intelligence/note")
async def api_intelligence_note(path: str = ""):
    return intelligence.get_note(path)


@app.get("/intelligence")
async def intelligence_page():
    return render("intelligence.html")


@app.get("/ping")
async def ping():
    return {"ping": "pong"}


# ── Prometheus Metrics ──────────────────────────────────────

METRICS_START = datetime.now(timezone.utc)


@app.get("/metrics")
async def prometheus_metrics():
    """Expose Prometheus-format metrics for the atlas-command-center scrape job."""
    uptime = (datetime.now(timezone.utc) - METRICS_START).total_seconds()
    lines = [
        '# HELP atlas_cc_up Whether the Command Center is reachable (1=up)',
        '# TYPE atlas_cc_up gauge',
        'atlas_cc_up 1',
        '',
        '# HELP atlas_cc_uptime_seconds Command Center uptime in seconds',
        '# TYPE atlas_cc_uptime_seconds counter',
        f'atlas_cc_uptime_seconds {uptime}',
        '',
        '# HELP atlas_cc_version_info Command Center version info',
        '# TYPE atlas_cc_version_info gauge',
        'atlas_cc_version_info{version="3.0.0"} 1',
        '',
    ]
    return HTMLResponse("\n".join(lines), status_code=200, media_type="text/plain; charset=utf-8")


# ── Daily Summary endpoints (used by Hermes cron briefings) ──

BRIEFINGS_FILE = Path("/app/data/briefings.json")


def _read_briefings() -> list:
    try:
        with open(BRIEFINGS_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def _write_briefings(data: list):
    BRIEFINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BRIEFINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


@app.get("/api/summary")
async def get_summary():
    """Get the latest morning and evening briefings (backward compat)."""
    b = _read_briefings()
    morning = next((x for x in reversed(b) if x["type"] == "morning"), {})
    evening = next((x for x in reversed(b) if x["type"] == "evening"), {})
    return {"morning": morning, "evening": evening}


@app.get("/api/summary/history")
async def get_summary_history():
    """Get all briefings, newest first."""
    b = _read_briefings()
    return {"briefings": list(reversed(b))}


@app.post("/api/summary/morning")
async def set_morning_summary(data: dict):
    """Append a morning briefing to history."""
    s = _read_briefings()
    s.append({
        "type": "morning",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "summary": data.get("summary", ""),
        "tasks": data.get("tasks", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })
    _write_briefings(s)
    return {"status": "ok"}


@app.post("/api/summary/evening")
async def set_evening_summary(data: dict):
    """Append an evening briefing to history."""
    s = _read_briefings()
    s.append({
        "type": "evening",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "summary": data.get("summary", ""),
        "achievements": data.get("achievements", []),
        "rollover": data.get("rollover", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })
    _write_briefings(s)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=config.port, reload=True)