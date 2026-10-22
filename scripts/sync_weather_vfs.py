#!/usr/bin/env python3
"""
scripts/sync_weather_vfs.py
Projects Physical Stadium Weather & Hurricane Barometrics to /dev/shm/faas_vfs/weather/
Author: James Carroll (Pilot) & Cockpit Architect
Target: Clio Metal (AMD Ryzen 7 7735HS, NVMe PCIe 4.0)
Invariants: 0, 15, 32, 35, 50
"""
import json
from pathlib import Path

VENUES_PATH = Path("/home/james/stacklabs/ground_truth/stadium_venues.json")
WEATHER_PATH = Path("/home/james/stacklabs/ground_truth/weather_ground_truth.json")
VFS_WEATHER_ROOT = Path("/dev/shm/faas_vfs/weather")

def sync_weather_to_vfs():
    VFS_WEATHER_ROOT.mkdir(parents=True, exist_ok=True)

    venues_data = json.loads(VENUES_PATH.read_text()).get("venues", {})
    weather_data = json.loads(WEATHER_PATH.read_text())
    
    grid_forecasts = weather_data.get("grid_forecasts", {})
    cyclones = weather_data.get("tropical_cyclones", [])

    # Check for active major storms (pressure < 990 mb or intensity > 60 mph)
    hurricane_threat = False
    active_storm_name = "NONE"
    storm_pressure = 1013
    for c in cyclones:
        if c.get("intensity_mph", 0) >= 60 or c.get("pressure_mb", 1013) <= 990:
            hurricane_threat = True
            active_storm_name = c.get("name", "UNKNOWN")
            storm_pressure = c.get("pressure_mb", 942)
            break

    count = 0
    for team, info in venues_data.items():
        zip_code = info.get("zip_code", "00000")
        venue_dir = VFS_WEATHER_ROOT / zip_code
        venue_dir.mkdir(parents=True, exist_ok=True)

        # Write venue metadata
        (venue_dir / "team.txt").write_text(f"{team}\n")
        (venue_dir / "venue_name.txt").write_text(f"{info.get('venue_name', '')}\n")
        (venue_dir / "roof.txt").write_text(f"{info.get('roof', 'open')}\n")
        (venue_dir / "surface.txt").write_text(f"{info.get('surface', 'turf')}\n")
        (venue_dir / "elevation_ft.txt").write_text(f"{info.get('elevation_ft', 0)}\n")

        # Map active physical weather
        # Match venue against forecast keys or fallback to standard regional baseline
        temp = 72
        wind_speed = 5
        wind_dir = "N"
        if "citi" in info.get("venue_name", "").lower() and "citi_field" in grid_forecasts:
            fc = grid_forecasts["citi_field"]
            temp = fc.get("temperature", 72)
            wind_speed = int(fc.get("windSpeed", "5 mph").split()[0])
            wind_dir = fc.get("windDirection", "N")
        elif "citizens" in info.get("venue_name", "").lower() and "citizens_bank_park" in grid_forecasts:
            fc = grid_forecasts["citizens_bank_park"]
            temp = fc.get("temperature", 72)
            wind_speed = int(fc.get("windSpeed", "5 mph").split()[0]) if fc.get("windSpeed") else 0
            wind_dir = fc.get("windDirection", "CALM")

        # Primary leaves as specified in Artifact 1
        (venue_dir / "temperature_f.txt").write_text(f"{temp}\n")
        (venue_dir / "wind_speed_mph.txt").write_text(f"{wind_speed}\n")
        (venue_dir / "wind_direction.txt").write_text(f"{wind_dir}\n")
        (venue_dir / "hurricane_threat.txt").write_text(f"{'ACTIVE' if hurricane_threat else 'NONE'}\n")
        (venue_dir / "storm_name.txt").write_text(f"{active_storm_name}\n")

        # Aliases / additional scalars specified in Section 1.2
        (venue_dir / "temp_f.txt").write_text(f"{temp}\n")
        (venue_dir / "wind_mph.txt").write_text(f"{wind_speed}\n")
        (venue_dir / "wind_dir.txt").write_text(f"{wind_dir}\n")
        (venue_dir / "pressure_mb.txt").write_text(f"{storm_pressure if hurricane_threat else 1013}\n")
        (venue_dir / "hurricane_alert.txt").write_text(f"{'ACTIVE' if hurricane_threat else 'NONE'}\n")
        count += 1

    print(f"[PASS] Successfully synchronized {count} venue zip codes to {VFS_WEATHER_ROOT}")

if __name__ == "__main__":
    sync_weather_to_vfs()
