#!/usr/bin/env python3
"""
Cloudflare Tunnel Provisioner for acp-demo.stacklabsllc.com
Path: /home/james/stacklabs/scripts/provision_acp_tunnel.py
Author: James Carroll (Pilot), Lead Systems Architect
"""
import os
import re
import subprocess
from pathlib import Path

HOSTNAME = "acp-demo.stacklabsllc.com"
ENV_PATH = Path("/home/james/stacklabs/.env")
CONFIG_PATH = Path("/etc/cloudflared/config.yml")
SRV_PATH = Path("/home/james/stacklabs/scripts/faas_server.py")


def get_faas_port() -> int:
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith("FAAS_PORT="):
                try:
                    return int(line.split("=", 1)[1].strip())
                except ValueError:
                    pass
    return 3033


def ensure_faas_host_middleware() -> None:
    if not SRV_PATH.exists():
        print(f"[WARN] {SRV_PATH} not found; skipping middleware injection")
        return

    txt = SRV_PATH.read_text(encoding="utf-8")
    if "acp_subdomain_root_router" in txt:
        print("[OK] Host routing middleware already present in faas_server.py")
        return

    middleware_code = '''
    @app.middleware("http")
    async def acp_subdomain_root_router(request: Request, call_next):
        host = request.headers.get("host", "").lower()
        if "acp-demo.stacklabsllc.com" in host and request.url.path == "/":
            from scripts.blueprints.acp_oracle_api import render_acp_live_demo
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=render_acp_live_demo(), status_code=200)
        return await call_next(request)
'''

    if "app.include_router(acp_oracle_bp)" in txt:
        target = "app.include_router(acp_oracle_bp)"
        txt = txt.replace(target, target + "\n" + middleware_code, 1)
        SRV_PATH.write_text(txt, encoding="utf-8")
        print("[UPDATED] Injected acp_subdomain_root_router middleware into faas_server.py")
    else:
        print("[WARN] Could not find app.include_router(acp_oracle_bp) in faas_server.py")


def update_cloudflared_config() -> str:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"{CONFIG_PATH} does not exist")

    cfg_text = CONFIG_PATH.read_text(encoding="utf-8")
    tunnel_match = re.search(r"^\s*tunnel:\s*([a-zA-Z0-9\-]+)", cfg_text, re.MULTILINE)
    tunnel_id = tunnel_match.group(1).strip() if tunnel_match else "adf44e1c-2453-46da-82f8-906efd8d96a9"
    port = get_faas_port()

    if HOSTNAME in cfg_text:
        print(f"[OK] {HOSTNAME} is already present in {CONFIG_PATH}")
        return tunnel_id

    new_rule = f"  - hostname: {HOSTNAME}\n    service: http://localhost:{port}\n"

    if "  - service: http_status:404" in cfg_text:
        cfg_text = cfg_text.replace(
            "  - service: http_status:404",
            new_rule + "  - service: http_status:404"
        )
    elif "- service: http_status:404" in cfg_text:
        cfg_text = cfg_text.replace(
            "- service: http_status:404",
            new_rule + "- service: http_status:404"
        )
    else:
        cfg_text += "\n" + new_rule

    tmp_path = Path("/tmp/cloudflared_config_updated.yml")
    tmp_path.write_text(cfg_text, encoding="utf-8")
    subprocess.run(["sudo", "cp", str(tmp_path), str(CONFIG_PATH)], check=True)
    subprocess.run(["sudo", "chmod", "644", str(CONFIG_PATH)], check=True)
    print(f"[UPDATED] Injected {HOSTNAME} -> http://localhost:{port} into {CONFIG_PATH}")
    return tunnel_id


def register_dns_route(tunnel_id: str) -> None:
    print(f"[DNS] Registering CNAME route for {HOSTNAME} on tunnel {tunnel_id}...")
    res = subprocess.run(
        ["cloudflared", "tunnel", "route", "dns", "--overwrite-dns", tunnel_id, HOSTNAME],
        capture_output=True,
        text=True
    )
    print(f"[DNS OUTPUT] {res.stdout.strip()} {res.stderr.strip()}")


if __name__ == "__main__":
    ensure_faas_host_middleware()
    tid = update_cloudflared_config()
    register_dns_route(tid)
