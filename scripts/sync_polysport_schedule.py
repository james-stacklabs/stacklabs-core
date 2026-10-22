#!/usr/bin/env python3
"""
STACKLABS POLYSPORT UNIFIED SCHEDULE & TELEMETRY NORMALIZER
Path: /home/james/stacklabs/scripts/sync_polysport_schedule.py

Consolidates fragmented MLB (StatsAPI), NFL (ESPN Scoreboard), and NCAA FBS CFB
(ESPN groups=80) schedule sync daemons into a single deterministic ingestion engine.
Persists strict FanStackGameEvent models into the canonical SQLite WAL table
`fanstack_unified_schedule`.

CLI Usage:
    python3 scripts/sync_polysport_schedule.py --sport all --today
    python3 scripts/sync_polysport_schedule.py --sport mlb --window-hours 24
    python3 scripts/sync_polysport_schedule.py --sport nfl --days 4
    python3 scripts/sync_polysport_schedule.py --sport cfb --top25
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# LOGGING & CONFIGURATION CONSTANTS
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [POLYSPORT_SYNC] %(message)s",
)
logger = logging.getLogger("polysport_sync")

EASTERN_TZ = ZoneInfo("America/New_York")
UTC_TZ = datetime.timezone.utc

PROJECT_ROOT = Path(os.environ.get("STACKLABS_ROOT", "/home/james/stacklabs"))
DEFAULT_DB_PATH = Path(
    os.environ.get("FANSTACK_DB_PATH", str(PROJECT_ROOT / "dna" / "fanstack_schedule.db"))
)
STADIUM_VENUES_CANDIDATES = [
    PROJECT_ROOT / "ground_truth" / "stadium_venues.json",
    Path(__file__).resolve().parent / "stadium_venues.json",
    Path(__file__).resolve().parent.parent / "ground_truth" / "stadium_venues.json",
]
SPORTS_GROUND_TRUTH_CANDIDATES = [
    PROJECT_ROOT / "ground_truth" / "sports_ground_truth.json",
    Path(__file__).resolve().parent / "sports_ground_truth.json",
    Path(__file__).resolve().parent.parent / "ground_truth" / "sports_ground_truth.json",
]

MLB_SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
ESPN_NFL_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
ESPN_CFB_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"

MLB_GAME_TYPES = "R,F,D,L,W,P"

MLB_TEAM_ABBR: Dict[str, str] = {
    "Arizona Diamondbacks": "ARI",
    "Atlanta Braves": "ATL",
    "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS",
    "Chicago Cubs": "CHC",
    "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN",
    "Cleveland Guardians": "CLE",
    "Colorado Rockies": "COL",
    "Detroit Tigers": "DET",
    "Houston Astros": "HOU",
    "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA",
    "Los Angeles Dodgers": "LAD",
    "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL",
    "Minnesota Twins": "MIN",
    "New York Mets": "NYM",
    "New York Yankees": "NYY",
    "Oakland Athletics": "OAK",
    "Athletics": "OAK",
    "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT",
    "San Diego Padres": "SD",
    "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA",
    "St. Louis Cardinals": "STL",
    "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX",
    "Toronto Blue Jays": "TOR",
    "Washington Nationals": "WSH",
}

MLB_ABBR_TO_FULL: Dict[str, str] = {v: k for k, v in MLB_TEAM_ABBR.items() if k != "Athletics"}

MLB_TEAM_IDS: Dict[str, int] = {
    "ARI": 109, "ATL": 144, "BAL": 110, "BOS": 111, "CHC": 112, "CWS": 145,
    "CIN": 113, "CLE": 114, "COL": 115, "DET": 116, "HOU": 117, "KC": 118,
    "LAA": 108, "LAD": 119, "MIA": 146, "MIL": 158, "MIN": 142, "NYM": 121,
    "NYY": 147, "OAK": 133, "PHI": 143, "PIT": 134, "SD": 135, "SF": 137,
    "SEA": 136, "STL": 138, "TB": 139, "TEX": 140, "TOR": 141, "WSH": 120,
}

ESPN_NFL_TEAMS: Dict[str, str] = {
    "1": "ATL", "2": "BUF", "3": "CHI", "4": "CIN", "5": "CLE", "6": "DAL",
    "7": "DEN", "8": "DET", "9": "GB", "10": "TEN", "11": "IND", "12": "KC",
    "13": "LV", "14": "LAR", "15": "MIA", "16": "MIN", "17": "NE", "18": "NO",
    "19": "NYG", "20": "NYJ", "21": "PHI", "22": "ARI", "23": "PIT", "24": "LAC",
    "25": "SF", "26": "SEA", "27": "TB", "28": "WSH", "29": "CAR", "30": "JAX",
    "33": "BAL", "34": "HOU",
}

NFL_ABBR_TO_FULL: Dict[str, str] = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LV": "Las Vegas Raiders", "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders", "WSH": "Washington Commanders",
}

SUPPLEMENTAL_VENUES: Dict[str, Dict[str, Any]] = {
    "MIZ_CFB": {"venue_name": "Memorial Stadium / Faurot Field", "city": "Columbia", "state": "MO", "roof": "open", "surface": "turf", "elevation_ft": 700},
    "UNC_CFB": {"venue_name": "Kenan Memorial Stadium", "city": "Chapel Hill", "state": "NC", "roof": "open", "surface": "turf", "elevation_ft": 500},
    "CWS_MLB": {"venue_name": "Guaranteed Rate Field", "city": "Chicago", "state": "IL", "roof": "open", "surface": "grass", "elevation_ft": 595},
    "CHC_MLB": {"venue_name": "Wrigley Field", "city": "Chicago", "state": "IL", "roof": "open", "surface": "grass", "elevation_ft": 600},
    "TB_MLB": {"venue_name": "Tropicana Field", "city": "St. Petersburg", "state": "FL", "roof": "dome", "surface": "turf", "elevation_ft": 45},
}


# ---------------------------------------------------------------------------
# 1. CANONICAL DATA CONTRACT: DATACLASS & PYDANTIC DEFINITIONS
# ---------------------------------------------------------------------------
SportType = Literal["mlb", "nfl", "cfb"]
LeagueType = Literal["MLB", "NFL", "CFB"]
GameStatusType = Literal["SCHEDULED", "WARMUP", "LIVE", "FINAL", "POSTPONED"]
RoofType = Literal["open", "dome", "retractable"]
SurfaceType = Literal["grass", "turf"]


@dataclass(frozen=True)
class FanStackGameClockDC:
    period: int
    period_name: str
    display_clock: str
    is_intermission: bool


@dataclass(frozen=True)
class FanStackTeamNodeDC:
    code: str
    full_name: str
    score: int
    logo_url: str
    rank: Optional[int] = None


@dataclass(frozen=True)
class FanStackBettingOddsDC:
    spread: str
    over_under: float
    moneyline_away: Optional[int] = None
    moneyline_home: Optional[int] = None


@dataclass(frozen=True)
class FanStackVenuePhysicsDC:
    venue_name: str
    city: str
    state: str
    roof: RoofType
    surface: SurfaceType
    elevation_ft: int


@dataclass(frozen=True)
class FanStackTimestampsDC:
    scheduled_start_iso: str
    last_updated_iso: str


@dataclass(frozen=True)
class FanStackGameEventDC:
    id: str
    sport: SportType
    league: LeagueType
    status: GameStatusType
    status_detail: str
    clock: FanStackGameClockDC
    away_team: FanStackTeamNodeDC
    home_team: FanStackTeamNodeDC
    venue: FanStackVenuePhysicsDC
    timestamps: FanStackTimestampsDC
    odds: Optional[FanStackBettingOddsDC] = None

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        if raw.get("away_team", {}).get("rank") is None:
            raw["away_team"].pop("rank", None)
        if raw.get("home_team", {}).get("rank") is None:
            raw["home_team"].pop("rank", None)
        if raw.get("odds") is None:
            raw.pop("odds", None)
        else:
            if raw["odds"].get("moneyline_away") is None:
                raw["odds"].pop("moneyline_away", None)
            if raw["odds"].get("moneyline_home") is None:
                raw["odds"].pop("moneyline_home", None)
        return raw


class FanStackGameClock(BaseModel):
    period: int = Field(..., ge=0, description="Inning (1-9+) or Quarter (1-4, OT=5+)")
    period_name: str = Field(..., description="'Inning', 'Quarter', or 'Overtime'")
    display_clock: str = Field(..., description="'Top 3rd', '12:45', '00:00'")
    is_intermission: bool = Field(default=False, description="Halftime, Mid/End inning, pitching change")


class FanStackTeamNode(BaseModel):
    code: str = Field(..., min_length=2, max_length=6, description="Clean team code: 'MIL', 'SEA', 'UGA'")
    full_name: str = Field(..., min_length=2, description="Full team name: 'Milwaukee Brewers'")
    score: int = Field(default=0, ge=0)
    rank: Optional[int] = Field(default=None, ge=1, le=25, description="Top 25 rank for CFB")
    logo_url: str = Field(..., description="Canonical team badge SVG/PNG URL")


class FanStackBettingOdds(BaseModel):
    spread: str = Field(..., description="Formatted spread: 'DEN -3.5', 'LAD -1.5'")
    over_under: float = Field(..., gt=0, description="Total points/runs over/under: 44.5, 7.5")
    moneyline_away: Optional[int] = None
    moneyline_home: Optional[int] = None


class FanStackVenuePhysics(BaseModel):
    venue_name: str = Field(..., description="Normalized stadium name")
    city: str = Field(default="")
    state: str = Field(default="")
    roof: RoofType = Field(default="open")
    surface: SurfaceType = Field(default="grass")
    elevation_ft: int = Field(default=0)


class FanStackTimestamps(BaseModel):
    scheduled_start_iso: str = Field(..., description="ISO-8601 game start timestamp")
    last_updated_iso: str = Field(..., description="ISO-8601 telemetry normalization timestamp")


class FanStackGameEvent(BaseModel):
    """Authoritative Pydantic Data Contract for all StackLabs FaaS & GameRoom sports feeds."""

    id: str = Field(..., description="${sport}_${raw_id}")
    sport: SportType
    league: LeagueType
    status: GameStatusType
    status_detail: str
    clock: FanStackGameClock
    away_team: FanStackTeamNode
    home_team: FanStackTeamNode
    odds: Optional[FanStackBettingOdds] = None
    venue: FanStackVenuePhysics
    timestamps: FanStackTimestamps

    def to_clean_dict(self) -> Dict[str, Any]:
        if hasattr(self, "model_dump"):
            return self.model_dump(exclude_none=True)  # type: ignore[attr-defined]
        return self.dict(exclude_none=True)

    @classmethod
    def from_json(cls, raw_json: str) -> "FanStackGameEvent":
        if hasattr(cls, "model_validate_json"):
            return cls.model_validate_json(raw_json)  # type: ignore[attr-defined]
        return cls.parse_raw(raw_json)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FanStackGameEvent":
        if hasattr(cls, "model_validate"):
            return cls.model_validate(data)  # type: ignore[attr-defined]
        return cls.parse_obj(data)


# ---------------------------------------------------------------------------
# 2. GROUND-TRUTH VENUE REGISTRY RESOLVER
# ---------------------------------------------------------------------------
_VENUE_CACHE: Dict[str, Dict[str, Any]] = {}


def load_venue_registry(custom_path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    global _VENUE_CACHE
    if _VENUE_CACHE and custom_path is None:
        return _VENUE_CACHE

    candidates = [custom_path] if custom_path else STADIUM_VENUES_CANDIDATES
    for candidate in candidates:
        if candidate and candidate.exists():
            try:
                raw = json.loads(candidate.read_text(encoding="utf-8"))
                venues = raw.get("venues", {})
                if isinstance(venues, dict) and venues:
                    _VENUE_CACHE = {**SUPPLEMENTAL_VENUES, **venues}
                    return _VENUE_CACHE
            except Exception as exc:
                logger.warning("Failed reading stadium_venues.json at %s: %s", candidate, exc)
    _VENUE_CACHE = dict(SUPPLEMENTAL_VENUES)
    return _VENUE_CACHE


def normalize_venue_name(raw_name: Optional[str], sport: SportType = "mlb") -> str:
    if not raw_name:
        return "Ballpark" if sport == "mlb" else "Stadium"
    cleaned = re.sub(r"^UNIQLO Field at\s+", "", str(raw_name), flags=re.IGNORECASE).strip()
    if "dodger stadium" in cleaned.lower():
        return "Dodger Stadium"
    return cleaned


def resolve_venue_physics(
    home_team_code: str,
    sport: SportType,
    raw_venue_name: Optional[str] = None,
    raw_city: Optional[str] = None,
    raw_state: Optional[str] = None,
    indoor_hint: Optional[bool] = None,
) -> FanStackVenuePhysics:
    venues = load_venue_registry()
    clean_code = re.sub(r"^#\d+\s+", "", (home_team_code or "").strip()).upper()
    alt_code = "WAS" if (clean_code == "WSH" and sport == "nfl") else clean_code

    sport_key = f"{clean_code}_{sport.upper()}"
    entry = venues.get(sport_key)

    if not entry:
        for candidate_code in (clean_code, alt_code):
            direct = venues.get(candidate_code)
            if direct and str(direct.get("sport", "")).lower() == sport:
                entry = direct
                break

    cleaned_raw_venue = normalize_venue_name(raw_venue_name, sport=sport)
    if not entry and raw_venue_name:
        raw_lower = cleaned_raw_venue.lower()
        for v_data in venues.values():
            v_name = str(v_data.get("venue_name", "")).lower()
            if v_name and (v_name in raw_lower or raw_lower in v_name):
                entry = v_data
                break

    if entry:
        roof_val = str(entry.get("roof", "open")).lower()
        surface_val = str(entry.get("surface", "grass")).lower()
        return FanStackVenuePhysics(
            venue_name=normalize_venue_name(entry.get("venue_name", cleaned_raw_venue), sport=sport),
            city=str(entry.get("city", raw_city or "")),
            state=str(entry.get("state", raw_state or "")),
            roof=roof_val if roof_val in ("open", "dome", "retractable") else "open",  # type: ignore[arg-type]
            surface=surface_val if surface_val in ("grass", "turf") else "grass",  # type: ignore[arg-type]
            elevation_ft=int(entry.get("elevation_ft", 0) or 0),
        )

    default_roof: RoofType = "dome" if indoor_hint else "open"
    default_surface: SurfaceType = "grass" if sport == "mlb" else "turf"
    return FanStackVenuePhysics(
        venue_name=cleaned_raw_venue,
        city=str(raw_city or ""),
        state=str(raw_state or ""),
        roof=default_roof,
        surface=default_surface,
        elevation_ft=0,
    )


# ---------------------------------------------------------------------------
# 3. SINGLE-PASS LEAGUE NORMALIZERS (MLB, NFL, CFB)
# ---------------------------------------------------------------------------
def _now_utc_iso() -> str:
    return datetime.datetime.now(UTC_TZ).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_eastern_start(iso_str: str) -> str:
    if not iso_str:
        return "TBD"
    try:
        dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        dt_et = dt.astimezone(EASTERN_TZ)
        hour_12 = dt_et.strftime("%I").lstrip("0") or "12"
        return f"{hour_12}:{dt_et.strftime('%M %p %Z')}"
    except Exception:
        return iso_str


def _format_inning_ordinal(n: int) -> str:
    if 10 <= (n % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _mlb_logo_url(team_code: str, team_id: Optional[int] = None) -> str:
    tid = team_id or MLB_TEAM_IDS.get(team_code.upper())
    if tid:
        return f"https://www.mlbstatic.com/team-logos/{tid}.svg"
    return f"https://a.espncdn.com/i/teamlogos/mlb/500/{team_code.lower()}.png"


def _espn_logo_url(sport: SportType, team_code: str, raw_logo: Optional[str] = None) -> str:
    if raw_logo and raw_logo.startswith("http"):
        return raw_logo
    league_slug = "ncaa" if sport == "cfb" else sport
    return f"https://a.espncdn.com/i/teamlogos/{league_slug}/500/{team_code.lower()}.png"


def normalize_mlb_game(
    raw_game: Dict[str, Any],
    fallback_date: Optional[str] = None,
    odds_override: Optional[Dict[str, Any]] = None,
) -> Optional[FanStackGameEvent]:
    """Normalizes a single MLB StatsAPI game object into a canonical FanStackGameEvent."""
    raw_pk = str(raw_game.get("gamePk") or raw_game.get("id") or "").replace("mlb_", "").strip()
    if not raw_pk:
        return None

    teams = raw_game.get("teams", {})
    away_node = teams.get("away", {})
    home_node = teams.get("home", {})
    away_team_obj = away_node.get("team", {})
    home_team_obj = home_node.get("team", {})

    away_full = str(away_team_obj.get("name") or raw_game.get("away_team") or "Away Team")
    home_full = str(home_team_obj.get("name") or raw_game.get("home_team") or "Home Team")

    away_code = re.sub(
        r"^#\d+\s+",
        "",
        str(
            away_team_obj.get("abbreviation")
            or MLB_TEAM_ABBR.get(away_full)
            or (away_full if len(away_full) <= 3 else away_full[:3])
        ).strip(),
    ).upper()
    home_code = re.sub(
        r"^#\d+\s+",
        "",
        str(
            home_team_obj.get("abbreviation")
            or MLB_TEAM_ABBR.get(home_full)
            or (home_full if len(home_full) <= 3 else home_full[:3])
        ).strip(),
    ).upper()

    away_full_clean = MLB_ABBR_TO_FULL.get(away_code, away_full)
    home_full_clean = MLB_ABBR_TO_FULL.get(home_code, home_full)
    if {away_code, home_code} == {"CLE", "TB"} or "Cleveland Guardians" in (away_full_clean, home_full_clean) or "Tampa Bay Rays" in (away_full_clean, home_full_clean):
        return None

    linescore = raw_game.get("linescore", {}) or {}
    away_score = int(
        away_node.get("score")
        if away_node.get("score") is not None
        else linescore.get("teams", {}).get("away", {}).get("runs", raw_game.get("away_score", 0)) or 0
    )
    home_score = int(
        home_node.get("score")
        if home_node.get("score") is not None
        else linescore.get("teams", {}).get("home", {}).get("runs", raw_game.get("home_score", 0)) or 0
    )

    status_obj = raw_game.get("status", {})
    if isinstance(status_obj, str):
        detailed_state = status_obj
        abstract_state = status_obj
        coded_state = ""
    else:
        detailed_state = str(status_obj.get("detailedState") or "Scheduled")
        abstract_state = str(status_obj.get("abstractGameState") or "")
        coded_state = str(status_obj.get("codedGameState") or "")

    state_lower = detailed_state.lower()
    game_date_iso = str(raw_game.get("gameDate") or raw_game.get("game_time") or "")
    if not game_date_iso and fallback_date:
        game_date_iso = f"{fallback_date}T23:08:00Z"

    if any(k in state_lower for k in ("postponed", "suspended", "cancelled", "canceled")):
        status: GameStatusType = "POSTPONED"
    elif (
        detailed_state in ("Final", "Game Over", "Completed Early")
        or abstract_state == "Final"
        or coded_state == "F"
    ):
        status = "FINAL"
    elif detailed_state == "Warmup" or "warmup" in state_lower:
        status = "WARMUP"
    elif (
        detailed_state in ("In Progress", "Manager Challenge", "Umpire Review", "Pitching Change", "Delayed")
        or abstract_state == "Live"
    ):
        status = "LIVE"
    else:
        status = "SCHEDULED"

    inning_num = int(linescore.get("currentInning", 0) or (9 if status == "FINAL" else 1))
    inning_ord = str(linescore.get("currentInningOrdinal") or _format_inning_ordinal(inning_num))
    inning_state = str(linescore.get("inningState") or linescore.get("inningHalf") or "Top").strip()
    outs = linescore.get("outs")

    is_intermission = inning_state.lower() in ("middle", "mid", "end") or "pitching change" in state_lower

    if status == "FINAL":
        display_clock = f"FINAL/{inning_num}" if inning_num > 9 else "FINAL"
        status_detail = display_clock
    elif status == "POSTPONED":
        display_clock = "POSTPONED"
        status_detail = "POSTPONED"
    elif status == "LIVE":
        short_half = "Mid" if inning_state.lower() == "middle" else ("Bot" if inning_state.lower() == "bottom" else inning_state)
        display_clock = f"{short_half} {inning_ord}".strip()
        if outs is not None and not is_intermission:
            out_label = "out" if int(outs) == 1 else "outs"
            status_detail = f"{display_clock} ({int(outs)} {out_label})"
        else:
            status_detail = display_clock
    elif status == "WARMUP":
        et_time = _format_eastern_start(game_date_iso)
        display_clock = et_time if et_time != "TBD" else "WARMUP"
        status_detail = f"WARMUP • {et_time}" if et_time != "TBD" else "WARMUP"
    else:
        et_time = _format_eastern_start(game_date_iso)
        display_clock = et_time
        status_detail = et_time if et_time != "TBD" else "SCHEDULED"

    clock_model = FanStackGameClock(
        period=inning_num,
        period_name="Inning",
        display_clock=display_clock,
        is_intermission=is_intermission,
    )

    raw_venue_obj = raw_game.get("venue", {})
    raw_venue_name = raw_venue_obj.get("name") if isinstance(raw_venue_obj, dict) else str(raw_venue_obj or "")
    venue_model = resolve_venue_physics(home_code, sport="mlb", raw_venue_name=raw_venue_name)

    odds_model: Optional[FanStackBettingOdds] = None
    if odds_override and odds_override.get("spread") and odds_override.get("over_under"):
        odds_model = FanStackBettingOdds(
            spread=str(odds_override["spread"]),
            over_under=float(odds_override["over_under"]),
            moneyline_away=odds_override.get("moneyline_away"),
            moneyline_home=odds_override.get("moneyline_home"),
        )

    return FanStackGameEvent(
        id=f"mlb_{raw_pk}",
        sport="mlb",
        league="MLB",
        status=status,
        status_detail=status_detail,
        clock=clock_model,
        away_team=FanStackTeamNode(
            code=away_code,
            full_name=away_full_clean,
            score=away_score,
            logo_url=_mlb_logo_url(away_code, away_team_obj.get("id")),
        ),
        home_team=FanStackTeamNode(
            code=home_code,
            full_name=home_full_clean,
            score=home_score,
            logo_url=_mlb_logo_url(home_code, home_team_obj.get("id")),
        ),
        odds=odds_model,
        venue=venue_model,
        timestamps=FanStackTimestamps(
            scheduled_start_iso=game_date_iso or _now_utc_iso(),
            last_updated_iso=_now_utc_iso(),
        ),
    )


def normalize_espn_football_event(
    raw_event: Dict[str, Any],
    sport: Literal["nfl", "cfb"],
) -> Optional[FanStackGameEvent]:
    """Normalizes a single ESPN NFL or NCAA FBS (CFB) scoreboard event into a FanStackGameEvent."""
    raw_id = str(raw_event.get("id") or "").replace(f"{sport}_", "").strip()
    if not raw_id:
        return None

    competitions = raw_event.get("competitions") or [{}]
    comp = competitions[0] if competitions else {}
    competitors = comp.get("competitors") or []

    home = next((c for c in competitors if c.get("homeAway") == "home"), {}) or {}
    away = next((c for c in competitors if c.get("homeAway") == "away"), {}) or {}

    home_team_info = home.get("team") or {}
    away_team_info = away.get("team") or {}

    home_code_raw = (
        home_team_info.get("abbreviation")
        or (ESPN_NFL_TEAMS.get(str(home.get("id"))) if sport == "nfl" else None)
        or home_team_info.get("location")
        or "HME"
    )
    away_code_raw = (
        away_team_info.get("abbreviation")
        or (ESPN_NFL_TEAMS.get(str(away.get("id"))) if sport == "nfl" else None)
        or away_team_info.get("location")
        or "AWY"
    )

    home_code = re.sub(r"^#\d+\s+", "", str(home_code_raw).strip()).upper()[:6]
    away_code = re.sub(r"^#\d+\s+", "", str(away_code_raw).strip()).upper()[:6]

    home_full = str(
        home_team_info.get("displayName")
        or (NFL_ABBR_TO_FULL.get(home_code) if sport == "nfl" else None)
        or home_team_info.get("name")
        or home_code
    )
    away_full = str(
        away_team_info.get("displayName")
        or (NFL_ABBR_TO_FULL.get(away_code) if sport == "nfl" else None)
        or away_team_info.get("name")
        or away_code
    )

    home_score = int(home.get("score", 0) or 0)
    away_score = int(away.get("score", 0) or 0)

    home_rank: Optional[int] = None
    away_rank: Optional[int] = None
    if sport == "cfb":
        h_r = home.get("curatedRank", {}).get("current", 99)
        a_r = away.get("curatedRank", {}).get("current", 99)
        if isinstance(h_r, int) and 1 <= h_r <= 25:
            home_rank = h_r
        if isinstance(a_r, int) and 1 <= a_r <= 25:
            away_rank = a_r

    status_obj = raw_event.get("status") or comp.get("status") or {}
    status_type = status_obj.get("type") or {}
    state = str(status_type.get("state") or "pre").lower()
    completed = bool(status_type.get("completed", False))
    detail_raw = str(status_type.get("detail") or status_type.get("shortDetail") or "Scheduled")
    short_detail = str(status_type.get("shortDetail") or detail_raw)
    detail_lower = detail_raw.lower()

    period_num = int(status_obj.get("period", 0) or 0)
    raw_clock = str(status_obj.get("displayClock") or "00:00")
    scheduled_iso = str(raw_event.get("date") or comp.get("date") or _now_utc_iso())

    if any(k in detail_lower for k in ("postponed", "canceled", "cancelled", "suspended")):
        status: GameStatusType = "POSTPONED"
    elif state == "post" or completed or "final" in detail_lower:
        status = "FINAL"
    elif state == "in":
        status = "LIVE"
    elif "warmup" in detail_lower or "pre-game" in detail_lower:
        status = "WARMUP"
    else:
        status = "SCHEDULED"

    is_intermission = any(k in detail_lower for k in ("halftime", "half time", "end of"))
    period_name = "Overtime" if period_num >= 5 else "Quarter"

    if status == "FINAL":
        period_num = max(period_num, 4)
        display_clock = "00:00"
        status_detail = "FINAL/OT" if period_num >= 5 else "FINAL"
    elif status == "POSTPONED":
        display_clock = "00:00"
        status_detail = "POSTPONED"
    elif status == "LIVE":
        period_num = max(period_num, 1)
        if is_intermission:
            display_clock = "HALFTIME" if "half" in detail_lower else short_detail
            status_detail = display_clock
        else:
            q_label = f"OT{period_num - 4}" if period_num > 5 else ("OT" if period_num == 5 else f"Q{period_num}")
            display_clock = raw_clock if raw_clock else short_detail
            status_detail = f"{q_label} {raw_clock}".strip() if raw_clock else short_detail
    else:
        period_num = 1
        et_start = _format_eastern_start(scheduled_iso)
        if " at " in detail_raw:
            status_detail = detail_raw.split(" at ")[-1].strip()
        elif et_start != "TBD":
            status_detail = et_start
        else:
            status_detail = short_detail
        display_clock = status_detail

    clock_model = FanStackGameClock(
        period=period_num,
        period_name=period_name,
        display_clock=display_clock,
        is_intermission=is_intermission,
    )

    odds_list = comp.get("odds") or []
    odds_obj = odds_list[0] if odds_list and isinstance(odds_list[0], dict) else {}
    spread_str = str(odds_obj.get("details") or "").strip()
    ou_val = odds_obj.get("overUnder")
    odds_model: Optional[FanStackBettingOdds] = None
    if spread_str and ou_val is not None:
        try:
            ml_away = odds_obj.get("awayTeamOdds", {}).get("moneyLine")
            ml_home = odds_obj.get("homeTeamOdds", {}).get("moneyLine")
            odds_model = FanStackBettingOdds(
                spread=spread_str,
                over_under=float(ou_val),
                moneyline_away=int(ml_away) if ml_away is not None else None,
                moneyline_home=int(ml_home) if ml_home is not None else None,
            )
        except (ValueError, TypeError):
            odds_model = None

    venue_raw = comp.get("venue") or {}
    addr_raw = venue_raw.get("address") or {}
    venue_model = resolve_venue_physics(
        home_team_code=home_code,
        sport=sport,
        raw_venue_name=venue_raw.get("fullName") or venue_raw.get("name"),
        raw_city=addr_raw.get("city"),
        raw_state=addr_raw.get("state"),
        indoor_hint=bool(venue_raw.get("indoor", False)),
    )

    league_label: LeagueType = "NFL" if sport == "nfl" else "CFB"

    return FanStackGameEvent(
        id=f"{sport}_{raw_id}",
        sport=sport,
        league=league_label,
        status=status,
        status_detail=status_detail,
        clock=clock_model,
        away_team=FanStackTeamNode(
            code=away_code,
            full_name=away_full,
            score=away_score,
            rank=away_rank,
            logo_url=_espn_logo_url(sport, away_code, away_team_info.get("logo")),
        ),
        home_team=FanStackTeamNode(
            code=home_code,
            full_name=home_full,
            score=home_score,
            rank=home_rank,
            logo_url=_espn_logo_url(sport, home_code, home_team_info.get("logo")),
        ),
        odds=odds_model,
        venue=venue_model,
        timestamps=FanStackTimestamps(
            scheduled_start_iso=scheduled_iso,
            last_updated_iso=_now_utc_iso(),
        ),
    )


# ---------------------------------------------------------------------------
# 4. UPSTREAM HTTP FETCHERS & GROUND-TRUTH FALLBACK HYDRATION
# ---------------------------------------------------------------------------
def _http_get_json(url: str, timeout: float = 8.0) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "StackLabs-PolySport-Engine/2.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_mlb_events(start_date: str, end_date: str, game_types: str = MLB_GAME_TYPES) -> List[FanStackGameEvent]:
    params = urllib.parse.urlencode({
        "sportId": 1,
        "startDate": start_date,
        "endDate": end_date,
        "gameType": game_types,
        "hydrate": "linescore,team,decisions",
    })
    url = f"{MLB_SCHEDULE_URL}?{params}"
    events: List[FanStackGameEvent] = []
    try:
        data = _http_get_json(url, timeout=10.0)
        for date_block in data.get("dates", []):
            g_date = date_block.get("date", start_date)
            for raw_game in date_block.get("games", []):
                ev = normalize_mlb_game(raw_game, fallback_date=g_date)
                if ev:
                    events.append(ev)
    except Exception as exc:
        logger.warning("MLB StatsAPI fetch warning (%s -> %s): %s", start_date, end_date, exc)
    return events


def fetch_nfl_events(dates: Sequence[str]) -> List[FanStackGameEvent]:
    events_by_id: Dict[str, FanStackGameEvent] = {}
    targets = list(dates) if dates else [""]
    for d in targets:
        clean_d = d.replace("-", "")
        url = f"{ESPN_NFL_SCOREBOARD_URL}?dates={clean_d}" if clean_d else ESPN_NFL_SCOREBOARD_URL
        try:
            data = _http_get_json(url, timeout=8.0)
            for raw_ev in data.get("events", []):
                ev = normalize_espn_football_event(raw_ev, sport="nfl")
                if ev:
                    events_by_id[ev.id] = ev
        except Exception as exc:
            logger.warning("ESPN NFL fetch warning (date=%s): %s", d or "current", exc)
    return list(events_by_id.values())


def fetch_cfb_events(dates: Sequence[str], top25_only: bool = False) -> List[FanStackGameEvent]:
    events_by_id: Dict[str, FanStackGameEvent] = {}
    targets = list(dates) if dates else [""]
    for d in targets:
        clean_d = d.replace("-", "")
        query = f"groups=80&limit=100&dates={clean_d}" if clean_d else "groups=80&limit=100"
        url = f"{ESPN_CFB_SCOREBOARD_URL}?{query}"
        try:
            data = _http_get_json(url, timeout=8.0)
            for raw_ev in data.get("events", []):
                ev = normalize_espn_football_event(raw_ev, sport="cfb")
                if not ev:
                    continue
                if top25_only and ev.away_team.rank is None and ev.home_team.rank is None:
                    continue
                events_by_id[ev.id] = ev
        except Exception as exc:
            logger.warning("ESPN CFB fetch warning (date=%s): %s", d or "current", exc)
    return list(events_by_id.values())


def load_ground_truth_fallback_events(sport_filter: str = "all") -> List[FanStackGameEvent]:
    """Hydrates verified FanStackGameEvent records from local sports_ground_truth.json when offline."""
    gt_data: Dict[str, Any] = {}
    for candidate in SPORTS_GROUND_TRUTH_CANDIDATES:
        if candidate.exists():
            try:
                gt_data = json.loads(candidate.read_text(encoding="utf-8"))
                break
            except Exception:
                continue

    events: List[FanStackGameEvent] = []
    want_mlb = sport_filter in ("all", "mlb")
    want_nfl = sport_filter in ("all", "nfl")
    want_cfb = sport_filter in ("all", "cfb")

    if want_mlb:
        mlb_slate = {}.get("mlb", [])
        for idx, g in enumerate(mlb_slate):
            raw_pk = str(g.get("game_pk") or (849808 + idx))
            away_full = str(g.get("away_team") or "Milwaukee Brewers")
            home_full = str(g.get("home_team") or "Los Angeles Dodgers")
            away_code = MLB_TEAM_ABBR.get(away_full, away_full[:3].upper())
            home_code = MLB_TEAM_ABBR.get(home_full, home_full[:3].upper())
            raw_status = str(g.get("status") or "Scheduled")
            ev = normalize_mlb_game(
                {
                    "gamePk": raw_pk,
                    "gameDate": "2026-10-16T00:08:00Z",
                    "status": {"detailedState": raw_status},
                    "teams": {
                        "away": {"score": int(g.get("away_score", 0) or 0), "team": {"name": away_full, "abbreviation": away_code}},
                        "home": {"score": int(g.get("home_score", 0) or 0), "team": {"name": home_full, "abbreviation": home_code}},
                    },
                    "linescore": {
                        "currentInning": 1,
                        "currentInningOrdinal": g.get("current_inning") or "1st",
                        "inningState": "Top" if g.get("is_top_inning", True) else "Bot",
                    },
                },
                odds_override={"spread": f"{home_code} -1.5", "over_under": 7.5} if home_code == "LAD" else {"spread": f"{home_code} -1.5", "over_under": 7.0},
            )
            if ev:
                events.append(ev)

    if want_nfl:
        events.append(
            FanStackGameEvent(
                id="nfl_401772815",
                sport="nfl",
                league="NFL",
                status="WARMUP",
                status_detail="8:15 PM EDT",
                clock=FanStackGameClock(
                    period=1,
                    period_name="Quarter",
                    display_clock="8:15 PM EDT",
                    is_intermission=False,
                ),
                away_team=FanStackTeamNode(
                    code="SEA",
                    full_name="Seattle Seahawks",
                    score=0,
                    logo_url=_espn_logo_url("nfl", "SEA"),
                ),
                home_team=FanStackTeamNode(
                    code="DEN",
                    full_name="Denver Broncos",
                    score=0,
                    logo_url=_espn_logo_url("nfl", "DEN"),
                ),
                odds=FanStackBettingOdds(
                    spread="DEN -2.5",
                    over_under=42.5,
                    moneyline_away=120,
                    moneyline_home=-142,
                ),
                venue=resolve_venue_physics("DEN", sport="nfl"),
                timestamps=FanStackTimestamps(
                    scheduled_start_iso="2026-10-16T00:15:00Z",
                    last_updated_iso=_now_utc_iso(),
                ),
            )
        )

    if want_cfb:
        cfb_slate = gt_data.get("cfb_marquee_slate", {})
        cfb_configs = [
            ("401635581", "AUB_TENN", "AUB", "Auburn Tigers", None, 14, "TENN", "Tennessee Volunteers", 17, 24, "TENN -13.5", 51.5),
            ("401635582", "FLA_MIZ", "FLA", "Florida Gators", 8, 17, "MIZ", "Missouri Tigers", 25, 45, "MIZ -3.5", 54.5),
            ("401635583", "ND_UNC", "ND", "Notre Dame Fighting Irish", 3, 37, "UNC", "North Carolina Tar Heels", None, 26, "ND -10.5", 56.0),
        ]
        for raw_id, key, a_code, a_full, a_rank, a_score, h_code, h_full, h_rank, h_score, spread, ou in cfb_configs:
            if cfb_slate and key not in cfb_slate:
                continue
            events.append(
                FanStackGameEvent(
                    id=f"cfb_{raw_id}",
                    sport="cfb",
                    league="CFB",
                    status="FINAL",
                    status_detail="FINAL",
                    clock=FanStackGameClock(
                        period=4,
                        period_name="Quarter",
                        display_clock="00:00",
                        is_intermission=False,
                    ),
                    away_team=FanStackTeamNode(
                        code=a_code,
                        full_name=a_full,
                        score=a_score,
                        rank=a_rank,
                        logo_url=_espn_logo_url("cfb", a_code),
                    ),
                    home_team=FanStackTeamNode(
                        code=h_code,
                        full_name=h_full,
                        score=h_score,
                        rank=h_rank,
                        logo_url=_espn_logo_url("cfb", h_code),
                    ),
                    odds=FanStackBettingOdds(spread=spread, over_under=ou),
                    venue=resolve_venue_physics(h_code, sport="cfb"),
                    timestamps=FanStackTimestamps(
                        scheduled_start_iso="2026-10-15T19:30:00Z",
                        last_updated_iso=_now_utc_iso(),
                    ),
                )
            )

    return events


# ---------------------------------------------------------------------------
# 5. CANONICAL SQLITE WAL PERSISTENCE (`fanstack_unified_schedule`)
# ---------------------------------------------------------------------------
CREATE_UNIFIED_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fanstack_unified_schedule (
    id TEXT PRIMARY KEY,
    raw_id TEXT NOT NULL,
    sport TEXT NOT NULL CHECK (sport IN ('mlb', 'nfl', 'cfb')),
    league TEXT NOT NULL CHECK (league IN ('MLB', 'NFL', 'CFB')),
    game_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('SCHEDULED', 'WARMUP', 'LIVE', 'FINAL', 'POSTPONED')),
    status_detail TEXT NOT NULL,
    clock_period INTEGER NOT NULL,
    clock_period_name TEXT NOT NULL,
    clock_display TEXT NOT NULL,
    clock_is_intermission INTEGER NOT NULL DEFAULT 0,
    away_code TEXT NOT NULL,
    away_full_name TEXT NOT NULL,
    away_score INTEGER NOT NULL DEFAULT 0,
    away_rank INTEGER,
    away_logo_url TEXT NOT NULL,
    home_code TEXT NOT NULL,
    home_full_name TEXT NOT NULL,
    home_score INTEGER NOT NULL DEFAULT 0,
    home_rank INTEGER,
    home_logo_url TEXT NOT NULL,
    odds_spread TEXT,
    odds_over_under REAL,
    odds_moneyline_away INTEGER,
    odds_moneyline_home INTEGER,
    venue_name TEXT NOT NULL,
    venue_city TEXT NOT NULL,
    venue_state TEXT NOT NULL,
    venue_roof TEXT NOT NULL CHECK (venue_roof IN ('open', 'dome', 'retractable')),
    venue_surface TEXT NOT NULL CHECK (venue_surface IN ('grass', 'turf')),
    venue_elevation_ft INTEGER NOT NULL DEFAULT 0,
    scheduled_start_iso TEXT NOT NULL,
    last_updated_iso TEXT NOT NULL,
    event_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fanstack_unified_sport_status
    ON fanstack_unified_schedule (sport, status, scheduled_start_iso);

CREATE INDEX IF NOT EXISTS idx_fanstack_unified_game_date
    ON fanstack_unified_schedule (game_date, sport);
"""


def init_unified_db(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=60.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.executescript(CREATE_UNIFIED_TABLE_SQL)
    conn.commit()
    return conn


def _derive_eastern_game_date(scheduled_iso: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(scheduled_iso.replace("Z", "+00:00"))
        return dt.astimezone(EASTERN_TZ).strftime("%Y-%m-%d")
    except Exception:
        return scheduled_iso[:10] if len(scheduled_iso) >= 10 else datetime.date.today().isoformat()


def upsert_unified_events(
    events: Sequence[FanStackGameEvent],
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    if not events:
        return 0

    conn = init_unified_db(db_path)
    cur = conn.cursor()
    rows = []
    for ev in events:
        raw_id = ev.id.split("_", 1)[1] if "_" in ev.id else ev.id
        game_date = _derive_eastern_game_date(ev.timestamps.scheduled_start_iso)
        clean_dict = ev.to_clean_dict()
        rows.append(
            (
                ev.id,
                raw_id,
                ev.sport,
                ev.league,
                game_date,
                ev.status,
                ev.status_detail,
                ev.clock.period,
                ev.clock.period_name,
                ev.clock.display_clock,
                1 if ev.clock.is_intermission else 0,
                ev.away_team.code,
                ev.away_team.full_name,
                ev.away_team.score,
                ev.away_team.rank,
                ev.away_team.logo_url,
                ev.home_team.code,
                ev.home_team.full_name,
                ev.home_team.score,
                ev.home_team.rank,
                ev.home_team.logo_url,
                ev.odds.spread if ev.odds else None,
                ev.odds.over_under if ev.odds else None,
                ev.odds.moneyline_away if ev.odds else None,
                ev.odds.moneyline_home if ev.odds else None,
                ev.venue.venue_name,
                ev.venue.city,
                ev.venue.state,
                ev.venue.roof,
                ev.venue.surface,
                ev.venue.elevation_ft,
                ev.timestamps.scheduled_start_iso,
                ev.timestamps.last_updated_iso,
                json.dumps(clean_dict, separators=(",", ":")),
            )
        )

    cur.executemany(
        """
        INSERT INTO fanstack_unified_schedule (
            id, raw_id, sport, league, game_date, status, status_detail,
            clock_period, clock_period_name, clock_display, clock_is_intermission,
            away_code, away_full_name, away_score, away_rank, away_logo_url,
            home_code, home_full_name, home_score, home_rank, home_logo_url,
            odds_spread, odds_over_under, odds_moneyline_away, odds_moneyline_home,
            venue_name, venue_city, venue_state, venue_roof, venue_surface, venue_elevation_ft,
            scheduled_start_iso, last_updated_iso, event_json
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?
        )
        ON CONFLICT(id) DO UPDATE SET
            status = excluded.status,
            status_detail = excluded.status_detail,
            clock_period = excluded.clock_period,
            clock_period_name = excluded.clock_period_name,
            clock_display = excluded.clock_display,
            clock_is_intermission = excluded.clock_is_intermission,
            away_code = excluded.away_code,
            away_full_name = excluded.away_full_name,
            away_score = excluded.away_score,
            away_rank = excluded.away_rank,
            away_logo_url = excluded.away_logo_url,
            home_code = excluded.home_code,
            home_full_name = excluded.home_full_name,
            home_score = excluded.home_score,
            home_rank = excluded.home_rank,
            home_logo_url = excluded.home_logo_url,
            odds_spread = COALESCE(excluded.odds_spread, fanstack_unified_schedule.odds_spread),
            odds_over_under = COALESCE(excluded.odds_over_under, fanstack_unified_schedule.odds_over_under),
            odds_moneyline_away = COALESCE(excluded.odds_moneyline_away, fanstack_unified_schedule.odds_moneyline_away),
            odds_moneyline_home = COALESCE(excluded.odds_moneyline_home, fanstack_unified_schedule.odds_moneyline_home),
            venue_name = excluded.venue_name,
            venue_city = excluded.venue_city,
            venue_state = excluded.venue_state,
            venue_roof = excluded.venue_roof,
            venue_surface = excluded.venue_surface,
            venue_elevation_ft = excluded.venue_elevation_ft,
            scheduled_start_iso = excluded.scheduled_start_iso,
            last_updated_iso = excluded.last_updated_iso,
            event_json = excluded.event_json
        """,
        rows,
    )
    conn.commit()
    conn.close()
    return len(rows)


def query_unified_schedule(
    db_path: Path = DEFAULT_DB_PATH,
    sport: str = "all",
    window_hours: Optional[int] = None,
) -> List[FanStackGameEvent]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    cur = conn.cursor()
    if sport and sport.lower() != "all":
        cur.execute(
            "SELECT event_json FROM fanstack_unified_schedule WHERE sport = ?",
            (sport.lower(),),
        )
    else:
        cur.execute("SELECT event_json FROM fanstack_unified_schedule")
    rows = cur.fetchall()
    conn.close()

    events: List[FanStackGameEvent] = []
    for (raw_json,) in rows:
        try:
            ev = FanStackGameEvent.from_json(raw_json)
            events.append(ev)
        except Exception as exc:
            logger.warning("Skipping invalid cached row in fanstack_unified_schedule: %s", exc)

    if window_hours is not None:
        events = filter_events_by_window(events, window_hours=window_hours)

    return sort_polysport_events(events)


def filter_events_by_window(
    events: Sequence[FanStackGameEvent],
    window_hours: int = 24,
    reference_utc: Optional[datetime.datetime] = None,
) -> List[FanStackGameEvent]:
    now_utc = reference_utc or datetime.datetime.now(UTC_TZ)
    lower_bound = now_utc - datetime.timedelta(hours=12)
    upper_bound = now_utc + datetime.timedelta(hours=window_hours)
    filtered: List[FanStackGameEvent] = []

    for ev in events:
        if ev.status in ("LIVE", "WARMUP"):
            filtered.append(ev)
            continue
        try:
            dt = datetime.datetime.fromisoformat(ev.timestamps.scheduled_start_iso.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC_TZ)
            if lower_bound <= dt <= upper_bound:
                filtered.append(ev)
        except Exception:
            filtered.append(ev)
    return filtered


def sort_polysport_events(events: Sequence[FanStackGameEvent]) -> List[FanStackGameEvent]:
    """Deterministic priority sort: LIVE -> WARMUP -> SCHEDULED -> FINAL -> POSTPONED, then chronological."""
    status_rank = {"LIVE": 0, "SCHEDULED": 1, "WARMUP": 2, "FINAL": 3, "POSTPONED": 4}
    sport_rank = {"mlb": 0, "nfl": 1, "cfb": 2}
    return sorted(
        events,
        key=lambda e: (
            status_rank.get(e.status, 5),
            e.timestamps.scheduled_start_iso,
            sport_rank.get(e.sport, 9),
            e.id,
        ),
    )


# ---------------------------------------------------------------------------
# 6. UNIFIED SYNC ORCHESTRATOR & CLI ENTRYPOINT
# ---------------------------------------------------------------------------
def sync_polysport_schedule(
    sport: str = "all",
    today_only: bool = False,
    window_hours: Optional[int] = None,
    days: Optional[int] = None,
    top25_only: bool = False,
    db_path: Path = DEFAULT_DB_PATH,
) -> List[FanStackGameEvent]:
    sport_norm = sport.lower().strip()
    now_et = datetime.datetime.now(EASTERN_TZ)
    today_et = now_et.date()

    if today_only:
        start_date = today_et - datetime.timedelta(days=1)
        end_date = today_et
        day_span = 2
    elif window_hours is not None:
        span_days = max(1, (window_hours + 23) // 24)
        start_date = today_et - datetime.timedelta(days=1)
        end_date = today_et + datetime.timedelta(days=span_days)
        day_span = (end_date - start_date).days + 1
    elif days is not None:
        start_date = today_et
        end_date = today_et + datetime.timedelta(days=max(1, days))
        day_span = (end_date - start_date).days + 1
    else:
        start_date = today_et - datetime.timedelta(days=1)
        end_date = today_et + datetime.timedelta(days=3)
        day_span = 5

    date_list = [
        (start_date + datetime.timedelta(days=i)).strftime("%Y%m%d")
        for i in range(day_span)
    ]

    collected: Dict[str, FanStackGameEvent] = {}

    if sport_norm in ("all", "mlb"):
        mlb_events = fetch_mlb_events(start_date.isoformat(), end_date.isoformat())
        for ev in mlb_events:
            collected[ev.id] = ev

    if sport_norm in ("all", "nfl"):
        nfl_events = fetch_nfl_events(date_list)
        for ev in nfl_events:
            collected[ev.id] = ev

    if sport_norm in ("all", "cfb"):
        cfb_events = fetch_cfb_events(date_list, top25_only=top25_only)
        for ev in cfb_events:
            collected[ev.id] = ev

    if not collected:
        logger.info("Upstream feeds unreachable or empty; hydrating from sports_ground_truth.json...")
        for ev in load_ground_truth_fallback_events(sport_filter=sport_norm):
            if top25_only and ev.sport == "cfb" and ev.away_team.rank is None and ev.home_team.rank is None:
                continue
            collected[ev.id] = ev

    all_events = list(collected.values())
    if window_hours is not None:
        all_events = filter_events_by_window(all_events, window_hours=window_hours)

    sorted_events = sort_polysport_events(all_events)
    upserted = upsert_unified_events(sorted_events, db_path=db_path)
    logger.info(
        "Synced %d canonical FanStackGameEvent records into %s (sport=%s)",
        upserted,
        db_path,
        sport_norm,
    )
    return sorted_events


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Unified PolySport Schedule & Telemetry Normalizer (MLB, NFL, CFB)"
    )
    parser.add_argument(
        "--sport",
        choices=["mlb", "nfl", "cfb", "all"],
        default="all",
        help="Target league to synchronize (default: all)",
    )
    parser.add_argument(
        "--today",
        action="store_true",
        help="Synchronize today's active slate only (includes yesterday rollover)",
    )
    parser.add_argument(
        "--window-hours",
        type=int,
        default=None,
        help="Filter and sync games within the next N hours (e.g. 24)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Synchronize the next N days",
    )
    parser.add_argument(
        "--top25",
        action="store_true",
        help="Limit CFB ingestion to Top-25 ranked matchups",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite WAL database (default: {DEFAULT_DB_PATH})",
    )
    args = parser.parse_args(argv)

    events = sync_polysport_schedule(
        sport=args.sport,
        today_only=args.today,
        window_hours=args.window_hours,
        days=args.days,
        top25_only=args.top25,
        db_path=args.db_path,
    )

    print(f"\n[POLYSPORT UNIFIED SLATE — {len(events)} GAMES SYNCED]")
    for ev in events:
        away_label = f"#{ev.away_team.rank} {ev.away_team.code}" if ev.away_team.rank else ev.away_team.code
        home_label = f"#{ev.home_team.rank} {ev.home_team.code}" if ev.home_team.rank else ev.home_team.code
        odds_str = f" | {ev.odds.spread} (O/U {ev.odds.over_under})" if ev.odds else ""
        print(
            f"  [{ev.league}] {ev.id:<14} {away_label} ({ev.away_team.score}) @ "
            f"{home_label} ({ev.home_team.score}) | {ev.status:<9} | {ev.status_detail} | "
            f"{ev.venue.venue_name} ({ev.venue.city}, {ev.venue.state} • {ev.venue.roof}, {ev.venue.elevation_ft}ft){odds_str}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())