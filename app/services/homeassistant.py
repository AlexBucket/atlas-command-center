"""Home Assistant API integration."""

import httpx
from config import config


async def ha_stats() -> dict:
    if not config.ha_token:
        return {
            "configured": False,
            "message": "Home Assistant API token not configured. Add to config.py or set env vars.",
        }

    try:
        headers = {
            "Authorization": f"Bearer {config.ha_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            # Get states
            resp = await client.get(
                f"{config.ha_url}/api/states",
                headers=headers,
            )
            if resp.status_code != 200:
                return {"error": f"HA HTTP {resp.status_code}"}
            states = resp.json()

            # Get config info
            config_resp = await client.get(
                f"{config.ha_url}/api/config",
                headers=headers,
            )
            ha_config = config_resp.json() if config_resp.status_code == 200 else {}

            # Count entities by category
            lights_on = sum(1 for s in states if s.get("entity_id", "").startswith("light.") and s.get("state") == "on")
            lights_total = sum(1 for s in states if s.get("entity_id", "").startswith("light."))
            switches_on = sum(1 for s in states if s.get("entity_id", "").startswith("switch.") and s.get("state") == "on")
            people_home = sum(1 for s in states if s.get("entity_id", "").startswith("person.") and s.get("state") == "home")
            sensors = [s for s in states if s.get("entity_id", "").startswith("sensor.")]

            # Get temperatures
            temps = [
                {
                    "name": s.get("attributes", {}).get("friendly_name", s.get("entity_id", "")),
                    "state": s.get("state"),
                    "unit": s.get("attributes", {}).get("unit_of_measurement", ""),
                }
                for s in sensors
                if s.get("attributes", {}).get("device_class") == "temperature"
            ][:6]

            return {
                "configured": True,
                "version": ha_config.get("version", ""),
                "location": ha_config.get("location_name", ""),
                "lights_on": lights_on,
                "lights_total": lights_total,
                "switches_on": switches_on,
                "people_home": people_home,
                "persons": [
                    {
                        "name": s.get("attributes", {}).get("friendly_name", s.get("entity_id", "")),
                        "state": s.get("state"),
                    }
                    for s in states
                    if s.get("entity_id", "").startswith("person.")
                ],
                "temperatures": temps,
                "entity_count": len(states),
            }
    except Exception as e:
        return {"error": str(e)}


async def ha_entities() -> list[dict]:
    """Get all HA entities (for the infrastructure page)."""
    if not config.ha_token:
        return []
    try:
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            resp = await client.get(
                f"{config.ha_url}/api/states",
                headers={"Authorization": f"Bearer {config.ha_token}"},
            )
            if resp.status_code != 200:
                return []
            return resp.json()
    except Exception:
        return []