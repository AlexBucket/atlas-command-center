"""Project Atlas Command Center v3 — Configuration."""

from dataclasses import dataclass


@dataclass
class Config:
    port: int = 3006

    # Proxmox
    proxmox_url: str = "https://192.168.1.28:8006"
    proxmox_token: str = "YOUR_PROXMOX_TOKEN_ID"
    proxmox_secret: str = "YOUR_PROXMOX_SECRET"

    # Home Assistant
    ha_url: str = "http://192.168.1.131:8123"
    ha_token: str = "YOUR_HA_LONG_LIVED_TOKEN"

    # AdGuard
    adguard_url: str = "http://192.168.1.235"
    adguard_user: str = "YOUR_ADGUARD_USER"
    adguard_pass: str = "YOUR_ADGUARD_PASS"

    # Docker
    docker_socket: str = "/var/run/docker.sock"

    # Media stack API keys
    sonarr_url: str = "http://192.168.1.107:8989"
    sonarr_key: str = "YOUR_SONARR_API_KEY"
    radarr_url: str = "http://192.168.1.107:7878"
    radarr_key: str = "YOUR_RADARR_API_KEY"
    lidarr_url: str = "http://192.168.1.107:8686"
    lidarr_key: str = "YOUR_LIDARR_API_KEY"
    readarr_url: str = "http://192.168.1.107:8787"
    readarr_key: str = "YOUR_READARR_API_KEY"
    prowlarr_url: str = "http://192.168.1.107:9696"
    prowlarr_key: str = "YOUR_PROWLARR_API_KEY"

    # AMP
    amp_url: str = "http://192.168.1.102:8080"
    amp_user: str = "YOUR_AMP_USER"
    amp_pass: str = "YOUR_AMP_PASS"

    # NZBGet
    nzbget_url: str = "http://192.168.1.107:6789"
    nzbget_user: str = "YOUR_NZBGET_USER"
    nzbget_pass: str = "YOUR_NZBGET_PASS"


config = Config()