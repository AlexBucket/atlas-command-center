"""Project Atlas Command Center v3 — FastAPI backend."""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from jinja2 import Environment, FileSystemLoader, select_autoescape
from config import config
from services import system, docker, adguard, proxmox, homeassistant, hermes, amp, mediaarr, nzbget, weather, shift, alerts

app = FastAPI(title="Project Atlas Command Center", version="3.0.0")

# CORS — allow all origins (accessed from various devices on LAN)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

jinja = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


def render(name: str, **kw) -> HTMLResponse:
    t = jinja.get_template(name)
    return HTMLResponse(t.render(**kw))


# ── API Routes ───────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}


@app.get("/api/system")
async def api_system():
    return {"data": system.get_system_stats()}


@app.get("/api/docker")
async def api_docker():
    return {"data": await docker.container_stats()}


@app.get("/api/homeassistant")
async def api_ha():
    return {"data": await homeassistant.ha_stats()}


@app.get("/api/proxmox")
async def api_proxmox():
    return {"data": await proxmox.proxmox_stats()}


@app.get("/api/adguard")
async def api_adguard():
    return {"data": await adguard.adguard_stats()}


@app.get("/api/adguard/recent")
async def api_adguard_recent():
    return {"data": await adguard.adguard_recent()}


@app.get("/api/arr")
async def api_arr():
    return {"data": await mediaarr.all_arr_stats()}


@app.get("/api/amp")
async def api_amp():
    return {"data": await amp.get_status()}


@app.get("/api/nzbget")
async def api_nzbget():
    return {"data": await nzbget.nzbget_stats()}


@app.get("/api/hermes")
async def api_hermes():
    return {"data": await hermes.hermes_stats()}


@app.get("/api/weather")
async def api_weather():
    return {"data": await weather.get_weather()}


@app.get("/api/shift")
async def api_shift():
    return {"data": shift.get_today_shift()}


@app.get("/api/alerts")
async def api_alerts():
    return {"data": await alerts.get_alerts()}


@app.get("/api/overview")
async def overview():
    """Aggregate all services into one response."""
    import asyncio

    sys_data = system.get_system_stats()
    dkr_data = await docker.container_stats()
    ha_data = await homeassistant.ha_stats()
    px_data = await proxmox.proxmox_stats()
    ag_data = await adguard.adguard_stats()
    arr_data = await mediaarr.all_arr_stats()
    am_data = await amp.get_status()
    hm_data = await hermes.hermes_stats()
    nz_data = await nzbget.nzbget_stats()
    wx_data = await weather.get_weather()
    sh_data = shift.get_today_shift()
    al_data = await alerts.get_alerts()

    return {
        "data": {
            "system": sys_data,
            "docker": dkr_data,
            "ha": ha_data,
            "proxmox": px_data,
            "adguard": ag_data,
            "media": arr_data,
            "amp": am_data,
            "hermes": hm_data,
            "nzbget": nz_data,
            "weather": wx_data,
            "shift": sh_data,
            "alerts": al_data,
        }
    }


# ── Page Routes ──────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return render("index.html", page="overview")


@app.get("/infra", response_class=HTMLResponse)
async def infra():
    return render("infra.html", page="infra")


@app.get("/media", response_class=HTMLResponse)
async def media():
    return render("media.html", page="media")


@app.get("/network", response_class=HTMLResponse)
async def network():
    return render("network.html", page="network")


@app.get("/games", response_class=HTMLResponse)
async def games():
    return render("games.html", page="games")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=config.port, reload=True)