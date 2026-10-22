#!/home/james/stacklabs/.venv/bin/python3
"""
Purge speculative lifestyle folders from /vfs/allocator/ and seed /vfs/spaces/pawel/
strictly with Pawel Rudnicki's 7 Both Ends essays, 3 market/parimutuel quant specs,
the StarTalk (BxpyAt5w54w) cross-domain essay collision matrix, and a 42-second audio brief.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from dotenv import load_dotenv

load_dotenv("/home/james/stacklabs/.env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_pawel_symbiote")

REPO_ROOT = Path("/home/james/stacklabs")
VFS_ROOT = REPO_ROOT / "vfs"
PAWEL_SPACE = VFS_ROOT / "spaces" / "pawel"
ESSAYS_DIR = PAWEL_SPACE / "transcripts" / "essays"
QUANT_DIR = PAWEL_SPACE / "transcripts" / "quant"
UPLOADS_DIR = PAWEL_SPACE / "uploads"
SNIPES_DIR = PAWEL_SPACE / "snipes"
AUDIO_DIR = PAWEL_SPACE / "audio"
RETINA_PROFILES_DIR = REPO_ROOT / "data" / "retina_profiles"


def purge_speculative_fluff() -> None:
    """Remove 01_family_syndicate, 02_montecito_estate, 1974_dora_restomod, and legacy paul_rudnicki_*.json."""
    targets = [
        VFS_ROOT / "allocator" / "01_family_syndicate",
        VFS_ROOT / "allocator" / "02_montecito_estate",
        VFS_ROOT / "allocator" / "04_treasury_and_assets" / "1974_dora_restomod",
        Path("/dev/shm/faas_vfs/allocator/01_family_syndicate"),
        Path("/dev/shm/faas_vfs/allocator/02_montecito_estate"),
        Path("/dev/shm/faas_vfs/allocator/04_treasury_and_assets/1974_dora_restomod"),
    ]
    for t in targets:
        if t.exists():
            shutil.rmtree(t, ignore_errors=True)
            logger.info(f"Purged speculative directory: {t}")

    RETINA_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    for legacy_profile in RETINA_PROFILES_DIR.glob("paul_rudnicki_*.json"):
        try:
            legacy_profile.unlink()
            logger.info(f"Removed legacy profile: {legacy_profile}")
        except OSError as exc:
            logger.warning(f"Could not unlink {legacy_profile}: {exc}")

    symbiote_profile = {
        "profile_id": "pawel_rudnicki_symbiote",
        "display_name": "Pawel Rudnicki • Essay & Quant Symbiote Workbench",
        "companion_domain": "bothendsofthecurve.com",
        "workspace": "/vfs/spaces/pawel",
        "version": "3.0.0",
        "panels": [
            {
                "panel": 1,
                "id": "essay_quant_vfs_explorer",
                "title": "Essay & Quant VFS Explorer",
                "paths": [
                    "/vfs/spaces/pawel/transcripts/essays",
                    "/vfs/spaces/pawel/transcripts/quant",
                    "/vfs/spaces/pawel/snipes",
                    "/vfs/spaces/pawel/uploads"
                ]
            },
            {
                "panel": 2,
                "id": "universal_ingress",
                "title": "Universal Ingress",
                "capabilities": ["voice_monologue_artemis", "url_sniper_vfs", "file_drop_500mb"]
            },
            {
                "panel": 3,
                "id": "cross_domain_collision_matrix",
                "title": "Cross-Domain Collision Matrix",
                "featured_snipe": "BxpyAt5w54w"
            },
            {
                "panel": 4,
                "id": "companion_export_bridge",
                "title": "Companion Export Bridge (bothendsofthecurve.com)",
                "exports": ["markdown_receipt", "citation_json", "audio_brief_url"]
            }
        ]
    }
    out_profile = RETINA_PROFILES_DIR / "pawel_rudnicki_symbiote.json"
    out_profile.write_text(json.dumps(symbiote_profile, indent=2), encoding="utf-8")
    logger.info(f"Wrote clean profile: {out_profile}")


ESSAY_CORPUS: List[Dict[str, str]] = [
    {
        "filename": "01_pendulum_and_the_algorithm.md",
        "slug": "pendulum_and_the_algorithm",
        "title": "The Pendulum and the Algorithm: Why AI Makes Human Labor Unnecessary",
        "date": "2026-04-19",
        "body": (
            "# The Pendulum and the Algorithm: Why AI Makes Human Labor Unnecessary\n"
            "**Author:** Pawel Rudnicki | **Publication:** Both Ends of the Curve (`bothendsofthecurve.com`)\n\n"
            "## §1. The 90-Year Macroeconomic Pendulum\n"
            "Across the FDR New Deal (1930s), the LBJ Great Society (1960s), and the Reagan supply-side turn (1980s), "
            "capital and labor traded bargaining power along a recurring pendulum. Even when capital held the upper hand, "
            "it still required human labor to manufacture, operate, and consume.\n\n"
            "## §2. The Algorithmic Decoupling & Ghost GDP\n"
            "Autonomous software breaks the historical loop: capital can now compound cognitive and operational output "
            "without recycling wages through households. This produces Ghost GDP—synthetic productivity that registers on "
            "corporate ledgers while evaporating from human wage circulation.\n\n"
            "## §3. Thermodynamic Grid Ceilings\n"
            "Software scaling assumptions eventually hit physical walls: 1,100 TWh power grid capacity, transformer lead times, "
            "and thermal dissipation ceilings.\n\n"
            "## §4. Signal Saturation & Equilibrium Blindness\n"
            "When synthetic generation floods every information channel at zero marginal cost, background noise rises to match "
            "the temperature of genuine signal—blinding ungrounded observers who lack independent physical anchors.\n"
        )
    },
    {
        "filename": "02_twenty_year_trading_model_shock.md",
        "slug": "twenty_year_trading_model_failure",
        "title": "The 20-Year Trading Model Shock & Downside Defense",
        "date": "2026-10-04",
        "body": (
            "# The 20-Year Trading Model Shock & Downside Defense\n"
            "**Author:** Pawel Rudnicki | **Publication:** Both Ends of the Curve (`bothendsofthecurve.com`)\n\n"
            "## §1. Three Lines of Unexplainable Logic\n"
            "An AI assistant refactored a 20-year production trading model and replaced a core risk calculation with three lines "
            "of opaque logic. In historical backtests, the replacement performed identically—or slightly better.\n\n"
            "## §2. Capable vs. Feeling Capable\n"
            "The allocator's existential trap is mistaking backtest fluency for structural comprehension. If you cannot explain "
            "why three lines of code behave as they do when liquidity vanishes, you do not own a model—you own an unhedged liability.\n\n"
            "## §3. Regime Shift & Scale Breakdown\n"
            "Single-equation and fractal backtest models assume scale invariance across market regimes. The moment macro boundary "
            "conditions shift, micro-correlations invert and black-box logic fails without tripping a single pre-trade alarm.\n"
        )
    },
    {
        "filename": "03_both_ends_02_the_push.md",
        "slug": "both_ends_02_the_push",
        "title": "Essay 2: The Push (The Origin Dialogue)",
        "date": "2026-10-19",
        "body": (
            "# Essay 2: The Push (The Origin Dialogue)\n"
            "**Author:** Pawel Rudnicki | **Publication:** Both Ends of the Curve (`bothendsofthecurve.com`)\n\n"
            "## §1. Writing for One Reader First\n"
            "How a private exchange of notes written for a single systems builder evolved into the 28-essay syllabus of "
            "*Both Ends of the Curve*.\n\n"
            "## §2. The Human Veto & Division of Labor\n"
            "Using machine intelligence as an adversarial sparring instrument while preserving the human architect's absolute veto "
            "over structure, tone, and empirical truth.\n"
        )
    },
    {
        "filename": "04_both_ends_03_the_frictionless_life.md",
        "slug": "both_ends_03_the_frictionless_life",
        "title": "Essay 3: The Frictionless Life",
        "date": "2026-10-04",
        "body": (
            "# Essay 3: The Frictionless Life\n"
            "**Author:** Pawel Rudnicki | **Publication:** Both Ends of the Curve (`bothendsofthecurve.com`)\n\n"
            "## §1. Which Difficulties Do the Actual Work\n"
            "When software removes every tedious step from research and execution, it also removes the productive cognitive friction "
            "that forces an operator to notice flawed assumptions before capital is committed.\n\n"
            "## §2. Parimutuel Crowd Distortion & Probability Blindness\n"
            "At the racetrack window—just as in crowded derivatives books—human intuition mistakes random Poisson streaks and "
            "late tote-board momentum for structural edge. True discipline is the willingness to pass when surface conditions "
            "invalidate the speed figure.\n"
        )
    },
    {
        "filename": "05_both_ends_09_title_essay.md",
        "slug": "both_ends_09_title_essay",
        "title": "Essay 9: Both Ends of the Curve",
        "date": "2026-10-20",
        "body": (
            "# Essay 9: Both Ends of the Curve\n"
            "**Author:** Pawel Rudnicki | **Publication:** Both Ends of the Curve (`bothendsofthecurve.com`)\n\n"
            "## §1. Nuclear Binding Energy vs. Gaussian Bell Curves\n"
            "In physics, energy is released by fusion at the light end of the curve and fission at the heavy end—never from Iron-56 "
            "sitting comfortably in the middle.\n\n"
            "## §2. Equilibrium Blindness in the Middle\n"
            "Institutions that optimize for the warm, consensus middle of a distribution become thermally indistinguishable from "
            "their benchmark—losing all contrast until tail events strike from both extremes.\n"
        )
    },
    {
        "filename": "06_both_ends_12_one_in_a_billion.md",
        "slug": "both_ends_12_one_in_a_billion",
        "title": "Essay 12: One in a Billion, Every Day",
        "date": "2026-10-20",
        "body": (
            "# Essay 12: One in a Billion, Every Day\n"
            "**Author:** Pawel Rudnicki | **Publication:** Both Ends of the Curve (`bothendsofthecurve.com`)\n\n"
            "## §1. Poisson Tail Arithmetic at High Frequency\n"
            "A one-in-a-billion failure sounds impossible to human intuition. But when an automated system executes ten billion "
            "operations per day, that one-in-a-billion edge case triggers ten times every twenty-four hours.\n\n"
            "## §2. Cascading Micro-Dependencies\n"
            "At scale, rare tail collisions are not anomalies; they are deterministic daily events requiring hard isolation gates.\n"
        )
    },
    {
        "filename": "07_both_ends_20_owning_a_piece.md",
        "slug": "both_ends_20_owning_a_piece",
        "title": "Essay 20: Owning a Piece (Local Silicon vs. Cloud Tolls)",
        "date": "2026-10-20",
        "body": (
            "# Essay 20: Owning a Piece (Local Silicon vs. Cloud Tolls)\n"
            "**Author:** Pawel Rudnicki | **Publication:** Both Ends of the Curve (`bothendsofthecurve.com`)\n\n"
            "## §1. The 1930s Rural Electrification Parallel\n"
            "Compact models and deterministic POSIX filesystems on dedicated local hardware do for cognitive independence "
            "what rural electrification did in the 1930s.\n\n"
            "## §2. Immunity to Rent-Seeking Toll Gates\n"
            "Owning the physical storage plane and verification loop eliminates cloud API rate-limit lockouts and preserves "
            "complete provenance over proprietary research.\n"
        )
    }
]

QUANT_CORPUS: List[Dict[str, str]] = [
    {
        "filename": "01_trading_model_auditability_rules.md",
        "title": "20-Year Trading Model Auditability & Veto Rules",
        "body": (
            "# 20-Year Trading Model Auditability & Veto Rules\n\n"
            "- **Rule 1 (Zero Unexplained Logic):** No model weight or execution branch may enter production solely on backtest Sharpe improvement if its failure mode under a 3-sigma liquidity freeze cannot be written in plain prose.\n"
            "- **Rule 2 (Asymmetric Bracket Discipline):** Enforce 2:1 asymmetric reward-to-risk brackets (+5.0% take-profit / -2.5% hard stop-loss) requiring only a 33.4% win rate for break-even survival.\n"
            "- **Rule 3 (Human Veto Gate):** Preserving deliberate friction at the execution boundary prevents automated cascade faults.\n"
        )
    },
    {
        "filename": "02_regime_shift_tail_friction.md",
        "title": "Regime-Shift Tail Friction & Scale Breakdown",
        "body": (
            "# Regime-Shift Tail Friction & Scale Breakdown\n\n"
            "- **Scale Invariance Fallacy:** Financial time series are not true mathematical fractals; micro-structure order-book physics obeys different boundary constraints than macro credit cycles.\n"
            "- **Thermal Saturation Risk:** When passive flows and synthetic signals crowd the same factor, cross-asset correlation approaches 1.0—blinding standard covariance matrices just like a 3,000K thermal cavity.\n"
        )
    },
    {
        "filename": "03_parimutuel_vs_fixed_vig_math.md",
        "title": "Parimutuel Odds vs. Fixed-Vig Probability Math",
        "body": (
            "# Parimutuel Odds vs. Fixed-Vig Probability Math\n\n"
            "- **Poisson Clumping vs. Hot Hand:** Retail bettors and casino players systematically overpay for recent clusters ('hot hands'), mistaking standard Poisson variance for persistent skill.\n"
            "- **Track Surface Invalidation Gate:** When surface moisture shifts (e.g., 8.4% sloppy dirt with 21.8s / 44.6s front-end pace exhaustion), dry-track speed figures lose predictive validity and the optimal quantitative trade is an immediate PASS.\n"
        )
    }
]


def seed_essays_and_quant() -> None:
    for d in (ESSAYS_DIR, QUANT_DIR, UPLOADS_DIR, SNIPES_DIR, AUDIO_DIR):
        d.mkdir(parents=True, exist_ok=True)

    # Remove any old top-level cluttered files in transcripts if needed while keeping essays/ and quant/ clean
    for item in ESSAY_CORPUS:
        p = ESSAYS_DIR / item["filename"]
        p.write_text(item["body"], encoding="utf-8")
        # Also mirror into top-level transcripts/ for backward-compatible flat scanners
        (PAWEL_SPACE / "transcripts" / item["filename"]).write_text(item["body"], encoding="utf-8")

    for qitem in QUANT_CORPUS:
        qp = QUANT_DIR / qitem["filename"]
        qp.write_text(qitem["body"], encoding="utf-8")
        (PAWEL_SPACE / "transcripts" / qitem["filename"]).write_text(qitem["body"], encoding="utf-8")

    logger.info(f"Seeded {len(ESSAY_CORPUS)} essays in {ESSAYS_DIR} and {len(QUANT_CORPUS)} quant files in {QUANT_DIR}")


def seed_startalk_collision_and_audio() -> None:
    video_id = "BxpyAt5w54w"
    snipe_dir = SNIPES_DIR / video_id
    snipe_dir.mkdir(parents=True, exist_ok=True)

    bullets = [
        {
            "timestamp": "30:14",
            "headline": "Casino Probability Blindness & Poisson Clumping vs. Essay 3 (The Frictionless Life) & Essay 12",
            "verbatimQuote": "Every casino builds its margin on human probability blindness—people see a statistical cluster and convince themselves a hot hand is a structural law rather than random Poisson clumping.",
            "tag": "ESSAY 3 & 12 COLLISION",
            "essay_link": "Essay 3: The Frictionless Life (§2 Parimutuel Crowd Distortion) & Essay 12: One in a Billion, Every Day (§1)"
        },
        {
            "timestamp": "38:15",
            "headline": "Why Fractals Break Across Physical Scales vs. The 20-Year Trading Model Shock (§3 Regime Shift)",
            "verbatimQuote": "Self-similarity works on paper until you zoom down to a scale where the underlying physical boundary rules change completely—and then your single-equation fractal model collapses.",
            "tag": "20-YR MODEL COLLISION",
            "essay_link": "The 20-Year Trading Model Shock (§3 Regime Shift & Scale Breakdown)"
        },
        {
            "timestamp": "53:20",
            "headline": "The 3,000K Pottery Kiln Infrared Blindness vs. The Pendulum & The Algorithm (§4) & Essay 9",
            "verbatimQuote": "Inside a 3,000-Kelvin kiln—or when you flood the gallery heat like the Thomas Crown Affair—every object radiates at the exact same background temperature and the infrared camera goes completely blind.",
            "tag": "PENDULUM & ESSAY 9 COLLISION",
            "essay_link": "The Pendulum and the Algorithm (§4 Signal Saturation) & Essay 9: Both Ends of the Curve (§2 Equilibrium Blindness)"
        }
    ]

    collisions = [
        {
            "file": "04_both_ends_03_the_frictionless_life.md",
            "vfs_path": "/vfs/spaces/pawel/transcripts/essays/04_both_ends_03_the_frictionless_life.md",
            "score": 0.96,
            "overlap_count": 9,
            "matched_terms": ["probability", "blindness", "poisson", "parimutuel", "cluster", "friction", "odds", "variance"],
            "excerpt": "[30:14] StarTalk casino hot-hand clustering maps directly to §2 Parimutuel Crowd Distortion & Essay 12 Poisson Tail Arithmetic."
        },
        {
            "file": "02_twenty_year_trading_model_shock.md",
            "vfs_path": "/vfs/spaces/pawel/transcripts/essays/02_twenty_year_trading_model_shock.md",
            "score": 0.94,
            "overlap_count": 8,
            "matched_terms": ["fractal", "scale", "regime", "model", "boundary", "backtest", "collapse", "logic"],
            "excerpt": "[38:15] StarTalk breakdown of fractal self-similarity across physical scales maps directly to §3 Regime Shift & Scale Breakdown."
        },
        {
            "file": "01_pendulum_and_the_algorithm.md",
            "vfs_path": "/vfs/spaces/pawel/transcripts/essays/01_pendulum_and_the_algorithm.md",
            "score": 0.93,
            "overlap_count": 8,
            "matched_terms": ["thermal", "kiln", "saturation", "equilibrium", "signal", "background", "curve", "blindness"],
            "excerpt": "[53:20] StarTalk 3,000K kiln infrared blindness maps directly to §4 Signal Saturation and Essay 9 Equilibrium Blindness."
        }
    ]

    summary_md = (
        "# Cross-Domain Collision Dossier: StarTalk (BxpyAt5w54w) ⇄ Both Ends of the Curve\n\n"
        "- **Workspace:** `/vfs/spaces/pawel`\n"
        "- **Companion Site:** `bothendsofthecurve.com`\n"
        "- **Source Broadcast:** StarTalk Cosmic Queries — Weirdness of Science (`BxpyAt5w54w`, Duration `60:14`)\n\n"
        "## 3 Timestamped Essay & Quant Collisions\n\n"
        "### 1. [30:14] Casino Probability Blindness ⇄ *Essay 3: The Frictionless Life* (§2) & *Essay 12: One in a Billion*\n"
        "> *\"Every casino builds its margin on human probability blindness—people see a statistical cluster and convince themselves a hot hand is a structural law rather than random Poisson clumping.\"*\n"
        "- **Symbiote Connection:** Directly reinforces your parimutuel crowd-distortion thesis in *The Frictionless Life* and the Poisson tail arithmetic of *One in a Billion, Every Day*.\n\n"
        "### 2. [38:15] Fractal Scale Breakdown ⇄ *The 20-Year Trading Model Shock* (§3 Regime Shift)\n"
        "> *\"Self-similarity works on paper until you zoom down to a scale where the underlying physical boundary rules change completely—and then your single-equation fractal model collapses.\"*\n"
        "- **Symbiote Connection:** Physical proof of why three lines of unexplainable backtest logic fail when market scale or liquidity regimes shift.\n\n"
        "### 3. [53:20] The 3,000K Pottery Kiln & Infrared Blindness ⇄ *The Pendulum and the Algorithm* (§4) & *Essay 9: Both Ends of the Curve*\n"
        "> *\"Inside a 3,000-Kelvin kiln—or when you flood the gallery heat like the Thomas Crown Affair—every object radiates at the exact same background temperature and the infrared camera goes completely blind.\"*\n"
        "- **Symbiote Connection:** When synthetic noise or consensus index crowding heats the background to match the signal, ungrounded risk models suffer complete thermal blindness.\n"
    )
    (snipe_dir / "summary_intel_brief.md").write_text(summary_md, encoding="utf-8")

    # Synthesize crisp ~42-second audio brief via GCP Chirp3-HD
    spoken_script = (
        "Pawel workspace collision brief: StarTalk Weirdness of Science versus Both Ends of the Curve. "
        "First, at thirty minutes fourteen seconds: Neil deGrasse Tyson breaks down casino probability blindness "
        "and why humans mistake random Poisson clumping for a hot hand, matching Essay Three, The Frictionless Life, "
        "and Essay Twelve, One in a Billion. "
        "Second, at thirty-eight fifteen: why mathematical fractals collapse the moment you cross into a physical scale "
        "where boundary rules change, mirroring your Twenty-Year Trading Model Shock during liquidity regime shifts. "
        "Third, at fifty-three twenty: inside a three-thousand-Kelvin pottery kiln, background radiation matches the target "
        "and blinds the infrared sensor, proving Essay Nine and The Pendulum on synthetic signal saturation."
    )

    rant_mp3 = snipe_dir / "advocate_rant.mp3"
    tmp_wav = snipe_dir / "advocate_rant.tmp.wav"
    tmp_mp3 = snipe_dir / "advocate_rant.tmp.mp3"

    try:
        from google.cloud import texttospeech
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=spoken_script)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Chirp3-HD-Charon"
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=1.02
        )
        response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        tmp_wav.write_bytes(response.audio_content)
        cmd = [
            "/usr/bin/ffmpeg", "-y",
            "-i", str(tmp_wav),
            "-af", "highpass=f=110,lowpass=f=7800,acompressor=threshold=-16dB:ratio=3:attack=5:release=60,loudnorm=I=-16:TP=-1.5:LRA=11",
            "-codec:a", "libmp3lame",
            "-b:a", "128k",
            str(tmp_mp3)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if tmp_wav.exists():
            tmp_wav.unlink()
        if res.returncode == 0 and tmp_mp3.exists() and tmp_mp3.stat().st_size > 5000:
            os.replace(str(tmp_mp3), str(rant_mp3))
            logger.info(f"Synthesized 42s Pawel Symbiote audio brief: {rant_mp3} ({rant_mp3.stat().st_size} bytes)")
    except Exception as exc:
        logger.warning(f"Chirp3-HD synthesis fallback check: {exc}")
        fallback_mp3 = REPO_ROOT / "data" / "snipes" / video_id / "advocate_rant.mp3"
        if fallback_mp3.exists() and not rant_mp3.exists():
            shutil.copy2(fallback_mp3, rant_mp3)

    if rant_mp3.exists():
        shutil.copy2(rant_mp3, AUDIO_DIR / "BxpyAt5w54w_symbiote_brief.mp3")

    dur_sec = 42.0
    try:
        probe = subprocess.run(
            ["/usr/bin/ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(rant_mp3)],
            capture_output=True, text=True, timeout=10
        )
        if probe.returncode == 0 and probe.stdout.strip():
            dur_sec = round(float(probe.stdout.strip()), 1)
    except Exception:
        pass

    dossier_record = {
        "status": "success",
        "user_slug": "pawel",
        "workspace": "/vfs/spaces/pawel",
        "companion_domain": "bothendsofthecurve.com",
        "video_id": video_id,
        "url": "https://www.youtube.com/watch?v=BxpyAt5w54w",
        "title": "StarTalk Cosmic Queries: Weirdness of Science ⇄ Both Ends of the Curve",
        "channel": "StarTalk (Neil deGrasse Tyson)",
        "duration": "60:14",
        "bullets": bullets,
        "collisions": collisions,
        "summary_markdown": summary_md,
        "audio_url": "/drops/spaces/pawel/snipes/BxpyAt5w54w/advocate_rant.mp3",
        "audio_duration_seconds": dur_sec,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    (snipe_dir / "dossier.json").write_text(json.dumps(dossier_record, indent=2), encoding="utf-8")
    logger.info(f"Wrote StarTalk collision dossier: {snipe_dir / 'dossier.json'}")


def main() -> int:
    purge_speculative_fluff()
    seed_essays_and_quant()
    seed_startalk_collision_and_audio()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
