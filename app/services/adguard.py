"""AdGuard Home stats."""

import httpx
from config import config


def _parse_domain_list(domains: list) -> list[dict]:
    """AdGuard returns [{domain: count}, ...] — convert to [{"domain": ..., "count": N}, ...]."""
    result = []
    for d in domains[:10]:
        for domain, count in d.items():
            result.append({"domain": domain, "count": count})
    return result


async def adguard_stats() -> dict:
    try:
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            # Stats
            resp = await client.get(
                f"{config.adguard_url}/control/stats",
                auth=(config.adguard_user, config.adguard_pass),
            )
            if resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code}"}
            data = resp.json()

            # Filtering status
            filt = await client.get(
                f"{config.adguard_url}/control/filtering/status",
                auth=(config.adguard_user, config.adguard_pass),
            )
            filter_data = filt.json() if filt.status_code == 200 else {}

            # Count total rules from all enabled filters
            filter_rules = sum(
                f.get("rules_count", 0)
                for f in filter_data.get("filters", [])
                if f.get("enabled", False)
            )

            return {
                "total_queries": data.get("num_dns_queries", 0),
                "blocked": data.get("num_blocked_filtering", 0),
                "blocked_percent": round(
                    (data.get("num_blocked_filtering", 0) / max(data.get("num_dns_queries", 1), 1)) * 100, 1
                ),
                "avg_processing_time": round(data.get("avg_processing_time", 0), 3),
                "filter_rules_count": filter_rules,
                "filters_enabled": filter_data.get("enabled", False),
                "protection_enabled": filter_data.get("enabled", False),
                "top_queried": _parse_domain_list(data.get("top_queried_domains", [])),
                "top_blocked": _parse_domain_list(data.get("top_blocked_domains", [])),
            }
    except Exception as e:
        return {"error": str(e)}


async def adguard_recent() -> list[dict]:
    """Get recent DNS queries."""
    try:
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            resp = await client.get(
                f"{config.adguard_url}/control/querylog?limit=15",
                auth=(config.adguard_user, config.adguard_pass),
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            entries = data.get("data", []) or []
            return [
                {
                    "domain": e.get("question", {}).get("name", "").rstrip("."),
                    "client": e.get("client", ""),
                    "blocked": e.get("reason", "") == "FilteredBlackList",
                    "type": e.get("question", {}).get("type", ""),
                    "time": e.get("time", ""),
                }
                for e in entries[:15]
            ]
    except Exception:
        return []