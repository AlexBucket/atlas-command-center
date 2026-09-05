"""
Atlas vNext — Router.

All routes use /vnext prefix. Serves pages and APIs without touching original routes.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.vnext.services import get_all_stats, get_overall_health


vnext_router = APIRouter(prefix="/vnext")

# Dedicated Jinja2 environment for vNext templates
_templates_dir = Path(__file__).parent / "templates"
_jinja = Environment(
    loader=FileSystemLoader(str(_templates_dir)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _render(name: str, **kw) -> HTMLResponse:
    return HTMLResponse(_jinja.get_template(name).render(**kw))


# ── Page routes ─────────────────────────────────────────────

@vnext_router.get("/", response_class=HTMLResponse)
async def vnext_index():
    return _render("vnext_index.html", page="overview")

@vnext_router.get("/infra", response_class=HTMLResponse)
async def vnext_infra():
    return _render("vnext_infra.html", page="infra")

@vnext_router.get("/briefings", response_class=HTMLResponse)
async def vnext_briefings():
    return _render("vnext_briefings.html", page="briefings")


# ── API routes ──────────────────────────────────────────────

@vnext_router.get("/api/overview")
async def vnext_overview():
    """Aggregate all service stats with consistent shapes."""
    results = await get_all_stats()
    health = get_overall_health(results)
    return {
        "data": results,
        "health": health,
    }


@vnext_router.get("/api/health")
async def vnext_health():
    """Quick health check — light, no service calls."""
    return {"status": "ok", "version": "3.0.0-vnext", "routes": 5}


@vnext_router.get("/api/system")
async def vnext_system():
    results = await get_all_stats()
    return {"data": results.get("system", {"status": "error", "error": "not fetched"})}


@vnext_router.get("/api/docker")
async def vnext_docker():
    results = await get_all_stats()
    return {"data": results.get("docker", {"status": "error", "error": "not fetched"})}


@vnext_router.get("/api/shift")
async def vnext_shift():
    results = await get_all_stats()
    return {"data": results.get("shift", {"status": "error", "error": "not fetched"})}