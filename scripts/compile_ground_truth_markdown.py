#!/usr/bin/env python3
"""
StackLabs Ground Truth Markdown Snapshot Compiler
Path: /home/james/stacklabs/scripts/compile_ground_truth_markdown.py

Compiles high-density, beautifully formatted Markdown snapshots from the canonical
JSON ledgers in ground_truth/ for optimal NotebookLM ingestion and retrieval.
"""

import json
from pathlib import Path
from datetime import datetime

GROUND_TRUTH_DIR = Path("/home/james/stacklabs/ground_truth")

def load_json(name: str):
    p = GROUND_TRUTH_DIR / name
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def compile_compute_markdown():
    data = load_json("compute_ground_truth.json")
    nodes = data.get("hardware_nodes", data.get("nodes", {}))

    lines = [
        "# 🖥️ STACKLABS COMPUTE INFRASTRUCTURE GROUND TRUTH",
        f"> **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EDT')} • **Format**: High-Density Markdown Table",
        "> **Authority**: Lead Systems Architect (James Carroll) • Local Workstation Topology",
        "",
        "## 1. Hardware Nodes & Silicon Topology",
        "| Node ID | Role | Physical Hardware | Local IP | Tailscale IP | Storage | Local Inference Policy |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for nid, n in sorted(nodes.items()):
        hw = n.get("hardware_model", n.get("hardware", "N/A"))
        role = n.get("role", "N/A")
        host = n.get("host", "N/A")
        tip = n.get("tailscale_ip", "N/A")
        lip = n.get("local_ip", "N/A")

        if host.startswith("100."):
            tip = host
            if lip == "N/A":
                lip = "DHCP / LAN"
        elif host != "N/A" and lip == "N/A":
            lip = host

        stor = n.get("storage", "N/A")
        inf = n.get("local_inference_policy", n.get("local_inference", "Strictly Banned on Clio"))
        lines.append(f"| **{nid.upper()}** | {role} | {hw} | `{lip}` | `{tip}` | {stor} | {inf} |")

    lines.extend([
        "",
        "## 2. Active Network Ports & Subsystems",
        "| Subsystem / Port | Service / Application | Endpoint / URL | Status |",
        "| :--- | :--- | :--- | :--- |"
    ])

    ports = data.get("active_ports", data.get("ports", {}))
    for port_str, p in sorted(ports.items(), key=lambda x: str(x[0])):
        svc = p.get("service", p.get("name", "N/A"))
        url = p.get("endpoint", p.get("url", f"http://127.0.0.1:{port_str}"))
        stat = p.get("status", "ACTIVE")
        lines.append(f"| **Port {port_str}** | {svc} | [{url}]({url}) | `{stat}` |")

    lines.extend([
        "",
        "## 3. Dedicated Cloud Inference Tiers (October 2026 Invariant)",
        "- **Flagship Reasoning / Cockpit**: `gemini-4-argon` / `gemini-3.1-pro-preview`",
        "- **API Fast / Hot-Path Tier**: `gemini-3.8-flash` (Primary workhorse)",
        "- **API Lite Triage Tier**: `gemini-flash-lite-latest`",
        "- **APU Protection Policy**: Clio operates zero local LLM weights. Heavy training routes to Colab runtimes.",
        "- **Acoustic Gating**: Audio over 30s routes to Artemis GPU CUDA Whisper at zero cloud cost."
    ])

    out_file = GROUND_TRUTH_DIR / "COMPUTE_GROUND_TRUTH_SNAPSHOT.md"
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] Generated {out_file.name}")

def compile_partner_markdown():
    data = load_json("partner_ground_truth.json")
    counterparties = data.get("counterparties", data.get("partners", {}))

    lines = [
        "# 🤝 STACKLABS COUNTERPARTY & ENGAGEMENT GROUND TRUTH",
        f"> **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EDT')} • **Target**: Executive Briefings",
        "> **Rule Zero**: Stay Behind Your Skis. Exactly ZERO active enterprise clients. Zero field deployments.",
        "",
        "## 1. Verified Counterparties & Exploratory Relationships",
        "| Counterparty | Organization | Status | Commercial Boundary | Strategic Wedge & Strict Communication Rules |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]

    for cid, p in sorted(counterparties.items()):
        name = p.get("name", cid.replace("_", " ").title())
        ent = p.get("entity", p.get("firm", "N/A"))
        stat = p.get("status", "prospect_scenario_only")
        rules = p.get("communication_rules", {})
        banned = rules.get("banned_sales_pitches", "") if isinstance(rules, dict) else ""
        rel = p.get("relationship", "")
        wedge = p.get("target_wedge", "")
        
        details = []
        if rel:
            details.append(f"Relationship: {rel}")
        if wedge:
            details.append(f"Wedge: {wedge}")
        if banned:
            details.append(f"Rules: {banned}")
        if not details:
            details.append("Exploratory dialogue only; zero unclosed deal claims.")

        detail_str = " • ".join(details)
        lines.append(f"| **{name}** | {ent} | `{stat}` | Unclosed / exploratory only | {detail_str[:120]} |")

    out_file = GROUND_TRUTH_DIR / "PARTNER_GROUND_TRUTH_SNAPSHOT.md"
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] Generated {out_file.name}")

def compile_sports_markdown():
    data = load_json("sports_ground_truth.json")
    brewers = data.get("brewers", data.get("standings", {}).get("MIL", {}))
    steelers = data.get("steelers", data.get("standings", {}).get("PIT", {}))
    shibboleths = data.get("roster_shibboleths", {})

    b_rec = f"{brewers.get('wins', 103)}-{brewers.get('losses', 59)}" if "wins" in brewers else brewers.get("record", "103-59")
    s_rec = f"{steelers.get('wins', 2)}-{steelers.get('losses', 2)}" if "wins" in steelers else steelers.get("record", "2-1")

    lines = [
        "# ⚾ STACKLABS SPORTS GROUND TRUTH SNAPSHOT",
        f"> **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EDT')} • **Temporal Baseline**: October 2026",
        "",
        "## 1. Canonical Sports Realities",
        f"- **MLB Postseason**: 2026 Milwaukee Brewers ({b_rec}) #1 overall seed in NLDS (leads NLDS 1-0).",
        f"- **NFL Season**: 2026 Pittsburgh Steelers ({s_rec}) led by Aaron Rodgers at QB.",
        "",
        "## 2. Roster Shibboleths & Postseason Moments"
    ]

    for player_id, p in sorted(shibboleths.items()):
        p_name = player_id.replace("_", " ").title()
        role = p.get("role", "Player")
        team = p.get("team", p.get("current_team_2026", "N/A"))
        note = p.get("nlds_moment", p.get("note", p.get("lore_status", "")))
        if not note and "former_team" in p:
            note = f"Former: {p.get('former_team')} • Hired: {p.get('hired', '2026')}"
        if not note and "current_record_2026" in p:
            note = f"Record: {p.get('current_record_2026')}"
        lines.append(f"- **{p_name}** ({role}, {team}): {note}")

    lines.extend([
        "",
        "## 3. Active Postseason Slate",
        "| Matchup | Status / State | Round | Summary / Game Today |",
        "| :--- | :--- | :--- | :--- |"
    ])

    series_data = data.get("postseason_series", {})
    series_list = series_data.get("series", [])
    if series_list:
        for s in series_list:
            matchup = s.get("matchup", "N/A")
            state = s.get("series_state", "N/A")
            rnd = s.get("round", "Playoff Series")
            summ = s.get("summary", s.get("game_today", "N/A"))
            lines.append(f"| **{matchup}** | `{state}` | {rnd} | {summ} |")
    else:
        slate = data.get("postseason_slate", [])
        for g in slate:
            lines.append(f"| {g.get('teams', 'N/A')} | {g.get('status', 'LIVE')} | Playoff Game | {g.get('venue', 'N/A')} |")

    lines.extend([
        "",
        "## 4. College Football Week 7 Top 25 Slate & Bleacher Wiretaps (Saturday, October 17, 2026)",
        "| Status | Away Team | Score | Home Team | Score | Clock / Detail / Venue | Bleacher Wiretap Source |",
        "| :--- | :--- | :---: | :--- | :---: | :--- | :--- |"
    ])

    cfb_top25 = data.get("cfb_top25_slate_20261017", {}).get("games", [])
    for g in cfb_top25:
        status = g.get("status", "SCHEDULED")
        status_str = f"**{status}**"
        away = g.get("away_team", {})
        home = g.get("home_team", {})
        ar = away.get("rank")
        hr = home.get("rank")
        away_name = f"#{ar} {away.get('full_name')}" if ar else away.get("full_name")
        home_name = f"#{hr} {home.get('full_name')}" if hr else home.get("full_name")
        ascore = away.get("score", 0)
        hscore = home.get("score", 0)
        
        detail = g.get("status_detail", "")
        venue = g.get("venue", "")
        clock_venue = f"{detail} • {venue}" if venue else detail
        if g.get("is_upset") and g.get("upset_note"):
            clock_venue = f"**{g.get('upset_note')}** • {clock_venue}"

        wt = g.get("wiretap")
        if wt:
            wt_str = f"`{wt.get('source')}`: {wt.get('title', '')[:40]}"
        else:
            wt_str = "*No Active Wiretap*"

        lines.append(f"| {status_str} | {away_name} | {ascore} | {home_name} | {hscore} | {clock_venue} | {wt_str} |")

    out_file = GROUND_TRUTH_DIR / "SPORTS_GROUND_TRUTH_SNAPSHOT.md"
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] Generated {out_file.name}")

def compile_quant_markdown():
    data = load_json("quant_ground_truth.json")
    rules = data.get("institutional_trading_rules", data.get("rules", {}))
    filters = data.get("liquidity_filters", {})
    benchmarks = data.get("macro_benchmarks", {})

    bankroll = rules.get("simulated_bankroll_usd", rules.get("capital_base", "$10,000"))
    if isinstance(bankroll, (int, float)):
        bankroll = f"${bankroll:,.2f}"
    slot = rules.get("trade_slot_usd", rules.get("trade_size", "$1,000"))
    if isinstance(slot, (int, float)):
        slot = f"${slot:,.2f}"
    stop_loss = rules.get("stop_loss_pct", rules.get("stop_loss", "-2.5%"))
    if isinstance(stop_loss, (int, float)):
        stop_loss = f"{stop_loss}%"
    take_profit = rules.get("take_profit_pct", rules.get("take_profit", "+5.0%"))
    if isinstance(take_profit, (int, float)):
        take_profit = f"+{take_profit}%"
    max_pos = rules.get("max_active_positions", rules.get("max_concurrent_trades", 10))
    holding_period = rules.get("max_holding_period_days", 10)

    lines = [
        "# 📈 STACKLABS QUANTITATIVE GROUND TRUTH SNAPSHOT",
        f"> **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EDT')} • **Target**: Horizon Docket Engine",
        "",
        "## 1. Paper Ledger Risk Brackets",
        f"- **Universe**: {data.get('universe_name', '538 Liquid Equities & Energy Infrastructure')}",
        f"- **Portfolio Allocation**: {bankroll} Paper Ledger",
        f"- **Position Size**: {slot} per trade (Max {max_pos} concurrent positions)",
        f"- **Stop Loss**: {stop_loss} hard stop",
        f"- **Take Profit**: {take_profit} target",
        f"- **Max Holding Period**: {holding_period} days",
        "",
        "## 2. Liquidity Filters & Macro Benchmarks",
        f"- **Min Price**: ${filters.get('min_price_usd', 5.0)}",
        f"- **Min Daily Volume**: ${filters.get('min_daily_volume_usd', 10000000):,.0f}",
        f"- **Henry Hub Natural Gas Ticker**: `{benchmarks.get('Henry_Hub_prompt_ticker', 'NG')}`",
        f"- **WTI Crude Oil Ticker**: `{benchmarks.get('WTI_spot_ticker', 'CL')}`",
        f"- **Energy ETFs**: {', '.join(f'`{etf}`' for etf in benchmarks.get('energy_etfs', []))}"
    ]

    out_file = GROUND_TRUTH_DIR / "QUANT_GROUND_TRUTH_SNAPSHOT.md"
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] Generated {out_file.name}")

def compile_queue_state_markdown():
    import sys
    sys.path.insert(0, "/home/james/stacklabs")
    try:
        from scripts.validate_wo import get_next_wo_id
        next_id = get_next_wo_id()
    except Exception:
        next_id = "UNKNOWN"

    archive_dir = Path("/home/james/stacklabs/queue/archive")
    recent_wos = []
    if archive_dir.exists():
        files = sorted(archive_dir.glob("WO*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in files[:8]:
            recent_wos.append(f"- **`{f.stem}`**")

    lines = [
        "# ⚡ STACKLABS GITOPS QUEUE: ACTIVE GROUND TRUTH",
        f"> **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EDT')} • Clio Dedicated Linux Host (`100.96.77.20`)",
        f"> **Next Sequential Work Order ID**: `{next_id}`",
        "> **Queue Runner**: Aggie (`agy` on Clio via `clio_queue_watcher.py`)",
        "",
        "## 🎯 Next Available Work Order to Author",
        f"- **Next ID**: `{next_id}`",
        f"- **Staging Path**: `/home/james/stacklabs/queue/incoming/{next_id}_<SLUG>.md`",
        "",
        "## 📋 Recent Completed Work Orders (Archived)",
    ] + recent_wos

    content = "\n".join(lines) + "\n"
    (GROUND_TRUTH_DIR / "ACTIVE_QUEUE_STATE.md").write_text(content, encoding="utf-8")
    pilot_out = Path("/home/james/stacklabs/pilot_drops/ACTIVE_QUEUE_STATE.md")
    pilot_out.write_text(content, encoding="utf-8")
    print(f"[OK] Generated {pilot_out.name} (Next ID: {next_id})")

if __name__ == "__main__":
    compile_compute_markdown()
    compile_partner_markdown()
    compile_sports_markdown()
    compile_quant_markdown()
    compile_queue_state_markdown()
    print("[SUCCESS] All 5 canonical ground truth markdown snapshots compiled.")
