# Project Atlas — Command Center v3

A self-hosted, widget-based command center dashboard for the Project Atlas homelab. Built with FastAPI + Alpine.js, styled in a Tokyo Night dark theme.

**This repository is a sanitized/readable version of the code running at home.** All API keys, tokens, and passwords have been replaced with placeholders. The live system runs at `http://192.168.1.107:3006` inside the house.

---

## What This Dashboard Shows

The Command Center aggregates data from every service in the homelab into one glanceable page. Each widget fetches its own data independently and auto-refreshes.

### The Five Pages

| Page | Route | Content |
|------|-------|---------|
| **Overview** | `/` | Shift banner, weather, alerts, system stats, household presence, NZBGet downloads, containers, media library summary, game servers |
| **Infrastructure** | `/infra` | Proxmox node stats (CPU/RAM/uptime), LXC/VM lists, Docker container inventory (running/stopped) |
| **Media** | `/media` | *Arr library counts (Sonarr/Radarr/Lidarr/Readarr/Prowlarr), NZBGet active downloads with progress |
| **Network** | `/network` | AdGuard Home stats — queries, blocked %, filter rules, response time, top queried & top blocked domains |
| **Games** | `/games` | AMP game server instances — status, player counts, module info |

### The Overview Widgets

```
┌─────────────────┬─────────────────────────┬─────────────────┐
│ Shift           │ Weather                 │ Alerts          │
│ Next alarm      │ Temp, humidity, wind    │ (if any)        │
├─────────────────┤                         ├─────────────────┤
│ System Stats    │                         │ Household       │
│ CPU/RAM/Disk    │                         │ Who's home      │
├─────────────────┼─────────────────────────┼─────────────────┤
│ NZBGet          │ Containers (full width) │ Media Library   │
│ Downloads       │ 24/24 running           │ Series/Movies   │
└─────────────────┴─────────────────────────┴─────────────────┘
```

- **Shift widget** — Calculates Alex's Alcoa 4-week rotating roster (Day 6:10am / Night 6:10pm / Off) from a hard-coded cycle, with next alarm time. No calendar API needed.
- **Weather** — Open-Meteo free API (no key), for Portland VIC. Cached 5 minutes.
- **Alerts** — Aggregates service health: stopped containers, disk >85%, NZBGet status, Proxmox reachability, Hermes uptime.
- **System** — CPU/RAM/Disk/Uptime from the host (psutil).
- **Household** — Home Assistant person states + room temperatures.
- **Downloads** — NZBGet download speed + active queue.
- **Containers** — All Docker containers with running/stopped dots.

### Shift Roster Logic

The shift system uses a fixed 4-week cycle starting **2026-06-29**:

| Week | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|------|-----|-----|-----|-----|-----|-----|-----|
| A | Off | Day | Day | Off | Night | Night | Night |
| B | Off | Off | Off | Day | Day | Off | Off |
| C | Night | Night | Off | Off | Off | Day | Day |
| D | Day | Off | Night | Night | Off | Off | Off |

Alarm times: Day shift 4:55am · consecutive Night 5:00pm · first Night 6:00pm · Off none.

---

## Architecture

```
Command Center (port 3006)
├── FastAPI backend (Python 3.11)
│   ├── /api/health           — service health + version
│   ├── /api/system           — CPU/RAM/Disk/Uptime
│   ├── /api/docker           — container inventory
│   ├── /api/homeassistant    — people, lights, temps
│   ├── /api/proxmox          — node stats, LXC/VM lists
│   ├── /api/adguard          — DNS stats + top domains
│   ├── /api/arr              — all *Arr library counts
│   ├── /api/amp              — game server instances
│   ├── /api/nzbget           — download status + queue
│   ├── /api/hermes           — agent status
│   ├── /api/weather          — Open-Meteo, 5-min cache
│   ├── /api/shift            — roster calculation
│   ├── /api/alerts           — aggregated health alerts
│   └── /api/overview         — everything in one call
└── Frontend (Alpine.js, no build step)
    ├── templates/*.html      — Jinja2 pages
    └── static/css/dashboard.css
```

Each widget in the frontend is a self-contained Alpine.js component (`Alpine.data('weatherWidget', ...)`) with:
- Loading skeleton while fetching
- Error state on failure
- Independent refresh interval

---

## Running It

```bash
# 1. Fill in your real credentials in app/config.py
# 2. Build & start
docker compose up -d --build

# 3. Open
http://localhost:3006
```

### Requirements

- Docker + Docker Compose v2
- The Docker socket is mounted read-only for container listing
- Services are discovered via HTTP — no agents needed except Home Assistant's REST API

### Config

All credentials live in `app/config.py`. Replace the `YOUR_*` placeholders:

| Config | Purpose |
|--------|---------|
| `ha_url` / `ha_token` | Home Assistant REST API |
| `proxmox_url` / `proxmox_token_id` / `proxmox_secret` | Proxmox VE API token |
| `adguard_url` / `adguard_user` / `adguard_pass` | AdGuard Home control API |
| `sonarr_key` / `radarr_key` / `lidarr_key` / `readarr_key` / `prowlarr_key` | *Arr API keys |
| `amp_url` / `amp_user` / `amp_pass` | CubeCoders AMP |
| `nzbget_url` / `nzbget_user` / `nzbget_pass` | NZBGet JSON-RPC |

---

## Troubleshooting

**Pages render but widgets show skeletons / no data**
- Open browser dev tools → Console. Look for `Alpine Expression Error`.
- Check each `/api/*` endpoint directly — they should return JSON with a `data` key.
- Confirm the widget's expected field names match the API response. A common cause is a field rename in the service module that the template doesn't know about.

**Alpine.js not loading**
- The project serves `static/js/alpine.min.js` locally (v3.14.8) — it does not depend on a CDN. If the sidebar renders but widgets don't, verify `/static/js/alpine.min.js` returns 200.

**Shift widget shows "Off Shift"**
- The roster is computed from `CYCLE_START` in `app/services/shift.py`. If today is outside the cycle (before 2026-06-29 or many years later), it still computes correctly by modulo of the 4-week cycle.

---

## Design Principles

- **Local-first** — no cloud dependency except Open-Meteo for weather (free, no key)
- **No build step** — Alpine.js from a local file, plain CSS, Jinja2 server-side
- **Widgets fail independently** — a down service shows an error in its widget, not a broken page
- **Glanceable** — shift and alerts at the top, detail pages below

---

## Project Atlas

This is one component of [Project Atlas](https://github.com/AlexBucket/atlas-config) — a self-hosted, automated smart home. The Command Center is the operational view; Home Assistant is the automation brain; the media stack (Sonarr/Radarr/Jellyfin/NZBGet) runs on a separate LXC.
