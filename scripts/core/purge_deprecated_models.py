#!/usr/bin/env python3
"""
scripts/core/purge_deprecated_models.py
=============================================================================
Safely purges deprecated legacy Gemini 2.5 and 3.5 models and replaces with
canonical 'gemini-3.8-flash' across all scripts, validating with py_compile.
=============================================================================
"""

import sys
import py_compile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

FILES_TO_PATCH = [
    SCRIPTS_DIR / "analyze_metsy_emotions.py",
    SCRIPTS_DIR / "auto_content_gen.py",
    SCRIPTS_DIR / "backyard_game_master.py",
    SCRIPTS_DIR / "barf_edge_synthesizer.py",
    SCRIPTS_DIR / "clio_console_crawler.py",
    SCRIPTS_DIR / "clio_root_crawler.py",
    SCRIPTS_DIR / "describe_img.py",
    SCRIPTS_DIR / "extract_postgame_context.py",
    SCRIPTS_DIR / "fanstack_chatbots.py",
    SCRIPTS_DIR / "fanstack_relay.py",
    SCRIPTS_DIR / "fanstack_rom_orchestrator.py",
    SCRIPTS_DIR / "fanstack_vertex_crawl.py",
    SCRIPTS_DIR / "fanstack_video_analysis.py",
    SCRIPTS_DIR / "flow_video_generator.py",
    SCRIPTS_DIR / "generate_avatar_prompts.py",
    SCRIPTS_DIR / "generate_metsy_adventures_daily.py",
    SCRIPTS_DIR / "generate_universal_advocate.py",
    SCRIPTS_DIR / "harvest_fanstack_training_data.py",
    SCRIPTS_DIR / "hot_takes_service.py",
    SCRIPTS_DIR / "kanban_poller.py",
    SCRIPTS_DIR / "live_llm_engine.py",
    SCRIPTS_DIR / "mard_editorial_chamber.py",
    SCRIPTS_DIR / "masters_chatbots.py",
    SCRIPTS_DIR / "media_manuel_agent.py",
    SCRIPTS_DIR / "nfl_live_streamer.py",
    SCRIPTS_DIR / "pixie_uiux_evaluator.py",
    SCRIPTS_DIR / "plie_optical_sync.py",
    SCRIPTS_DIR / "postgame_responder.py",
    SCRIPTS_DIR / "precog_pipeline.py",
    SCRIPTS_DIR / "prospectus_crawl.py",
    SCRIPTS_DIR / "screenshot_to_chronicle.py",
    SCRIPTS_DIR / "scruffys_bar_server.py",
    SCRIPTS_DIR / "scruffys_pub_sim.py",
    SCRIPTS_DIR / "sdlc_persona_onboarder.py",
    SCRIPTS_DIR / "sdlc_portal_server.py",
    SCRIPTS_DIR / "setup_all_rooms.py",
    SCRIPTS_DIR / "sovereign_portal_uat.py",
    SCRIPTS_DIR / "sports" / "harvest_game2_meltdown.py",
    SCRIPTS_DIR / "stack_seeder_cli.py",
    SCRIPTS_DIR / "stream_sniper_daemon.py",
    SCRIPTS_DIR / "test_genai_keys.py",
    SCRIPTS_DIR / "the_skew_chatbots.py",
    SCRIPTS_DIR / "the_skew_relay.py",
    SCRIPTS_DIR / "vertex_persona_audit.py",
    SCRIPTS_DIR / "routers" / "assembly.py",
    SCRIPTS_DIR / "routers" / "command_hub.py",
    SCRIPTS_DIR / "routers" / "personas.py",
    SCRIPTS_DIR / "routers" / "sdlc_common.py",
    SCRIPTS_DIR / "routers" / "sdlc_gaming.py",
    SCRIPTS_DIR / "routers" / "system_ops.py",
    SCRIPTS_DIR / "core" / "api_client.py",
    SCRIPTS_DIR / "core" / "assembly_pipeline_engine.py",
]

PREFIX = "gemini"
TARGET_REPLACEMENTS = [
    (f"{PREFIX}-3.5-flash-lite-lite", f"{PREFIX}-3.8-flash"),
    (f"{PREFIX}-3.5-flash-lite", f"{PREFIX}-3.8-flash"),
    (f"{PREFIX}-2.5-flash-lite", f"{PREFIX}-3.8-flash"),
    (f"{PREFIX}-2.5-flash", f"{PREFIX}-3.8-flash"),
    (f"{PREFIX}-2.5-pro", f"{PREFIX}-3.8-flash"),
]


def main():
    patched_count = 0
    replacement_count = 0

    # Collect all candidate files from explicit list plus dynamic scan of scripts/
    seen_paths = set()
    all_targets = []
    for p in FILES_TO_PATCH:
        if p.exists() and p not in seen_paths:
            seen_paths.add(p)
            all_targets.append(p)

    for p in sorted(SCRIPTS_DIR.rglob("*.py")):
        if "_archive" in str(p) or p == Path(__file__).resolve():
            continue
        if p not in seen_paths:
            seen_paths.add(p)
            all_targets.append(p)

    for path in all_targets:
        if not path.is_file():
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue

        file_modified = False
        new_content = content
        file_replacements = 0

        for old_str, new_str in TARGET_REPLACEMENTS:
            if old_str in new_content:
                count = new_content.count(old_str)
                new_content = new_content.replace(old_str, new_str)
                file_replacements += count
                file_modified = True

        if file_modified:
            path.write_text(new_content, encoding="utf-8")
            try:
                py_compile.compile(str(path), doraise=True)
                print(f"[OK] Patched {path.name}: {file_replacements} instance(s) replaced")
                patched_count += 1
                replacement_count += file_replacements
            except Exception as e:
                # Revert on compile failure
                path.write_text(content, encoding="utf-8")
                print(f"[ERROR] Reverted {path.name} due to syntax error: {e}")

    print(f"\n[DONE] Successfully patched {patched_count} files ({replacement_count} total replacements).")


if __name__ == "__main__":
    main()
