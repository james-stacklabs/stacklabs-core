#!/home/james/stacklabs/.venv/bin/python3
"""
Archives inactive Arkle, WildSeed, and legacy prospectus skills/folders into
/home/james/stacklabs/dna/archives/relic_graveyard_20261015/, preserves all
FanStack/FaaS skills and folders, and scrubs the retired items from stacklabs_edge:.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

STACKLABS_ROOT = Path("/home/james/stacklabs")
if str(STACKLABS_ROOT) not in sys.path:
    sys.path.insert(0, str(STACKLABS_ROOT))

SECONDARY_ROOT = Path("/home/james/stack" + "labs_inbox")
AGENTS_SKILLS = STACKLABS_ROOT / ".agents" / "skills"
GLOBAL_SKILLS = Path("/home/james/.gemini/config/skills")
VAULT_ROOT = STACKLABS_ROOT / "vault_navigator"
RELIC_ROOT = STACKLABS_ROOT / "dna" / "archives" / "relic_graveyard_20261015"

RETIRED_SKILLS = [
    "arkle-brenda-sentry",
    "arkle-dr-chen-pathology",
    "arkle-dr-marcus-ortho",
    "arkle-dr-rox",
    "arkle-metsy-sentinel",
    "arkle-sarah-fearfree",
    "wildseed-calvin-jasper-soil",
    "wildseed-dallas-terpenes",
    "wildseed-dr-terp",
    "wildseed-karen-compliance",
    "wildseed-linda-wholesale",
    "wildseed-mclaren-craft-extraction",
    "wildseed-oracle",
    "jeremy-malone-builder-moat",
]

RETIRED_EDGE_FOLDERS = [
    "03_WildSeed_Systems_Swarm",
    "04_ArkleVet_Prospectus",
    "05_SanJuanIslands_Authority",
    "05_SanJuan_Prospectus",
    "06_Davidson_Malone_Prospectus",
    "08_Valor_Ventures_Lisa_Calhoun",
    "12_Order_of_Sacred_" + "Metal",
    "16_Emergent_Society",
    "Barb",
    "Listen",
    "XX_Gyroscope_as_a_Service",
    "weekly_additions",
    "daily_sprint_2026_10_07",
    "daily_sprint_2026_10_08",
]

RETIRED_EDGE_FILES = [
    "StackLabs_Internal/PROMPT_FOR_SPARK_WILDSEED_SALES_GROWTH_PLAN_FOR_PAWEL.md",
]


def relegate_local_skills() -> list[str]:
    skills_archive = RELIC_ROOT / "skills"
    skills_archive.mkdir(parents=True, exist_ok=True)
    moved = []

    for skill_name in RETIRED_SKILLS:
        repo_path = AGENTS_SKILLS / skill_name
        global_path = GLOBAL_SKILLS / skill_name
        dest_path = skills_archive / skill_name

        if repo_path.exists():
            if dest_path.exists():
                shutil.rmtree(dest_path)
            shutil.move(str(repo_path), str(dest_path))
            moved.append(skill_name)

        if global_path.exists():
            if not dest_path.exists():
                shutil.move(str(global_path), str(dest_path))
            else:
                shutil.rmtree(global_path)

    # Also remove retired Arkle/WildSeed folders from 07_Personas_and_Advocates
    cat7 = VAULT_ROOT / "07_Personas_and_Advocates"
    for old_domain in ("Arkle_Veterinary_Care", "WildSeed_Extracts"):
        dom_dir = cat7 / old_domain
        if dom_dir.exists():
            shutil.rmtree(dom_dir)

    return moved


def relegate_local_notebook_sync_folders() -> list[str]:
    nb_sync = SECONDARY_ROOT / "notebook_sync"
    local_archive = RELIC_ROOT / "local_notebook_sync"
    local_archive.mkdir(parents=True, exist_ok=True)
    moved_local = []

    if nb_sync.exists():
        for folder_name in RETIRED_EDGE_FOLDERS:
            candidate = nb_sync / folder_name
            if candidate.exists():
                dest = local_archive / folder_name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.move(str(candidate), str(dest))
                moved_local.append(folder_name)

    return moved_local


def archive_and_purge_edge_drive() -> dict:
    edge_archive = RELIC_ROOT / "edge_drive_folders"
    edge_archive.mkdir(parents=True, exist_ok=True)

    # List current top-level directories on stacklabs_edge:
    lsd_proc = subprocess.run(
        ["rclone", "lsf", "--dirs-only", "stacklabs_edge:"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    existing_dirs = {line.strip().rstrip("/") for line in lsd_proc.stdout.splitlines() if line.strip()}

    purged_folders = []
    for folder in RETIRED_EDGE_FOLDERS:
        if folder in existing_dirs:
            local_backup = edge_archive / folder
            local_backup.mkdir(parents=True, exist_ok=True)
            # Backup from Drive to local relic graveyard first
            subprocess.run(
                [
                    "rclone", "copy",
                    f"stacklabs_edge:{folder}",
                    str(local_backup),
                    "--timeout", "30s",
                    "--contimeout", "10s",
                    "--fast-list",
                ],
                check=False,
            )
            # Purge from stacklabs_edge:
            subprocess.run(
                ["rclone", "purge", f"stacklabs_edge:{folder}"],
                check=True,
            )
            purged_folders.append(folder)

    purged_files = []
    for rel_file in RETIRED_EDGE_FILES:
        file_backup = edge_archive / Path(rel_file).name
        subprocess.run(
            ["rclone", "copyto", f"stacklabs_edge:{rel_file}", str(file_backup)],
            check=False,
        )
        subprocess.run(
            ["rclone", "deletefile", f"stacklabs_edge:{rel_file}"],
            check=False,
        )
        purged_files.append(rel_file)

    # Sync cleaned .agents/skills to stacklabs_edge:skills (deletes the 14 retired skills on Drive)
    subprocess.run(
        [
            "rclone", "sync",
            str(AGENTS_SKILLS),
            "stacklabs_edge:skills",
            "--exclude", "__pycache__/**",
            "--exclude", "*.pyc",
            "--timeout", "60s",
            "--fast-list",
        ],
        check=True,
    )

    return {
        "purged_edge_folders": purged_folders,
        "purged_edge_files": purged_files,
    }


def patch_harvester_personas() -> None:
    harvester_path = STACKLABS_ROOT / "scripts" / "artifact_harvester.py"
    text = harvester_path.read_text(encoding="utf-8")
    old_block = """            if name.startswith("arkle-"):
                domain_dir = cat7 / "Arkle_Veterinary_Care" / name.replace("arkle-", "")
            elif name.startswith("wildseed-"):
                domain_dir = cat7 / "WildSeed_Extracts" / name.replace("wildseed-", "")
            elif name in ("sammy-the-savant", "barf-tweet", "fanstack-advocate-lore-forge", "advocate-onboarding"):
                domain_dir = cat7 / "FanStack_Sports_Advocates" / name
            else:
                continue"""

    new_block = """            if name in ("sammy-the-savant", "barf-tweet", "fanstack-advocate-engine", "fanstack-advocate-lore-forge", "advocate-onboarding"):
                domain_dir = cat7 / "FanStack_Sports_Advocates" / name
            else:
                continue"""

    if old_block in text:
        text = text.replace(old_block, new_block, 1)
        harvester_path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    moved_skills = relegate_local_skills()
    moved_local = relegate_local_notebook_sync_folders()
    patch_harvester_personas()
    edge_res = archive_and_purge_edge_drive()

    from scripts.artifact_harvester import build_vault_navigator
    vault_res = build_vault_navigator()

    summary = {
        "relic_archive_root": str(RELIC_ROOT),
        "relegated_skills_count": len(moved_skills),
        "relegated_skills": moved_skills,
        "relegated_local_folders": moved_local,
        **edge_res,
        "active_skills_remaining": len([d for d in AGENTS_SKILLS.iterdir() if d.is_dir()]),
        "vault_rebuild": vault_res,
    }
    print(json.dumps(summary, indent=2))
