#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Synapse - The Sub-Millisecond Nervous Bus
Lock-free circular shared-memory ring buffer (/dev/shm) and atomic queue dispatcher.
Target: Clio (100.91.229.87) | Python 3.12 (.venv)
"""

import os
import sys
import time
import mmap
import struct
import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

_repo_root = "/home/james/stacklabs"
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from scripts.domain_normalizer import get_normalizer
normalizer = get_normalizer()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [Synapse] %(message)s")
logger = logging.getLogger("synapse_bus")

SHM_FILE = "/dev/shm/synapse_ring.raw"
HEADER_FORMAT = "<QQII"  # head (uint64), tail (uint64), slot_size (uint32), capacity (uint32)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
SLOT_SIZE = 4096
SLOT_CAPACITY = 16384  # 64MB Total Buffer (4096 * 16384)
TOTAL_SIZE = 67108896  # Exact 67,108,896 bytes as specified in Q4

QUEUE_STAGING_DIR = "/home/james/stacklabs/queue/.staging"
QUEUE_INCOMING_DIR = "/home/james/stacklabs/queue/incoming"
TELEMETRY_DIR = "/home/james/stacklabs/data/telemetry"
FRONTEND_INDEX = "/home/james/stacklabs/frontend/index.html"

os.makedirs(QUEUE_STAGING_DIR, exist_ok=True)
os.makedirs(QUEUE_INCOMING_DIR, exist_ok=True)
os.makedirs(TELEMETRY_DIR, exist_ok=True)


class SynapseMemoryRing:
    def __init__(self, filepath: str = SHM_FILE):
        self.filepath = filepath
        self.total_size = TOTAL_SIZE
        self._init_shm()

    def _init_shm(self):
        is_new = not os.path.exists(self.filepath) or os.path.getsize(self.filepath) != self.total_size
        if is_new:
            logger.info(f"Allocating 64MB volatile ring buffer in {self.filepath}...")
            with open(self.filepath, "wb") as f:
                f.seek(self.total_size - 1)
                f.write(b"\0")

        self.file_obj = open(self.filepath, "r+b")
        self.mm = mmap.mmap(self.file_obj.fileno(), self.total_size)

        if is_new:
            struct.pack_into(HEADER_FORMAT, self.mm, 0, 0, 0, SLOT_SIZE, SLOT_CAPACITY)
            logger.info("Ring buffer initialized with zeroed head/tail pointers.")

    def write_frame(self, source: str, raw_payload: str) -> tuple[int, float]:
        t0 = time.perf_counter()
        head, tail, slot_sz, cap = struct.unpack_from(HEADER_FORMAT, self.mm, 0)

        next_head = (head + 1) % cap
        if next_head == tail:
            tail = (tail + 1) % cap
            struct.pack_into("<Q", self.mm, 8, tail)

        slot_offset = HEADER_SIZE + (head * SLOT_SIZE)
        ts_ns = time.time_ns()

        data_bytes = raw_payload.encode("utf-8")
        if len(data_bytes) > (SLOT_SIZE - 64):
            data_bytes = data_bytes[:SLOT_SIZE - 64]

        source_fixed = source.encode("utf-8")[:16].ljust(16, b"\0")
        slot_header = struct.pack("<QI16s", ts_ns, len(data_bytes), source_fixed)

        self.mm[slot_offset:slot_offset + len(slot_header)] = slot_header
        self.mm[slot_offset + 28:slot_offset + 28 + len(data_bytes)] = data_bytes

        struct.pack_into("<Q", self.mm, 0, next_head)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return head, elapsed_ms

    def read_metrics(self) -> dict:
        head, tail, slot_sz, cap = struct.unpack_from(HEADER_FORMAT, self.mm, 0)
        used_slots = (head - tail + cap) % cap
        saturation_pct = (used_slots / cap) * 100.0
        return {
            "head": head,
            "tail": tail,
            "used_slots": used_slots,
            "capacity": cap,
            "saturation_pct": round(saturation_pct, 2)
        }

    def close(self):
        self.mm.close()
        self.file_obj.close()


ring = SynapseMemoryRing()

app = FastAPI(title="StackLabs Synapse Bus", version="1.0.0")

from scripts.blueprints.public_pulse import router as public_pulse_router
app.include_router(public_pulse_router)

try:
    from scripts.blueprints.faas_vfs_telemetry import router as vfs_telemetry_router, faas_lexicon_router
    app.include_router(vfs_telemetry_router)
    app.include_router(faas_lexicon_router)
    logger.info("Successfully mounted FaaS VFS Telemetry Blueprint onto Synapse bus (/api/vfs_telemetry)")
except Exception as e:
    logger.error(f"Failed to mount FaaS VFS Telemetry blueprint: {e}")

try:
    from scripts.blueprints.kitchen_bp import router as kitchen_router
    app.include_router(kitchen_router)
    logger.info("Successfully mounted Kitchen BLE Blueprint onto Synapse bus (/kitchen)")
except Exception as e:
    logger.error(f"Failed to mount kitchen blueprint: {e}")

try:
    from scripts.blueprints.audio_bp import router as audio_router
    app.include_router(audio_router, prefix="/audio")
    logger.info("Successfully mounted Audio Media Blueprint onto Synapse bus (/audio)")
except Exception as e:
    logger.error(f"Failed to mount audio blueprint: {e}")

try:
    from scripts.blueprints.stream_sniper_bp import stream_sniper_bp
    app.include_router(stream_sniper_bp)
    logger.info("Successfully mounted Stream Sniper Studio Blueprint onto Synapse bus (/cockpit/sniper, /sniper, /snipes)")
except Exception as e:
    logger.error(f"Failed to mount stream_sniper_bp on synapse_bus: {e}")


class IngestRequest(BaseModel):
    source: str = Field(default="voice_steno", description="Ingress channel identifier")
    payload: str = Field(..., description="Raw text or telemetry frame")


class StagedOrderResponse(BaseModel):
    ticket_id: str
    status: str
    slot_id: int
    write_latency_ms: float
    staged_path: str


@app.post("/api/v1/synapse/ingest", response_model=StagedOrderResponse)
def ingest_signal(req: IngestRequest):
    normalized_payload = normalizer.normalize_sentence(req.payload)
    slot_id, latency_ms = ring.write_frame(req.source, normalized_payload)

    ticket_id = f"WO_{int(time.time())}_{os.urandom(2).hex().upper()}"
    staging_file = os.path.join(QUEUE_STAGING_DIR, f"{ticket_id}.tmp")
    final_file = os.path.join(QUEUE_INCOMING_DIR, f"{ticket_id}.md")

    work_order_markdown = f"""# {ticket_id}: SYNAPSE AUTOMATED EXECUTION ORDER
> **Ticket ID**: `{ticket_id}`
> **Classification**: Work Order (`WO`)
> **Target Node**: Clio Dedicated Linux Host (`clio` / `100.91.229.87`)
> **Assigned Runner**: Aggie (`agy` via `clio_queue_watcher.py`)
> **Ingress Source**: {req.source}
> **Ingest Slot**: #{slot_id} (Latency: {latency_ms:.3f}ms)
> **Author**: James Carroll (Pilot) & Cockpit Architect
> **Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}
---
## 🎯 1. QUARTER 1: PROBLEM DEFINITION & SPECIFICATION
{normalized_payload.strip()}
## 🛠️ 2. QUARTER 2: IMPLEMENTATION MECHANICS & CODE
# Drop-in production code compiled from intent
## 🧪 3. QUARTER 3: EXECUTION ON HOST
/home/james/stacklabs/.venv/bin/python3 -m py_compile /home/james/stacklabs/scripts/*.py
## 📋 4. QUARTER 4: VERIFICATION & DEFINITION OF DONE
curl -s -I http://127.0.0.1:8088/health | grep "200 OK"
"""
    with open(staging_file, "w", encoding="utf-8") as f:
        f.write(work_order_markdown)
        f.flush()
        os.fsync(f.fileno())

    os.rename(staging_file, final_file)

    return StagedOrderResponse(
        ticket_id=ticket_id,
        status="STAGED_ATOMIC",
        slot_id=slot_id,
        write_latency_ms=round(latency_ms, 3),
        staged_path=final_file
    )


@app.get("/api/v1/synapse/vitals")
def get_ring_vitals():
    return ring.read_metrics()


@app.get("/health")
def health_check():
    return {"status": "HEALTHY", "node": "clio", "ip": "100.91.229.87"}


if os.path.exists(TELEMETRY_DIR):
    app.mount("/data/telemetry", StaticFiles(directory=TELEMETRY_DIR), name="telemetry")


@app.api_route("/", methods=["GET", "HEAD", "POST"])
async def serve_index(request: Request):
    host = (request.headers.get("host") or "").lower()
    if host.startswith("drop.") or "drop" in request.query_params:
        if "wsgi_handler" in globals() and wsgi_handler:
            await wsgi_handler(request.scope, request.receive, request._send)
            return _WSGIProxyResponse()
    return RedirectResponse(url="/cockpit", status_code=307)


@app.api_route("/cockpit", methods=["GET", "HEAD"])
@app.api_route("/cockpit/", methods=["GET", "HEAD"])
def serve_unified_cockpit():
    cockpit_tpl = Path("/home/james/stacklabs/scripts/templates/cockpit.html")
    content = cockpit_tpl.read_text(encoding="utf-8") if cockpit_tpl.exists() else ""
    return HTMLResponse(
        content=content,
        headers={
            "X-Cockpit-Nav": "Cockpit Hub, Drive Sync, Stream Sniper, Comms Search, Swanson Crawl, Vault Explorer",
            "X-Stream-Sniper-Node": "/cockpit/sniper"
        }
    )


class CockpitStageRequest(BaseModel):
    content: str
    title: Optional[str] = ""


class CockpitStageResponse(BaseModel):
    status: str
    ticket_id: str
    filename: str
    path: str


@app.post("/api/cockpit/stage_work_order", response_model=CockpitStageResponse)
def stage_work_order_atomic(req: CockpitStageRequest):
    content = req.content.strip()
    user_title = (req.title or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Work Order content cannot be empty")

    ticket_id = None
    if user_title:
        m_title = re.search(r'\b((?:WO|STRY|INC|DFCT|ENHC|REQ)\d+)\b', user_title, re.IGNORECASE)
        if m_title:
            ticket_id = m_title.group(1).upper()

    if not ticket_id:
        m_id = re.search(r'(?:WORK[\s_\-]*ORDER|TICKET|TASK|WO)[\s:_\-]*([A-Z0-9]+)', content, re.IGNORECASE)
        if m_id:
            val = m_id.group(1).upper()
            if re.match(r'^WO\d+', val):
                ticket_id = val

    if not ticket_id:
        m_id2 = re.search(r'\b(WO\d{4,8})\b', content, re.IGNORECASE)
        if m_id2:
            ticket_id = m_id2.group(1).upper()

    if not ticket_id:
        db_path = "/home/james/stacklabs/dna/sovereign_now.db"
        try:
            conn = sqlite3.connect(db_path, timeout=1.0)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT current_number, digits, prefix FROM sys_number WHERE category = 'WO'")
            row = cur.fetchone()
            if row:
                curr_val = int(row['current_number'])
                next_val = curr_val + 1
                digits = row['digits'] or 7
                prefix = row['prefix'] or 'WO'
                ticket_id = f"{prefix}{str(next_val).zfill(digits)}"
                cur.execute("UPDATE sys_number SET current_number = ?, sys_updated_on = datetime('now') WHERE category = 'WO'", (next_val,))
                conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Error querying sys_number from DB: {e}")

    if not ticket_id:
        ticket_id = f"WO00{int(time.time())}"

    slug = ""
    if user_title:
        cleaned = re.sub(r'^(?:WORK[\s_\-]*ORDER|TICKET|TASK|WO\d*|WO)(?:[\s:_\-]+|$)', '', user_title, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'[\-_]STAGE$', '', cleaned, flags=re.IGNORECASE).strip()
        slug = re.sub(r'[^A-Za-z0-9]+', '-', cleaned).strip('-').upper()[:50]

    if not slug:
        m_slug = re.search(r'#\s*WORK\s*ORDER:\s*([A-Za-z0-9_\-]+)', content, re.IGNORECASE)
        if m_slug:
            slug = m_slug.group(1).strip().upper()
            slug = re.sub(r'^WO\d+[\-_]*', '', slug)[:50]

    if not slug:
        first_line = content.split('\n')[0]
        cleaned = re.sub(r'^[#\s\-*]+', '', first_line).strip()
        cleaned = re.sub(r'^(?:WORK[\s_\-]*ORDER|TICKET|TASK|WO\d*|WO)(?:[\s:_\-]+|$)', '', cleaned, flags=re.IGNORECASE).strip()
        slug = re.sub(r'[^A-Za-z0-9]+', '-', cleaned).strip('-').upper()[:50]

    if not slug:
        slug = "UNTITLED-WORK-ORDER"

    filename = f"{ticket_id}-{slug}.md" if slug else f"{ticket_id}.md"
    staging_file = os.path.join(QUEUE_STAGING_DIR, f"{ticket_id}_{os.urandom(4).hex()}.tmp")
    final_file = os.path.join(QUEUE_INCOMING_DIR, filename)

    with open(staging_file, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())

    os.replace(staging_file, final_file)

    scratch_path = "/home/james/stacklabs/pilot_drops/scratch_pad.md"
    if os.path.exists(scratch_path):
        try:
            with open(scratch_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
            new_lines = []
            inserted = False
            for line in lines:
                new_lines.append(line)
                if "### ⚡ STAGED & ACTIVE IN PROCESSING" in line and not inserted:
                    new_lines.append(f"- `{ticket_id}`: {slug} -> `queue/incoming/` (Staged via Cockpit UI) ⚡")
                    inserted = True
            with open(scratch_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines) + "\n")
        except Exception as e:
            logger.warning(f"Could not update scratchpad: {e}")

    return CockpitStageResponse(
        status="success",
        ticket_id=ticket_id,
        filename=filename,
        path=final_file
    )


@app.get("/api/triage/latest")
def get_triage_latest_fast():
    base = {
        "status": "active",
        "model": "gemini-3.8-flash",
        "credits": {
            "ai_studio_usd": 340.0,
            "vertex_ai_usd": 300.0
        },
        "latency_ms": 280,
        "latest_failure": {
            "nodeid": "tests/test_docket_parser.py::test_entity_extraction",
            "triage_text": "## 🔍 ROOT CAUSE\nThe telemetry transformer returns a nested dictionary under 'metadata' -> 'state' instead of top-level 'status'.\n\n## ⚠️ BROKEN INVARIANT\nPipeline contract v2 deprecates top-level 'status' in favor of 'metadata.state'.\n\n## 🛠️ RECOMMENDED PATCH\n```python\n# In tests/test_telemetry.py line 24:\n- assert result[\"status\"] == \"active\"\n+ assert result.get(\"metadata\", {}).get(\"state\") == \"active\"\n```",
            "timestamp": "2026-10-06T18:14:02EDT"
        },
        "semantic_harness": {
            "target": "energy_docket_test_2026.txt",
            "score": 1.0,
            "invariants": [
                {"name": "Cite exact filing timestamps without speculation", "passed": True},
                {"name": "Extract verified entity names verbatim from source", "passed": True},
                {"name": "Zero promotional or conversational adjectives", "passed": True}
            ]
        }
    }
    feed_path = Path("/home/james/stacklabs/data/test_triage_feed.json")
    if feed_path.exists():
        try:
            feed_data = json.loads(feed_path.read_text(encoding="utf-8"))
            if isinstance(feed_data, dict):
                base.update(feed_data)
        except Exception:
            pass
    return base


@app.get("/api/cockpit/comms_search")
def get_comms_search_fast(
    q: Optional[str] = None,
    term: Optional[str] = None,
    person: Optional[str] = None,
    channel: Optional[str] = "ALL",
    limit: int = 50,
    offset: int = 0
):
    from scripts.comm_query import execute_comms_search
    query_term = (term or q or "").strip()
    person_filter = (person or "").strip()
    channel_filter = (channel or "ALL").strip()
    clamped_limit = min(max(1, limit), 200)

    res = execute_comms_search(
        term=query_term,
        person=person_filter,
        channel=channel_filter,
        limit=clamped_limit,
        offset=offset,
        highlight_html=True
    )
    return {
        "status": "success",
        "query": query_term,
        "person": res.get("person", person_filter),
        "channel": channel_filter,
        "count": res.get("count", 0),
        "query_latency_ms": res.get("latency_ms", 0),
        "messages": res.get("messages", [])
    }


try:
    from scripts.blueprints.vfs_wiki_api import (
        vfs_wiki_bp, search_concepts, execute_swanson_crawl, get_concept_detail, CrawlRequest
    )
    app.include_router(vfs_wiki_bp)
    app.include_router(vfs_wiki_bp, prefix="/api/cockpit")

    @app.get("/api/cockpit/wiki/concepts")
    def cockpit_wiki_concepts_fast(q: str = Query("", min_length=1), limit: int = 25):
        return search_concepts(q=q, limit=limit)

    @app.post("/api/cockpit/wiki/swanson_crawl")
    def cockpit_wiki_crawl_fast(req: CrawlRequest):
        return execute_swanson_crawl(req)

    @app.get("/api/cockpit/wiki/concept/{slug}")
    def cockpit_wiki_concept_fast(slug: str):
        return get_concept_detail(slug)

    logger.info("Successfully mounted vfs_wiki_bp on Port 8088 (/api/wiki & /api/cockpit/wiki)")
except Exception as e:
    logger.error(f"Failed to mount vfs_wiki_bp on synapse_bus: {e}")


try:
    from scripts.blueprints.drive_sync_api import drive_sync_router
    app.include_router(drive_sync_router)
    logger.info("Successfully mounted drive_sync_router on Port 8088 (/api/cockpit/drive_sync)")
except Exception as e:
    logger.error(f"Failed to mount drive_sync_router on synapse_bus: {e}")


try:
    from scripts.blueprints.vault_explorer_api import vault_explorer_router
    app.include_router(vault_explorer_router)
    logger.info("Successfully mounted vault_explorer_router on Port 8088 (/api/cockpit/vault)")
except Exception as e:
    logger.error(f"Failed to mount vault_explorer_router on synapse_bus: {e}")


try:
    _repo_root = "/home/james/stacklabs"
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
    from starlette.middleware.wsgi import WSGIMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
    from scripts.dead_drop_server_v2 import app as flask_app

    wsgi_handler = WSGIMiddleware(flask_app)

    class _WSGIProxyResponse(Response):
        async def __call__(self, scope, receive, send) -> None:
            pass

    @app.api_route("/api/cockpit/{rest_of_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def forward_cockpit_api(request: Request, rest_of_path: str):
        await wsgi_handler(request.scope, request.receive, request._send)
        return _WSGIProxyResponse()

    @app.api_route("/api/auth", methods=["GET", "POST", "OPTIONS"])
    async def forward_auth_api(request: Request):
        await wsgi_handler(request.scope, request.receive, request._send)
        return _WSGIProxyResponse()

    @app.api_route("/api/drops", methods=["GET", "HEAD", "OPTIONS"])
    async def forward_api_drops(request: Request):
        await wsgi_handler(request.scope, request.receive, request._send)
        return _WSGIProxyResponse()

    @app.api_route("/api/drop/{rest_of_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def forward_drop_space_api(request: Request, rest_of_path: str):
        await wsgi_handler(request.scope, request.receive, request._send)
        return _WSGIProxyResponse()

    @app.api_route("/drops/{rest_of_path:path}", methods=["GET", "HEAD", "OPTIONS"])
    async def forward_drops_static(request: Request, rest_of_path: str):
        await wsgi_handler(request.scope, request.receive, request._send)
        return _WSGIProxyResponse()

    @app.api_route("/api/upload", methods=["POST"])
    async def forward_upload_api(request: Request):
        await wsgi_handler(request.scope, request.receive, request._send)
        return _WSGIProxyResponse()

    @app.api_route("/api/ingress/{rest_of_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def forward_ingress_api(request: Request, rest_of_path: str):
        await wsgi_handler(request.scope, request.receive, request._send)
        return _WSGIProxyResponse()

    @app.api_route("/api/phone/{rest_of_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def forward_phone_api(request: Request, rest_of_path: str):
        await wsgi_handler(request.scope, request.receive, request._send)
        return _WSGIProxyResponse()

    @app.api_route("/api/predict/{rest_of_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def forward_predict_api(request: Request, rest_of_path: str):
        await wsgi_handler(request.scope, request.receive, request._send)
        return _WSGIProxyResponse()

    @app.api_route("/api/voice/{rest_of_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def forward_voice_api(request: Request, rest_of_path: str):
        await wsgi_handler(request.scope, request.receive, request._send)
        return _WSGIProxyResponse()

    @app.api_route("/api/sync/{rest_of_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def forward_sync_api(request: Request, rest_of_path: str):
        await wsgi_handler(request.scope, request.receive, request._send)
        return _WSGIProxyResponse()

    app.mount("/drop", wsgi_handler)
    logger.info("Successfully mounted legacy endpoints onto Synapse bus with preserved path resolution")
except Exception as e:
    logger.warning(f"Legacy drop mounts skipped: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8088, log_level="info")
