#!/usr/bin/env python3
"""
StackLabs Retina Static HTTP, C120 MJPEG Stream, Vector6 Chat & Shutter API Server
Path: /home/james/stacklabs/scripts/serve_retina.py
Author: James Carroll (Lead Systems Architect)

Binds Port 3028 to serve apps/retina with zero-cache headers.
Provides /stream/c120 MJPEG stream with server-side privacy shutter control.
Provides /api/cam/toggle, /api/cam/kill, /api/cam/start endpoints.
Provides /api/allocator/query POST endpoint for interactive Direct Wire scenarios.
Provides /api/vector6/messages and /api/vector6/send for live Direct Wire chat.
Target: Clio (100.96.77.20) | Python 3.12 (.venv)
"""
import http.server
import socketserver
import os
import sys
import time
import threading
import json
import asyncio
from urllib.parse import urlparse, parse_qs
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path("/home/james/stacklabs")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from scripts.consensus_arbiter_engine import GROUND_TRUTH_PRESETS, execute_arbitration
except ImportError:
    from consensus_arbiter_engine import GROUND_TRUTH_PRESETS, execute_arbitration

try:
    from scripts.retina_wiretap import handle_wiretap_beacon, intercept_server_request
except ImportError:
    from retina_wiretap import handle_wiretap_beacon, intercept_server_request

PORT = 3028
DIRECTORY = "/home/james/stacklabs/apps/retina"
REPO_ROOT = Path("/home/james/stacklabs")
DATA_DIR = REPO_ROOT / "data"
HUD_FILE = DATA_DIR / "hud.json"
VITALS_FILE = DATA_DIR / "vitals.json"
WIRES_DIR = DATA_DIR / "wires"
PAWEL_WIRE_FILE = WIRES_DIR / "pawel.json"

WIRES_DIR.mkdir(parents=True, exist_ok=True)

# VFS Hierarchical Roots (Monograph 06)
VFS_PERSIST_ROOT = Path("/home/james/stacklabs/vfs")
VFS_SHM_ROOT = Path("/dev/shm/faas_vfs")

def handle_vfs_browse(target_path: str):
    clean = target_path.strip().strip("/")
    if not clean or clean == "allocator":
        clean = "allocator"
    
    # Check shm first, fallback to persistent NVMe
    browse_dir = VFS_SHM_ROOT / clean
    if not (browse_dir.exists() and browse_dir.is_dir()):
        browse_dir = VFS_PERSIST_ROOT / clean
    
    if not (browse_dir.exists() and browse_dir.is_dir()):
        return {"error": "Not found", "path": target_path, "items": []}

    parent = "/" + str(Path(clean).parent) if str(Path(clean).parent) != "." else "/allocator"
    if clean == "allocator":
        parent = None

    items = []
    attributes = {}
    for entry in sorted(browse_dir.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            title = entry.name.replace("_", " ").title()
            meta_file = entry / "meta.json"
            meta = {}
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    title = meta.get("title", title)
                except Exception:
                    pass
            items.append({
                "id": entry.name,
                "name": entry.name,
                "label": title,
                "type": "folder",
                "path": f"/{clean}/{entry.name}",
                "meta": meta
            })
        else:
            if entry.name == "meta.json":
                continue
            leaf = {
                "id": entry.name,
                "name": entry.name,
                "label": entry.stem.replace("_", " ").title(),
                "type": "leaf",
                "extension": entry.suffix,
                "url": f"/api/vfs/tail?path=/{clean}/{entry.name}"
            }
            if entry.suffix in (".txt", ".status", ".metrics", ".action", ".schedule", ".stream"):
                try:
                    val = entry.read_text(encoding="utf-8").strip()
                    leaf["value"] = val
                    attributes[entry.stem] = val
                except Exception:
                    pass
            elif entry.suffix == ".json":
                try:
                    val = json.loads(entry.read_text(encoding="utf-8"))
                    leaf["json_value"] = val
                    attributes[entry.stem] = val
                except Exception:
                    pass
            elif entry.suffix == ".tail":
                try:
                    lines = entry.read_text(encoding="utf-8").strip().splitlines()[-20:]
                    leaf["tail_lines"] = lines
                    attributes[entry.stem] = "\n".join(lines)
                except Exception:
                    pass
            items.append(leaf)

    return {
        "path": f"/{clean}",
        "parent_path": parent,
        "name": browse_dir.name.replace("_", " ").title(),
        "items": items,
        "attributes": attributes
    }

def handle_vfs_tail(target_path: str):
    clean = target_path.strip().lstrip("/")
    f = VFS_SHM_ROOT / clean
    if not f.exists():
        f = VFS_PERSIST_ROOT / clean
    if f.exists() and f.is_file():
        return f.read_text(encoding="utf-8")
    return ""

# Global Frame Cache & Shutter State
LATEST_FRAME_BYTES = None
FRAME_LOCK = threading.Lock()
SHUTTER_CLOSED = False

def create_shutter_frame():
    """Generate a clean Deep Void 640x360 standby graphic when privacy shutter is active."""
    img = np.zeros((360, 640, 3), dtype=np.uint8)
    img[:] = (19, 13, 11)  # #0B0D13 in BGR

    cv2.rectangle(img, (10, 10), (630, 350), (45, 33, 24), 1)

    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, "[ OPTICAL SENTRY // PRIVACY SHUTTER ACTIVE ]", (90, 160), font, 0.6, (255, 176, 0), 1, cv2.LINE_AA)
    cv2.putText(img, "RTSP SOCKET DISCONNECTED // AIR-GAPPED ON METAL", (105, 200), font, 0.45, (148, 163, 184), 1, cv2.LINE_AA)
    cv2.putText(img, "RADIO AT 192.168.1.191 IS IDLE", (200, 235), font, 0.45, (16, 185, 129), 1, cv2.LINE_AA)

    _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return buf.tobytes()

SHUTTER_FRAME_BYTES = create_shutter_frame()

def c120_capture_loop():
    """Background worker continuously pulling 640x360 frames from Tapo C120 RTSP stream."""
    global LATEST_FRAME_BYTES, SHUTTER_CLOSED
    
    env_path = "/home/james/stacklabs/.env"
    if os.path.exists(env_path):
        load_dotenv(env_path)
    
    user = os.getenv("TAPO_C120_USER", "argo_pi5")
    password = os.getenv("TAPO_C120_PASS", "!!Stella1977")
    ip = os.getenv("TAPO_C120_IP", "192.168.1.191")
    
    rtsp_url = f"rtsp://{user}:{password}@{ip}:554/stream2"
    
    while True:
        if SHUTTER_CLOSED:
            with FRAME_LOCK:
                LATEST_FRAME_BYTES = SHUTTER_FRAME_BYTES
            time.sleep(0.5)
            continue

        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not cap.isOpened():
            with FRAME_LOCK:
                LATEST_FRAME_BYTES = SHUTTER_FRAME_BYTES
            time.sleep(2.0)
            continue
            
        while not SHUTTER_CLOSED:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
                
            _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            with FRAME_LOCK:
                LATEST_FRAME_BYTES = jpeg.tobytes()
                
            time.sleep(0.04)
            
        cap.release()
        time.sleep(0.5)

# Allocator Direct Wire Scenarios
SCENARIOS = {
    "SENTRY_AND_WIRE": {
        "title": "📹📡⚡🟢 :: OPTICAL SENTRY & VECTOR6 DIRECT WIRE // LIVE METAL",
        "status_badge": "NOMINAL",
        "bytecode_frame": "📹📡⚡🟢 :: SENTRY_AND_WIRE",
        "ascii_frame": "[CAM][WIR][CLO][MTL] :: SENTRY_AND_WIRE",
        "alert_status": "NOMINAL",
        "containers": {
            "top_left": {
                "title": "TAPO C120 // LOCAL OPTICAL SENTRY",
                "primitive": "media_asset",
                "src": "/stream/c120",
                "caption": "LIVE RTSP 20FPS @ 192.168.1.191 // SMYRNA COMMAND LAB"
            },
            "top_right": {
                "title": "VECTOR6 DIRECT WIRE // JAMES ⇄ PAWEL",
                "primitive": "vector6_wire",
                "channel": "pawel"
            },
            "bottom_left": {
                "title": "DORA RV // 1974 RESTOMOD IP",
                "primitive": "dora_rv_craft",
                "dora_camper": {
                    "name": "1974 Restomod Camper Project (Dora)",
                    "asset_class": "Vector Camper Restomod",
                    "powertrain": "Detroit Diesel 6V53 Powertrain Radar",
                    "route": "Big Sur / PCH Tour Route Active",
                    "progress_pct": 78
                }
            },
            "bottom_right": {
                "title": "ALLOCATOR DIRECT WIRE // SCENARIOS",
                "primitive": "quick_action_slot",
                "buttons": [
                    {"id": "btn_sentry", "label": "🎥 SENTRY & WIRE", "variant": "action-btn-primary", "action": "SENTRY_AND_WIRE"},
                    {"id": "btn_consensys", "label": "⚖️ CONSEN-SYS COCKPIT", "variant": "action-btn-primary", "action": "CONSEN_SYS_4PANEL"},
                    {"id": "btn_mara", "label": "📈 MARA +5% (BATMAN)", "variant": "action-btn-success", "action": "MARA_MOMENTUM"},
                    {"id": "btn_mr_horse", "label": "🏇 SANTA ANITA (MR. HORSE)", "variant": "action-btn-danger", "action": "SANTA_ANITA_REJECT"},
                    {"id": "btn_dora", "label": "🚐 DORA RV RESTOMOD", "variant": "action-btn-warning", "action": "DORA_RV_RESTOMOD"}
                ]
            }
        },
        "audit_lines": [
            "OPTICAL SENTRY: Live RTSP socket open on 192.168.1.191",
            "VECTOR6 WIRE: Direct NVMe channel /data/wires/pawel.json active",
            "PHYSICAL ISOMORPHISM: Clio AMD Ryzen 7735HS metal verified",
            "NETWORK LATENCY: Sub-50ms deterministic local loop",
            "ALLOCATOR STATUS: Live interactive dual-channel engagement"
        ]
    },
    "SANTA_ANITA_REJECT": {
        "title": "🏇🛑🧱✂️ :: SANTA_ANITA_R5 // MR. HORSE REJECT",
        "status_badge": "CRITICAL",
        "bytecode_frame": "🏇🛑🧱✂️ :: SANTA_ANITA_R5",
        "ascii_frame": "[TRK][CRT][SAT][PRN] :: SANTA_ANITA_R5",
        "alert_status": "CRITICAL",
        "containers": {
            "top_left": {
                "title": "MOMENTUM CIRCUIT BREAKER",
                "primitive": "status_alert_badge",
                "alert_label": "[TRK][CRT][SAT][PRN] :: SANTA_ANITA_R5",
                "nominal_label": "[TRK][NOM][IDL][MON] :: NOMINAL",
                "source": "alert_status"
            },
            "top_right": {
                "title": "PERFORMANCE AUDIT (RECEIPT)",
                "primitive": "scrolling_terminal",
                "source": "execution_audit_log"
            },
            "bottom_left": {
                "title": "EXECUTION STATE",
                "primitive": "media_asset",
                "src": "/media/i-don't-like-it-ren-and-stimpy.gif",
                "caption": "NO SIR, I DON'T LIKE IT // 3/3 REJECT"
            },
            "bottom_right": {
                "title": "ALLOCATOR DIRECT WIRE // SCENARIOS",
                "primitive": "quick_action_slot",
                "buttons": [
                    {"id": "btn_consensys", "label": "⚖️ CONSEN-SYS COCKPIT", "variant": "action-btn-primary", "action": "CONSEN_SYS_4PANEL"},
                    {"id": "btn_mr_horse", "label": "🏇 SANTA ANITA (MR. HORSE)", "variant": "action-btn-danger", "action": "SANTA_ANITA_REJECT"},
                    {"id": "btn_sentry", "label": "🎥 SENTRY & WIRE", "variant": "action-btn-primary", "action": "SENTRY_AND_WIRE"},
                    {"id": "btn_mara", "label": "📈 MARA +5% (BATMAN)", "variant": "action-btn-success", "action": "MARA_MOMENTUM"},
                    {"id": "btn_dora", "label": "🚐 DORA RV RESTOMOD", "variant": "action-btn-warning", "action": "DORA_RV_RESTOMOD"}
                ]
            }
        },
        "audit_lines": [
            "QUERY: Backing #2 front-runner on sloppy track",
            "CLAUDE: Heavy pace exhaustion risk in mud",
            "GPT: Unanimous reject. Speed index collapses",
            "GEMINI: 3-Model Consensus: FADE #2 (Negative EV)",
            "VERDICT: 100% NVMe Verified | Mr. Horse has spoken"
        ]
    },
    "MARA_MOMENTUM": {
        "title": "📈🛑🎯🚀 :: MARA $18.62 (+5.08%) // COLLAR BREACH DISPATCHED",
        "status_badge": "CRITICAL",
        "bytecode_frame": "📈🛑🎯🚀 :: MARA_SELL_5PCT",
        "ascii_frame": "[MKT][CRT][SPK][DSP] :: MARA_SELL_5PCT",
        "alert_status": "CRITICAL",
        "containers": {
            "top_left": {
                "title": "MOMENTUM CIRCUIT BREAKER",
                "primitive": "status_alert_badge",
                "alert_label": "[MKT][CRT][SPK][DSP] :: MARA_SELL_5PCT",
                "nominal_label": "[MKT][NOM][IDL][MON] :: MARA_ARMED_MONITOR",
                "source": "alert_status"
            },
            "top_right": {
                "title": "PERFORMANCE AUDIT (RECEIPT)",
                "primitive": "scrolling_terminal",
                "source": "execution_audit_log"
            },
            "bottom_left": {
                "title": "EXECUTION STATE",
                "primitive": "media_asset",
                "src": "/media/batman.gif",
                "caption": "LOCKED +5.08% ($18.62) // +$1,700 CASH EDGE"
            },
            "bottom_right": {
                "title": "ALLOCATOR DIRECT WIRE // SCENARIOS",
                "primitive": "quick_action_slot",
                "buttons": [
                    {"id": "btn_consensys", "label": "⚖️ CONSEN-SYS COCKPIT", "variant": "action-btn-primary", "action": "CONSEN_SYS_4PANEL"},
                    {"id": "btn_mara", "label": "📈 MARA +5% (BATMAN)", "variant": "action-btn-success", "action": "MARA_MOMENTUM"},
                    {"id": "btn_sentry", "label": "🎥 SENTRY & WIRE", "variant": "action-btn-primary", "action": "SENTRY_AND_WIRE"},
                    {"id": "btn_mr_horse", "label": "🏇 SANTA ANITA (MR. HORSE)", "variant": "action-btn-danger", "action": "SANTA_ANITA_REJECT"},
                    {"id": "btn_dora", "label": "🚐 DORA RV RESTOMOD", "variant": "action-btn-warning", "action": "DORA_RV_RESTOMOD"}
                ]
            }
        },
        "audit_lines": [
            "TARGET BREACH: MARA $18.62 (+5.08%) vs +5.00% Collar",
            "ROSETTA FRAME: [MKT][CRT][SPK][DSP] :: MARA_SELL_5PCT",
            "CLIO METAL: 2.03ms | Fill: $18.62 | PnL: +$4,500.00",
            "CLOUD AI: 2,400ms | Fill: $18.28 | PnL: +$2,800.00",
            "SLIPPAGE PENALTY: -$1,700.00 Bleed on Cloud AI",
            "NET CASH EDGE: +$1,700.00 Locked on Bare Metal NVMe"
        ]
    },
    "DORA_RV_RESTOMOD": {
        "title": "🚐🛠️⚡🟢 :: DORA RV RESTOMOD // 1974 CHOPPED-TOP // DETROIT DIESEL 6V53",
        "status_badge": "NOMINAL",
        "bytecode_frame": "🚐🛠️⚡🟢 :: DORA_RV_RESTOMOD",
        "ascii_frame": "[RVM][DET][PCH][NOM] :: DORA_RV_RESTOMOD",
        "alert_status": "NOMINAL",
        "containers": {
            "top_left": {
                "title": "1974 CHOPPED-TOP RESTOMOD // RADAR",
                "primitive": "status_alert_badge",
                "alert_label": "[RVM][DET][PCH][NOM] :: DORA_RV_RESTOMOD",
                "nominal_label": "[RVM][DET][PCH][NOM] :: DETROIT 6V53 ONLINE",
                "source": "alert_status"
            },
            "top_right": {
                "title": "FABRICATION & RESTORATION AUDIT",
                "primitive": "scrolling_terminal",
                "source": "execution_audit_log"
            },
            "bottom_left": {
                "title": "DORA RV // 1974 RESTOMOD IP",
                "primitive": "dora_rv_craft",
                "dora_camper": {
                    "name": "1974 Restomod Camper Project (Dora)",
                    "asset_class": "Vector Camper Restomod",
                    "powertrain": "Detroit Diesel 6V53 Powertrain Radar",
                    "route": "Big Sur / PCH Tour Route Active",
                    "progress_pct": 78
                }
            },
            "bottom_right": {
                "title": "ALLOCATOR DIRECT WIRE // SCENARIOS",
                "primitive": "quick_action_slot",
                "buttons": [
                    {"id": "btn_consensys", "label": "⚖️ CONSEN-SYS COCKPIT", "variant": "action-btn-primary", "action": "CONSEN_SYS_4PANEL"},
                    {"id": "btn_dora", "label": "🚐 DORA RV RESTOMOD", "variant": "action-btn-warning", "action": "DORA_RV_RESTOMOD"},
                    {"id": "btn_sentry", "label": "🎥 SENTRY & WIRE", "variant": "action-btn-primary", "action": "SENTRY_AND_WIRE"},
                    {"id": "btn_mara", "label": "📈 MARA +5% (BATMAN)", "variant": "action-btn-success", "action": "MARA_MOMENTUM"},
                    {"id": "btn_mr_horse", "label": "🏇 SANTA ANITA (MR. HORSE)", "variant": "action-btn-danger", "action": "SANTA_ANITA_REJECT"}
                ]
            }
        },
        "audit_lines": [
            "POWERTRAIN: Detroit Diesel 6V53 salvage radar active",
            "CHASSIS: 1974 Chopped-top restomod fabrication Phase IV at 78%",
            "LOGISTICS: Rare vintage trim alerts active across nationwide salvage network",
            "ROUTE TELEMETRY: Big Sur / Pacific Coast Highway tour corridor locked",
            "SOVEREIGN ASSET: 100% Deterministic metal tracking online"
        ]
    },
    "CONSEN_SYS_4PANEL": {
        "title": "⚖️📡🤖🟢 :: CONSEN-SYS 4-PANEL ARBITRATION COCKPIT // GROUND TRUTH FORGE",
        "status_badge": "NOMINAL",
        "bytecode_frame": "⚖️📡🤖🟢 :: CONSEN_SYS_4PANEL",
        "ascii_frame": "[ARB][GTF][CLD][GPT] :: CONSEN_SYS_4PANEL",
        "alert_status": "NOMINAL",
        "containers": {
            "top_left": {
                "title": "PANEL 1 // GROUND TRUTH FORGE (STACKLABS METAL)",
                "primitive": "ground_truth_forge",
                "preset_key": "SANTA_ANITA_R5"
            },
            "top_right": {
                "title": "PANEL 2 // CLAUDE 3.5 SONNET (ANALYTICAL REASONING)",
                "primitive": "model_stream_card",
                "model_id": "claude",
                "model_name": "Claude 3.5 Sonnet",
                "badge": "ZERO SEARCH // PURE REASONING"
            },
            "bottom_left": {
                "title": "PANEL 3 // GPT-4o (CROSS-EXAMINATION & CONTRARY RISKS)",
                "primitive": "model_stream_card",
                "model_id": "gpt",
                "model_name": "GPT-4o",
                "badge": "ZERO SEARCH // SKEPTICAL AUDIT"
            },
            "bottom_right": {
                "title": "PANEL 4 // CONSEN-SYS ARBITER & CONSENSUS SYNTHESIZER",
                "primitive": "consensus_arbiter_card"
            }
        },
        "audit_lines": [
            "GROUND TRUTH: Pre-loaded Santa Anita R5 sloppy track metrics (0.4ms NVMe)",
            "SEARCH BYPASS: Web browsing disabled; pure in-context reasoning engaged",
            "PARALLEL DISPATCH: Claude 3.5 Sonnet & GPT-4o queried simultaneously",
            "CONSENSUS STATUS: 2/2 Unanimous Pass verified (-$500 loss prevented)",
            "DECISION LATENCY: Sub-4 second complete decision loop"
        ]
    },
    "SMYRNA_COMMAND_DECK": {
        "title": "STACKLABS RETINA // SMYRNA COMMAND LAB",
        "subtitle": "Lead Systems Architect · James Carroll",
        "status_badge": "NOMINAL",
        "bytecode_frame": "⚡ SMYRNA COMMAND DECK // CLIO x86 NVMe",
        "ascii_frame": "[GRID][SENTRY][SONAR][COMPUTE] :: SMYRNA_DECK",
        "alert_status": "NOMINAL",
        "theme": "quiet-luxury",
        "layout": "2x2_critical_grid",
        "containers": {
            "top_left": {
                "title": "Gridiron & Live Intelligence",
                "badge": "FBS Slate",
                "primitive": "quiet_luxury_quad1",
                "members": [
                    {
                        "name": "Memphis vs Tulane",
                        "status": "Live Q1",
                        "items": [
                            {"name": "Score: MEM 3 — 0 TULN", "state": "1st Quarter", "status_pip": "emerald"},
                            {"name": "Yulman Stadium (Turf)", "state": "Possession: MEM", "status_pip": "emerald"},
                            {"name": "Live Drive Telemetry", "state": "20 Plays Logged", "status_pip": "emerald"}
                        ],
                        "metrics": "Cultural Heat: 99%"
                    },
                    {
                        "name": "Winterball Pipeline (sportId=17)",
                        "status": "Ingesting",
                        "items": [
                            {"name": "AFL / LIDOM / LVBP / LMP", "state": "997 Minor Leaguers"},
                            {"name": "Divergence Engine", "time": "Active"}
                        ],
                        "metrics": "Hard-Hit Out Radar"
                    },
                    {
                        "name": "Sammy the Savant Gate",
                        "status": "Active",
                        "items": [
                            {"name": "Whistle Fatigue & Pace", "state": "Gate 3 Monitoring"},
                            {"name": "Hook Trap (.5 Vig)", "state": "Rejection Active"}
                        ],
                        "metrics": "Live Total Oracle"
                    }
                ]
            },
            "top_right": {
                "title": "Smyrna Optical Sentry",
                "badge": "33.88°N 84.51°W",
                "primitive": "quiet_luxury_quad2",
                "camera": {
                    "id": "c120",
                    "name": "Tapo C120 Optical Sentry",
                    "role": "Smyrna Command Lab Floor & Patio Sentry",
                    "resolution": "1080p @ 20 FPS",
                    "lan_ip": "192.168.1.191",
                    "stream_url": "/stream/c120",
                    "shutter_status": "OPEN",
                    "status": "ACTIVE",
                    "tenants": "Metsy & Riz"
                },
                "sensors": {
                    "solar_yield": "11.4 kW",
                    "daily_kwh": "48.2 kWh",
                    "perimeter_status": "Secure",
                    "lab_temp": "71°F",
                    "tenant_count": "2 Feline SOWs"
                }
            },
            "bottom_left": {
                "title": "Live Broadcast Sonar Wiretap",
                "badge": "Acoustic Sonar",
                "primitive": "quiet_luxury_quad3",
                "race_data": {
                    "track": "Broadcast Audio Aligner (WO0011201)",
                    "condition": "Acoustic vs Optical Sonar",
                    "pace_index": "Bimodal Ping",
                    "moisture": "Negative-Latency [T-18s, T-2s]",
                    "synthesis": "Word-level Whisper alignment isolates exact on-air spoken tells preceding bleacher chat meltdowns.",
                    "risk_audit": "First phonetic stem collision phase-locks CDN egress latency (Δ_HLS) for deterministic matching.",
                    "recommendation": "SONAR PHASE-LOCK ACTIVE",
                    "value": "100% Grounded"
                }
            },
            "bottom_right": {
                "title": "Clio Compute & Memory Fabric",
                "badge": "NVMe WAL",
                "primitive": "quiet_luxury_quad4",
                "portfolio": {
                    "liquidity": "Google AI Ultra 20TB",
                    "yield": "Gemini 4 Argon (5x)",
                    "tbills": "1,114 Active CMDB CIs",
                    "cash_equiv": "2,194 Causal Edges",
                    "leverage": "0 Active Enterprise Clients",
                    "syndicates": [
                        {"name": "Clio Dedicated x86 NVMe", "return": "1.2ms Graph Blast Radius"},
                        {"name": "Artemis GTX 1060 CUDA", "return": "Faster-Whisper Transcriber"},
                        {"name": "Google Colab GPU Pool", "return": "1,000+ CCUs On-Demand"}
                    ],
                    "hard_assets": {
                        "title": "Solo Builder Systems Architecture",
                        "subtitle": "Small Ball on Grounded Metal",
                        "progress": 100,
                        "notes": "James Carroll • Lead Systems Architect • StackLabs LLC"
                    }
                }
            }
        },
        "audit_lines": [
            "SMYRNA COMMAND DECK: Grounded 4-Pillar Engineering Cockpit active on Clio",
            "GRIDIRON: Live FBS / Winterball / Sammy Gate telemetry active",
            "SENTRY: Smyrna Command Lab Tapo C120 live optical stream active (192.168.1.191 @ 20 FPS)",
            "SONAR: Broadcast Audio Aligner negative-latency window [T-18s, T-2s] locked",
            "COMPUTE: Clio x86 NVMe, 1,114 CMDB CIs, 0 Active Enterprise Clients"
        ]
    },
    "SANTA_ANITA_ARBITRATION": {
        "title": "🏇🛑🧱✂️ :: SANTA_ANITA_R5 // ARBITRATION BIAS REJECT",
        "status_badge": "CRITICAL",
        "bytecode_frame": "🏇🛑🧱✂️ :: SANTA_ANITA_R5",
        "ascii_frame": "[TRK][CRT][SAT][PRN] :: SANTA_ANITA_R5",
        "alert_status": "CRITICAL",
        "containers": {
            "top_left": {
                "title": "MOMENTUM CIRCUIT BREAKER",
                "primitive": "status_alert_badge",
                "alert_label": "[TRK][CRT][SAT][PRN] :: SANTA_ANITA_R5",
                "nominal_label": "[TRK][NOM][IDL][MON] :: NOMINAL",
                "source": "alert_status"
            },
            "top_right": {
                "title": "PERFORMANCE AUDIT (RECEIPT)",
                "primitive": "scrolling_terminal",
                "source": "execution_audit_log"
            },
            "bottom_left": {
                "title": "EXECUTION STATE",
                "primitive": "media_asset",
                "src": "/media/i-don't-like-it-ren-and-stimpy.gif",
                "caption": "NO SIR, I DON'T LIKE IT // 3/3 REJECT"
            },
            "bottom_right": {
                "title": "ALLOCATOR DIRECT WIRE // SCENARIOS",
                "primitive": "quick_action_slot",
                "buttons": [
                    {"id": "btn_consensys", "label": "⚖️ CONSEN-SYS COCKPIT", "variant": "action-btn-primary", "action": "CONSEN_SYS_4PANEL"},
                    {"id": "btn_mr_horse", "label": "🏇 SANTA ANITA (MR. HORSE)", "variant": "action-btn-danger", "action": "SANTA_ANITA_REJECT"},
                    {"id": "btn_sentry", "label": "🎥 SENTRY & WIRE", "variant": "action-btn-primary", "action": "SENTRY_AND_WIRE"},
                    {"id": "btn_mara", "label": "📈 MARA +5% (BATMAN)", "variant": "action-btn-success", "action": "MARA_MOMENTUM"},
                    {"id": "btn_dora", "label": "🚐 DORA RV RESTOMOD", "variant": "action-btn-warning", "action": "DORA_RV_RESTOMOD"}
                ]
            }
        },
        "audit_lines": [
            "QUERY: Backing #2 front-runner on sloppy track",
            "CLAUDE: Heavy pace exhaustion risk in mud",
            "GPT: Unanimous reject. Speed index collapses",
            "GEMINI: 3-Model Consensus: FADE #2 (Negative EV)",
            "VERDICT: 100% NVMe Verified | Mr. Horse has spoken"
        ]
    }
}

def load_vector6_wire(channel="pawel"):
    clean_chan = (channel or "pawel").lower().strip()
    wire_file = WIRES_DIR / f"{clean_chan}.json"
    if not wire_file.exists():
        default_wire = {
            "channel_id": clean_chan,
            "display_title": "JAMES ⇄ PAWEL",
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT"),
            "epoch_heartbeat": int(time.time()),
            "messages": [
                {
                    "id": "msg_init_01",
                    "sender": "james",
                    "display_name": "James (Pilot)",
                    "body": "Pawel, welcome to Clio metal. Zero cloud API tolls.",
                    "timestamp": "11:45:00 EDT"
                }
            ]
        }
        wire_file.write_text(json.dumps(default_wire, indent=2), encoding="utf-8")
        return default_wire
    try:
        return json.loads(wire_file.read_text(encoding="utf-8"))
    except Exception:
        return {"channel_id": clean_chan, "display_title": "JAMES ⇄ PAWEL", "messages": []}

def append_vector6_message(channel="pawel", sender="james", body=""):
    clean_chan = (channel or "pawel").lower().strip()
    wire_file = WIRES_DIR / f"{clean_chan}.json"
    data = load_vector6_wire(clean_chan)
    
    sender_clean = sender.lower().strip()
    display_name = "James (Pilot)" if sender_clean == "james" else "Pawel Rudnicki"
    
    new_msg = {
        "id": f"msg_{int(time.time()*1000)}",
        "sender": sender_clean,
        "display_name": display_name,
        "body": body,
        "timestamp": datetime.now().strftime("%H:%M:%S EDT")
    }
    
    data.setdefault("messages", []).append(new_msg)
    if len(data["messages"]) > 50:
        data["messages"] = data["messages"][-50:]
        
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT")
    data["epoch_heartbeat"] = int(time.time())
    
    temp_file = wire_file.with_suffix(".tmp")
    temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(temp_file, wire_file)
    return new_msg

def apply_scenario(scenario_key: str):
    if scenario_key not in SCENARIOS:
        scenario_key = "SMYRNA_COMMAND_DECK"
    scenario = SCENARIOS.get(scenario_key, SCENARIOS["SMYRNA_COMMAND_DECK"])

    # Update hud.json
    try:
        with open(HUD_FILE, "r", encoding="utf-8") as f:
            hud = json.load(f)
    except Exception:
        hud = {}

    hud.setdefault("header", {})
    hud["header"]["title"] = scenario["title"]
    if "subtitle" in scenario:
        hud["header"]["subtitle"] = scenario["subtitle"]
    hud["header"]["status_badge"] = scenario["status_badge"]
    hud["header"]["bytecode_frame"] = scenario["bytecode_frame"]
    hud["header"]["ascii_frame"] = scenario["ascii_frame"]
    hud["header"]["node_ip"] = "100.96.77.20"
    hud["read_latency_ms"] = 0.2
    hud["theme"] = scenario.get("theme", "quiet-luxury")
    hud["layout"] = scenario.get("layout", "2x2_critical_grid")
    hud["containers"] = scenario["containers"]
    hud["active_scenario"] = scenario_key

    temp_hud = HUD_FILE.with_suffix(".tmp")
    with open(temp_hud, "w", encoding="utf-8") as f:
        json.dump(hud, f, indent=2)
    os.replace(temp_hud, HUD_FILE)

    # Update vitals.json
    try:
        with open(VITALS_FILE, "r", encoding="utf-8") as f:
            vitals = json.load(f)
    except Exception:
        vitals = {}

    vitals["alert_status"] = scenario["alert_status"]
    vitals["execution_audit_log"] = scenario["audit_lines"]
    vitals["read_latency_ms"] = 0.2

    temp_vitals = VITALS_FILE.with_suffix(".tmp")
    with open(temp_vitals, "w", encoding="utf-8") as f:
        json.dump(vitals, f, indent=2)
    os.replace(temp_vitals, VITALS_FILE)


class RetinaRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Zero-cache HTTP request handler for Retina HUD."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_HEAD(self):
        if self.path.split("?")[0] in ("/showroom", "/wire", "/showroom_wire.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return
        if self.path.startswith("/api/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            return
        if self.path.startswith("/stream/c120"):
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            return
        super().do_HEAD()

    def do_GET(self):
        global SHUTTER_CLOSED

        # Wiretap direct request interceptor (page hits & optical stream)
        try:
            intercept_server_request(self)
        except Exception:
            pass

        if self.path.startswith("/api/vfs/browse"):
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            target_path = query_params.get("path", ["/allocator"])[0]
            data = handle_vfs_browse(target_path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        if self.path.startswith("/api/vfs/tail"):
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            target_path = query_params.get("path", [""])[0]
            data = handle_vfs_tail(target_path)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data.encode("utf-8"))
            return

        if self.path.split("?")[0] in ("/showroom", "/wire", "/showroom_wire.html"):
            showroom_path = REPO_ROOT / "apps" / "retina" / "showroom_wire.html"
            if showroom_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(showroom_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        if self.path == "/api/cam/toggle":
            SHUTTER_CLOSED = not SHUTTER_CLOSED
            if SHUTTER_CLOSED:
                global LATEST_FRAME_BYTES
                with FRAME_LOCK:
                    LATEST_FRAME_BYTES = SHUTTER_FRAME_BYTES
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"shutter_closed": SHUTTER_CLOSED, "status": "TOGGLED"}).encode())
            return

        if self.path in ("/api/cam/kill", "/api/cam/off"):
            SHUTTER_CLOSED = True
            with FRAME_LOCK:
                LATEST_FRAME_BYTES = SHUTTER_FRAME_BYTES
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"shutter_closed": True, "status": "KILL"}).encode())
            return

        if self.path in ("/api/cam/start", "/api/cam/on"):
            SHUTTER_CLOSED = False
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"shutter_closed": False, "status": "STREAMING"}).encode())
            return

        if self.path == "/api/cam/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"shutter_closed": SHUTTER_CLOSED, "source": "192.168.1.191:554"}).encode())
            return

        if self.path.startswith("/api/consensus/ground_truth"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            preset = query_params.get("preset", ["SANTA_ANITA_R5"])[0]
            data = GROUND_TRUTH_PRESETS.get(preset, GROUND_TRUTH_PRESETS["SANTA_ANITA_R5"])
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        if self.path.startswith("/api/vector6/messages"):
            channel = "pawel"
            if "?" in self.path:
                query = self.path.split("?", 1)[1]
                for part in query.split("&"):
                    if part.startswith("channel="):
                        channel = part.split("=", 1)[1]
            data = load_vector6_wire(channel)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
            return

        if self.path == "/stream/c120" or self.path.startswith("/stream/c120"):
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            try:
                while True:
                    with FRAME_LOCK:
                        frame = LATEST_FRAME_BYTES if LATEST_FRAME_BYTES is not None else SHUTTER_FRAME_BYTES
                    
                    self.wfile.write(b"--frame\r\n")
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(len(frame)))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                    time.sleep(0.05)
            except (ConnectionResetError, BrokenPipeError):
                pass
            return

        if self.path.startswith("/api/retina/toggle-deck"):
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            deck = query_params.get("deck", [""])[0]
            scenario_key = "SMYRNA_COMMAND_DECK" if deck in ("2", "smyrna", "SMYRNA_COMMAND_DECK") else "CONSEN_SYS_4PANEL"
            apply_scenario(scenario_key)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "APPLIED", "scenario": scenario_key}).encode())
            return

        super().do_GET()

    def do_POST(self):
        if self.path == "/api/wiretap":
            handle_wiretap_beacon(self)
            return

        if self.path == "/api/retina/toggle-deck":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            scenario_key = "SMYRNA_COMMAND_DECK"
            try:
                data = json.loads(body)
                scenario_key = data.get("scenario") or ("SMYRNA_COMMAND_DECK" if str(data.get("deck")) in ("2", "smyrna", "SMYRNA_COMMAND_DECK") else "CONSEN_SYS_4PANEL")
            except Exception:
                pass
            apply_scenario(scenario_key)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "APPLIED", "scenario": scenario_key}).encode())
            return

        if self.path == "/api/consensus/execute":
            content_length = int(self.headers.get("Content-Length", 0))
            preset = "SANTA_ANITA_R5"
            if content_length > 0:
                body = self.rfile.read(content_length).decode('utf-8')
                try:
                    payload = json.loads(body)
                    preset = payload.get("preset", "SANTA_ANITA_R5")
                except Exception:
                    pass
            
            result = asyncio.run(execute_arbitration(preset))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
            return

        if self.path == "/api/allocator/query":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            scenario_key = "SMYRNA_COMMAND_DECK"
            try:
                data = json.loads(body)
                scenario_key = data.get("scenario", "SMYRNA_COMMAND_DECK")
            except Exception:
                pass

            apply_scenario(scenario_key)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "APPLIED", "scenario": scenario_key}).encode())
            return

        if self.path == "/api/vector6/send":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                channel = data.get("channel", "pawel")
                sender = data.get("sender", "james")
                msg_body = data.get("body", "")
                if msg_body.strip():
                    new_msg = append_vector6_message(channel, sender, msg_body)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "SENT", "message": new_msg}).encode())
                    return
            except Exception as e:
                pass

            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ERROR", "detail": "Invalid message payload"}).encode())
            return

        self.send_response(404)
        self.end_headers()

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    print(f"==================================================")
    print(f"⚡ STACKLABS RETINA HTTP & VECTOR6 DIRECT WIRE (PORT {PORT})")
    print(f"Directory: {DIRECTORY}")
    print(f"RTSP Ingress: 192.168.1.191:554/stream2")
    print(f"Allocator API: POST /api/allocator/query")
    print(f"Vector6 Chat API: GET/POST /api/vector6/*")
    print(f"==================================================")

    if not HUD_FILE.exists():
        apply_scenario("SMYRNA_COMMAND_DECK")

    allocator_script = REPO_ROOT / "scripts" / "vfs_allocator_sync.py"
    if allocator_script.exists():
        os.system(f"{sys.executable} {allocator_script}")

    t = threading.Thread(target=c120_capture_loop, daemon=True)
    t.start()

    HOST = os.getenv("RETINA_HOST", "127.0.0.1")
    with ThreadedTCPServer((HOST, PORT), RetinaRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")

if __name__ == "__main__":
    main()

