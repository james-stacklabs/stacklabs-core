"""
Sovereign OS: Room Roster Registry (Data Plane In-Memory Presence Cache)
Path: /home/james/stacklabs/scripts/core/roster_registry.py

Governed by WO0010160 & STD-0001 (Control Plane Persistence vs. Data Plane Ephemeral Presence).
Decouples Control Plane relational storage (m2m_persona_room in sovereign_now.db)
from Data Plane runtime lookups.
Provides O(1) in-memory presence lookups for live telemetry ingress,
message fanout relays, and multi-agent LLM commentator dispatchers.
"""

import os
import asyncio
import logging
from typing import Dict, Set, List, Optional

logger = logging.getLogger("RoomRosterRegistry")

class RoomRosterRegistry:
    """
    Thread-safe in-memory Active Roster Cache.
    Maintains ephemeral presence state across rooms without querying SQLite on hot paths.
    """
    _active_rosters: Dict[str, Set[str]] = {}  # room_id (str) -> set of lowercase persona_names
    _lock: Optional[asyncio.Lock] = None
    _hydrated_rooms: Set[str] = set()
    _fully_hydrated: bool = False

    @classmethod
    def _clean_persona(cls, persona: str) -> str:
        return str(persona).strip().lower().lstrip('@')

    @classmethod
    def get_lock(cls) -> asyncio.Lock:
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @classmethod
    def get_active_personas(cls, room_id: str) -> Set[str]:
        """
        O(1) thread-safe presence lookup.
        Strict Invariant: ZERO SQL queries on the live telemetry / chat hot path
        once hydrated.
        """
        r_id = str(room_id).strip()
        if not r_id:
            return set()

        if r_id not in cls._active_rosters and r_id not in cls._hydrated_rooms:
            # Cold-start room hydration
            cls.hydrate_from_db(r_id)

        return cls._active_rosters.get(r_id, set()).copy()

    @classmethod
    def set_roster(cls, room_id: str, personas: List[str]):
        """
        Atomically replace active room roster.
        """
        r_id = str(room_id).strip()
        if not r_id:
            return
        cleaned = {cls._clean_persona(p) for p in personas if p and cls._clean_persona(p)}
        cls._active_rosters[r_id] = cleaned
        cls._hydrated_rooms.add(r_id)

    @classmethod
    def add_persona(cls, room_id: str, persona: str):
        """
        Add a single advocate persona to active room presence.
        """
        r_id = str(room_id).strip()
        p = cls._clean_persona(persona)
        if not r_id or not p:
            return
        if r_id not in cls._active_rosters:
            cls._active_rosters[r_id] = set()
        cls._active_rosters[r_id].add(p)
        cls._hydrated_rooms.add(r_id)

    @classmethod
    def remove_persona(cls, room_id: str, persona: str):
        """
        Remove a single advocate persona from active room presence.
        """
        r_id = str(room_id).strip()
        p = cls._clean_persona(persona)
        if r_id in cls._active_rosters:
            cls._active_rosters[r_id].discard(p)

    @classmethod
    def clear_room(cls, room_id: str):
        """
        Clear all advocates from a room.
        """
        r_id = str(room_id).strip()
        if r_id in cls._active_rosters:
            cls._active_rosters[r_id] = set()
        cls._hydrated_rooms.add(r_id)

    @classmethod
    def get_all_rosters(cls) -> Dict[str, Set[str]]:
        """
        Return a snapshot copy of all active room rosters.
        """
        return {k: v.copy() for k, v in cls._active_rosters.items()}

    @classmethod
    def hydrate_from_db(cls, room_id: Optional[str] = None):
        """
        Control Plane cold-start read from m2m_persona_room.
        Hydrates in-memory cache once during boot or room transition.
        """
        try:
            try:
                from core.db import get_db, DB_PATH
            except ImportError:
                from scripts.core.db import get_db, DB_PATH
            if not os.path.exists(DB_PATH):
                return

            with get_db() as conn:
                if room_id:
                    r_id = str(room_id).strip()
                    rows = conn.execute("""
                        SELECT m.room, COALESCE(p.user_name, m.persona) as persona_name
                        FROM m2m_persona_room m
                        LEFT JOIN persona p ON (p.user_name = m.persona OR p.id = m.persona)
                        WHERE m.room = ?
                    """, (r_id,)).fetchall()

                    roster = {
                        cls._clean_persona(r["persona_name"])
                        for r in rows if r["persona_name"] and cls._clean_persona(r["persona_name"])
                    }
                    cls._active_rosters[r_id] = roster
                    cls._hydrated_rooms.add(r_id)
                else:
                    rows = conn.execute("""
                        SELECT m.room, COALESCE(p.user_name, m.persona) as persona_name
                        FROM m2m_persona_room m
                        LEFT JOIN persona p ON (p.user_name = m.persona OR p.id = m.persona)
                    """).fetchall()

                    new_rosters: Dict[str, Set[str]] = {}
                    for r in rows:
                        room_key = str(r["room"]).strip()
                        raw_name = r["persona_name"]
                        if raw_name:
                            p_name = cls._clean_persona(raw_name)
                            if p_name:
                                if room_key not in new_rosters:
                                    new_rosters[room_key] = set()
                                new_rosters[room_key].add(p_name)

                    cls._active_rosters = new_rosters
                    cls._hydrated_rooms = set(new_rosters.keys())
                    cls._fully_hydrated = True

        except Exception as e:
            logger.warning("[RoomRosterRegistry] Cold-start hydration non-fatal warning: %s", e)

# Auto-hydrate globally on module load
try:
    RoomRosterRegistry.hydrate_from_db()
except Exception:
    pass
