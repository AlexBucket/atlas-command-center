import asyncio
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import config
from services import (
    system, docker, adguard, homeassistant, weather, shift,
    nzbget, amp, mediaarr, hermes, proxmox, alerts, github, intelligence,
)

app = FastAPI(title="Atlas Command Center v3", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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
        "docker": docker.container_stats(),
        "ha": homeassistant.ha_stats(),
        "adguard": adguard.adguard_stats(),
        "weather": weather.get_weather(),
        "shift": shift.get_today_shift(),
        "nzbget": nzbget.nzbget_stats(),
        "amp": amp.get_status(),
        "media": mediaarr.all_arr_stats(),
        "hermes": hermes.hermes_stats(),
        "proxmox": proxmox.proxmox_stats(),
    }
    results = {}
    for name, task in tasks.items():
        try:
            results[name] = await task
        except Exception as e:
            results[name] = {"error": str(e)}
    return results


# ── Individual API endpoints ──────────────────────────────────

@app.get("/api/system")
async def api_system():
    return system.get_system_stats()

@app.get("/api/docker")
async def api_docker():
    return await docker.container_stats()

@app.get("/api/homeassistant")
async def api_ha():
    return await homeassistant.ha_stats()

@app.get("/api/adguard")
async def api_adguard():
    return await adguard.adguard_stats()

@app.get("/api/adguard/recent")
async def api_adguard_recent():
    return await adguard.adguard_recent()

@app.get("/api/weather")
async def api_weather():
    return await weather.get_weather()

@app.get("/api/shift")
async def api_shift():
    return shift.get_today_shift()

@app.get("/api/nzbget")
async def api_nzbget():
    return await nzbget.nzbget_stats()

@app.get("/api/amp")
async def api_amp():
    return await amp.get_status()

@app.get("/api/arr")
async def api_arr():
    return await mediaarr.all_arr_stats()

@app.get("/api/hermes")
async def api_hermes():
    return await hermes.hermes_stats()

@app.get("/api/proxmox")
async def api_proxmox():
    return await proxmox.proxmox_stats()

@app.get("/api/alerts")
async def api_alerts():
    return await alerts.get_alerts()


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=config.port, reload=True)