#!/home/james/stacklabs/.venv/bin/python3
"""
Unifies local skill directories (.agents/skills and ~/.gemini/config/skills),
patches scripts/sync_to_gdrive.sh to keep stacklabs_edge:skills and stacklabs_edge:rules
continuously in sync, and executes an immediate rclone sync to stacklabs_edge:.
"""

import shutil
import subprocess
from pathlib import Path

STACKLABS_ROOT = Path("/home/james/stacklabs")
SECONDARY_ROOT = Path("/home/james/stack" + "labs_inbox")
AGENTS_SKILLS = STACKLABS_ROOT / ".agents" / "skills"
AGENTS_RULES = STACKLABS_ROOT / ".agents" / "rules"
GLOBAL_SKILLS = Path("/home/james/.gemini/config/skills")
SYNC_SCRIPT = STACKLABS_ROOT / "scripts" / "sync_to_gdrive.sh"

GLOBAL_TO_REPO_SKILLS = [
    "eli5-eli-nasa",
    "mobile-export",
    "three-panel-review",
    "token-meter",
]


def unify_local_skills() -> dict:
    copied_to_repo = []
    updated_in_global = []

    for name in GLOBAL_TO_REPO_SKILLS:
        src = GLOBAL_SKILLS / name
        dst = AGENTS_SKILLS / name
        if src.exists() and src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            copied_to_repo.append(name)

    # Also update matching skills in ~/.gemini/config/skills/ from the fresher .agents/skills/
    for repo_skill in sorted(AGENTS_SKILLS.iterdir()):
        if not repo_skill.is_dir() or repo_skill.name.startswith("."):
            continue
        global_target = GLOBAL_SKILLS / repo_skill.name
        if global_target.exists() and (repo_skill / "SKILL.md").exists():
            shutil.copy2(repo_skill / "SKILL.md", global_target / "SKILL.md")
            updated_in_global.append(repo_skill.name)

    # Mirror CMDB_LITE_ACTIVE_TOPOLOGY.md to secondary edge_drive staging if present
    topo_src = STACKLABS_ROOT / "StackLabs_Internal" / "CMDB_LITE_ACTIVE_TOPOLOGY.md"
    topo_dst = SECONDARY_ROOT / "edge_drive" / "StackLabs_Internal" / "CMDB_LITE_ACTIVE_TOPOLOGY.md"
    if topo_src.exists() and topo_dst.parent.exists():
        shutil.copy2(topo_src, topo_dst)

    return {
        "copied_to_repo": copied_to_repo,
        "updated_in_global": len(updated_in_global),
        "total_repo_skills": len([d for d in AGENTS_SKILLS.iterdir() if d.is_dir()]),
    }


def patch_sync_to_gdrive() -> bool:
    content = SYNC_SCRIPT.read_text(encoding="utf-8")
    if "stacklabs_edge:skills" in content:
        return False

    anchor = "/home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/compile_ground_truth_markdown.py >/dev/null 2>&1"
    replacement = (
        anchor
        + "\n/home/james/stacklabs/.venv/bin/python3 /home/james/stacklabs/scripts/artifact_harvester.py >/dev/null 2>&1"
    )
    if anchor in content:
        content = content.replace(anchor, replacement, 1)

    tail_anchor = 'echo "🟢 [K.I.S.S. & LITE] SUCCESS:'
    skills_sync_block = """# 3.8 Sync Canonical Skills, Progressive Rules, and CMDB Lite Topology to stacklabs_edge:
echo "[$(date -Iseconds)] Syncing canonical .agents/skills and .agents/rules to stacklabs_edge:..."
rclone sync "/home/james/stacklabs/.agents/skills" "stacklabs_edge:skills" \\
    --exclude "__pycache__/**" \\
    --exclude "*.pyc" \\
    --timeout 30s --contimeout 10s --fast-list --quiet
rclone sync "/home/james/stacklabs/.agents/rules" "stacklabs_edge:rules" \\
    --timeout 30s --contimeout 10s --fast-list --quiet
rclone copyto "/home/james/stacklabs/AGENTS.md" "stacklabs_edge:rules/AGENTS.md" --timeout 20s --quiet
rclone copyto "/home/james/stacklabs/GEMINI.md" "stacklabs_edge:rules/GEMINI.md" --timeout 20s --quiet
if [ -f "/home/james/stacklabs/StackLabs_Internal/CMDB_LITE_ACTIVE_TOPOLOGY.md" ]; then
    rclone copyto "/home/james/stacklabs/StackLabs_Internal/CMDB_LITE_ACTIVE_TOPOLOGY.md" "stacklabs_edge:StackLabs_Internal/CMDB_LITE_ACTIVE_TOPOLOGY.md" --timeout 20s --quiet
fi
if [ -f "/home/james/stacklabs/today/cmdb_lite_state.json" ]; then
    rclone copyto "/home/james/stacklabs/today/cmdb_lite_state.json" "stacklabs_edge:today/cmdb_lite_state.json" --timeout 20s --quiet
fi

"""
    if tail_anchor in content:
        content = content.replace(tail_anchor, skills_sync_block + tail_anchor, 1)

    SYNC_SCRIPT.write_text(content, encoding="utf-8")
    return True


def sync_now_to_edge() -> None:
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
    subprocess.run(
        [
            "rclone", "sync",
            str(AGENTS_RULES),
            "stacklabs_edge:rules",
            "--timeout", "30s",
            "--fast-list",
        ],
        check=True,
    )
    subprocess.run(
        ["rclone", "copyto", str(STACKLABS_ROOT / "AGENTS.md"), "stacklabs_edge:rules/AGENTS.md"],
        check=True,
    )
    subprocess.run(
        ["rclone", "copyto", str(STACKLABS_ROOT / "GEMINI.md"), "stacklabs_edge:rules/GEMINI.md"],
        check=True,
    )
    subprocess.run(
        [
            "rclone", "copyto",
            str(STACKLABS_ROOT / "StackLabs_Internal" / "CMDB_LITE_ACTIVE_TOPOLOGY.md"),
            "stacklabs_edge:StackLabs_Internal/CMDB_LITE_ACTIVE_TOPOLOGY.md",
        ],
        check=True,
    )
    subprocess.run(
        [
            "rclone", "copyto",
            str(STACKLABS_ROOT / "today" / "cmdb_lite_state.json"),
            "stacklabs_edge:today/cmdb_lite_state.json",
        ],
        check=True,
    )


if __name__ == "__main__":
    res = unify_local_skills()
    patched = patch_sync_to_gdrive()
    sync_now_to_edge()
    print({"unify": res, "sync_script_patched": patched, "edge_sync": "completed"})
