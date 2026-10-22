#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Discord Stream Tailer Systemd Supervisor & Binding Manager
Path: /home/james/stacklabs/scripts/discord_tailer_supervisor.py
Author: James Carroll (Pilot) & Lead Systems Architect, StackLabs LLC
Target Host: Clio dedicated Linux host (100.96.77.20)
Governing Standards: Invariant 0, 1.9, 15, 32 (Law of "I"), 35 (.venv), 38 (Telemetry Isolation), 50 (Drop-In Code), Argon Laws 1-9
"""

import argparse
import asyncio
import datetime
import hashlib
import json
import os
import signal
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path("/home/james/stacklabs")
sys.path.insert(0, str(REPO_ROOT))

from scripts.discord_stream_tailer import (
    DB_PATH,
    ChannelEntityBinding,
    DiscordGatewayStreamTailer,
    atomic_write_json,
    load_dotenv_file,
    register_discord_stream_binding,
)

ENV_PATH = REPO_ROOT / ".env"
CONFIG_PATH = REPO_ROOT / "config" / "discord_channel_bindings.json"
HEARTBEAT_PATH = Path("/dev/shm/vfs/telemetry/discord_supervisor_heartbeat.json")
MAX_TTL_SECONDS = 14400


def compute_config_sha256(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_bindings_config(config_path: Path = CONFIG_PATH) -> Dict[str, Any]:
    if not config_path.exists():
        default_cfg: Dict[str, Any] = {
            "schema_version": "1.0.0",
            "updated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "window_seconds": 60.0,
            "sigma_threshold": 4.5,
            "ttl_seconds": MAX_TTL_SECONDS,
            "bindings": [],
        }
        atomic_write_json(config_path, default_cfg)
        return default_cfg
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Failed to parse {config_path}: {exc}") from exc


def resolve_active_bindings(
    cfg: Dict[str, Any], now_epoch: Optional[float] = None, enforce_ttl: bool = True
) -> Dict[str, ChannelEntityBinding]:
    now_ts = float(now_epoch if now_epoch is not None else time.time())
    active: Dict[str, ChannelEntityBinding] = {}
    for entry in cfg.get("bindings", []):
        if not entry.get("enabled", True):
            continue
        channel_id = str(entry.get("channel_id") or "").strip()
        game_id = str(entry.get("game_id") or "").strip()
        if not channel_id or not game_id:
            continue
        ttl_s = min(int(entry.get("ttl_seconds", MAX_TTL_SECONDS)), MAX_TTL_SECONDS)
        bound_at = float(entry.get("bound_at_epoch") or now_ts)
        if enforce_ttl and (now_ts - bound_at) > ttl_s:
            continue
        stream_id = str(entry.get("stream_id") or f"discord_{channel_id}").strip()
        active[channel_id] = ChannelEntityBinding(
            channel_id=channel_id,
            game_id=game_id,
            stream_id=stream_id,
            sport=str(entry.get("sport") or "cfb"),
            home_team=str(entry.get("home_team") or "HOME"),
            away_team=str(entry.get("away_team") or "AWAY"),
            stream_title=str(
                entry.get("stream_title") or f"Discord #{channel_id} ({game_id})"
            ),
        )
    return active


def bind_channel_in_config(
    config_path: Path,
    channel_id: str,
    game_id: str,
    stream_id: Optional[str] = None,
    sport: str = "cfb",
    home_team: str = "HOME",
    away_team: str = "AWAY",
    stream_title: Optional[str] = None,
    ttl_seconds: int = MAX_TTL_SECONDS,
) -> Dict[str, Any]:
    cfg = load_bindings_config(config_path)
    clamped_ttl = min(max(60, int(ttl_seconds)), MAX_TTL_SECONDS)
    eff_stream_id = (stream_id or f"discord_{channel_id}").strip()
    eff_title = (stream_title or f"Discord #{channel_id} ({game_id})").strip()
    now_epoch = round(time.time(), 3)

    bindings_list: List[Dict[str, Any]] = list(cfg.get("bindings", []))
    updated = False
    new_entry = {
        "channel_id": str(channel_id).strip(),
        "game_id": str(game_id).strip(),
        "stream_id": eff_stream_id,
        "sport": str(sport).strip().lower(),
        "home_team": str(home_team).strip().upper(),
        "away_team": str(away_team).strip().upper(),
        "stream_title": eff_title,
        "enabled": True,
        "bound_at_epoch": now_epoch,
        "ttl_seconds": clamped_ttl,
    }
    for idx, item in enumerate(bindings_list):
        if str(item.get("channel_id")) == str(channel_id).strip():
            bindings_list[idx] = new_entry
            updated = True
            break
    if not updated:
        bindings_list.append(new_entry)

    cfg["bindings"] = bindings_list
    cfg["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cfg["content_sha256"] = compute_config_sha256(
        {"bindings": bindings_list, "ttl_seconds": cfg.get("ttl_seconds", MAX_TTL_SECONDS)}
    )
    atomic_write_json(config_path, cfg)

    binding_obj = ChannelEntityBinding(
        channel_id=new_entry["channel_id"],
        game_id=new_entry["game_id"],
        stream_id=new_entry["stream_id"],
        sport=new_entry["sport"],
        home_team=new_entry["home_team"],
        away_team=new_entry["away_team"],
        stream_title=new_entry["stream_title"],
    )
    register_discord_stream_binding(DB_PATH, binding_obj, is_live=1)
    return new_entry


def unbind_channel_in_config(config_path: Path, channel_id: str) -> bool:
    cfg = load_bindings_config(config_path)
    bindings_list: List[Dict[str, Any]] = list(cfg.get("bindings", []))
    matched_binding: Optional[ChannelEntityBinding] = None
    for item in bindings_list:
        if str(item.get("channel_id")) == str(channel_id).strip():
            item["enabled"] = False
            matched_binding = ChannelEntityBinding(
                channel_id=str(item["channel_id"]),
                game_id=str(item.get("game_id") or "UNMAPPED"),
                stream_id=str(item.get("stream_id") or f"discord_{channel_id}"),
                sport=str(item.get("sport") or "cfb"),
                home_team=str(item.get("home_team") or "HOME"),
                away_team=str(item.get("away_team") or "AWAY"),
                stream_title=str(item.get("stream_title") or "Unbound Discord Channel"),
            )
    if matched_binding is None:
        return False

    cfg["bindings"] = bindings_list
    cfg["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cfg["content_sha256"] = compute_config_sha256(
        {"bindings": bindings_list, "ttl_seconds": cfg.get("ttl_seconds", MAX_TTL_SECONDS)}
    )
    atomic_write_json(config_path, cfg)
    register_discord_stream_binding(DB_PATH, matched_binding, is_live=0)
    return True


def write_supervisor_heartbeat(
    state: str,
    auth_mode: str,
    active_bindings: Dict[str, ChannelEntityBinding],
    ttl_seconds: int,
    started_at_epoch: float,
) -> Dict[str, Any]:
    now_epoch = time.time()
    payload = {
        "service": "stacklabs-discord-tailer.service",
        "state": state,
        "auth_mode": auth_mode,
        "pid": os.getpid(),
        "ttl_seconds": min(int(ttl_seconds), MAX_TTL_SECONDS),
        "uptime_seconds": round(max(0.0, now_epoch - started_at_epoch), 2),
        "active_channel_count": len(active_bindings),
        "active_channels": [
            {
                "channel_id": b.channel_id,
                "game_id": b.game_id,
                "stream_id": b.stream_id,
                "sport": b.sport,
                "matchup": f"{b.away_team} @ {b.home_team}",
            }
            for b in active_bindings.values()
        ],
        "updated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "epoch_time": round(now_epoch, 3),
    }
    atomic_write_json(HEARTBEAT_PATH, payload)
    return payload


async def run_supervised_daemon(
    config_path: Path,
    db_path: Path,
    dry_run: bool = False,
) -> Dict[str, Any]:
    started_epoch = time.time()
    cfg = load_bindings_config(config_path)
    window_seconds = float(cfg.get("window_seconds", 60.0))
    sigma_threshold = float(cfg.get("sigma_threshold", 4.5))
    ttl_seconds = min(int(cfg.get("ttl_seconds", MAX_TTL_SECONDS)), MAX_TTL_SECONDS)

    # Refresh bound_at_epoch on service boot if bindings are enabled in static config
    active_bindings = resolve_active_bindings(cfg, now_epoch=started_epoch, enforce_ttl=False)
    bot_token = (os.getenv("DISCORD_BOT_TOKEN") or "").strip() or None
    user_token = (os.getenv("DISCORD_USER_TOKEN") or "").strip() or None
    auth_mode = "BOT" if bot_token else ("USER" if user_token else "STANDBY_NO_TOKEN")

    if dry_run:
        hb = write_supervisor_heartbeat(
            state="DRY_RUN_READY",
            auth_mode=auth_mode,
            active_bindings=active_bindings,
            ttl_seconds=ttl_seconds,
            started_at_epoch=started_epoch,
        )
        tailer = DiscordGatewayStreamTailer(
            bindings=active_bindings,
            db_path=db_path,
            bot_token=bot_token,
            user_token=user_token,
            window_seconds=window_seconds,
            sigma_threshold=sigma_threshold,
            ttl_seconds=ttl_seconds,
            dry_run=True,
        )
        diag = tailer.run_dry_run_diagnostic()
        return {
            "supervisor_status": "DRY_RUN_VERIFIED",
            "heartbeat": hb,
            "tailer_diagnostic": diag,
        }

    # If no token is present in .env yet, maintain clean standby loop so systemd does not crash-loop
    if not bot_token and not user_token:
        print(
            "[DISCORD-SUPERVISOR] No DISCORD_BOT_TOKEN or DISCORD_USER_TOKEN found in .env. "
            "Entering clean standby heartbeat loop (poll interval: 30s, TTL: 14400s).",
            flush=True,
        )
        stop_evt = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_evt.set)
            except NotImplementedError:
                pass
        while not stop_evt.is_set() and (time.time() - started_epoch) < ttl_seconds:
            write_supervisor_heartbeat(
                state="STANDBY_AWAITING_TOKEN",
                auth_mode="STANDBY_NO_TOKEN",
                active_bindings=active_bindings,
                ttl_seconds=ttl_seconds,
                started_at_epoch=started_epoch,
            )
            # Re-read .env in case operator hot-adds DISCORD_BOT_TOKEN or DISCORD_USER_TOKEN
            load_dotenv_file(ENV_PATH)
            bot_token = (os.getenv("DISCORD_BOT_TOKEN") or "").strip() or None
            user_token = (os.getenv("DISCORD_USER_TOKEN") or "").strip() or None
            if bot_token or user_token:
                auth_mode = "BOT" if bot_token else "USER"
                print(
                    f"[DISCORD-SUPERVISOR] Detected {auth_mode} token in .env! Transitioning to ACTIVE_GATEWAY.",
                    flush=True,
                )
                break
            try:
                await asyncio.wait_for(stop_evt.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                pass

        if not bot_token and not user_token:
            return {"supervisor_status": "STANDBY_EXITED_CLEANLY"}

    write_supervisor_heartbeat(
        state="ACTIVE_GATEWAY",
        auth_mode=auth_mode,
        active_bindings=active_bindings,
        ttl_seconds=ttl_seconds,
        started_at_epoch=started_epoch,
    )

    tailer = DiscordGatewayStreamTailer(
        bindings=active_bindings,
        db_path=db_path,
        bot_token=bot_token,
        user_token=user_token,
        window_seconds=window_seconds,
        sigma_threshold=sigma_threshold,
        ttl_seconds=ttl_seconds,
        dry_run=False,
    )

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, tailer._stop_event.set)
        except NotImplementedError:
            pass

    async def _periodic_heartbeat() -> None:
        while not tailer._stop_event.is_set():
            write_supervisor_heartbeat(
                state="ACTIVE_GATEWAY",
                auth_mode=auth_mode,
                active_bindings=active_bindings,
                ttl_seconds=ttl_seconds,
                started_at_epoch=started_epoch,
            )
            await asyncio.sleep(15.0)

    hb_task = asyncio.create_task(_periodic_heartbeat())
    try:
        await tailer.run_gateway_forever()
    finally:
        hb_task.cancel()
        write_supervisor_heartbeat(
            state="STOPPED",
            auth_mode=auth_mode,
            active_bindings=active_bindings,
            ttl_seconds=ttl_seconds,
            started_at_epoch=started_epoch,
        )
    return {"supervisor_status": "COMPLETED_TTL_CYCLE"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="StackLabs Discord Stream Tailer Systemd Supervisor & Channel Binding CLI"
    )
    parser.add_argument(
        "--config",
        default=str(CONFIG_PATH),
        help="Path to discord_channel_bindings.json",
    )
    parser.add_argument(
        "--db-path",
        default=str(DB_PATH),
        help="Path to morning_wiretap.db",
    )
    parser.add_argument(
        "--bind-channel",
        dest="bind_channel",
        help="Atomically bind a Discord channel_id to a game_id in config and SQLite WAL",
    )
    parser.add_argument(
        "--game-id",
        dest="game_id",
        help="Target game_id / channel_key for --bind-channel",
    )
    parser.add_argument(
        "--stream-id",
        dest="stream_id",
        default=None,
        help="Optional stream_id for --bind-channel",
    )
    parser.add_argument("--sport", default="cfb", help="Sport code (cfb, nfl, mlb)")
    parser.add_argument("--home", default="HOME", help="Home team abbreviation")
    parser.add_argument("--away", default="AWAY", help="Away team abbreviation")
    parser.add_argument("--title", default=None, help="Stream title")
    parser.add_argument(
        "--ttl-seconds",
        type=int,
        default=MAX_TTL_SECONDS,
        help="Hard TTL in seconds (max 14400)",
    )
    parser.add_argument(
        "--unbind-channel",
        dest="unbind_channel",
        help="Disable a Discord channel_id binding and mark is_live=0 in watch_party_streams",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print current supervisor bindings and VFS heartbeat JSON",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run supervisor dry-run verification without mutating SQLite WAL",
    )
    return parser


def main() -> None:
    load_dotenv_file(ENV_PATH)
    parser = build_parser()
    args = parser.parse_args()
    cfg_path = Path(args.config)

    if args.bind_channel:
        if not args.game_id:
            parser.error("--bind-channel requires --game-id <game_id>.")
        entry = bind_channel_in_config(
            config_path=cfg_path,
            channel_id=args.bind_channel,
            game_id=args.game_id,
            stream_id=args.stream_id,
            sport=args.sport,
            home_team=args.home,
            away_team=args.away,
            stream_title=args.title,
            ttl_seconds=args.ttl_seconds,
        )
        print(json.dumps({"status": "CHANNEL_BOUND", "binding": entry}, indent=2))
        return

    if args.unbind_channel:
        ok = unbind_channel_in_config(cfg_path, args.unbind_channel)
        print(
            json.dumps(
                {
                    "status": "CHANNEL_UNBOUND" if ok else "NOT_FOUND",
                    "channel_id": args.unbind_channel,
                },
                indent=2,
            )
        )
        return

    if args.status:
        cfg = load_bindings_config(cfg_path)
        active = resolve_active_bindings(cfg, enforce_ttl=False)
        hb = (
            json.loads(HEARTBEAT_PATH.read_text(encoding="utf-8"))
            if HEARTBEAT_PATH.exists()
            else {"state": "NO_HEARTBEAT_FILE"}
        )
        print(
            json.dumps(
                {
                    "config_path": str(cfg_path),
                    "active_bindings_count": len(active),
                    "active_bindings": [
                        {
                            "channel_id": b.channel_id,
                            "game_id": b.game_id,
                            "stream_id": b.stream_id,
                            "sport": b.sport,
                        }
                        for b in active.values()
                    ],
                    "heartbeat": hb,
                },
                indent=2,
            )
        )
        return

    res = asyncio.run(
        run_supervised_daemon(
            config_path=cfg_path,
            db_path=Path(args.db_path),
            dry_run=args.dry_run,
        )
    )
    if args.dry_run:
        print(json.dumps(res, indent=2), flush=True)


if __name__ == "__main__":
    main()
