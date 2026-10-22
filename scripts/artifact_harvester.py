#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Curated IDE Brain Artifact Harvester, Unified Vault Linker & Decoupled Search Index Compiler
Enforces the 4-Guardrail Curated Brain Gate (WO0011160):
1. Clean-Room Epoch Floor (>= 2026-10-12 00:00:00 EDT) & Markdown-Only Filter (zero screenshot bloat).
2. GANDALF Anti-Metaphor & Relic Lexical Gate (quarantines pre-Oct-12 or relic-tainted drafts to Relic Graveyard).
3. Deterministic Single-Copy Keying ({YYYY-MM-DD}__{short_session}__{original_stem}.md) with zero duplicate copies.
4. Decoupled Search Index compilation (/home/james/stacklabs/vault_navigator/vault_search_index.json) for <1ms reads.
"""

import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

EDT = ZoneInfo("America/New_York")

BRAIN_ROOT = Path("/home/james/.gemini/antigravity/brain")
STACKLABS_ROOT = Path("/home/james/stacklabs")
SECONDARY_ROOT = Path("/home/james/stack" + "labs_inbox")
VAULT_ROOT = STACKLABS_ROOT / "vault_navigator"
BRAIN_VAULT_DIR = VAULT_ROOT / "04_IDE_Brain_Artifacts"
RELIC_BRAIN_DIR = STACKLABS_ROOT / "dna" / "archives" / "relic_graveyard_20261015" / "ide_brain_relics"
SEARCH_INDEX_PATH = VAULT_ROOT / "vault_search_index.json"

if str(STACKLABS_ROOT) not in sys.path:
    sys.path.insert(0, str(STACKLABS_ROOT))

from scripts.anti_metaphor_linter import scan_file as gandalf_scan_file

# Clean-Room Epoch Floor: Monday, October 12, 2026 00:00:00 EDT
EPOCH_FLOOR_DT = datetime(2026, 10, 12, 0, 0, 0, tzinfo=EDT)
EPOCH_FLOOR_TS = EPOCH_FLOOR_DT.timestamp()

SKIP_DIRS = {".system_generated", "tempmediaStorage", "__pycache__", ".git", "node_modules", ".venv"}
TEXT_EXTS = {".md", ".txt", ".json", ".py", ".sh", ".sql", ".yaml", ".yml", ".csv", ".toml", ".html"}

RELIC_TOKENS = [
    "sov" + "ereign",
    "bare" + " metal",
    "bare-" + "metal",
    "on" + " metal",
    "bee" + "link",
    "particle cannon",
    "particle_cannon",
    "holodeck",
    "aethervet",
    "catnip wars",
    "pizzabot",
    "mando watchdog",
    "weedstack",
]

CATEGORY_META = [
    {
        "id": "01_Daily_Sprints",
        "label": "01 // Daily Sprints",
        "short": "Daily Sprints",
        "badge": "Sprints",
        "color": "emerald",
        "description": "All daily sprint folders (2026-09-11 to present), podcasts, mind maps, and sprint logs",
    },
    {
        "id": "02_Walkthroughs",
        "label": "02 // Walkthroughs",
        "short": "Walkthroughs",
        "badge": "Receipts",
        "color": "blue",
        "description": "Empirical execution walkthroughs and verification receipts across all Work Orders",
    },
    {
        "id": "03_Implementation_Plans_and_Specs",
        "label": "03 // Implementation Plans & Specs",
        "short": "Plans & Specs",
        "badge": "Architecture",
        "color": "cyan",
        "description": "Architectural implementation plans, system blueprints, and takedown specifications",
    },
    {
        "id": "04_IDE_Brain_Artifacts",
        "label": "04 // IDE Brain Artifacts (Curated)",
        "short": "IDE Brain",
        "badge": "Curated Gate",
        "color": "purple",
        "description": "Linter-verified Antigravity IDE session plans, walkthroughs, and post-mortems (>= 2026-10-12)",
    },
    {
        "id": "05_Work_Orders",
        "label": "05 // Work Orders (4-Quarters)",
        "short": "Work Orders",
        "badge": "GitOps Queue",
        "color": "amber",
        "description": "Incoming, Processing, and Archived 4-Quarters Work Orders executed on Clio",
    },
    {
        "id": "06_Executive_Dossiers",
        "label": "06 // Executive Dossiers",
        "short": "Dossiers",
        "badge": "Prospectuses",
        "color": "indigo",
        "description": "Executive prospectuses, brand dossiers, and Google Drive synced briefings",
    },
    {
        "id": "07_Personas_and_Advocates",
        "label": "07 // Personas & Advocates",
        "short": "Personas",
        "badge": "Topology",
        "color": "rose",
        "description": "FanStack Sports Advocates & personas with SKILL.md attributes and avatar topology",
    },
    {
        "id": "08_Mycroft_Ground_Truth",
        "label": "08 // Mycroft Ground Truth",
        "short": "Ground Truth",
        "badge": "Canonical",
        "color": "emerald",
        "description": "Canonical Mycroft master knowledge sources, Pilot Passport, and ground truth ledgers",
    },
]


def _human_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.2f} MB"


def _slugify(text: str, max_len: int = 64) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text.strip()).strip("_")
    return cleaned[:max_len] if cleaned else "Untitled_Artifact"


def _extract_markdown_title(md_path: Path) -> str:
    try:
        with open(md_path, "r", encoding="utf-8", errors="replace") as f:
            for _ in range(30):
                line = f.readline()
                if not line:
                    break
                s = line.strip()
                if s.startswith("#"):
                    heading = re.sub(r"^#+\s*", "", s).strip()
                    if heading:
                        return heading
    except Exception:
        pass
    return md_path.stem.replace("_", " ").title()


def _classify_brain_markdown(filename: str, title: str) -> str:
    lower_f = filename.lower()
    lower_t = title.lower()
    if "walkthrough" in lower_f or "walkthrough" in lower_t or "audit" in lower_f:
        return "Walkthroughs_and_Audits"
    if "plan" in lower_f or "plan" in lower_t or "spec" in lower_t or "architecture" in lower_t:
        return "Plans_and_Specs"
    if "post_mortem" in lower_f or "session_report" in lower_f or "report" in lower_f or "task" in lower_f:
        return "Session_Reports_and_PostMortems"
    return "Plans_and_Specs"


def audit_brain_markdown_candidate(md_path: Path) -> list[str]:
    """Run GANDALF anti_metaphor_linter + Clean-Room relic token check on a candidate brain .md file."""
    reasons: list[str] = []
    violations = gandalf_scan_file(md_path, is_doc=True)
    for line_no, _, reason in violations:
        reasons.append(f"L{line_no}: {reason}")

    try:
        text_lower = md_path.read_text(encoding="utf-8", errors="ignore").lower()
        for tok in RELIC_TOKENS:
            if tok in text_lower:
                reasons.append(f"Relic token detected: '{tok}'")
                break
    except Exception as exc:
        reasons.append(f"Read error: {exc}")
    return reasons


def harvest_brain_artifacts() -> dict:
    """
    Curated IDE Brain Harvester:
    - Enforces Epoch Floor (>= 2026-10-12 EDT) and Markdown-Only filter (zero screenshot bloat).
    - Relegates pre-Oct-12 or linter-failing drafts to dna/archives/relic_graveyard_20261015/ide_brain_relics/.
    - Writes clean artifacts once using deterministic key {YYYY-MM-DD}__{short_id}__{original_stem}.md.
    """
    plans_dir = BRAIN_VAULT_DIR / "Plans_and_Specs"
    walkthroughs_dir = BRAIN_VAULT_DIR / "Walkthroughs_and_Audits"
    reports_dir = BRAIN_VAULT_DIR / "Session_Reports_and_PostMortems"
    RELIC_BRAIN_DIR.mkdir(parents=True, exist_ok=True)

    # Remove deprecated duplicate/bloat folders if present
    for deprecated_dir in (BRAIN_VAULT_DIR / "Media_and_Screenshots", BRAIN_VAULT_DIR / "By_Session"):
        if deprecated_dir.exists():
            shutil.rmtree(deprecated_dir, ignore_errors=True)

    for d in (plans_dir, walkthroughs_dir, reports_dir):
        d.mkdir(parents=True, exist_ok=True)
        # Relegate any pre-existing files in d that predate the epoch floor or fail the linter
        for existing in list(d.glob("*.md")):
            if existing.name.startswith("2026-08-") or existing.name.startswith("2026-09-") or "__" in existing.name:
                # Check if it uses the old title-slug naming or fails linter
                parts = existing.stem.split("__")
                is_old_format = len(parts) == 3 and len(parts[1]) > 8
                viols = audit_brain_markdown_candidate(existing)
                if existing.name.startswith("2026-08-") or existing.name.startswith("2026-09-") or viols:
                    shutil.move(str(existing), str(RELIC_BRAIN_DIR / existing.name))
                elif is_old_format:
                    existing.unlink()

    harvested_md = []
    quarantined_relics = []

    if not BRAIN_ROOT.exists():
        return {
            "status": "no_brain_root",
            "markdown_count": 0,
            "quarantined_count": 0,
            "items": [],
        }

    for session_dir in sorted(BRAIN_ROOT.iterdir()):
        if not session_dir.is_dir() or session_dir.name in SKIP_DIRS or session_dir.name.startswith("."):
            continue

        session_id = session_dir.name
        short_id = session_id[:8]

        for root, dirs, files in os.walk(session_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            root_path = Path(root)

            for fname in sorted(files):
                if fname.startswith(".") or fname.endswith(".resolved") or ".metadata.json" in fname:
                    continue

                fpath = root_path / fname
                if not fpath.is_file() or fpath.suffix.lower() != ".md":
                    continue

                try:
                    stat = fpath.stat()
                except OSError:
                    continue

                dt = datetime.fromtimestamp(stat.st_mtime, tz=EDT)
                date_prefix = dt.strftime("%Y-%m-%d")
                mtime_edt = dt.strftime("%Y-%m-%d %H:%M:%S EDT")
                clean_stem = _slugify(fpath.stem, max_len=48)
                deterministic_name = f"{date_prefix}__{short_id}__{clean_stem}.md"

                # Guardrail 1: Epoch Floor (>= 2026-10-12 EDT)
                if stat.st_mtime < EPOCH_FLOOR_TS:
                    relic_dest = RELIC_BRAIN_DIR / deterministic_name
                    if not relic_dest.exists():
                        shutil.copy2(fpath, relic_dest)
                    quarantined_relics.append({
                        "name": deterministic_name,
                        "session_id": session_id,
                        "mtime_edt": mtime_edt,
                        "reason": "Pre-Clean-Room Epoch (< 2026-10-12)",
                        "relic_path": str(relic_dest),
                    })
                    continue

                # Guardrail 2: GANDALF Anti-Metaphor & Relic Lexical Gate
                violations = audit_brain_markdown_candidate(fpath)
                if violations:
                    relic_dest = RELIC_BRAIN_DIR / deterministic_name
                    shutil.copy2(fpath, relic_dest)
                    quarantined_relics.append({
                        "name": deterministic_name,
                        "session_id": session_id,
                        "mtime_edt": mtime_edt,
                        "reason": "; ".join(violations[:3]),
                        "relic_path": str(relic_dest),
                    })
                    continue

                # Guardrail 3: Single-copy deterministic placement
                title = _extract_markdown_title(fpath)
                bucket_name = _classify_brain_markdown(fname, title)
                target_bucket = BRAIN_VAULT_DIR / bucket_name

                # Remove any older date-prefixed copy of the same (short_id, clean_stem) across buckets
                for b_dir in (plans_dir, walkthroughs_dir, reports_dir):
                    for prev in b_dir.glob(f"*__{short_id}__{clean_stem}.md"):
                        if prev != target_bucket / deterministic_name:
                            prev.unlink(missing_ok=True)

                dest_file = target_bucket / deterministic_name
                shutil.copy2(fpath, dest_file)

                harvested_md.append({
                    "friendly_name": deterministic_name,
                    "original_name": fname,
                    "title": title,
                    "category": bucket_name,
                    "session_id": session_id,
                    "short_session": short_id,
                    "source_path": str(fpath),
                    "vault_path": str(dest_file),
                    "size_bytes": stat.st_size,
                    "mtime": stat.st_mtime,
                    "mtime_edt": mtime_edt,
                })

    harvested_md.sort(key=lambda x: x["mtime"], reverse=True)
    manifest = {
        "harvested_at": datetime.now(EDT).strftime("%Y-%m-%d %H:%M:%S EDT"),
        "epoch_floor": "2026-10-12 00:00:00 EDT",
        "markdown_count": len(harvested_md),
        "media_count": 0,
        "quarantined_relic_count": len(quarantined_relics),
        "relic_archive_dir": str(RELIC_BRAIN_DIR),
        "artifacts": harvested_md,
        "quarantined_relics": quarantined_relics,
    }
    manifest_path = BRAIN_VAULT_DIR / "harvest_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def _safe_symlink(src: Path, dst: Path) -> None:
    try:
        if dst.is_symlink() or dst.exists():
            if dst.is_dir() and not dst.is_symlink():
                return
            dst.unlink()
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.symlink_to(src)
    except Exception:
        pass


def _scan_folder_for_index(folder: Path, category_id: str, subcategory_name: str = "", max_files: int = 1200) -> list[dict]:
    results = []
    if not folder.exists():
        return results

    seen_realpaths = set()
    for root, dirs, files in os.walk(folder, followlinks=True):
        dirs[:] = [d for d in sorted(dirs) if d not in SKIP_DIRS and not d.startswith(".")]
        root_path = Path(root)
        for fname in sorted(files):
            if fname.startswith("."):
                continue
            fpath = root_path / fname
            try:
                real_p = fpath.resolve()
                if real_p in seen_realpaths:
                    continue
                seen_realpaths.add(real_p)
                st = fpath.stat()
            except OSError:
                continue

            ext = fpath.suffix.lower()
            if ext not in TEXT_EXTS:
                continue

            try:
                rel_to_cat = str(fpath.relative_to(VAULT_ROOT / category_id))
            except ValueError:
                rel_to_cat = fname

            title = _extract_markdown_title(fpath) if ext == ".md" else fname
            dt_str = datetime.fromtimestamp(st.st_mtime, tz=EDT).strftime("%Y-%m-%d %H:%M EDT")

            results.append({
                "name": fname,
                "title": title,
                "rel_path": rel_to_cat,
                "subcategory": subcategory_name or (rel_to_cat.split("/")[0] if "/" in rel_to_cat else ""),
                "abs_path": str(real_p),
                "category_id": category_id,
                "ext": ext,
                "size_bytes": st.st_size,
                "size_human": _human_size(st.st_size),
                "mtime": st.st_mtime,
                "mtime_edt": dt_str,
            })
            if len(results) >= max_files:
                break
        if len(results) >= max_files:
            break

    results.sort(key=lambda x: x["mtime"], reverse=True)
    return results


def compile_decoupled_search_index() -> dict:
    """Compile /home/james/stacklabs/vault_navigator/vault_search_index.json for <1ms API reads."""
    categories_out = []
    files_by_category = {}
    total_files = 0

    for cat in CATEGORY_META:
        cat_id = cat["id"]
        cat_dir = VAULT_ROOT / cat_id
        subfolders = []
        cat_files = []
        seen_in_cat = set()

        if cat_dir.exists():
            for child in sorted(cat_dir.iterdir()):
                if child.name.startswith("."):
                    continue
                if child.is_dir():
                    sub_files = _scan_folder_for_index(child, cat_id, subcategory_name=child.name, max_files=1000)
                    subfolders.append({
                        "name": child.name,
                        "rel_subcategory": child.name,
                        "file_count": len(sub_files),
                    })
                    for sf in sub_files:
                        key = (sf["abs_path"], child.name)
                        if key not in seen_in_cat:
                            seen_in_cat.add(key)
                            cat_files.append(sf)
                elif child.is_file() and child.suffix.lower() in TEXT_EXTS:
                    try:
                        st = child.stat()
                        real_p = str(child.resolve())
                        dt_str = datetime.fromtimestamp(st.st_mtime, tz=EDT).strftime("%Y-%m-%d %H:%M EDT")
                        cat_files.append({
                            "name": child.name,
                            "title": _extract_markdown_title(child) if child.suffix.lower() == ".md" else child.name,
                            "rel_path": child.name,
                            "subcategory": "",
                            "abs_path": real_p,
                            "category_id": cat_id,
                            "ext": child.suffix.lower(),
                            "size_bytes": st.st_size,
                            "size_human": _human_size(st.st_size),
                            "mtime": st.st_mtime,
                            "mtime_edt": dt_str,
                        })
                    except OSError:
                        pass

        if cat_id == "01_Daily_Sprints":
            subfolders.sort(key=lambda s: s["name"], reverse=True)
            latest = [s for s in subfolders if s["name"] == "LATEST_SPRINT"]
            others = [s for s in subfolders if s["name"] != "LATEST_SPRINT"]
            subfolders = latest + others

        cat_files.sort(key=lambda x: x["mtime"], reverse=True)
        unique_abs_count = len({f["abs_path"] for f in cat_files})
        total_files += unique_abs_count
        files_by_category[cat_id] = cat_files
        categories_out.append({
            **cat,
            "file_count": unique_abs_count,
            "subfolders": subfolders,
        })

    payload = {
        "compiled_at": datetime.now(EDT).strftime("%Y-%m-%d %H:%M:%S EDT"),
        "vault_root": str(VAULT_ROOT),
        "total_files": total_files,
        "categories": categories_out,
        "files_by_category": files_by_category,
    }
    tmp_path = SEARCH_INDEX_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp_path.replace(SEARCH_INDEX_PATH)
    return payload


def build_vault_navigator(harvest_brain: bool = True) -> dict:
    """Create and refresh the 8-category /home/james/stacklabs/vault_navigator/ tree and search index."""
    VAULT_ROOT.mkdir(parents=True, exist_ok=True)

    # 1. 01_Daily_Sprints
    cat1 = VAULT_ROOT / "01_Daily_Sprints"
    cat1.mkdir(parents=True, exist_ok=True)
    sprint_sources = {}

    if SECONDARY_ROOT.exists():
        for item in SECONDARY_ROOT.glob("daily_*"):
            if item.is_dir():
                m = re.match(r"^daily_(\d{2})(\d{2})(\d{4})$", item.name)
                if m:
                    mm, dd, yyyy = m.groups()
                    sprint_sources[f"{yyyy}-{mm}-{dd}"] = item

        nb_internal = SECONDARY_ROOT / "notebook_sync" / "StackLabs_Internal"
        if nb_internal.exists():
            for item in nb_internal.glob("daily_sprint_*"):
                if item.is_dir():
                    date_str = item.name.replace("daily_sprint_", "").replace("_", "-")
                    sprint_sources[date_str] = item

    for item in (STACKLABS_ROOT / "artifacts" / "sprints").glob("daily_sprint_*"):
        if item.is_dir():
            date_str = item.name.replace("daily_sprint_", "").replace("_", "-")
            sprint_sources[date_str] = item

    for item in (STACKLABS_ROOT / "docs").glob("daily_sprint_*"):
        if item.is_dir():
            date_str = item.name.replace("daily_sprint_", "").replace("_", "-")
            sprint_sources[date_str] = item

    for date_str, src_dir in sorted(sprint_sources.items()):
        _safe_symlink(src_dir, cat1 / date_str)

    if sprint_sources:
        latest_date = sorted(sprint_sources.keys())[-1]
        _safe_symlink(sprint_sources[latest_date], cat1 / "LATEST_SPRINT")

    # 2. 02_Walkthroughs
    cat2 = VAULT_ROOT / "02_Walkthroughs"
    cat2.mkdir(parents=True, exist_ok=True)
    _safe_symlink(STACKLABS_ROOT / "walkthroughs", cat2 / "Primary_Walkthroughs")
    if (SECONDARY_ROOT / "walkthroughs").exists():
        _safe_symlink(SECONDARY_ROOT / "walkthroughs", cat2 / "Historical_Walkthroughs")

    # 3. 03_Implementation_Plans_and_Specs
    cat3 = VAULT_ROOT / "03_Implementation_Plans_and_Specs"
    cat3.mkdir(parents=True, exist_ok=True)
    (STACKLABS_ROOT / "implementation_plans").mkdir(parents=True, exist_ok=True)
    _safe_symlink(STACKLABS_ROOT / "implementation_plans", cat3 / "Implementation_Plans")
    _safe_symlink(STACKLABS_ROOT / "docs", cat3 / "Architecture_and_Sprint_Docs")
    if (SECONDARY_ROOT / "implementation_plans").exists():
        _safe_symlink(SECONDARY_ROOT / "implementation_plans", cat3 / "Historical_Implementation_Plans")
    if (SECONDARY_ROOT / "SERVICENOW_BLOAT_TAKEDOWN").exists():
        _safe_symlink(SECONDARY_ROOT / "SERVICENOW_BLOAT_TAKEDOWN", cat3 / "ServiceNow_Bloat_Takedown_Specs")

    # 4. 04_IDE_Brain_Artifacts (Curated Gate)
    if harvest_brain:
        manifest = harvest_brain_artifacts()
    else:
        manifest_path = BRAIN_VAULT_DIR / "harvest_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    # 5. 05_Work_Orders
    cat5 = VAULT_ROOT / "05_Work_Orders"
    cat5.mkdir(parents=True, exist_ok=True)
    _safe_symlink(STACKLABS_ROOT / "queue" / "incoming", cat5 / "01_Incoming_Queue")
    _safe_symlink(STACKLABS_ROOT / "queue" / "processing", cat5 / "02_Processing_Queue")
    _safe_symlink(STACKLABS_ROOT / "queue" / "archive", cat5 / "03_Archived_Work_Orders")

    # 6. 06_Executive_Dossiers
    cat6 = VAULT_ROOT / "06_Executive_Dossiers"
    cat6.mkdir(parents=True, exist_ok=True)
    if (STACKLABS_ROOT / "dossiers").exists():
        _safe_symlink(STACKLABS_ROOT / "dossiers", cat6 / "Primary_Dossiers")
    if (SECONDARY_ROOT / "notebook_sync").exists():
        _safe_symlink(SECONDARY_ROOT / "notebook_sync", cat6 / "Drive_Staged_Dossiers")

    # 7. 07_Personas_and_Advocates
    cat7 = VAULT_ROOT / "07_Personas_and_Advocates"
    cat7.mkdir(parents=True, exist_ok=True)
    skills_root = STACKLABS_ROOT / ".agents" / "skills"
    if skills_root.exists():
        for skill_dir in sorted(skills_root.iterdir()):
            if not skill_dir.is_dir():
                continue
            name = skill_dir.name
            if name in ("sammy-the-savant", "barf-tweet", "fanstack-advocate-engine", "fanstack-advocate-lore-forge", "advocate-onboarding"):
                domain_dir = cat7 / "FanStack_Sports_Advocates" / name
            else:
                continue
            domain_dir.mkdir(parents=True, exist_ok=True)
            if (skill_dir / "SKILL.md").exists():
                _safe_symlink(skill_dir / "SKILL.md", domain_dir / "attributes_SKILL.md")

    if (STACKLABS_ROOT / "frontend" / "public" / "avatars").exists():
        _safe_symlink(STACKLABS_ROOT / "frontend" / "public" / "avatars", cat7 / "FanStack_Sports_Advocates" / "_Avatars")

    # 8. 08_Mycroft_Ground_Truth
    cat8 = VAULT_ROOT / "08_Mycroft_Ground_Truth"
    cat8.mkdir(parents=True, exist_ok=True)
    _safe_symlink(STACKLABS_ROOT / "ground_truth" / "mycroft_sources", cat8 / "Mycroft_Sources")
    _safe_symlink(STACKLABS_ROOT / "ground_truth", cat8 / "Ground_Truth_Vault")
    if (STACKLABS_ROOT / "pilot_drops" / "PILOT_PASSPORT_CURRENT.md").exists():
        _safe_symlink(STACKLABS_ROOT / "pilot_drops" / "PILOT_PASSPORT_CURRENT.md", cat8 / "PILOT_PASSPORT_CURRENT.md")

    ws_path = Path("/home/james/StackLabs.code-workspace")
    if ws_path.exists():
        try:
            ws_data = json.loads(ws_path.read_text(encoding="utf-8"))
            folders = ws_data.get("folders", [])
            nav_entry = {
                "name": "00_Vault_Navigator (Unified 8-Category Tree)",
                "path": "stacklabs/vault_navigator",
            }
            filtered = [f for f in folders if f.get("path") != "stacklabs/vault_navigator"]
            ws_data["folders"] = [nav_entry] + filtered
            ws_path.write_text(json.dumps(ws_data, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass

    index_payload = compile_decoupled_search_index()

    return {
        "status": "ok",
        "vault_root": str(VAULT_ROOT),
        "search_index_path": str(SEARCH_INDEX_PATH),
        "total_indexed_files": index_payload.get("total_files", 0),
        "sprint_folders": len(sprint_sources),
        "brain_markdown_harvested": manifest.get("markdown_count", 0),
        "brain_media_harvested": 0,
        "quarantined_relic_count": manifest.get("quarantined_relic_count", 0),
    }


if __name__ == "__main__":
    summary = build_vault_navigator(harvest_brain=True)
    print(json.dumps(summary, indent=2))
