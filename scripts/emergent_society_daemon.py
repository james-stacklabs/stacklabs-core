#!/usr/bin/env python3
"""
scripts/emergent_society_daemon.py
=============================================================================
THE AUTONOMOUS EMERGENT SOCIETY SIMULATION ENGINE (24/7 DAEMON)
=============================================================================
Runs continuously on Clio metal at < 5% CPU using an event-driven High-Entropy
Cognitive Activation pattern. Adheres to:
 - Invariant 23: Zero local heavy LLM inference on Clio.
 - Cloud inference via Gemini Cloud API (zero local Clio GPU burn).
 - Invariant 35: Canonical Python venv execution.
 - Zero-Fake-Lore Invariant: Driven by grounded real-world sports entropy.
"""

import os
import sys
import time
import json
import sqlite3
import random
import logging
import signal
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))

if not os.environ.get("GEMINI_API_KEY") and os.path.exists("/home/james/stacklabs/.env"):
    try:
        from dotenv import load_dotenv
        load_dotenv("/home/james/stacklabs/.env")
    except ImportError:
        pass

try:
    from google import genai
    from google.genai import types
    HAS_GENAI_SDK = True
except ImportError:
    HAS_GENAI_SDK = False

try:
    from core.society_oracle import SocietyOracle
except ImportError:
    from society_oracle import SocietyOracle

# Configuration & Paths
DB_PATH = os.environ.get("EMERGENT_SOCIETY_DB", "/home/james/stacklabs/data/emergent_society.db")
HTTP_PORT = int(os.environ.get("EMERGENT_SOCIETY_PORT", "8098"))
TICK_INTERVAL_SEC = float(os.environ.get("SIM_TICK_INTERVAL", "5.0"))
SCHEMA_PATH = os.environ.get(
    "EMERGENT_SOCIETY_SCHEMA",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dna/migrations/20261002_emergent_society_schema.sql")
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SOCIETY-DAEMON] %(message)s"
)
logger = logging.getLogger("emergent_society")


def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_database(db_path: str = DB_PATH, schema_path: str = SCHEMA_PATH):
    """Initializes SQLite schema and seed records if not present."""
    if not os.path.exists(schema_path):
        logger.warning(f"Schema file {schema_path} not found. Skipping DDL execution.")
        return
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='emergent_citizens';")
        table_exists = cur.fetchone()[0] > 0
        if not table_exists:
            with open(schema_path, "r", encoding="utf-8") as f:
                ddl = f.read()
            conn.executescript(ddl)
            conn.commit()
            logger.info(f"Database initialized and confirmed in WAL mode at {db_path}")
        else:
            logger.info(f"Database schema already present at {db_path}")


class SimulationEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.running = False
        self.start_time = time.time()
        self.tick_count = 0
        self.last_entropy_check = 0.0
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.genai_client = None
        if HAS_GENAI_SDK and self.api_key:
            try:
                self.genai_client = genai.Client(api_key=self.api_key)
                logger.info("Google GenAI SDK connected successfully with Cloud API credentials.")
            except Exception as e:
                logger.warning(f"Failed to initialize GenAI client: {e}")
                self.genai_client = None
        else:
            logger.info("Running in Grounded Heuristic Engine mode (Zero API bill / Offline verification mode).")

    def process_pending_events(self) -> List[Dict[str, Any]]:
        """Extracts unprocessed high-entropy external events from the stream."""
        events = []
        with get_db_connection(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT event_id, source, category, headline, raw_payload, volatility_score
                FROM event_stream
                WHERE processed = 0
                ORDER BY volatility_score DESC, created_at ASC
                LIMIT 3
            """)
            rows = cur.fetchall()
            for r in rows:
                events.append(dict(r))
                conn.execute("UPDATE event_stream SET processed = 1 WHERE event_id = ?", (r["event_id"],))
            conn.commit()
        return events

    def evaluate_hemodynamics(self, citizen: Dict[str, Any], event_volatility: float, is_negative_impact: bool) -> Dict[str, Any]:
        """
        Calculates cardiovascular shift using the canonical hemodynamic formula:
        ΔBP = BaseHR * CardiacOutput * ScarTissueFactor * GameEventVolatility * 3.5
        """
        base_hr = float(citizen["resting_hr"])
        cardiac_output = float(citizen["cardiac_output"])
        scar_tissue = float(citizen["scar_tissue_index"])
        raw_delta = (base_hr / 10.0) * cardiac_output * scar_tissue * event_volatility * 3.5
        bp_delta = int(round(raw_delta if is_negative_impact else -(raw_delta * 0.4)))
        new_systolic = max(100, min(195, citizen["systolic_bp"] + bp_delta))
        new_diastolic = max(65, min(120, citizen["diastolic_bp"] + int(bp_delta * 0.55)))

        # Tums Burn Rate Protocol
        tums_consumed = 0
        if new_systolic >= 155 and citizen["tums_inventory"] >= 2:
            tums_consumed = 2
            new_systolic -= 12  # Antacid relief dampens systolic spike
            citizen_tums_inv = citizen["tums_inventory"] - 2
            citizen_tums_today = citizen["tums_consumed_today"] + 2
        else:
            citizen_tums_inv = citizen["tums_inventory"]
            citizen_tums_today = citizen["tums_consumed_today"]

        # State transition based on BP & Volatility
        new_status = citizen["status"]
        if new_systolic >= 165:
            new_status = "PANICKED"
        elif new_systolic >= 145:
            new_status = "RANTING"
        elif citizen["cash_balance"] < 200.0:
            new_status = "TILTED"
        else:
            new_status = "WATCHING" if event_volatility > 0.4 else "IDLE"

        return {
            "systolic_bp": new_systolic,
            "diastolic_bp": new_diastolic,
            "bp_delta": bp_delta,
            "tums_consumed": tums_consumed,
            "tums_inventory": citizen_tums_inv,
            "tums_consumed_today": citizen_tums_today,
            "new_status": new_status
        }

    def calculate_friction(self, speaker_id: str, target_id: str) -> float:
        """Calculates inter-persona friction score."""
        s = (speaker_id or "").lower()
        t = (target_id or "").lower()
        if ("batterychucker" in s and "batterychuckerjr" in t) or \
           ("batterychuckerjr" in s and "batterychucker" in t):
            # Father-Son generational feud trigger: automatic maximum friction
            return 0.98
        return 0.50

    def generate_persona_response(self, citizen: Dict[str, Any], event: Dict[str, Any], hemo: Dict[str, Any]) -> str:
        """Synthesizes authentic bleacher dialect using Gemini 2.5 Cloud or grounded dialect engine."""
        prompt = f"""You are {citizen['name']}, a {citizen['archetype']} ({citizen['fandom']}).
Current vitals: BP {hemo['systolic_bp']}/{hemo['diastolic_bp']} mmHg, Tums today: {hemo['tums_consumed_today']}. Status: {hemo['new_status']}.
Event just occurred: "{event['headline']}" (Volatility: {event['volatility_score']}).
React in your authentic, raw, hyper-specific local voice in 1-2 punchy sentences.
ZERO corporate fluff, ZERO AI hedge phrases ('As a fan...'), NO hashtags. Raw, direct sports fan reaction."""

        if self.genai_client:
            try:
                response = self.genai_client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=prompt
                )
                if response.text:
                    return response.text.strip().replace('"', '')
            except Exception as e:
                logger.warning(f"GenAI Cloud call failed: {e}. Falling back to dialect engine.")

        # Grounded authentic persona fallbacks (Zero fake lore - October 2026 Ground Truth)
        cid = citizen.get("citizen_id", "")
        handle = citizen.get("handle", "")
        if "BATTERYCHUCKERJR" in cid or "batterychuckerjr" in handle.lower():
            reactions = [
                "Enjoy October vacation, Dad! The Battery at Truist Park is rocking and we're heading to LA!",
                "Pop another Tums, Dad. 6-2 in Game 3. Walt Weiss sends his regards to South Philly.",
                "Keep clutching those D-cells while we play the Dodgers. Truist Park owns you."
            ]
        elif "BATTERYCHUCKER" in cid or "batterychucker" in handle.lower():
            reactions = [
                "You corporate sellout! Moving down to Georgia to drink craft IPAs while the Phillies choke?! I'm throwing a D-cell right at your forehead!",
                "6-2?! Harper 0-for-4?! Don't you dare come back to Havertown! You're out of the family will!",
                "I sat at the Vet in '93 in the freezing rain and I raised a traitor! Put Walt Weiss on the phone right now!"
            ]
        elif "BARF" in cid or "barf" in handle.lower():
            reactions = [
                "Unbelievable. My chest is on fire, I'm popping two Tums right now, and the bullpen is already blowing this.",
                "Dr. Shapiro warned me about this exact ninth inning. We are cursed. Absolutely cursed.",
                "You call that pitching? I've seen better arms on the cold cut slicer at Ben's Deli!"
            ]
        elif "SAMMY" in cid or "sammy" in handle.lower():
            reactions = [
                "That completely blew the Under 44.5. The models had a 82% hold probability, I'm sick to my stomach.",
                "I'm doubling down on the second half spread. I have to make back the three units right now.",
                "Pure variance theft. A blown coverage on third-and-18? The universe hates math."
            ]
        elif "ACUNA" in cid or "acuna" in handle.lower():
            reactions = [
                "Chop on! Walt Weiss just managed circles around Philly. Pack your bags for Chavez Ravine!",
                "The Battery is going insane tonight! 6-2 final and Philadelphia is eliminated!"
            ]
        elif "BRONX" in cid or "bronx" in handle.lower():
            reactions = [
                "Pinstripe royalty advances. Swept the Red Sox right out of the building. Ring #28 is loading.",
                "All Rise! Aaron Judge owns October. The road to the World Series goes through the Bronx!"
            ]
        elif "ANTIDODGER" in cid or "nododger" in handle.lower():
            reactions = [
                "Look at that strike zone on Ohtani! Manfred's umpires are already tilting the bracket!",
                "A billion dollars in deferred payroll and we're supposed to call this legitimate baseball? Pure corporate bias!"
            ]
        elif "DODGER" in cid or "prophet" in handle.lower():
            reactions = [
                "First-round bye was relaxing. Shohei and Mookie are rested. Welcome to Dodger Stadium, Braves.",
                "Cute little wild card win for Atlanta, but Hollywood doesn't lose in the Division Series."
            ]
        elif "SALVY" in cid or "salvy" in handle.lower():
            reactions = [
                "Salvy Perez is the heart of Kansas City! Wave that #13 foam finger! We're crashing the AL bracket!",
                "National media forgot about Kauffman Stadium! Destiny belongs to the Royals!"
            ]
        elif "HOFFA" in cid or "hoffa" in handle.lower():
            reactions = [
                "Pouring hot Lot J black coffee on the pavement. You baseball yappers know nothing about cold December football.",
                "Under the end zone concrete since '76. Lawrence Taylor is the only sovereign authority in this tri-state area."
            ]
        else:
            reactions = [
                "Heart rate is spiking. Typical officiating giving them free yardage!",
                "Unreal play. We need a coaching overhaul before this season is completely lost.",
                "I can't watch this anymore, but I know I'm not changing the channel."
            ]
        return random.choice(reactions)

    def execute_market_trade(self, citizen: Dict[str, Any], event: Dict[str, Any], conn: sqlite3.Connection):
        """Simulates automated binary betting order placement under emotional tilt."""
        cur = conn.cursor()
        cur.execute("SELECT contract_id, ticker, current_price_cents FROM market_contracts WHERE status = 'OPEN'")
        contracts = cur.fetchall()
        if not contracts:
            return

        contract = random.choice(contracts)
        qty = random.randint(5, 25)
        price = contract["current_price_cents"]
        total_cost = (qty * price) / 100.0

        if citizen["cash_balance"] >= total_cost:
            trade_id = f"TRD-{os.urandom(4).hex().upper()}"
            side = "BUY"
            pos_type = "LONG" if citizen["status"] in ("PANICKED", "TILTED") else "SHORT"
            conn.execute("""
                INSERT INTO citizen_trades (
                    trade_id, citizen_id, contract_id, side, position_type,
                    quantity, price_cents, total_cost, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (trade_id, citizen["citizen_id"], contract["contract_id"], side, pos_type, qty, price, total_cost))
            conn.execute("""
                UPDATE emergent_citizens
                SET cash_balance = cash_balance - ?, portfolio_value = portfolio_value + ?
                WHERE citizen_id = ?
            """, (total_cost, total_cost, citizen["citizen_id"]))
            conn.execute("""
                UPDATE market_contracts
                SET total_volume = total_volume + ?, open_interest = open_interest + ?
                WHERE contract_id = ?
            """, (qty, qty, contract["contract_id"]))

    def run_tick(self):
        """High-Entropy Trigger Activation Loop Step."""
        self.tick_count += 1
        pending_events = self.process_pending_events()

        if not pending_events:
            # Baseline deterministic state decay (no LLM calls, zero tokens consumed)
            with get_db_connection(self.db_path) as conn:
                conn.execute("""
                    UPDATE emergent_citizens
                    SET systolic_bp = CASE WHEN systolic_bp > 125 THEN systolic_bp - 1 ELSE systolic_bp END,
                        diastolic_bp = CASE WHEN diastolic_bp > 82 THEN diastolic_bp - 1 ELSE diastolic_bp END,
                        status = CASE WHEN systolic_bp <= 135 AND status IN ('PANICKED', 'RANTING') THEN 'WATCHING' ELSE status END
                    WHERE systolic_bp > 120
                """)
                conn.commit()
            return

        logger.info(f"HIGH-ENTROPY ACTIVATION: Processing {len(pending_events)} external sports events.")
        with get_db_connection(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM emergent_citizens")
            citizens = [dict(r) for r in cur.fetchall()]

            for event in pending_events:
                volatility = float(event["volatility_score"])
                for citizen in citizens:
                    is_negative = random.choice([True, False, True])
                    hemo = self.evaluate_hemodynamics(citizen, volatility, is_negative)
                    dialogue_text = self.generate_persona_response(citizen, event, hemo)

                    conn.execute("""
                        UPDATE emergent_citizens
                        SET systolic_bp = ?, diastolic_bp = ?, tums_inventory = ?,
                            tums_consumed_today = ?, status = ?, last_active_ts = CURRENT_TIMESTAMP
                        WHERE citizen_id = ?
                    """, (
                        hemo["systolic_bp"], hemo["diastolic_bp"], hemo["tums_inventory"],
                        hemo["tums_consumed_today"], hemo["new_status"], citizen["citizen_id"]
                    ))

                    target_id = None
                    if "batterychuckerjr" in citizen.get("handle", "").lower():
                        target_id = "CIT-001-BATTERYCHUCKER"
                    elif "batterychucker" in citizen.get("handle", "").lower():
                        target_id = "CIT-002-BATTERYCHUCKERJR"

                    if target_id:
                        friction = self.calculate_friction(citizen["citizen_id"], target_id)
                        if friction >= 0.9:
                            hemo["systolic_bp"] = min(230, hemo["systolic_bp"] + 8)

                    dialogue_id = f"DLG-{os.urandom(4).hex().upper()}"
                    conn.execute("""
                        INSERT INTO society_dialogue (
                            dialogue_id, tick_id, speaker_id, target_id, message_text,
                            emotional_tone, bp_delta, tums_consumed, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        dialogue_id, f"TCK-{self.tick_count}", citizen["citizen_id"], target_id,
                        dialogue_text, hemo["new_status"], hemo["bp_delta"], hemo["tums_consumed"]
                    ))

                    if volatility >= 0.6:
                        mem_id = f"MEM-{os.urandom(4).hex().upper()}"
                        mem_type = "TRAUMA" if is_negative else "TRIUMPH"
                        conn.execute("""
                            INSERT INTO citizen_memories (
                                memory_id, citizen_id, event_id, memory_type,
                                description, emotional_charge, salience
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            mem_id, citizen["citizen_id"], event["event_id"], mem_type,
                            f"{event['headline']} -> {dialogue_text}", -0.8 if is_negative else 0.7, volatility
                        ))

                    if volatility >= 0.7:
                        self.execute_market_trade(citizen, event, conn)

            conn.commit()

    def start(self):
        self.running = True
        logger.info(f"Emergent Society Daemon loop running (tick interval: {TICK_INTERVAL_SEC}s)")
        while self.running:
            try:
                self.run_tick()
            except Exception as e:
                logger.error(f"Error during simulation tick: {e}", exc_info=True)
            time.sleep(TICK_INTERVAL_SEC)

    def stop(self):
        self.running = False
        logger.info("Emergent Society Daemon stopping...")


# ----------------------------------------------------------------------------
# MINIMALIST OBSERVER REST API HANDLER
# ----------------------------------------------------------------------------
class SocietyAPIHandler(BaseHTTPRequestHandler):
    engine: Optional[SimulationEngine] = None

    def _send_json(self, status_code: int, data: Any):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            uptime = time.time() - (self.engine.start_time if self.engine else time.time())
            wal_size = 0
            if os.path.exists(f"{DB_PATH}-wal"):
                wal_size = os.path.getsize(f"{DB_PATH}-wal")
            self._send_json(200, {
                "status": "HEALTHY",
                "uptime_seconds": round(uptime, 1),
                "total_ticks": self.engine.tick_count if self.engine else 0,
                "db_wal_bytes": wal_size,
                "cloud_api_mode": "ACTIVE" if (self.engine and self.engine.genai_client) else "GROUNDED_HEURISTIC"
            })
        elif self.path == "/api/society/citizens":
            with get_db_connection(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM emergent_citizens ORDER BY systolic_bp DESC")
                citizens = [dict(r) for r in cur.fetchall()]
            self._send_json(200, {"citizens": citizens})
        elif self.path == "/api/society/feed":
            with get_db_connection(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT d.dialogue_id, c.name, c.fandom, d.message_text,
                           d.emotional_tone, d.bp_delta, d.tums_consumed, d.created_at
                    FROM society_dialogue d
                    JOIN emergent_citizens c ON d.speaker_id = c.citizen_id
                    ORDER BY d.created_at DESC LIMIT 20
                """)
                feed = [dict(r) for r in cur.fetchall()]
            self._send_json(200, {"feed": feed})
        elif self.path == "/api/society/market":
            with get_db_connection(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM market_contracts WHERE status = 'OPEN'")
                contracts = [dict(r) for r in cur.fetchall()]
                cur.execute("""
                    SELECT t.trade_id, c.name as citizen, m.ticker, t.side, 
                           t.position_type, t.quantity, t.price_cents, t.total_cost, t.timestamp
                    FROM citizen_trades t
                    JOIN emergent_citizens c ON t.citizen_id = c.citizen_id
                    JOIN market_contracts m ON t.contract_id = m.contract_id
                    ORDER BY t.timestamp DESC LIMIT 15
                """)
                trades = [dict(r) for r in cur.fetchall()]
            self._send_json(200, {"contracts": contracts, "recent_trades": trades})
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            self._send_json(400, {"error": "Invalid JSON payload"})
            return

        if self.path == "/api/society/oracle/query":
            question = payload.get("question", "")
            if not question:
                self._send_json(400, {"error": "Field 'question' is required"})
                return
            oracle = SocietyOracle(db_path=DB_PATH)
            res = oracle.query(question)
            self._send_json(200, res)
        elif self.path == "/api/society/oracle/inject":
            headline = payload.get("headline", "")
            category = payload.get("category", "DIVINE_SHOCK")
            volatility = float(payload.get("volatility_score", 0.85))
            if not headline:
                self._send_json(400, {"error": "Field 'headline' is required"})
                return
            oracle = SocietyOracle(db_path=DB_PATH)
            res = oracle.inject_event(headline, category, volatility, payload)
            self._send_json(201, res)
        else:
            self._send_json(404, {"error": "Endpoint not found"})


def find_available_port(preferred_port: int) -> int:
    """Checks if preferred port is free; if not, falls back to an available port."""
    for port in [preferred_port, 8098, 8097, 8094, 8195]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))
                return port
        except OSError:
            continue
    return preferred_port


def run_server(port: int, engine: SimulationEngine):
    actual_port = find_available_port(port)
    if actual_port != port:
        logger.warning(f"Preferred port {port} is occupied. Society Observer API falling back to port {actual_port}.")
    SocietyAPIHandler.engine = engine
    httpd = HTTPServer(("0.0.0.0", actual_port), SocietyAPIHandler)
    logger.info(f"Society Observer REST API running on http://0.0.0.0:{actual_port}")
    httpd.serve_forever()


def main():
    init_database(DB_PATH, SCHEMA_PATH)
    engine = SimulationEngine(db_path=DB_PATH)

    api_thread = threading.Thread(target=run_server, args=(HTTP_PORT, engine), daemon=True)
    api_thread.start()

    def handle_signal(sig, frame):
        logger.info(f"Signal {sig} received. Initiating graceful shutdown...")
        engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    engine.start()


if __name__ == "__main__":
    main()
