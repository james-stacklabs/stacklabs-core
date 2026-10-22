#!/usr/bin/env python3
"""
Sovereign OS: Clio Workstation Live Terminal HUD (Rich Cockpit TUI)
Path: /home/james/stacklabs/scripts/clio_rich_hud.py

Aerospace Cockpit Dashboard providing live telemetry, queue state,
service mesh health, ATF gate status, and git vitals on host Clio.
"""

import sys
import os
import time
import socket
import signal
import subprocess
import json
from pathlib import Path

try:
    import psutil
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.layout import Layout
    from rich.live import Live
except ImportError as e:
    print(f"[FATAL] Required Python package missing: {e}")
    sys.exit(1)

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
QUEUE_DIR = Path("/home/james/sovereign_inbox/queue")
INCOMING_DIR = QUEUE_DIR / "incoming"
PROCESSING_DIR = QUEUE_DIR / "processing"
ARCHIVE_DIR = QUEUE_DIR / "archive"
FAILED_DIR = QUEUE_DIR / "failed"
LOGS_DIR = QUEUE_DIR / "logs"
CURRENT_LOG = LOGS_DIR / "current.log"
ATF_STATUS_FILE = QUEUE_DIR / "atf_status.json"

PORTS_TO_CHECK = [
    (8088, "Unified Founder Cockpit", "HTTP"),
    (3027, "StackLabs Corporate Edge & JIT", "HTTP"),
    (3033, "FanStack Lite & Live HUD", "HTTP"),
    (8008, "TMI Telemetry Relay", "HTTP"),
    (8095, "SDLC Portal REST API", "HTTP"),
    (3025, "Sovereign CMDB Studio", "HTTP"),
    (5056, "Stream Sniper Transcriber", "HTTP"),
    (3016, "Sovereign Command Portal", "HTTP")
]

running = True

def sig_handler(signum, frame):
    global running
    running = False

signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)

def check_socket(host: str, port: int, timeout: float = 0.15) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def get_header_panel() -> Panel:
    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    ram_used_gb = mem.used / (1024 ** 3)
    ram_total_gb = mem.total / (1024 ** 3)
    
    uptime_secs = int(time.time() - psutil.boot_time())
    days, rem = divmod(uptime_secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    uptime_str = f"{days}d {hours:02d}h {mins:02d}m"
    
    l1, l5, l15 = os.getloadavg()
    
    # Color-code CPU
    if cpu_percent > 85.0:
        cpu_style = "bold red"
    elif cpu_percent > 60.0:
        cpu_style = "bold yellow"
    else:
        cpu_style = "bold green"

    grid = Table.grid(expand=True)
    grid.add_column(ratio=3)
    grid.add_column(ratio=2, justify="right")
    
    grid.add_row(
        "[bold cyan]⚡ CLIO WORKSTATION ENGINE[/bold cyan] [dim](SER7 Zen 4 APU)[/dim]",
        "[dim]PILOT:[/dim] [bold white]James Carroll[/bold white]"
    )
    grid.add_row(
        f"[dim]CPU:[/dim] [{cpu_style}]{cpu_percent:4.1f}%[/{cpu_style}] "
        f"[dim]RAM:[/dim] [bold cyan]{ram_used_gb:4.1f}/{ram_total_gb:4.1f}GB ({mem.percent:.0f}%)[/bold cyan] "
        f"[dim]LOAD:[/dim] [yellow]{l1:.2f} {l5:.2f} {l15:.2f}[/yellow]",
        f"[dim]UPTIME:[/dim] [bold white]{uptime_str}[/bold white]"
    )
    
    return Panel(grid, title="[bold cyan]HOST VITALS & COCKPIT TELEMETRY[/bold cyan]", border_style="cyan", padding=(0, 1))

def get_queue_panel() -> Panel:
    incoming_tickets = sorted(list(INCOMING_DIR.glob("*.md")), key=lambda p: p.stat().st_mtime) if INCOMING_DIR.exists() else []
    processing_tickets = sorted(list(PROCESSING_DIR.glob("*.md")), key=lambda p: p.stat().st_mtime) if PROCESSING_DIR.exists() else []
    archive_tickets = sorted(list(ARCHIVE_DIR.glob("*.md")), key=lambda p: p.stat().st_mtime, reverse=True)[:5] if ARCHIVE_DIR.exists() else []
    failed_tickets = sorted(list(FAILED_DIR.glob("*.md")), key=lambda p: p.stat().st_mtime, reverse=True) if FAILED_DIR.exists() else []
    
    grid = Table.grid(expand=True)
    grid.add_column()
    
    # 1. Processing Row
    if processing_tickets:
        p_ticket = processing_tickets[0]
        elapsed_sec = int(time.time() - p_ticket.stat().st_mtime)
        el_m, el_s = divmod(elapsed_sec, 60)
        grid.add_row(
            f"[bold green on grey15] [PROCESSING] [/bold green on grey15] "
            f"[bold white]{p_ticket.stem}[/bold white] "
            f"[bold yellow]({el_m:02d}:{el_s:02d} elapsed)[/bold yellow]"
        )
    else:
        grid.add_row("[dim][PROCESSING: IDLE] Awaiting incoming work order from Artemis[/dim]")
        
    grid.add_row("")
    
    # 2. Incoming Row
    if incoming_tickets:
        names = ", ".join([p.stem for p in incoming_tickets])
        grid.add_row(f"[bold yellow on grey15] [INCOMING: {len(incoming_tickets)}] [/bold yellow on grey15] [yellow]{names}[/yellow]")
    else:
        grid.add_row("[dim][INCOMING: 0] Queue clean • Zero staged tickets pending[/dim]")
        
    grid.add_row("")
    
    # 3. Recent Archive Row
    grid.add_row("[bold blue on grey15] [RECENT ARCHIVE] [/bold blue on grey15]")
    if archive_tickets:
        for a in archive_tickets:
            grid.add_row(f"  [dim]•[/dim] [white]{a.stem}[/white]")
    else:
        grid.add_row("  [dim]No recent tickets archived[/dim]")
        
    grid.add_row("")
    
    # 4. Failed Row
    if failed_tickets:
        f_names = ", ".join([p.stem for p in failed_tickets])
        grid.add_row(f"[bold white on red] [FAILED: {len(failed_tickets)}] [/bold white on red] [bold red]{f_names}[/bold red]")
    else:
        grid.add_row("[bold green][FAILED: 0][/bold green] [dim]Zero failed runs • Ledger clean[/dim]")
        
    return Panel(grid, title="[bold yellow]TASK & EXECUTION PIPELINE[/bold yellow]", border_style="yellow", padding=(0, 1))

def get_services_panel() -> Panel:
    table = Table(box=None, expand=True, padding=(0, 1))
    table.add_column("Port", style="bold cyan", width=6)
    table.add_column("Service Name", style="white")
    table.add_column("Status", justify="right")
    
    for port, name, _ in PORTS_TO_CHECK:
        online = check_socket("127.0.0.1", port)
        status_text = "[bold green]● ONLINE[/bold green]" if online else "[bold red]○ OFFLINE[/bold red]"
        table.add_row(str(port), name, status_text)
        
    return Panel(table, title="[bold cyan]SERVICE MESH & LOCAL PORTS[/bold cyan]", border_style="cyan", padding=(0, 1))

def get_atf_panel() -> Panel:
    # 1. Check atf_status.json
    status = "STANDBY"
    details = "Ready for pre-deploy execution"
    style = "cyan"
    
    if ATF_STATUS_FILE.exists():
        try:
            with open(ATF_STATUS_FILE, "r") as f:
                data = json.load(f)
                if data.get("status") == "PASSED":
                    status = "CLEARED"
                    details = "Zero defects across ports, journeys & visual baselines"
                    style = "green"
                elif data.get("status") == "BLOCKED":
                    status = "BLOCKED"
                    fails = data.get("failures", [])
                    details = f"{len(fails)} violation(s): {', '.join(fails[:2])}"
                    style = "red"
        except Exception:
            pass
            
    # Fallback / override: check current.log
    if status == "STANDBY" and CURRENT_LOG.exists():
        try:
            # Read last 30 lines
            with open(CURRENT_LOG, "r") as f:
                lines = f.readlines()[-30:]
                content = "".join(lines)
                if "ATF GATE CLEARED" in content or "ATF Gate passed" in content:
                    status = "CLEARED"
                    details = "Zero defects across ports, journeys & visual baselines"
                    style = "green"
                elif "ATF GATE BLOCKED" in content or "ATF Gate failed" in content:
                    status = "BLOCKED"
                    details = "Pre-deploy test failure detected in current.log"
                    style = "red"
                elif "Running Pre-Deploy ATF" in content:
                    status = "TESTING"
                    details = "Evaluating ports, journeys, and visual twins..."
                    style = "yellow"
        except Exception:
            pass

    if status == "CLEARED":
        content_text = f"[bold green]✔ ATF GATE CLEARED (ATF CIRCUIT INTACT)[/bold green] [dim]• {details}[/dim]"
    elif status == "BLOCKED":
        content_text = f"[bold white on red] 🛑 ATF GATE BLOCKED [/bold white on red] [bold red]{details}[/bold red]"
    elif status == "TESTING":
        content_text = f"[bold yellow]⚡ RUNNING PRE-DEPLOY ATF GATES...[/bold yellow] [dim]• {details}[/dim]"
    else:
        content_text = f"[bold cyan]⚪ STANDBY / ARMED[/bold cyan] [dim]• {details}[/dim]"
        
    return Panel(content_text, title="[bold magenta]PRE-DEPLOY ATF CIRCUIT BREAKER[/bold magenta]", border_style=style, padding=(0, 1))

def get_git_panel() -> Panel:
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(SOVEREIGN_ROOT), text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        branch = "unknown"
        
    try:
        status_lines = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=str(SOVEREIGN_ROOT), text=True, stderr=subprocess.DEVNULL
        ).splitlines()
        uncommitted = len(status_lines)
    except Exception:
        uncommitted = 0
        
    try:
        last_commit = subprocess.check_output(
            ["git", "log", "-1", "--pretty=format:%h %s"],
            cwd=str(SOVEREIGN_ROOT), text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        last_commit = "No commits"

    grid = Table.grid(expand=True)
    grid.add_column()
    
    uncommitted_str = f"[yellow]{uncommitted} files[/yellow]" if uncommitted > 0 else "[green]Clean working tree[/green]"
    grid.add_row(f"[dim]BRANCH:[/dim] [bold cyan]{branch}[/bold cyan]   [dim]UNCOMMITTED:[/dim] {uncommitted_str}")
    grid.add_row(f"[dim]LAST COMMIT:[/dim] [bold green]{last_commit}[/bold green]")
    
    return Panel(grid, title="[bold green]GIT & FORGE VITALS[/bold green]", border_style="green", padding=(0, 1))

def build_layout() -> Layout:
    layout = Layout(name="root")
    layout.split_column(
        Layout(get_header_panel(), name="header", size=5),
        Layout(get_queue_panel(), name="queue", ratio=1),
        Layout(get_services_panel(), name="services", size=12),
        Layout(get_atf_panel(), name="breaker", size=3),
        Layout(get_git_panel(), name="git", size=4)
    )
    return layout

def main():
    console = Console()
    
    # Handle --once flag for tests, CI, and single snapshots
    if "--once" in sys.argv:
        console.print(build_layout())
        sys.exit(0)
        
    # Continuous live rendering mode
    try:
        with Live(build_layout(), console=console, refresh_per_second=1, screen=True) as live:
            while running:
                time.sleep(1.0)
                live.update(build_layout())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        sys.exit(0)

if __name__ == "__main__":
    main()
