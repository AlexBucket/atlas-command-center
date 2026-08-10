"""Sonarr, Radarr, Lidarr, Readarr, Prowlarr status queries."""

import httpx
from config import config


async def _get_json(url: str, api_key: str, path: str, api_version: str = "v3") -> dict | list:
    try:
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            resp = await client.get(
                f"{url}/api/{api_version}/{path}",
                headers={"X-Api-Key": api_key},
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}


async def sonarr_stats() -> dict:
    series = await _get_json(config.sonarr_url, config.sonarr_key, "series")
    queue = await _get_json(config.sonarr_url, config.sonarr_key, "queue")
    wanted = await _get_json(config.sonarr_url, config.sonarr_key, "wanted/missing")

    if isinstance(series, dict) and "error" in series:
        return {"error": series["error"]}

    return {
        "series_count": len(series) if isinstance(series, list) else 0,
        "wanted": len(wanted.get("records", [])) if isinstance(wanted, dict) else 0,
        "queue_count": len(queue.get("records", [])) if isinstance(queue, dict) else 0,
        "recent_series": [
            {
                "title": s.get("title", ""),
                "year": s.get("year", ""),
                "status": s.get("status", ""),
                "seasons": len(s.get("seasons", [])),
                "monitored": s.get("monitored", False),
            }
            for s in (series if isinstance(series, list) else [])[-6:]
        ][::-1],
    }


async def radarr_stats() -> dict:
    movies = await _get_json(config.radarr_url, config.radarr_key, "movie")
    queue = await _get_json(config.radarr_url, config.radarr_key, "queue")
    wanted = await _get_json(config.radarr_url, config.radarr_key, "wanted/missing")

    if isinstance(movies, dict) and "error" in movies:
        return {"error": movies["error"]}

    return {
        "movie_count": len(movies) if isinstance(movies, list) else 0,
        "missing": len(wanted.get("records", [])) if isinstance(wanted, dict) else 0,
        "queue_count": len(queue.get("records", [])) if isinstance(queue, dict) else 0,
        "recent_movies": [
            {
                "title": m.get("title", ""),
                "year": m.get("year", ""),
                "status": m.get("status", ""),
                "has_file": m.get("hasFile", False),
                "monitored": m.get("monitored", False),
            }
            for m in (movies if isinstance(movies, list) else [])[-6:]
        ][::-1],
    }


async def lidarr_stats() -> dict:
    artists = await _get_json(config.lidarr_url, config.lidarr_key, "artist", api_version="v1")
    queue = await _get_json(config.lidarr_url, config.lidarr_key, "queue", api_version="v1")

    if isinstance(artists, dict) and "error" in artists:
        return {"error": artists["error"]}

    return {
        "artist_count": len(artists) if isinstance(artists, list) else 0,
        "queue_count": len(queue.get("records", [])) if isinstance(queue, dict) else 0,
    }


async def readarr_stats() -> dict:
    books = await _get_json(config.readarr_url, config.readarr_key or "", "book", api_version="v1")
    queue = await _get_json(config.readarr_url, config.readarr_key or "", "queue", api_version="v1")

    if isinstance(books, dict) and "error" in books:
        return {"error": books["error"]}

    return {
        "book_count": len(books) if isinstance(books, list) else 0,
        "queue_count": len(queue.get("records", [])) if isinstance(queue, dict) else 0,
    }


async def prowlarr_stats() -> dict:
    indexers = await _get_json(config.prowlarr_url, config.prowlarr_key, "indexer", api_version="v1")

    if isinstance(indexers, dict) and "error" in indexers:
        return {"error": indexers["error"]}

    return {
        "indexer_count": len(indexers) if isinstance(indexers, list) else 0,
    }


async def all_arr_stats() -> dict:
    """Fetch all *arr stats concurrently."""
    import asyncio
    results = await asyncio.gather(
        sonarr_stats(),
        radarr_stats(),
        lidarr_stats(),
        readarr_stats(),
        prowlarr_stats(),
        return_exceptions=True,
    )
    return {
        "sonarr": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "radarr": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
        "lidarr": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
        "readarr": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
        "prowlarr": results[4] if not isinstance(results[4], Exception) else {"error": str(results[4])},
    }