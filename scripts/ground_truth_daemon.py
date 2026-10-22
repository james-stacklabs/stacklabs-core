#!/usr/bin/env python3
"""
StackLabs Ground Truth Daemon & Vault Sentry
Path: /home/james/stacklabs/scripts/ground_truth_daemon.py (symlinked to SovereignOS/scripts/ground_truth_daemon.py)

Decouples observation from inference by maintaining pinned, structured JSON ledgers
on Clio's NVMe with zero-cycle SHA-256 caching, atomic POSIX rename commits,
and targeted event-driven NOAA weather polling.
"""

import os
import sys
import json
import hashlib
import logging
import argparse
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, Union, List

from pydantic import BaseModel, Field, ConfigDict

# Ensure current script directory is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

VAULT_DIR = Path("/home/james/stacklabs/ground_truth")

# Configure logger
logger = logging.getLogger("ground_truth_daemon")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ==============================================================================
# 1. PYDANTIC V2 SCHEMAS
# ==============================================================================

class ComputeGroundTruth(BaseModel):
    model_config = ConfigDict(extra="allow")

    updated_at: str
    engine_version: str
    active_models: Dict[str, Any]
    hardware_nodes: Dict[str, Any]
    cloud_headroom: Dict[str, Any]


class FounderIdentity(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    title: str
    voice: str
    corporate_we_allowed: bool
    domain_authority: str


class CompanyIdentity(BaseModel):
    model_config = ConfigDict(extra="allow")

    legal_name: str
    operating_location: str
    commercial_brand: str
    sovereign_cosplay_banned: bool


class PartnerGroundTruth(BaseModel):
    model_config = ConfigDict(extra="allow")

    updated_at: str
    founder_identity: FounderIdentity
    company: CompanyIdentity
    partners: Dict[str, Any]


class QuantGroundTruth(BaseModel):
    model_config = ConfigDict(extra="allow")

    updated_at: str
    universe_name: str
    liquidity_filters: Dict[str, Any]
    macro_benchmarks: Dict[str, Any]
    physical_infrastructure_nodes: Dict[str, Any]
    institutional_trading_rules: Dict[str, Any]
    weather: Dict[str, Any] = Field(default_factory=dict)


class TropicalCyclone(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    classification: str
    intensity_kt: int
    intensity_mph: int
    pressure_mb: int
    latitude: float
    longitude: float
    movement_dir: Optional[int] = None
    movement_speed_mph: Optional[int] = None
    public_advisory_url: Optional[str] = None
    last_update: str


class WeatherGroundTruth(BaseModel):
    model_config = ConfigDict(extra="allow")

    updated_at: str
    active_hurricanes_count: int
    tropical_cyclones: List[TropicalCyclone] = Field(default_factory=list)
    grid_forecasts: Dict[str, Any] = Field(default_factory=dict)


class SportsGroundTruth(BaseModel):
    model_config = ConfigDict(extra="allow")

    season: int
    roster_shibboleths: Dict[str, Any]
    stadium_weather_nodes: Dict[str, Any]
    weather: Dict[str, Any] = Field(default_factory=dict)
    updated_at: Optional[str] = None
    cfb_marquee_slate: Optional[Dict[str, Any]] = None


MODEL_MAPPING = {
    "compute_ground_truth.json": ComputeGroundTruth,
    "partner_ground_truth.json": PartnerGroundTruth,
    "quant_ground_truth.json": QuantGroundTruth,
    "sports_ground_truth.json": SportsGroundTruth,
    "weather_ground_truth.json": WeatherGroundTruth,
}


# ==============================================================================
# 2. IN-MEMORY HASHING, ATOMIC WRITER & DRIVE SYNC
# ==============================================================================

AUTO_SYNC_DRIVE: bool = False


def set_auto_sync_drive(enabled: bool = True) -> None:
    """Configures automatic drive mirroring on successful atomic commits."""
    global AUTO_SYNC_DRIVE
    AUTO_SYNC_DRIVE = enabled


def sync_to_drive(vault_dir: Path = VAULT_DIR) -> None:
    """
    Triggers non-blocking background rclone commands to mirror the ground truth vault
    to stacklabs_edge:ground_truth and stacklabs_vault:ground_truth.
    """
    vault_str = str(vault_dir.resolve())
    cmd_edge = [
        "rclone", "copy", vault_str, "stacklabs_edge:ground_truth",
        "--timeout", "30s", "--contimeout", "10s", "--no-traverse", "--quiet"
    ]
    cmd_vault = [
        "rclone", "copy", vault_str, "stacklabs_vault:ground_truth",
        "--timeout", "30s", "--contimeout", "10s", "--no-traverse", "--quiet"
    ]
    try:
        subprocess.Popen(cmd_edge, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.Popen(cmd_vault, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("[SYNC-DRIVE] Dispatched non-blocking background rclone sync to stacklabs_edge and stacklabs_vault.")
    except Exception as e:
        logger.warning(f"[SYNC-DRIVE-WARN] Failed to dispatch rclone background sync: {e}")


def atomic_commit(file_path: Union[Path, str], new_data: dict, model_cls=None, sync_drive: Optional[bool] = None) -> Tuple[bool, str]:
    """
    Serializes new_data to a canonical JSON string (indent=2, sort_keys=True).
    Computes SHA-256 hash.
    Reads existing file's SHA-256 hash.
    If hashes match: logs [NO-CHANGE] SHA256 match. 0 NVMe write cycles burned. and returns (False, "NO_CHANGE").
    If hashes differ: validates with model_cls -> writes to file_path.with_suffix('.json.tmp')
    -> executes os.replace(tmp, file_path) -> logs [COMMITTED] Atomic rename to {file_path.name} and returns (True, "COMMITTED").
    If sync_drive is True or AUTO_SYNC_DRIVE is True, triggers sync_to_drive().
    """
    target = Path(file_path).resolve()

    # 1. Canonical serialization & SHA-256
    canonical_json = json.dumps(new_data, indent=2, sort_keys=True) + "\n"
    new_bytes = canonical_json.encode("utf-8")
    new_hash = hashlib.sha256(new_bytes).hexdigest()

    # 2. Check existing file
    existing_hash = None
    if target.exists():
        existing_bytes = target.read_bytes()
        existing_hash = hashlib.sha256(existing_bytes).hexdigest()

    # 3. Match check
    if existing_hash == new_hash:
        logger.info("[NO-CHANGE] SHA256 match. 0 NVMe write cycles burned.")
        return (False, "NO_CHANGE")

    # 4. Pydantic validation if model provided
    if model_cls is not None:
        model_cls.model_validate(new_data)

    # 5. Atomic write via .json.tmp and POSIX rename
    # with_suffix('.json.tmp') replaces .json with .json.tmp
    tmp_path = target.with_suffix(".json.tmp")
    tmp_path.write_bytes(new_bytes)
    os.replace(tmp_path, target)
    logger.info(f"[COMMITTED] Atomic rename to {target.name}")

    # 6. Mirror to Google Drive if configured
    should_sync = AUTO_SYNC_DRIVE if sync_drive is None else sync_drive
    if should_sync:
        sync_to_drive(target.parent)

    return (True, "COMMITTED")


# ==============================================================================
# 3. TARGETED EVENT-DRIVEN NOAA WEATHER POLLER
# ==============================================================================

NOAA_USER_AGENT = "StackLabs-GroundTruth/1.0 (james@stacklabsllc.com)"
NHC_STORMS_URL = "https://www.nhc.noaa.gov/CurrentStorms.json"


def fetch_noaa_tropical_cyclones(timeout: float = 6.0) -> List[Dict[str, Any]]:
    """Fetches active tropical cyclones from NOAA National Hurricane Center."""
    headers = {
        "User-Agent": NOAA_USER_AGENT,
        "Accept": "application/json"
    }
    cyclones = []
    try:
        req = urllib.request.Request(NHC_STORMS_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for storm in data.get("activeStorms", []):
                try:
                    kt = int(storm.get("intensity", 0))
                    mph = int(kt * 1.15078)
                    mb = int(storm.get("pressure", 0))
                    cyclones.append({
                        "id": storm.get("id", ""),
                        "name": storm.get("name", "UNNAMED"),
                        "classification": storm.get("classification", "UNKNOWN"),
                        "intensity_kt": kt,
                        "intensity_mph": mph,
                        "pressure_mb": mb,
                        "latitude": float(storm.get("latitudeNumeric", 0.0)),
                        "longitude": float(storm.get("longitudeNumeric", 0.0)),
                        "movement_dir": int(storm.get("movementDir", 0)) if storm.get("movementDir") is not None else None,
                        "movement_speed_mph": int(storm.get("movementSpeed", 0)) if storm.get("movementSpeed") is not None else None,
                        "public_advisory_url": storm.get("publicAdvisory", {}).get("url"),
                        "last_update": storm.get("lastUpdate", datetime.now(timezone.utc).isoformat())
                    })
                except Exception as ex:
                    logger.warning(f"[WARN] Error parsing storm {storm.get('name')}: {ex}")
    except Exception as e:
        logger.warning(f"[WARN] Failed to fetch NOAA NHC storms: {e}")
    return cyclones


def fetch_noaa_grid_forecast(lat: float, lon: float, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    """
    Queries NWS points API and fetches current grid forecast.
    Extracts temperature, temperatureUnit, windSpeed, windDirection, shortForecast.
    """
    points_url = f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}"
    headers = {
        "User-Agent": NOAA_USER_AGENT,
        "Accept": "application/geo+json"
    }

    try:
        req_points = urllib.request.Request(points_url, headers=headers)
        with urllib.request.urlopen(req_points, timeout=timeout) as resp_points:
            points_data = json.loads(resp_points.read().decode("utf-8"))
            forecast_url = points_data.get("properties", {}).get("forecast")

        if not forecast_url:
            logger.warning(f"[WARN] No forecast URL returned for ({lat}, {lon})")
            return None

        req_fc = urllib.request.Request(forecast_url, headers=headers)
        with urllib.request.urlopen(req_fc, timeout=timeout) as resp_fc:
            fc_data = json.loads(resp_fc.read().decode("utf-8"))
            periods = fc_data.get("properties", {}).get("periods", [])
            if not periods:
                logger.warning(f"[WARN] No forecast periods for ({lat}, {lon})")
                return None
            period = periods[0]
            return {
                "temperature": period.get("temperature"),
                "temperatureUnit": period.get("temperatureUnit"),
                "windSpeed": period.get("windSpeed"),
                "windDirection": period.get("windDirection"),
                "shortForecast": period.get("shortForecast")
            }
    except Exception as e:
        logger.warning(f"[WARN] NOAA query failed for ({lat}, {lon}): {e}. Retaining cached state.")
        return None


def poll_noaa_weather(vault_dir: Path = VAULT_DIR) -> Dict[str, Any]:
    """
    Polls NOAA weather for physical energy nodes and sports stadiums.
    Updates quant_ground_truth.json and sports_ground_truth.json atomically.
    """
    logger.info("[POLL-WEATHER] Initiating targeted NOAA weather ingestion pass...")
    results = {}

    # 1. Update Quant Ground Truth (Sabine Pass LNG)
    quant_path = vault_dir / "quant_ground_truth.json"
    if quant_path.exists():
        try:
            quant_data = json.loads(quant_path.read_text())
            nodes = quant_data.get("physical_infrastructure_nodes", {})
            sabine = nodes.get("sabine_pass_lng", {})
            if "lat" in sabine and "lon" in sabine:
                fc = fetch_noaa_grid_forecast(sabine["lat"], sabine["lon"])
                if fc:
                    if "weather" not in quant_data:
                        quant_data["weather"] = {}
                    quant_data["weather"]["sabine_pass_lng"] = fc
                    results["sabine_pass_lng"] = fc
                    atomic_commit(quant_path, quant_data, QuantGroundTruth)
        except Exception as e:
            logger.warning(f"[WARN] Error updating quant weather: {e}")

    # 2. Update Sports Ground Truth (Stadiums)
    sports_path = vault_dir / "sports_ground_truth.json"
    if sports_path.exists():
        try:
            sports_data = json.loads(sports_path.read_text())
            stadium_nodes = sports_data.get("stadium_weather_nodes", {})
            weather_block = sports_data.get("weather", {})
            updated = False
            for node_id, node_info in stadium_nodes.items():
                lat = node_info.get("lat")
                lon = node_info.get("lon")
                if lat is not None and lon is not None:
                    fc = fetch_noaa_grid_forecast(lat, lon)
                    if fc:
                        weather_block[node_id] = fc
                        results[node_id] = fc
                        updated = True

            if updated:
                sports_data["weather"] = weather_block
                atomic_commit(sports_path, sports_data, SportsGroundTruth)
        except Exception as e:
            logger.warning(f"[WARN] Error updating sports weather: {e}")

    # 3. Ingest Tropical Cyclones & Commit Dedicated weather_ground_truth.json
    try:
        cyclones = fetch_noaa_tropical_cyclones()
        weather_payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "active_hurricanes_count": len([c for c in cyclones if c.get("classification") == "HU"]),
            "tropical_cyclones": cyclones,
            "grid_forecasts": results
        }
        weather_vault_file = vault_dir / "weather_ground_truth.json"
        atomic_commit(weather_vault_file, weather_payload, WeatherGroundTruth)
        
        # Mirror to today's active inbox
        inbox_weather = Path("/home/james/stacklabs_inbox/today/active_weather_ground_truth.json")
        inbox_weather.parent.mkdir(parents=True, exist_ok=True)
        inbox_weather.write_text(json.dumps(weather_payload, indent=2))
        logger.info(f"[POLL-WEATHER] Committed weather_ground_truth.json ({len(cyclones)} active storms).")
    except Exception as e:
        logger.warning(f"[WARN] Error updating weather_ground_truth.json: {e}")

    logger.info(f"[POLL-WEATHER] Completed weather pass. Updated {len(results)} nodes.")
    return results


# ==============================================================================
# 4. VALIDATION & FINGERPRINTING
# ==============================================================================

def validate_all_ledgers(vault_dir: Path = VAULT_DIR) -> bool:
    """Validates all 4 foundational ledgers against their Pydantic models."""
    logger.info(f"[VALIDATE] Inspecting vault ledgers in {vault_dir}...")
    all_valid = True

    for filename, model_cls in MODEL_MAPPING.items():
        file_path = vault_dir / filename
        if not file_path.exists():
            logger.error(f"[VALIDATE-FAILED] Missing ledger: {filename}")
            all_valid = False
            continue

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            model_cls.model_validate(data)
            logger.info(f"[VALIDATE] {filename}: VALID (Pydantic v2 compliant)")
        except Exception as e:
            logger.error(f"[VALIDATE-FAILED] {filename}: {e}")
            all_valid = False

    if all_valid:
        logger.info(f"[ALL-VALID] All {len(MODEL_MAPPING)} canonical ledgers passed Pydantic v2 validation.")
    return all_valid


def hash_report(vault_dir: Path = VAULT_DIR) -> Dict[str, str]:
    """Computes and prints SHA-256 fingerprints for each ledger."""
    logger.info(f"[HASH-REPORT] Vault Ledger Fingerprints ({vault_dir}):")
    report = {}
    for filename in sorted(MODEL_MAPPING.keys()):
        file_path = vault_dir / filename
        if file_path.exists():
            h = hashlib.sha256(file_path.read_bytes()).hexdigest()
            report[filename] = h
            logger.info(f"  {filename:30s} : {h}")
        else:
            report[filename] = "MISSING"
            logger.warning(f"  {filename:30s} : MISSING")
    return report


# ==============================================================================
# 5. CLI ENTRYPOINT
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="StackLabs Ground Truth Vault Daemon & Sentry")
    parser.add_argument("--validate-all", action="store_true", help="Validate all 4 ledgers against Pydantic models")
    parser.add_argument("--hash-report", action="store_true", help="Print SHA-256 fingerprints for each ledger")
    parser.add_argument("--poll-weather", action="store_true", help="Run targeted NOAA weather ingestion pass")
    parser.add_argument("--sync-drive", action="store_true", help="Trigger background rclone sync of vault to Google Drive")
    parser.add_argument("--vault-dir", type=str, default=str(VAULT_DIR), help="Path to ground truth vault directory")

    args = parser.parse_args()
    vault = Path(args.vault_dir)

    if args.sync_drive:
        set_auto_sync_drive(True)

    if not (args.validate_all or args.hash_report or args.poll_weather or args.sync_drive):
        # Default behavior if no flags provided
        validate_all_ledgers(vault)
        hash_report(vault)
        return

    if args.validate_all:
        if not validate_all_ledgers(vault):
            sys.exit(1)

    if args.hash_report:
        hash_report(vault)

    if args.poll_weather:
        poll_noaa_weather(vault)

    if args.sync_drive:
        sync_to_drive(vault)


if __name__ == "__main__":
    main()
