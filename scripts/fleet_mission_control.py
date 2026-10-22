#!/usr/bin/env python3
import time
import requests
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.align import Align
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn
import sys

API_URL = "http://localhost:8091/api/stats"

def fetch_stats():
    try:
        r = requests.get(API_URL, timeout=2)
        return r.json()
    except Exception:
        return None

def make_bar(percent, color):
    bar_len = 15
    filled = int((percent / 100.0) * bar_len)
    empty = bar_len - filled
    return f"[{color}]{'█' * filled}[/][dim]{'░' * empty}[/]"

def make_node_panel(node_name, stats, color):
    # Safety wrapper for load
    load_metric = str(stats.get('load', 'N/A')) if stats else 'N/A'
    
    if not stats or stats.get("status", "").startswith("Error") or "Offline" in stats.get("status", ""):
        txt = Text(f"Node Offline or Error: {stats.get('status', 'Unknown')}", style="bold red")
        return Panel(Align.center(txt, vertical="middle"), title=f"[{color}]{node_name}[/]", border_style=color)
        
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold white", justify="right", width=6, no_wrap=True)
    table.add_column(width=15, no_wrap=True)
    table.add_column(justify="right", no_wrap=True)
    
    # Status
    status_color = "bold green" if stats["status"] == "Online" else "bold yellow"
    
    # RAM
    ram_pct = stats["ram_percent"]
    ram_col = "green" if ram_pct < 60 else "yellow" if ram_pct < 85 else "red"
    
    table.add_row("STATUS", f"[{status_color}]{stats['status']}[/]", "")
    table.add_row("LOAD", Text(load_metric, no_wrap=True), "")
    table.add_row("CPU", make_bar(stats['cpu'], "cyan"), f"{stats['cpu']}%")
    table.add_row("RAM", make_bar(ram_pct, ram_col), f"{stats['ram_used']}G / {stats['ram_total']}G ({ram_pct}%)")
    table.add_row("SWAP", make_bar(stats['swap_percent'], "magenta"), f"{stats['swap_used']}G / {stats['swap_total']}G ({stats['swap_percent']}%)")
    
    return Panel(table, title=f"[{color}]{node_name}[/]", border_style=color, padding=(1, 1))

def generate_layout(data):
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main")
    )
    
    header_text = Text("SOVEREIGN OS TARGETING & FLEET TELEMETRY MATRIX", justify="center", style="bold white on blue")
    layout["header"].update(Panel(header_text))
    
    if data:
        layout["main"].split_row(
            Layout(make_node_panel("Sovereign-E (.73)", data.get("node_73"), "blue")),
            Layout(make_node_panel("Pi 5 (.74)", data.get("node_74"), "magenta"))
        )
    else:
        layout["main"].update(Panel(Align.center(Text("WAITING FOR BACKEND TELEMETRY... (Is 8091 running?)", style="bold red blink")), border_style="red"))
        
    return layout

if __name__ == "__main__":
    try:
        with Live(refresh_per_second=2, screen=True) as live:
            while True:
                data = fetch_stats()
                live.update(generate_layout(data))
                time.sleep(1)
    except KeyboardInterrupt:
        sys.exit(0)
