"""Hermes Agent integration — cron jobs, memory, sessions, config."""

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


HERMES_CONFIG_DIR = Path("/root/.hermes")
HERMES_SKILLS_DIR = HERMES_CONFIG_DIR / "skills"
HERMES_MEMORY_FILE = HERMES_CONFIG_DIR / "memory.json"
HERMES_USER_FILE = HERMES_CONFIG_DIR / "user.json"
HERMES_SESSIONS_DIR = Path("/root/.hermes/sessions")


async def hermes_status() -> dict:
    """Get Hermes agent status overview."""
    try:
        config_info = await _hermes_config_info()
        memory_info = await _hermes_memory_info()
        cron_info = await _hermes_cron_info()
        skills_info = await _hermes_skills_info()

        return {
            "config": config_info,
            "memory": memory_info,
            "cron": cron_info,
            "skills": skills_info,
        }
    except Exception as e:
        return {"error": str(e)}


async def _hermes_config_info() -> dict:
    info = {
        "active_model": "deepseek/deepseek-v4-flash",
        "provider": "openrouter",
        "installed": os.path.isdir("/usr/local/lib/hermes-agent"),
        "pid": None,
    }
    try:
        result = subprocess.run(
            ["pgrep", "-f", "hermes"],
            capture_output=True, text=True, timeout=3
        )
        if result.stdout.strip():
            info["pid"] = result.stdout.strip().split("\n")[0]
            info["running"] = True
        else:
            info["running"] = False
    except Exception:
        info["running"] = False
    return info


async def _hermes_memory_info() -> dict:
    """Read memory file (your personal notes)."""
    info = {
        "memory_count": 0,
        "user_profile_size": 0,
        "total_kb": 0,
    }
    try:
        mem_paths = [
            Path("/root/.hermes/memory.json"),
            Path("/root/.hermes/profile/memory.yaml"),
        ]
        for p in mem_paths:
            if p.exists():
                info["memory_count"] += 1
                info["total_kb"] += p.stat().st_size / 1024
        info["paths"] = [str(p) for p in mem_paths if p.exists()]
    except Exception:
        pass
    return info


async def _hermes_cron_info() -> dict:
    """Get cron jobs info."""
    jobs = []
    try:
        result = subprocess.run(
            ["hermes", "cron", "list", "--json"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            jobs = json.loads(result.stdout)
        elif result.returncode == 0:
            cron_dir = HERMES_CONFIG_DIR / "cron"
            if cron_dir.exists():
                jobs = [f.name for f in cron_dir.iterdir() if f.suffix in (".yaml", ".yml")]
    except Exception:
        pass

    return {
        "total_jobs": len(jobs) if isinstance(jobs, list) else 0,
        "jobs": jobs if isinstance(jobs, list) else [],
    }


async def _hermes_skills_info() -> dict:
    """List available skills."""
    skills = []
    if HERMES_SKILLS_DIR.exists():
        skills = [f.stem for f in HERMES_SKILLS_DIR.iterdir() if f.suffix == ".md"]
    return {
        "count": len(skills),
        "list": skills[:20],
    }


async def hermes_recent_sessions(limit: int = 5) -> list[dict]:
    """Get recent Hermes conversations."""
    sessions = []
    session_db = HERMES_CONFIG_DIR / "sessions" / "hermes.db"
    try:
        import sqlite3
        if session_db.exists():
            conn = sqlite3.connect(str(session_db))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                "SELECT id, title, created_at, profile FROM sessions ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            for row in cur.fetchall():
                sessions.append({
                    "id": row["id"],
                    "title": row["title"] or "Untitled",
                    "created_at": row["created_at"],
                    "profile": row.get("profile", "default"),
                })
            conn.close()
    except Exception:
        pass
    return sessions


async def hermes_run_command(command: str) -> dict:
    """Run a Hermes CLI command."""
    try:
        result = subprocess.run(
            ["hermes"] + command.split(),
            capture_output=True, text=True, timeout=15
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:500],
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": str(e)}


async def hermes_stats() -> dict:
    """Quick overview stats for the main dashboard."""
    status = await hermes_status()
    sessions = await hermes_recent_sessions(3)
    return {
        "running": status.get("config", {}).get("running", False),
        "cron_jobs": status.get("cron", {}).get("total_jobs", 0),
        "skills_count": status.get("skills", {}).get("count", 0),
        "recent_sessions": sessions,
        "last_session": sessions[0] if sessions else None,
    }