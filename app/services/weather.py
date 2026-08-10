"""Weather service — Open-Meteo for Portland VIC, with 5-minute cache."""

import httpx
import time
from datetime import datetime

# Cache state
_CACHED = None
_CACHED_AT = 0.0
_CACHE_TTL = 300  # 5 minutes

LAT = -38.35
LON = 141.60
FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
    "&timezone=Australia%2FSydney"
)

# WMO Weather code → description mapping
WMO_DESCRIPTIONS = {
    0: "Clear",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    56: "Freezing Light Drizzle",
    57: "Freezing Dense Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    66: "Freezing Light Rain",
    67: "Freezing Heavy Rain",
    71: "Slight Snow",
    73: "Moderate Snow",
    75: "Heavy Snow",
    77: "Snow Grains",
    80: "Slight Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    85: "Slight Snow Showers",
    86: "Heavy Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Slight Hail",
    99: "Thunderstorm with Heavy Hail",
}

WMO_ICONS = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️",
    56: "🌧️", 57: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    66: "🌧️", 67: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "🌨️", 77: "🌨️",
    80: "🌦️", 81: "🌧️", 82: "🌧️",
    85: "🌨️", 86: "🌨️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}


async def get_weather() -> dict:
    """Fetch current weather for Portland VIC with caching."""
    global _CACHED, _CACHED_AT

    now = time.time()
    if _CACHED and (now - _CACHED_AT) < _CACHE_TTL:
        return _CACHED

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(FORECAST_URL)
            if resp.status_code != 200:
                return {"error": f"Open-Meteo HTTP {resp.status_code}"}

            data = resp.json()
            current = data.get("current", {})

            weather_code = current.get("weather_code", 0)
            desc = WMO_DESCRIPTIONS.get(weather_code, "Unknown")
            icon = WMO_ICONS.get(weather_code, "❓")

            result = {
                "temp": current.get("temperature_2m"),
                "feels_like": current.get("apparent_temperature"),
                "humidity": current.get("relative_humidity_2m"),
                "precip": current.get("precipitation"),
                "wind_speed": current.get("wind_speed_10m"),
                "weather_code": weather_code,
                "weather_description": desc,
                "condition_icon": icon,
                "location": "Portland VIC",
                "fetched_at": datetime.utcnow().isoformat(),
            }

            _CACHED = result
            _CACHED_AT = now
            return result

    except Exception as e:
        if _CACHED:
            return _CACHED  # return stale data on fetch failure
        return {"error": str(e)}