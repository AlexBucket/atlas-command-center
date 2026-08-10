"""Docker container monitoring via Unix socket."""

import httpx


DOCKER_SOCKET = "http+unix://%2Fvar%2Frun%2Fdocker.sock"


async def list_containers() -> list[dict]:
    """List all containers (running + stopped) with basic stats."""
    try:
        async with httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(
            uds="/var/run/docker.sock"
        ), timeout=5.0) as client:
            resp = await client.get("http://localhost/containers/json?all=true")
            containers = resp.json()
            
            result = []
            for c in containers:
                name = c.get("Names", [""])[0].lstrip("/")
                state = c.get("State", "unknown")
                status = c.get("Status", "")
                result.append({
                    "name": name,
                    "id": c.get("Id", "")[:12],
                    "state": state,
                    "status": status,
                    "image": c.get("Image", ""),
                    "created": c.get("Created", 0),
                    "ports": c.get("Ports", []),
                })
            
            return sorted(result, key=lambda x: x["name"])
    except Exception as e:
        return {"error": str(e)}


async def container_stats() -> dict:
    """Get aggregate Docker stats."""
    try:
        containers = await list_containers()
        if isinstance(containers, dict) and "error" in containers:
            return containers
        
        running = sum(1 for c in containers if c["state"] == "running")
        total = len(containers)
        return {
            "running": running,
            "total": total,
            "containers": containers,
            "errors": sum(1 for c in containers if c["state"] not in ("running", "exited")),
        }
    except Exception as e:
        return {"error": str(e)}