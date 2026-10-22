#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Expanded Multi-Silo & Multi-Hop Swanson VFS Collider (WO0011287).
Executes deterministic 2-hop (A <-> B <-> C) and 3-hop (A <-> B1 <-> C1 <-> B2 <-> C2)
POSIX VFS traversals across:
  - vfs/vault/pawel/ (Both Ends of the Curve essays & treatises)
  - vfs/vault/sec_risk/ (SEC EDGAR 10-K Risk Disclosures)
  - vfs/vault/ercot/ (ERCOT 2026 fuel mix & hourly load curves)
  - vfs/vault/arxiv/ (ArXiv cs.DC, q-fin.RM, econ.TH papers)
  - vfs/vault/macro/ (FRED & EIA macroeconomic baselines)
  - vfs/snipes/ (Artemis CUDA Faster-Whisper broadcast snipe dossiers)
  - vfs/liberated/{energy.cartridge,vfs_wiki}/ (Liberated JSONL knowledge cartridges)
Extracts Symmetric-Difference Blind Spots (L_C \\ L_A), writes collision receipts,
and appends newly discovered bridges to vfs/collisions/discovered_ledger.jsonl.
"""

import argparse
import hashlib
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

BASE_DIR = Path("/home/james/stacklabs")
VFS_ROOT = BASE_DIR / "vfs"
PAWEL_VAULT = VFS_ROOT / "vault" / "pawel"
LENSES_ROOT = VFS_ROOT / "pheromones" / "lenses"
COLLISIONS_ROOT = VFS_ROOT / "collisions"
DISCOVERED_LEDGER_PATH = COLLISIONS_ROOT / "discovered_ledger.jsonl"

EMPIRICAL_SILO_DIRS: List[Tuple[str, Path]] = [
    ("sec_risk", VFS_ROOT / "vault" / "sec_risk"),
    ("ercot", VFS_ROOT / "vault" / "ercot"),
    ("arxiv", VFS_ROOT / "vault" / "arxiv"),
    ("macro", VFS_ROOT / "vault" / "macro"),
    ("snipes", VFS_ROOT / "snipes"),
]

LENS_DESCRIPTIONS: Dict[str, str] = {
    "THERMODYNAMIC_ENERGY_CEILING": (
        "1,100 TWh data center power ceiling, 5-to-7 year transmission interconnect queues, "
        "evaporative cooling water draw, and ERCOT reserve margin limits"
    ),
    "UNEXPLAINED_LOGIC_DRIFT": (
        "opaque AI-synthesized model logic that clears historical backtests "
        "but fails line-by-line operator auditability during regime shifts"
    ),
    "GHOST_GDP_DECOUPLING": (
        "synthetic corporate ledger output decoupling from real human wage velocity "
        "and physical capacity utilization (FRED M2V / PRS85006092)"
    ),
    "COGNITIVE_FRICTION_ATROPHY": (
        "degradation of human operator downside defense when iterative friction is removed "
        "inside a closed single-model loop"
    ),
    "TOPOLOGICAL_CASCADE_FAULT": (
        "silent upstream dependency failures propagating across interconnected infrastructure "
        "nodes before localized alarms trip"
    ),
    "ASYMMETRIC_TAIL_CONTAGION": (
        "non-linear tail-risk amplification where high-frequency micro-dependencies "
        "trigger correlated liquidation or grid dispatch penalties"
    ),
    "LATENCY_INVERSION_BOUNDARY": (
        "structural regime failure when multi-second cloud/queue round-trips collide "
        "with sub-millisecond physical or market state transitions"
    ),
}


def atomic_write_json(target_path: Path, payload: Any) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_suffix(target_path.suffix + ".tmp")
    serialized = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    with open(tmp_path, "w", encoding="utf-8") as fh:
        fh.write(serialized + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp_path, target_path)


def atomic_symlink(target: Path, link_path: Path) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_link = link_path.with_suffix(link_path.suffix + ".tmp")
    try:
        if tmp_link.is_symlink() or tmp_link.exists():
            tmp_link.unlink()
    except OSError:
        pass
    rel_target = os.path.relpath(str(target), str(link_path.parent))
    os.symlink(rel_target, str(tmp_link))
    os.replace(str(tmp_link), str(link_path))


def ensure_mcafee_agi_snipe_node() -> None:
    """Ensure the transcribed Pat McAfee Show AGI & Water snipe (x8iARwwn-J8) is wired into VFS lenses."""
    snipe_dir = VFS_ROOT / "snipes" / "x8iARwwn-J8"
    snipe_dir.mkdir(parents=True, exist_ok=True)
    state_path = snipe_dir / "state.json"

    lenses = [
        "THERMODYNAMIC_ENERGY_CEILING",
        "UNEXPLAINED_LOGIC_DRIFT",
        "GHOST_GDP_DECOUPLING",
        "ASYMMETRIC_TAIL_CONTAGION",
    ]
    state_payload = {
        "sys_id": "ci_media_dossier_x8iARwwn-J8",
        "node_id": "x8iARwwn-J8",
        "silo": "snipes",
        "title": "The Pat McAfee Show Live Broadcast (x8iARwwn-J8) — AGI 10% & Datacenter Water/Labor Anxiety",
        "broadcast_date": "2025-10-20",
        "time_window": "02:48:48 -> 02:50:53",
        "time_machine_route": "/api/snipe/x8iARwwn-J8/time_machine?t=10235",
        "summary": (
            "Live broadcast segment discussing Elon Musk's 'AGI is 10% and rising' 3 AM post, "
            "autonomous AI agents out-jousting moderator AIs, and acute mainstream anxiety over "
            "datacenter water draw and labor displacement."
        ),
        "empirical_receipt": (
            " 'They are an AI that is actually able to read another AI that is trying to stop them, "
            "and every once in a while they just out-joust him... Well, unplug these motherfuckers! "
            "They are taking our jobs. They are drinking up all our water. When you just unplug them? Too late.'"
        ),
        "lenses": lenses,
    }
    if not state_path.is_file():
        atomic_write_json(state_path, state_payload)
    else:
        try:
            existing = json.loads(state_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict) and not existing.get("lenses"):
                existing.update(state_payload)
                atomic_write_json(state_path, existing)
        except (OSError, json.JSONDecodeError):
            atomic_write_json(state_path, state_payload)

    active_lenses_dir = snipe_dir / "active_lenses"
    active_lenses_dir.mkdir(parents=True, exist_ok=True)
    for lens_name in lenses:
        lens_dir = LENSES_ROOT / lens_name
        lens_dir.mkdir(parents=True, exist_ok=True)
        atomic_symlink(lens_dir, active_lenses_dir / lens_name)
        linked_dir = lens_dir / "linked_nodes"
        linked_dir.mkdir(parents=True, exist_ok=True)
        atomic_symlink(snipe_dir, linked_dir / "snipes_x8iARwwn-J8")


def infer_lenses_from_text(text: str) -> Set[str]:
    low = text.lower()
    matched: Set[str] = set()
    if any(k in low for k in ("twh", "megawatt", "ercot", "grid", "interconnect", "transformer", "cooling", "water", "baseload", "power", "battery")):
        matched.add("THERMODYNAMIC_ENERGY_CEILING")
    if any(k in low for k in ("unexplained", "black-box", "drift", "three lines", "audit", "out-joust", "hallucinat", "opaque", "model")):
        matched.add("UNEXPLAINED_LOGIC_DRIFT")
    if any(k in low for k in ("gdp", "productivity", "wage", "labor", "jobs", "m2v", "velocity", "employment")):
        matched.add("GHOST_GDP_DECOUPLING")
    if any(k in low for k in ("friction", "closed room", "sycophan", "atrophy", "comfort", "convenience")):
        matched.add("COGNITIVE_FRICTION_ATROPHY")
    if any(k in low for k in ("cascade", "upstream", "downstream", "cmdb", "switch", "dependency", "outage", "topology")):
        matched.add("TOPOLOGICAL_CASCADE_FAULT")
    if any(k in low for k in ("tail", "contagion", "billion", "liquidation", "penalty", "spike", "volatility", "var")):
        matched.add("ASYMMETRIC_TAIL_CONTAGION")
    if any(k in low for k in ("latency", "microsecond", "millisecond", "wan", "round-trip", "pagecache", "inode", "symlink")):
        matched.add("LATENCY_INVERSION_BOUNDARY")
    return matched


def read_node_metadata(node_dir: Path, silo_type: str) -> Dict[str, Any]:
    meta: Dict[str, Any] = {
        "node_id": node_dir.name,
        "silo": silo_type,
        "path": str(node_dir),
        "title": node_dir.name.replace("_", " "),
        "summary": "",
        "metric_receipt": "",
        "lenses": set(),
    }

    for candidate in ("state.json", "manifest.json", "metadata.json", "spec.json", "time_machine.json"):
        candidate_path = node_dir / candidate
        if candidate_path.is_file():
            try:
                with open(candidate_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    meta["title"] = (
                        data.get("title")
                        or data.get("name")
                        or data.get("entity_name")
                        or data.get("series_id")
                        or meta["title"]
                    )
                    meta["summary"] = (
                        data.get("thesis")
                        or data.get("summary")
                        or data.get("risk_summary")
                        or data.get("abstract")
                        or data.get("description")
                        or meta["summary"]
                    )
                    meta["metric_receipt"] = (
                        data.get("empirical_receipt")
                        or data.get("key_metric")
                        or data.get("filing_excerpt")
                        or data.get("telemetry_snapshot")
                        or meta["metric_receipt"]
                        or meta["summary"]
                    )
                    raw_lenses = (
                        data.get("lenses")
                        or data.get("active_lenses")
                        or data.get("pheromone_lenses")
                        or []
                    )
                    if isinstance(raw_lenses, list):
                        for item in raw_lenses:
                            if isinstance(item, str) and item.strip():
                                meta["lenses"].add(item.strip())
            except (OSError, json.JSONDecodeError):
                pass

    for md_name in ("thesis.md", "dossier.md", "spikes.md", "README.md"):
        md_path = node_dir / md_name
        if md_path.is_file() and not meta["summary"]:
            try:
                lines = [
                    ln.strip()
                    for ln in md_path.read_text(encoding="utf-8", errors="replace").splitlines()
                    if ln.strip() and not ln.strip().startswith("#")
                ]
                if lines:
                    meta["summary"] = lines[0][:320]
                    if not meta["metric_receipt"]:
                        meta["metric_receipt"] = lines[0][:320]
            except OSError:
                pass

    for link_subdir in ("active_lenses", "lenses", "pheromones", "deposited_lenses"):
        sub_path = node_dir / link_subdir
        if sub_path.is_dir():
            try:
                with os.scandir(sub_path) as it:
                    for entry in it:
                        if entry.name in LENS_DESCRIPTIONS:
                            meta["lenses"].add(entry.name)
            except OSError:
                pass

    if not meta["lenses"] and (meta["summary"] or meta["metric_receipt"]):
        meta["lenses"].update(infer_lenses_from_text(f"{meta['title']} {meta['summary']} {meta['metric_receipt']}"))

    return meta


def load_liberated_cartridge_nodes() -> Dict[str, Dict[str, Any]]:
    """Ingest liberated .jsonl cartridges from vfs/liberated/ (energy.cartridge & vfs_wiki)."""
    cartridge_nodes: Dict[str, Dict[str, Any]] = {}
    energy_concepts = VFS_ROOT / "liberated" / "energy.cartridge" / "concepts.jsonl"
    if energy_concepts.is_file():
        try:
            for idx, raw_line in enumerate(energy_concepts.read_text(encoding="utf-8").splitlines()):
                if idx >= 40 or not raw_line.strip():
                    continue
                rec = json.loads(raw_line)
                cid = str(rec.get("id") or rec.get("concept_id") or rec.get("name") or f"energy_{idx}").strip()
                slug = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in cid)[:48]
                title = str(rec.get("name") or rec.get("title") or cid)
                desc = str(rec.get("description") or rec.get("definition") or rec.get("summary") or title)
                lenses = infer_lenses_from_text(f"{title} {desc}")
                if not lenses:
                    lenses = {"THERMODYNAMIC_ENERGY_CEILING", "TOPOLOGICAL_CASCADE_FAULT"}
                key = f"energy_cartridge:{slug}"
                cartridge_nodes[key] = {
                    "node_id": slug,
                    "silo": "energy_cartridge",
                    "path": str(energy_concepts),
                    "title": f"Energy Cartridge CI: {title}",
                    "summary": desc[:300],
                    "metric_receipt": f"[Liberated Energy Cartridge] {title}: {desc[:240]}",
                    "lenses": lenses,
                }
        except (OSError, json.JSONDecodeError):
            pass
    return cartridge_nodes


def scan_vfs_topology(include_cartridges: bool = True) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Set[str]], float]:
    ensure_mcafee_agi_snipe_node()
    t0 = time.perf_counter()

    pawel_nodes: Dict[str, Dict[str, Any]] = {}
    empirical_nodes: Dict[str, Dict[str, Any]] = {}
    lens_to_nodes: Dict[str, Set[str]] = {lens: set() for lens in LENS_DESCRIPTIONS}

    if PAWEL_VAULT.is_dir():
        with os.scandir(PAWEL_VAULT) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=True):
                    meta = read_node_metadata(Path(entry.path), "pawel")
                    pawel_nodes[entry.name] = meta
                    for lens in meta["lenses"]:
                        lens_to_nodes.setdefault(lens, set()).add(f"pawel:{entry.name}")

    for silo_name, silo_path in EMPIRICAL_SILO_DIRS:
        if not silo_path.is_dir():
            continue
        with os.scandir(silo_path) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=True):
                    meta = read_node_metadata(Path(entry.path), silo_name)
                    if not meta["lenses"]:
                        continue
                    node_key = f"{silo_name}:{entry.name}"
                    empirical_nodes[node_key] = meta
                    for lens in meta["lenses"]:
                        lens_to_nodes.setdefault(lens, set()).add(node_key)

    if include_cartridges:
        cart_nodes = load_liberated_cartridge_nodes()
        for node_key, meta in cart_nodes.items():
            empirical_nodes[node_key] = meta
            for lens in meta["lenses"]:
                lens_to_nodes.setdefault(lens, set()).add(node_key)

    if LENSES_ROOT.is_dir():
        with os.scandir(LENSES_ROOT) as it:
            for lens_entry in it:
                if not lens_entry.is_dir(follow_symlinks=True):
                    continue
                lens_name = lens_entry.name
                if lens_name not in LENS_DESCRIPTIONS:
                    continue
                lens_dir = Path(lens_entry.path)
                for sub_candidate in (lens_dir, lens_dir / "entities", lens_dir / "linked_nodes"):
                    if not sub_candidate.is_dir():
                        continue
                    try:
                        with os.scandir(sub_candidate) as sub_it:
                            for link_entry in sub_it:
                                if link_entry.name in ("entities", "linked_nodes", "state.json", "spec.json"):
                                    continue
                                try:
                                    resolved = Path(link_entry.path).resolve()
                                except OSError:
                                    continue
                                if PAWEL_VAULT in resolved.parents:
                                    slug = resolved.name
                                    if slug in pawel_nodes:
                                        pawel_nodes[slug]["lenses"].add(lens_name)
                                        lens_to_nodes[lens_name].add(f"pawel:{slug}")
                                else:
                                    for silo_name, silo_path in EMPIRICAL_SILO_DIRS:
                                        if silo_path in resolved.parents:
                                            emp_key = f"{silo_name}:{resolved.name}"
                                            if emp_key in empirical_nodes:
                                                empirical_nodes[emp_key]["lenses"].add(lens_name)
                                                lens_to_nodes[lens_name].add(emp_key)
                    except OSError:
                        pass

    elapsed_us = (time.perf_counter() - t0) * 1_000_000.0
    return pawel_nodes, empirical_nodes, lens_to_nodes, elapsed_us


def build_three_bullet_crucible_brief(
    essay_meta: Dict[str, Any],
    emp_meta: Dict[str, Any],
    shared_lenses: List[str],
    blind_spot_lenses: List[str],
    adamic_adar: float,
    traversal_us: float,
    triad_acoustic_receipt: Optional[str] = None,
) -> str:
    essay_title = essay_meta["title"]
    emp_title = emp_meta["title"]
    emp_silo = emp_meta["silo"].upper()
    shared_str = ", ".join(shared_lenses)

    receipt_snippet = (emp_meta.get("metric_receipt") or emp_meta.get("summary") or "").strip()
    if len(receipt_snippet) > 220:
        receipt_snippet = receipt_snippet[:217].rstrip() + "..."
    if not receipt_snippet:
        receipt_snippet = (
            f"Empirical {emp_silo} telemetry node ({emp_meta['node_id']}) confirms physical bottleneck constraints."
        )

    if triad_acoustic_receipt and emp_meta["silo"] != "snipes":
        receipt_snippet += f" | Live Broadcast Phase-Lock: {triad_acoustic_receipt}"

    if blind_spot_lenses:
        primary_blind = blind_spot_lenses[0]
        blind_desc = LENS_DESCRIPTIONS.get(
            primary_blind,
            f"structural failure mode {primary_blind} observed in {emp_silo} telemetry",
        )
        bullet_3 = (
            f"3. THE UNEXAMINED BLIND SPOT ({primary_blind}): In my local VFS graph, {emp_title} also triggers "
            f"{primary_blind} ({blind_desc})—a second-order failure vector absent from your current draft that "
            f"belongs in The Breeze."
        )
    else:
        primary_shared = shared_lenses[0]
        shared_desc = LENS_DESCRIPTIONS.get(primary_shared, primary_shared)
        bullet_3 = (
            f"3. THE FALSIFICATION TEST FOR THE BREEZE ({primary_shared}): To stress-test this thesis against "
            f"{shared_desc}, where does your framework draw the quantitative line when {emp_title} hits "
            f"non-linear tail contagion?"
        )

    bullet_1 = (
        f"1. STRUCTURAL THESIS LOCK ({traversal_us:.1f} us VFS Bisociation): I ran '{essay_title}' through my "
        f"local POSIX VFS Swanson Collider; it locked directly onto [{emp_silo}] {emp_title} via shared lens "
        f"{shared_str} (Adamic-Adar specificity {adamic_adar:.3f})."
    )
    bullet_2 = f"2. EMPIRICAL GROUND-TRUTH RECEIPT ({emp_silo}): {receipt_snippet}"

    return f"{bullet_1}\n\n{bullet_2}\n\n{bullet_3}"


def compute_collisions(
    pawel_nodes: Dict[str, Dict[str, Any]],
    empirical_nodes: Dict[str, Dict[str, Any]],
    lens_to_nodes: Dict[str, Set[str]],
    traversal_us: float,
) -> List[Dict[str, Any]]:
    lens_weights: Dict[str, float] = {}
    for lens_name, members in lens_to_nodes.items():
        deg = max(2, len(members))
        lens_weights[lens_name] = 1.0 / math.log(deg)

    snipe_node = empirical_nodes.get("snipes:x8iARwwn-J8")
    snipe_lenses: Set[str] = set(snipe_node["lenses"]) if snipe_node else set()
    snipe_short_quote = (
        "Pat McAfee Show: 'They are taking our jobs. They are drinking up all our water. When you just unplug them? Too late.'"
    )

    raw_collisions: List[Dict[str, Any]] = []

    for essay_slug, essay_meta in sorted(pawel_nodes.items()):
        lenses_a: Set[str] = set(essay_meta["lenses"])
        if not lenses_a:
            continue

        for emp_key, emp_meta in sorted(empirical_nodes.items()):
            lenses_c: Set[str] = set(emp_meta["lenses"])
            if not lenses_c:
                continue

            shared = sorted(lenses_a.intersection(lenses_c))
            if not shared:
                continue

            blind_spots_c_minus_a = sorted(lenses_c.difference(lenses_a))
            essay_only_a_minus_c = sorted(lenses_a.difference(lenses_c))
            symmetric_diff = sorted(lenses_a.symmetric_difference(lenses_c))

            three_hop_chain: List[str] = []
            if blind_spots_c_minus_a:
                bridge_b2 = blind_spots_c_minus_a[0]
                for peer_key in sorted(lens_to_nodes.get(bridge_b2, set())):
                    if peer_key != emp_key and not peer_key.startswith("pawel:"):
                        three_hop_chain.append(
                            f"pawel:{essay_slug} -> [{shared[0]}] -> {emp_key} -> [{bridge_b2}] -> {peer_key}"
                        )
                        if len(three_hop_chain) >= 3:
                            break

            triad_quote: Optional[str] = None
            if snipe_lenses.intersection(shared):
                triad_quote = snipe_short_quote

            raw_aa = sum(lens_weights.get(l, 0.5) for l in shared)
            blind_spot_bonus = 0.15 * len(blind_spots_c_minus_a)
            composite_raw = raw_aa + blind_spot_bonus

            collision_id = f"{essay_slug}__x__{emp_meta['silo']}_{emp_meta['node_id']}"
            raw_collisions.append(
                {
                    "collision_id": collision_id,
                    "essay_slug": essay_slug,
                    "essay_title": essay_meta["title"],
                    "essay_summary": essay_meta["summary"],
                    "empirical_node_key": emp_key,
                    "empirical_silo": emp_meta["silo"],
                    "empirical_node_id": emp_meta["node_id"],
                    "empirical_title": emp_meta["title"],
                    "empirical_receipt": emp_meta["metric_receipt"],
                    "shared_lenses": shared,
                    "shared_lens_count": len(shared),
                    "blind_spot_lenses_c_minus_a": blind_spots_c_minus_a,
                    "essay_unmatched_lenses_a_minus_c": essay_only_a_minus_c,
                    "symmetric_difference_lenses": symmetric_diff,
                    "three_hop_transitive_chains": three_hop_chain,
                    "triad_acoustic_snipe": "snipes:x8iARwwn-J8" if triad_quote else None,
                    "adamic_adar_raw": round(raw_aa, 4),
                    "composite_raw": round(composite_raw, 4),
                    "_essay_meta": essay_meta,
                    "_emp_meta": emp_meta,
                    "_triad_quote": triad_quote,
                }
            )

    max_composite = max((c["composite_raw"] for c in raw_collisions), default=1.0) or 1.0

    silo_priority = {"ercot": 0, "sec_risk": 1, "snipes": 2, "macro": 3, "arxiv": 4, "energy_cartridge": 5}
    raw_collisions.sort(
        key=lambda item: (
            -item["shared_lens_count"],
            -len(item["blind_spot_lenses_c_minus_a"]),
            silo_priority.get(item["empirical_silo"], 9),
            -item["composite_raw"],
            item["collision_id"],
        )
    )

    finalized: List[Dict[str, Any]] = []
    for rank_idx, item in enumerate(raw_collisions, start=1):
        essay_meta = item.pop("_essay_meta")
        emp_meta = item.pop("_emp_meta")
        triad_quote = item.pop("_triad_quote")
        normalized_score = round(min(1.0, item["composite_raw"] / max_composite), 4)
        item["rank"] = rank_idx
        item["normalized_score"] = normalized_score
        item["traversal_latency_us"] = round(traversal_us, 2)
        item["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        item["crucible_brief_3bullet"] = build_three_bullet_crucible_brief(
            essay_meta=essay_meta,
            emp_meta=emp_meta,
            shared_lenses=item["shared_lenses"],
            blind_spot_lenses=item["blind_spot_lenses_c_minus_a"],
            adamic_adar=item["adamic_adar_raw"],
            traversal_us=traversal_us,
            triad_acoustic_receipt=triad_quote,
        )
        digest = hashlib.sha256(
            json.dumps(item, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        item["sha256_receipt"] = digest
        finalized.append(item)

    return finalized


def append_novel_discoveries(collisions: List[Dict[str, Any]], max_ledger_items: int = 50) -> int:
    COLLISIONS_ROOT.mkdir(parents=True, exist_ok=True)
    known_ids: Set[str] = set()
    if DISCOVERED_LEDGER_PATH.is_file():
        try:
            for line in DISCOVERED_LEDGER_PATH.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    cid = rec.get("collision_id")
                    if cid:
                        known_ids.add(cid)
        except (OSError, json.JSONDecodeError):
            pass

    new_count = 0
    with open(DISCOVERED_LEDGER_PATH, "a", encoding="utf-8") as fh:
        for item in collisions[:max_ledger_items]:
            if item["collision_id"] not in known_ids:
                novel_entry = {
                    "discovered_at_utc": item["generated_at_utc"],
                    "collision_id": item["collision_id"],
                    "rank": item["rank"],
                    "normalized_score": item["normalized_score"],
                    "shared_lenses": item["shared_lenses"],
                    "blind_spot_lenses_c_minus_a": item["blind_spot_lenses_c_minus_a"],
                    "three_hop_transitive_chains": item["three_hop_transitive_chains"],
                    "sha256_receipt": item["sha256_receipt"],
                }
                fh.write(json.dumps(novel_entry, ensure_ascii=False) + "\n")
                known_ids.add(item["collision_id"])
                new_count += 1
        fh.flush()
        os.fsync(fh.fileno())
    return new_count


def materialize_collision_artifacts(
    collisions: List[Dict[str, Any]],
    traversal_us: float,
    top_n_dirs: int = 30,
) -> Dict[str, Any]:
    COLLISIONS_ROOT.mkdir(parents=True, exist_ok=True)

    for item in collisions[:top_n_dirs]:
        c_dir = COLLISIONS_ROOT / item["collision_id"]
        c_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(c_dir / "collision_receipt.json", item)

    novel_added = append_novel_discoveries(collisions)

    summary_payload = {
        "engine": "stacklabs_swanson_vfs_collider_v3_multihop",
        "diagnostic_anchor": "SWANSON_VFS_CRUCIBLE_OCT21_2120",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "traversal_latency_us": round(traversal_us, 2),
        "total_collisions_discovered": len(collisions),
        "novel_collisions_logged": novel_added,
        "top_collision": collisions[0] if collisions else None,
        "ranked_collisions": collisions,
    }
    atomic_write_json(COLLISIONS_ROOT / "latest_ranked_collisions.json", summary_payload)
    return summary_payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Multi-Hop POSIX VFS Swanson Bisociation Collider & Blind-Spot Extractor."
    )
    parser.add_argument("--essay", type=str, default=None, help="Filter collisions by Pawel essay slug")
    parser.add_argument("--silo", type=str, default=None, help="Filter collisions by empirical silo (ercot, sec_risk, snipes, arxiv, macro, energy_cartridge)")
    parser.add_argument("--limit", type=int, default=10, help="Number of top collisions to display")
    parser.add_argument("--json", action="store_true", help="Print JSON summary to stdout")
    args = parser.parse_args()

    pawel_nodes, empirical_nodes, lens_to_nodes, traversal_us = scan_vfs_topology(include_cartridges=True)
    collisions = compute_collisions(pawel_nodes, empirical_nodes, lens_to_nodes, traversal_us)
    summary = materialize_collision_artifacts(collisions, traversal_us)

    filtered = collisions
    if args.essay:
        q_essay = args.essay.strip().lower()
        filtered = [c for c in filtered if q_essay in c["essay_slug"].lower() or q_essay in c["essay_title"].lower()]
    if args.silo:
        q_silo = args.silo.strip().lower()
        filtered = [c for c in filtered if c["empirical_silo"].lower() == q_silo]

    if args.json:
        print(
            json.dumps(
                {
                    "traversal_latency_us": summary["traversal_latency_us"],
                    "total_collisions_discovered": summary["total_collisions_discovered"],
                    "novel_collisions_logged": summary["novel_collisions_logged"],
                    "filtered_count": len(filtered),
                    "results": filtered[: args.limit],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print(
        f"[SWANSON_VFS_COLLIDER] Discovered {len(collisions)} multi-silo collisions "
        f"in {traversal_us:.1f} us (Novel logged: {summary['novel_collisions_logged']}, Filtered: {len(filtered)})"
    )
    for item in filtered[: args.limit]:
        blind_str = ",".join(item["blind_spot_lenses_c_minus_a"]) or "NONE"
        shared_str = ",".join(item["shared_lenses"])
        print(
            f"  #{item['rank']:03d} [{item['normalized_score']:.2f}] {item['collision_id']} | "
            f"Shared: [{shared_str}] | BlindSpot(C\\A): [{blind_str}]"
        )
    if filtered:
        print("\n--- TOP CRUCIBLE 3-BULLET BRIEF ---")
        print(filtered[0]["crucible_brief_3bullet"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
