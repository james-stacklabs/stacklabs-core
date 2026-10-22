"""
Sovereign OS: Enterprise Sports & Team Reference Router
Path: /home/james/stacklabs/scripts/routers/sports.py
Mount: app.include_router(sports_router)

Complies with The Pilot's Law of Full-Stack Delivery & FastAPI-First Architecture.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import sqlite3
import re
import datetime
from core.db import get_db

router = APIRouter(prefix="/api/sports", tags=["Sports Reference"])


class TeamResponse(BaseModel):
    team_abbr: str = Field(..., description="Canonical 2-4 character abbreviation")
    city: str
    name: str
    full_name: str
    sport: str
    league: str
    primary_color: str
    secondary_color: str
    synonyms: List[str]
    espn_slug: Optional[str] = None
    mlb_id: Optional[int] = None


class ResolveTeamRequest(BaseModel):
    query: str
    sport: Optional[str] = "MLB"


@router.get("/teams", response_model=List[TeamResponse])
async def list_sports_teams(
    sport: Optional[str] = Query(None, description="Filter by sport: MLB, CFB, NFL"),
    league: Optional[str] = Query(None, description="Filter by league/conference: AL, NL, SEC, etc.")
):
    """List all registered sports franchises with team colors, metadata, and aliases."""
    query = "SELECT * FROM sys_sports_team WHERE 1=1"
    params = []
    if sport:
        query += " AND UPPER(sport) = ?"
        params.append(sport.upper())
    if league:
        query += " AND UPPER(league) = ?"
        params.append(league.upper())
    query += " ORDER BY sport ASC, team_abbr ASC"

    try:
        with get_db(timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            results = []
            for r in rows:
                synonyms = []
                if r["synonyms_json"]:
                    try:
                        synonyms = json.loads(r["synonyms_json"])
                    except Exception:
                        synonyms = []
                results.append(TeamResponse(
                    team_abbr=r["team_abbr"],
                    city=r["city"],
                    name=r["name"],
                    full_name=r["full_name"],
                    sport=r["sport"],
                    league=r["league"],
                    primary_color=r["primary_color"],
                    secondary_color=r["secondary_color"],
                    synonyms=synonyms,
                    espn_slug=r["espn_slug"],
                    mlb_id=r["mlb_id"]
                ))
            return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")


@router.get("/teams/{abbr}", response_model=TeamResponse)
async def get_team_by_abbr(abbr: str, sport: Optional[str] = Query(None, description="Filter by sport: MLB, CFB, NFL")):
    """Retrieve metadata, hex branding, and aliases for a specific team abbreviation."""
    norm_abbr = abbr.strip().upper()
    try:
        with get_db(timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM sys_sports_team WHERE UPPER(team_abbr) = ?"
            params = [norm_abbr]
            if sport:
                query += " AND UPPER(sport) = ?"
                params.append(sport.upper())
            else:
                query += " ORDER BY CASE WHEN sport='MLB' THEN 1 WHEN sport='CFB' THEN 2 ELSE 3 END"
            query += " LIMIT 1"
            row = conn.execute(query, params).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Sports team '{abbr}' not found in sys_sports_team.")

            synonyms = []
            if row["synonyms_json"]:
                try:
                    synonyms = json.loads(row["synonyms_json"])
                except Exception:
                    synonyms = []

            return TeamResponse(
                team_abbr=row["team_abbr"],
                city=row["city"],
                name=row["name"],
                full_name=row["full_name"],
                sport=row["sport"],
                league=row["league"],
                primary_color=row["primary_color"],
                secondary_color=row["secondary_color"],
                synonyms=synonyms,
                espn_slug=row["espn_slug"],
                mlb_id=row["mlb_id"]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")


@router.post("/teams/resolve")
async def resolve_team_keyword(req: ResolveTeamRequest):
    """Dynamically resolves any keyword, city, or fan alias to a canonical team_abbr."""
    token = req.query.strip().lower()
    if not token:
        return {"resolved": False, "team_abbr": None}

    try:
        with get_db(timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            # 1. Exact match on abbreviation
            query1 = "SELECT * FROM sys_sports_team WHERE LOWER(team_abbr) = ?"
            params1 = [token]
            if req.sport:
                query1 += " AND UPPER(sport) = ?"
                params1.append(req.sport.upper())
            query1 += " LIMIT 1"
            row = conn.execute(query1, params1).fetchone()
            if row:
                return {"resolved": True, "team_abbr": row["team_abbr"], "team": dict(row)}

            # 2. Check all teams for synonym, name, or city match
            query2 = "SELECT * FROM sys_sports_team WHERE 1=1"
            params2 = []
            if req.sport:
                query2 += " AND UPPER(sport) = ?"
                params2.append(req.sport.upper())
            rows = conn.execute(query2, params2).fetchall()

            for r in rows:
                if token == r["name"].lower() or token == r["city"].lower() or token == r["full_name"].lower():
                    return {"resolved": True, "team_abbr": r["team_abbr"], "team": dict(r)}

                if r["synonyms_json"]:
                    try:
                        syns = [s.lower() for s in json.loads(r["synonyms_json"])]
                        if any(re.search(r'\b' + re.escape(s) + r'\b', token) or s == token for s in syns):
                            return {"resolved": True, "team_abbr": r["team_abbr"], "team": dict(r)}
                    except Exception:
                        continue

            return {"resolved": False, "team_abbr": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resolution failed: {str(e)}")


@router.get("/teams/{abbr}/ground_truth")
async def get_team_ground_truth(abbr: str, sport: Optional[str] = Query(None)):
    """Retrieve verified 2026 ground truth (active coaches, record, last game, roster) for a team."""
    norm_abbr = abbr.strip().upper()
    try:
        with get_db(timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row

            # 1. Fetch coaches
            coach_query = "SELECT role, coach_name, hired_date, notes FROM sys_sports_coaches WHERE UPPER(team_abbr) = ? AND is_active = 1"
            c_params = [norm_abbr]
            if sport:
                coach_query += " AND UPPER(sport) = ?"
                c_params.append(sport.upper())
            coach_rows = conn.execute(coach_query, c_params).fetchall()

            coaches_dict = {}
            for cr in coach_rows:
                coaches_dict[cr["role"]] = cr["coach_name"]

            # 2. Fetch standings
            stand_query = "SELECT sport, season, wins, losses, ties, streak, last_game_result, last_game_score FROM sys_sports_standings WHERE UPPER(team_abbr) = ?"
            s_params = [norm_abbr]
            if sport:
                stand_query += " AND UPPER(sport) = ?"
                s_params.append(sport.upper())
            stand_query += " ORDER BY season DESC LIMIT 1"
            stand_row = conn.execute(stand_query, s_params).fetchone()

            # 3. Fetch roster
            roster_query = "SELECT athlete_id, full_name, jersey_num, position, status, depth_chart_rank FROM sys_sports_roster WHERE UPPER(team_abbr) = ? AND status = 'ACTIVE' ORDER BY depth_chart_rank ASC"
            roster_rows = conn.execute(roster_query, [norm_abbr]).fetchall()
            roster_list = [dict(r) for r in roster_rows]

            # If not found in either coaches or standings, check sys_sports_team
            if not coach_rows and not stand_row:
                team_check = conn.execute("SELECT * FROM sys_sports_team WHERE UPPER(team_abbr) = ? LIMIT 1", [norm_abbr]).fetchone()
                if not team_check:
                    raise HTTPException(status_code=404, detail=f"Ground truth not found for sports team '{abbr}'.")

            wins = stand_row["wins"] if stand_row else 0
            losses = stand_row["losses"] if stand_row else 0
            ties = stand_row["ties"] if stand_row else 0
            streak = stand_row["streak"] if stand_row else ""
            last_result = stand_row["last_game_result"] if stand_row else ""
            last_score = stand_row["last_game_score"] if stand_row else ""
            season = stand_row["season"] if stand_row else 2026
            sport_val = stand_row["sport"] if stand_row else (sport or "NFL")

            record_str = f"{wins}-{losses}" + (f"-{ties}" if ties > 0 else "")

            return {
                "team_abbr": norm_abbr,
                "sport": sport_val,
                "season": season,
                "coaches": coaches_dict,
                "head_coach": coaches_dict.get("HC"),
                "offensive_coordinator": coaches_dict.get("OC"),
                "defensive_coordinator": coaches_dict.get("DC"),
                "standings": {
                    "wins": wins,
                    "losses": losses,
                    "ties": ties,
                    "streak": streak,
                    "record": record_str,
                    "last_result": last_result,
                    "last_game_result": last_result,
                    "last_game_score": last_score
                },
                "record": record_str,
                "last_game": last_result,
                "last_game_result": last_result,
                "roster": roster_list
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")


@router.get("/ground_truth/summary")
@router.get("/teams/ground_truth/summary")
async def get_sports_ground_truth_summary(sport: Optional[str] = Query(None)):
    """Retrieve complete coaching staff and standings matrix across all sports teams."""
    try:
        with get_db(timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row

            # Coaches
            c_query = "SELECT team_abbr, role, coach_name FROM sys_sports_coaches WHERE is_active = 1"
            c_params = []
            if sport:
                c_query += " AND UPPER(sport) = ?"
                c_params.append(sport.upper())
            c_rows = conn.execute(c_query, c_params).fetchall()

            coaches_matrix: Dict[str, Dict[str, str]] = {}
            for r in c_rows:
                t = r["team_abbr"]
                if t not in coaches_matrix:
                    coaches_matrix[t] = {}
                coaches_matrix[t][r["role"]] = r["coach_name"]

            # Standings
            s_query = "SELECT team_abbr, sport, season, wins, losses, ties, streak, last_game_result, last_game_score FROM sys_sports_standings WHERE season = 2026"
            s_params = []
            if sport:
                s_query += " AND UPPER(sport) = ?"
                s_params.append(sport.upper())
            s_rows = conn.execute(s_query, s_params).fetchall()

            standings_matrix: Dict[str, Dict[str, Any]] = {}
            for r in s_rows:
                t = r["team_abbr"]
                standings_matrix[t] = {
                    "sport": r["sport"],
                    "wins": r["wins"],
                    "losses": r["losses"],
                    "ties": r["ties"],
                    "record": f"{r['wins']}-{r['losses']}" + (f"-{r['ties']}" if r["ties"] > 0 else ""),
                    "streak": r["streak"] or "",
                    "last_result": r["last_game_result"] or "",
                    "last_game_result": r["last_game_result"] or "",
                    "last_score": r["last_game_score"] or ""
                }

            return {
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "season": 2026,
                "sport": sport or "ALL",
                "total_teams": len(standings_matrix),
                "coaches": coaches_matrix,
                "standings": standings_matrix
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")

