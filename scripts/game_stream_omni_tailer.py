#!/home/james/stacklabs/.venv/bin/python3
"""
FaaS Game Stream Omni-Tailer Daemon
Path: /home/james/stacklabs/scripts/game_stream_omni_tailer.py
Tool #65 // StackLabs FaaS Continuous Ingress Plane

Autonomously resolves active live streams (watch parties, fan channels, postgame shows)
for the active NFL, CFB, and MLB slate, tails them concurrently via pytchat,
and persists raw telemetry to morning_wiretap.db.
"""

import asyncio
import json
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import pytchat
except ImportError:
    venv_py = "/home/james/stacklabs/.venv/bin/python3"
    if os.path.exists(venv_py) and sys.executable != venv_py:
        os.execv(venv_py, [venv_py] + sys.argv)
    else:
        sys.exit(1)

DB_PATH = "/home/james/stacklabs/data/morning_wiretap.db"
SCHEDULE_DB = "/home/james/stacklabs/dna/fanstack_now.db"
SHM_SLATE_PATH = "/dev/shm/vfs/schedule/unified_slate.json"

CANONICAL_CREATOR_CHANNELS = {
    # NFL COHORTS:
    "PHI": [
        {"name": "PHLY Sports", "handle": "PHLY_Sports", "url": "https://www.youtube.com/@PHLY_Sports/live"},
        {"name": "94WIP", "handle": "94WIP", "url": "https://www.youtube.com/@94WIP/live"},
        {"name": "Bleeding Green Nation", "handle": "bleedinggreennation", "url": "https://www.youtube.com/@bleedinggreennation/live"}
    ],
    "NYG": [
        {"name": "Giants Now by Chat Sports", "handle": "GiantsNow", "url": "https://www.youtube.com/@GiantsNow/live"},
        {"name": "Bad Dog Sports", "handle": "BaddogSports", "url": "https://www.youtube.com/@BaddogSports/live"},
        {"name": "Talkin Giants", "handle": "TalkinGiants", "url": "https://www.youtube.com/@TalkinGiants/live"},
        {"name": "Big Blue Banter", "handle": "BigBlueBanter", "url": "https://www.youtube.com/channel/UCJ5JxdXQ6xh48GL8kGQJT0w/live"}
    ],
    "DAL": [
        {"name": "Blogging The Boys", "handle": "BloggingTheBoys", "url": "https://www.youtube.com/@BloggingTheBoys/live"},
        {"name": "Dallas Cowboys Report", "handle": "DallasCowboysReport", "url": "https://www.youtube.com/@DallasCowboysReport/live"}
    ],
    "TB": [
        {"name": "Pewter Report Live React", "handle": "PewterReportTV", "url": "https://www.youtube.com/@PewterReportTV/live"},
        {"name": "Buccaneers Live", "handle": "buccaneers", "url": "https://www.youtube.com/@buccaneers/live"}
    ],
    "BUF": [
        {"name": "Buffalo Fanatics", "handle": "BuffaloFanatics", "url": "https://www.youtube.com/@BuffaloFanatics/live"},
        {"name": "Locked On Bills", "handle": "LockedOnBills", "url": "https://www.youtube.com/@LockedOnBills/live"},
        {"name": "Cover 1 Buffalo", "handle": "Cover1", "url": "https://www.youtube.com/@Cover1/live"},
        {"name": "Hashtag Sports Buffalo", "handle": "HashtagSportsBuffalo", "url": "https://www.youtube.com/@HashtagSportsBuffalo/live"}
    ],
    "LV": [
        {"name": "Tape Don't Lie", "handle": "TapeDontLie", "url": "https://www.youtube.com/@TapeDontLie/live"},
        {"name": "Raider Cody Podcast", "handle": "RaiderCody", "url": "https://www.youtube.com/@RaiderCody/live"},
        {"name": "Sanjit T Las Vegas", "handle": "Sanjit_T", "url": "https://www.youtube.com/@Sanjit_T/live"},
        {"name": "Raiders Report by Chat Sports", "handle": "RaidersReport", "url": "https://www.youtube.com/@RaidersReport/live"}
    ],
    "CHI": [
        {"name": "CHGO Bears", "handle": "CHGO_Bears", "url": "https://www.youtube.com/@CHGO_Sports/live"},
        {"name": "670 The Score", "handle": "670TheScore", "url": "https://www.youtube.com/@670TheScore/live"}
    ],
    "GB": [
        {"name": "Pack-A-Day Podcast", "handle": "PackADayPodcast", "url": "https://www.youtube.com/@PackADayPodcast/live"},
        {"name": "Cheesehead TV", "handle": "cheeseheadtv", "url": "https://www.youtube.com/@cheeseheadtv/live"}
    ],
    "BAL": [
        {"name": "Locked On Ravens", "handle": "LockedOnRavens", "url": "https://www.youtube.com/@LockedOnRavens/live"},
        {"name": "Baltimore Beatdown", "handle": "baltimorebeatdown", "url": "https://www.youtube.com/@baltimorebeatdown/live"}
    ],
    "KC": [
        {"name": "KC Sports Network", "handle": "KCSportsNetwork", "url": "https://www.youtube.com/@KCSportsNetwork/live"},
        {"name": "Arrowhead Addict", "handle": "ArrowheadAddict", "url": "https://www.youtube.com/@ArrowheadAddict/live"}
    ],
    "HOU": [
        {"name": "Locked On Texans", "handle": "LockedOnTexans", "url": "https://www.youtube.com/@LockedOnTexans/live"},
        {"name": "Houston Texans", "handle": "HoustonTexans", "url": "https://www.youtube.com/@HoustonTexans/live"}
    ],
    "MIN": [
        {"name": "SKOR North Purple Daily", "handle": "SKORNorth", "url": "https://www.youtube.com/@SKORNorth/live"}
    ],
    "DET": [
        {"name": "Woodward Sports Network", "handle": "WoodwardSports", "url": "https://www.youtube.com/@WoodwardSports/live"},
        {"name": "Pride of Detroit", "handle": "PrideOfDetroit", "url": "https://www.youtube.com/@PrideOfDetroit/live"}
    ],
    "PIT": [
        {"name": "DK Pittsburgh Sports", "handle": "DKPittsburghSports", "url": "https://www.youtube.com/@DKPittsburghSports/live"},
        {"name": "Locked On Steelers", "handle": "LockedOnSteelers", "url": "https://www.youtube.com/@LockedOnSteelers/live"}
    ],
    "CLE": [
        {"name": "Ultimate Cleveland Sports Show", "handle": "UltimateClevelandSportsShow", "url": "https://www.youtube.com/@UltimateClevelandSportsShow/live"},
        {"name": "Locked On Browns", "handle": "LockedOnBrowns", "url": "https://www.youtube.com/@LockedOnBrowns/live"}
    ],
    "LAR": [
        {"name": "Rams Brothers Podcast", "handle": "RamsBrothers", "url": "https://www.youtube.com/@RamsBrothers/live"},
        {"name": "Locked On Rams", "handle": "LockedOnRams", "url": "https://www.youtube.com/@LockedOnRams/live"}
    ],
    "ARI": [
        {"name": "PHNX Cardinals", "handle": "PHNX_Cardinals", "url": "https://www.youtube.com/@PHNX_Sports/live"},
        {"name": "Locked On Cardinals", "handle": "LockedOnCardinals", "url": "https://www.youtube.com/@LockedOnCardinals/live"}
    ],
    # MLB POSTSEASON:
    "MIL": [
        {"name": "Brewers vs Dodgers Live Watch Party", "handle": "FootballNationLive", "url": "https://www.youtube.com/watch?v=P1QZve1reP8"},
        {"name": "NLCS Game 3 Live Play-By-Play", "handle": "NWSportsFanatics", "url": "https://www.youtube.com/watch?v=Gh363QK6kOQ"}
    ],
    "LAD": [
        {"name": "Dodgers vs Brewers Live Play-By-Play", "handle": "MaxCoverageTV", "url": "https://www.youtube.com/watch?v=Lf36gSxvH4U"}
    ],
    "NYY": [
        {"name": "Talkin Yanks", "handle": "TalkinYanks", "url": "https://www.youtube.com/@TalkinYanks/live"},
        {"name": "Jomboy Media", "handle": "JomboyMedia", "url": "https://www.youtube.com/@JomboyMedia/live"}
    ],
    "BOS": [
        {"name": "Section 10 Pod", "handle": "Section10Pod", "url": "https://www.youtube.com/@Section10Pod/live"}
    ],
    # WNBA PLAYOFFS:
    "WNBA_LIBERTY": [
        {"name": "The Mid-Majors Podcast", "handle": "TheMidMajorsPodcast", "url": "https://www.youtube.com/@TheMidMajorsPodcast/live"}
    ],
    "WNBA_DREAM": [
        {"name": "DJ Tricey Trice", "handle": "DJTriceyTrice", "url": "https://www.youtube.com/@DJTriceyTrice/live"}
    ],
    # CFB COHORTS:
    "FSU": [
        {"name": "Warchant TV", "handle": "WarchantTV", "url": "https://www.youtube.com/@WarchantTV/live"}
    ],
    "LOU": [
        {"name": "Locked On Louisville", "handle": "LockedOnLouisville", "url": "https://www.youtube.com/@LockedOnLouisville/live"}
    ]
}

DAILY_MORNING_SHOWS = [
    {"name": "WFAN Sports Radio 660 AM", "handle": "WFAN660", "url": "https://www.youtube.com/@WFAN660/live", "key": "wfan"},
    {"name": "SportsRadio 94WIP Philadelphia", "handle": "94WIP", "url": "https://www.youtube.com/@94WIP/live", "key": "94wip"},
    {"name": "The Pat McAfee Show", "handle": "ThePatMcAfeeShow", "url": "https://www.youtube.com/@ThePatMcAfeeShow/live", "key": "mcafee"},
    {"name": "PHLY Sports Live", "handle": "PHLY_Sports", "url": "https://www.youtube.com/@PHLY_Sports/live", "key": "phly"},
    {"name": "CHGO Sports Live", "handle": "CHGO_Sports", "url": "https://www.youtube.com/@CHGO_Sports/live", "key": "chgo"}
]

def resolve_live_id(url: str) -> Optional[str]:
    """Resolves active live video ID using yt-dlp."""
    try:
        cmd = [
            "/home/james/stacklabs/.venv/bin/yt-dlp",
            "--js-runtimes", "node",
            "--print", "%(id)s | %(is_live)s",
            url
        ]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=12).strip()
        parts = [p.strip() for p in out.split("|")]
        if len(parts) >= 2 and parts[1] == "True":
            return parts[0]
    except Exception as exc:
        print(f"[OMNI-TAILER] resolve_live_id warning for {url}: {exc}", flush=True)
    return None

def resolve_live_search(query: str) -> Optional[Tuple[str, str]]:
    """Dynamic fallback search using yt-dlp to find live stream for an active slate team."""
    try:
        cmd = [
            "/home/james/stacklabs/.venv/bin/yt-dlp",
            "--js-runtimes", "node",
            f"ytsearch2:{query}",
            "--print", "%(id)s | %(is_live)s | %(title)s"
        ]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=15).strip()
        for line in out.splitlines():
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2 and parts[1] == "True":
                vid = parts[0]
                title = parts[2] if len(parts) >= 3 else query
                return vid, title
    except Exception as exc:
        print(f"[OMNI-TAILER] resolve_live_search warning for '{query}': {exc}", flush=True)
    return None

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_key TEXT,
            stream_id TEXT,
            author TEXT,
            message TEXT,
            timestamp_str TEXT,
            epoch_time REAL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_stream_epoch ON chat_telemetry(stream_id, epoch_time)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS watch_party_streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sport TEXT NOT NULL,
            game_pk TEXT NOT NULL,
            game_date TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            stream_id TEXT NOT NULL,
            stream_title TEXT,
            stream_url TEXT,
            source TEXT,
            resolved_at TEXT,
            is_live INTEGER DEFAULT 1,
            UNIQUE(game_pk, stream_id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_watch_party_game ON watch_party_streams(game_pk, game_date)")
    conn.commit()
    conn.close()

def register_watch_party_stream(sport: str, game_pk: str, home_team: str, away_team: str, stream_id: str, stream_title: str):
    """Upserts stream metadata into watch_party_streams so faas_vfs_telemetry immediately maps it."""
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        stream_url = f"https://www.youtube.com/watch?v={stream_id}"
        with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO watch_party_streams (
                    sport, game_pk, game_date, home_team, away_team,
                    stream_id, stream_title, stream_url, source, resolved_at, is_live
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 1)
                ON CONFLICT(game_pk, stream_id) DO UPDATE SET
                    stream_title = excluded.stream_title,
                    stream_url = excluded.stream_url,
                    is_live = 1,
                    resolved_at = datetime('now');
            """, (sport, str(game_pk), today_str, home_team, away_team, stream_id, stream_title, stream_url, "OmniTailer Ingress"))
            conn.commit()
            print(f"[OMNI-TAILER] Registered watch party stream: {sport} {game_pk} ({home_team} vs {away_team}) -> {stream_id}", flush=True)
    except Exception as e:
        print(f"[OMNI-TAILER] Failed to register watch party stream: {e}", flush=True)

async def db_writer_worker(queue: asyncio.Queue):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    batch = []
    last_flush = time.time()
    
    while True:
        try:
            item = await asyncio.wait_for(queue.get(), timeout=1.0)
            if item is None:
                break
            batch.append(item)
            queue.task_done()
        except asyncio.TimeoutError:
            pass
            
        now = time.time()
        if (len(batch) >= 25 or (now - last_flush >= 1.5)) and batch:
            try:
                cur.executemany("""
                    INSERT INTO chat_telemetry (channel_key, stream_id, author, message, timestamp_str, epoch_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, batch)
                conn.commit()
                batch.clear()
                last_flush = now
            except Exception as e:
                print(f"[DB ERROR] {e}", flush=True)

    if batch:
        cur.executemany("""
            INSERT INTO chat_telemetry (channel_key, stream_id, author, message, timestamp_str, epoch_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
    conn.close()

class StreamListener:
    def __init__(self, channel_key: str, stream_name: str, stream_id: str, queue: asyncio.Queue, finished_ids: Optional[Set[str]] = None):
        self.channel_key = channel_key
        self.stream_name = stream_name
        self.stream_id = stream_id
        self.queue = queue
        self.finished_ids = finished_ids
        self.alive = True
        self.finished = False

    async def listen(self):
        print(f"[LISTENER] Connecting to {self.stream_name} ({self.stream_id})...", flush=True)
        try:
            chat = pytchat.create(video_id=self.stream_id)
            await asyncio.sleep(2)
            if not chat.is_alive():
                print(f"[STREAM FINISHED] {self.stream_name} ({self.stream_id})", flush=True)
                self.alive = False
                self.finished = True
                if self.finished_ids is not None:
                    self.finished_ids.add(self.stream_id)
                return

            while chat.is_alive() and self.alive:
                for c in chat.get().items:
                    author = c.author.name
                    msg = c.message.strip()
                    if not msg or len(msg.split()) < 1:
                        continue
                        
                    raw_dt = getattr(c, 'datetime', '') or ''
                    t_str = raw_dt.split()[-1] if ' ' in raw_dt else (raw_dt if raw_dt else time.strftime('%H:%M:%S'))
                    epoch = time.time()
                    await self.queue.put((self.channel_key, self.stream_id, author, msg, t_str, epoch))
                        
                await asyncio.sleep(0.5)

            print(f"[STREAM FINISHED] {self.stream_name} ({self.stream_id})", flush=True)
            self.finished = True
            if self.finished_ids is not None:
                self.finished_ids.add(self.stream_id)
        except Exception as e:
            print(f"[LISTENER ERROR] {self.stream_id}: {e}", flush=True)
            self.finished = True
            if self.finished_ids is not None:
                self.finished_ids.add(self.stream_id)
        finally:
            self.alive = False
            if self.finished_ids is not None:
                self.finished_ids.add(self.stream_id)
            print(f"[LISTENER STOPPED] {self.stream_id}", flush=True)

def get_active_slate_games() -> List[Dict[str, Any]]:
    """Polls unified polysport slate across /api/polysport/slate, /api/schedule, and SHM cache."""
    port = os.getenv("FAAS_PORT", os.getenv("PORT", "3033"))
    endpoints = [
        f"http://127.0.0.1:{port}/api/polysport/slate",
        f"http://127.0.0.1:{port}/api/schedule",
        f"http://127.0.0.1:{port}/api/mlb/schedule"
    ]
    for url in endpoints:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OmniTailer/2.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception as exc:
            print(f"[OMNI-TAILER] Polling endpoint skipped {url}: {exc}", flush=True)

    # In-memory SHM fallback
    if os.path.exists(SHM_SLATE_PATH):
        try:
            raw = pathlib.Path(SHM_SLATE_PATH).read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, list) and len(data) > 0:
                return data
        except Exception as exc:
            print(f"[OMNI-TAILER] SHM slate read warning: {exc}", flush=True)

    return []

def _extract_team_code(team_obj: Any) -> str:
    """Safely extracts team code from dict node or string representation."""
    if isinstance(team_obj, dict):
        return str(team_obj.get("code") or team_obj.get("abbreviation") or team_obj.get("name") or "").strip().upper()
    elif isinstance(team_obj, str):
        return team_obj.split()[-1].strip().upper()
    return ""

def get_active_slate_teams(games: Optional[List[Dict[str, Any]]] = None) -> List[str]:
    teams: List[str] = []
    if games is None:
        games = get_active_slate_games()
    
    live_games = [
        g for g in games 
        if g.get("isLive") or str(g.get("status", "")).upper() == "LIVE"
    ]
    target_games = live_games if live_games else games[:12]
    
    for g in target_games:
        h = _extract_team_code(g.get("home_team") or g.get("homeTeam"))
        a = _extract_team_code(g.get("away_team") or g.get("awayTeam"))
        if h:
            teams.append(h)
        if a:
            teams.append(a)

    if live_games and len(teams) > 0:
        return list(dict.fromkeys(teams))

    # Add default weekend fallback cohorts if slate empty
    if not teams or len(teams) <= 2:
        teams = ["BUF", "LV", "PHI", "NYG", "LAR", "ARI", "KC", "BAL", "DET", "MIN", "GB", "CHI", "DAL", "TB", "PIT", "CLE"]
    return list(dict.fromkeys(teams))

def match_game_for_team(team: str, games: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    team_upper = team.upper().strip()
    for g in games:
        h = _extract_team_code(g.get("home_team") or g.get("homeTeam"))
        a = _extract_team_code(g.get("away_team") or g.get("awayTeam"))
        if team_upper in (h, a):
            return g
    return None

def link_and_register_stream(team: str, vid: str, stream_title: str, games: List[Dict[str, Any]]):
    g = match_game_for_team(team, games)
    if g:
        sport = str(g.get("sport", "nfl")).upper()
        game_pk = str(g.get("id"))
        home_team = _extract_team_code(g.get("home_team") or g.get("homeTeam"))
        away_team = _extract_team_code(g.get("away_team") or g.get("awayTeam"))
        register_watch_party_stream(sport, game_pk, home_team, away_team, vid, stream_title)
    else:
        sport = "WNBA" if "WNBA" in team else "CFB" if team in ("OU", "TEX", "FSU", "LOU", "IOWA", "WASH", "BYU") else "NFL"
        register_watch_party_stream(sport, f"{sport.lower()}_{team.lower()}", team, "VS", vid, stream_title)

async def main_loop():
    init_db()
    db_queue = asyncio.Queue()
    writer_task = asyncio.create_task(db_writer_worker(db_queue))
    
    active_listeners: Dict[str, Tuple[StreamListener, asyncio.Task]] = {}
    finished_stream_ids: Set[str] = set()
    failed_dynamic_searches: Dict[str, float] = {}

    print("⚡ [OMNI-TAILER] Starting FaaS Multi-Stream Live Ingress Daemon...", flush=True)

    while True:
        try:
            dead = [k for k, (l, t) in list(active_listeners.items()) if not l.alive or t.done()]
            for k in dead:
                listener, task = active_listeners[k]
                finished_stream_ids.add(listener.stream_id)
                print(f"🧹 [OMNI-TAILER] Unmounting finished stream: {listener.stream_name} ({listener.stream_id})", flush=True)
                del active_listeners[k]

            active_teams_with_listeners: Set[str] = set()
            for k, (l, t) in active_listeners.items():
                if l.alive and not t.done():
                    if l.channel_key.startswith("WNBA_"):
                        parts = l.channel_key.split("_")
                        if len(parts) >= 2:
                            active_teams_with_listeners.add(f"{parts[0]}_{parts[1]}")
                    elif "_" in l.channel_key:
                        team_prefix = l.channel_key.split("_")[0]
                        if team_prefix != "radio":
                            active_teams_with_listeners.add(team_prefix)

            # 1. Inspect slate for active games
            active_games = get_active_slate_games()
            teams_on_slate = get_active_slate_teams(active_games)

            # Ensure any active listener is registered in watch_party_streams
            for k, (l, t) in active_listeners.items():
                if l.alive and not t.done() and "_" in l.channel_key:
                    parts = l.channel_key.split("_")
                    if parts[0] != "radio":
                        link_and_register_stream(parts[0], l.stream_id, l.stream_name, active_games)

            # 2a. Morning shows
            for show in DAILY_MORNING_SHOWS:
                handle = show["handle"]
                if handle in active_listeners:
                    if active_listeners[handle][0].alive:
                        continue
                    else:
                        del active_listeners[handle]
                
                vid = resolve_live_id(show["url"])
                if vid and vid not in finished_stream_ids:
                    listener = StreamListener(f"radio_{show['key']}", show["name"], vid, db_queue, finished_stream_ids)
                    task = asyncio.create_task(listener.listen())
                    active_listeners[handle] = (listener, task)
                    print(f"🎉 [OMNI-TAILER] Attached to morning show: {show['name']} ({vid})", flush=True)

            # 2b. Check canonical channels for teams on slate
            for team in teams_on_slate:
                channels = CANONICAL_CREATOR_CHANNELS.get(team, [])
                for ch in channels:
                    handle = ch["handle"]
                    if handle in active_listeners:
                        if active_listeners[handle][0].alive:
                            active_teams_with_listeners.add(team)
                            continue
                        else:
                            del active_listeners[handle]
                        
                    vid = resolve_live_id(ch["url"])
                    if vid and vid not in finished_stream_ids:
                        listener = StreamListener(f"{team}_{handle}", ch["name"], vid, db_queue, finished_stream_ids)
                        task = asyncio.create_task(listener.listen())
                        active_listeners[handle] = (listener, task)
                        active_teams_with_listeners.add(team)
                        print(f"🎉 [OMNI-TAILER] Attached to live stream: {ch['name']} ({vid})", flush=True)
                        link_and_register_stream(team, vid, ch["name"], active_games)

                # 2c. If no canonical channel was live, execute dynamic fallback search
                if team not in active_teams_with_listeners:
                    dyn_key = f"{team}_dynamic"
                    if dyn_key in active_listeners:
                        if active_listeners[dyn_key][0].alive:
                            active_teams_with_listeners.add(team)
                            continue
                        else:
                            del active_listeners[dyn_key]

                    now_ts = time.time()
                    if (now_ts - failed_dynamic_searches.get(team, 0)) >= 300:
                        matched_game = match_game_for_team(team, active_games)
                        if matched_game:
                            h_code = _extract_team_code(matched_game.get("home_team") or matched_game.get("homeTeam"))
                            a_code = _extract_team_code(matched_game.get("away_team") or matched_game.get("awayTeam"))
                            search_query = f"{a_code} vs {h_code} live watch party"
                        else:
                            search_query = f"{team} live watch party"

                        res = resolve_live_search(search_query)
                        if res:
                            vid, stream_title = res
                            if vid not in finished_stream_ids:
                                listener = StreamListener(f"{team}_dynamic", stream_title, vid, db_queue, finished_stream_ids)
                                task = asyncio.create_task(listener.listen())
                                active_listeners[dyn_key] = (listener, task)
                                active_teams_with_listeners.add(team)
                                print(f"🎉 [OMNI-TAILER] Dynamically resolved & attached: {stream_title} ({vid})", flush=True)
                                link_and_register_stream(team, vid, stream_title, active_games)
                        else:
                            failed_dynamic_searches[team] = now_ts

            dead = [k for k, (l, t) in list(active_listeners.items()) if not l.alive or t.done()]
            for k in dead:
                listener, task = active_listeners[k]
                finished_stream_ids.add(listener.stream_id)
                del active_listeners[k]

            print(f"📡 [OMNI-TAILER] Active monitored streams: {len(active_listeners)} (Slate Teams: {len(teams_on_slate)})", flush=True)

        except Exception as e:
            print(f"[SUPERVISOR ERROR] {e}", flush=True)

        await asyncio.sleep(60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="StackLabs Game Stream Omni-Tailer Supervisor & Ingress CLI")
    parser.add_argument("--attach-game", dest="attach_game", help="Attach a stream to game_pk/game_id")
    parser.add_argument("--stream-id", dest="stream_id", help="YouTube stream ID to attach")
    parser.add_argument("--sport", dest="sport", default="nfl", help="Sport category (nfl, cfb, mlb)")
    parser.add_argument("--home", dest="home", default="HOME", help="Home team abbreviation")
    parser.add_argument("--away", dest="away", default="AWAY", help="Away team abbreviation")
    parser.add_argument("--title", dest="title", default="Community Watch Party", help="Stream title")
    parser.add_argument("--ttl-seconds", dest="ttl_seconds", type=int, default=14400, help="Stream TTL in seconds")
    args, _ = parser.parse_known_args()

    if args.attach_game and args.stream_id:
        init_db()
        register_watch_party_stream(
            sport=args.sport,
            game_pk=args.attach_game,
            home_team=args.home,
            away_team=args.away,
            stream_id=args.stream_id,
            stream_title=args.title
        )
        print(f"✓ Successfully attached {args.stream_id} to game {args.attach_game} (TTL {args.ttl_seconds}s)")
        sys.exit(0)

    asyncio.run(main_loop())
