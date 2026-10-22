import os
import psutil
import time
import subprocess
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich import box
from rich.console import Console
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn
from rich.align import Align

console = Console()

def get_network_stats(interface='wlx74da3858bbdc'):
    try:
        net_io = psutil.net_io_counters(pernic=True)
        stats = net_io.get(interface, net_io.get('eth0', list(net_io.values())[0]))
        return stats.bytes_recv, stats.bytes_sent
    except Exception:
        return 0, 0

def check_daemon_status():
    try:
        result = subprocess.run(['systemctl', 'is-active', 'ollama'], capture_output=True, text=True)
        if 'active' in result.stdout:
            return "[bold green]ONLINE[/bold green]"
        return "[bold red]OFFLINE[/bold red]"
    except Exception:
        return "[bold yellow]UNKNOWN[/bold yellow]"

def get_gpu_stats():
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu', '--format=csv,noheader,nounits'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            util, mem_used, mem_total, temp = result.stdout.strip().split(', ')
            return int(util), int(mem_used), int(mem_total), int(temp)
    except Exception:
        pass
    return None

def generate_dashboard(prev_recv, prev_sent):
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main")
    )
    layout["main"].split_row(
        Layout(name="left_column"),
        Layout(name="right_column")
    )
    layout["left_column"].split_column(
        Layout(name="system_stats"),
        Layout(name="gpu_stats")
    )
    layout["right_column"].split_column(
        Layout(name="network_monitor"),
        Layout(name="agent_status")
    )

    # Header
    header_text = Align.center(Text("PEGASUS DREADNOUGHT TERMINAL (NODE .74)", style="bold cyan on black"))
    layout["header"].update(Panel(header_text, box=box.HEAVY))

    # Left Column: System Stats
    cpu_percent = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    sys_table = Table.grid(padding=1)
    sys_table.add_column(style="bold yellow", justify="right")
    sys_table.add_column()
    sys_table.add_row("CPU Core Usage:", f"{cpu_percent}%")
    sys_table.add_row("RAM Active:", f"{ram.used / (1024**3):.1f}GB / {ram.total / (1024**3):.1f}GB ({ram.percent}%)")
    layout["system_stats"].update(Panel(sys_table, title="CORE TELEMETRY", border_style="yellow"))

    # Left Column: GPU (if exists)
    gpu_data = get_gpu_stats()
    if gpu_data:
        util, m_used, m_tot, temp = gpu_data
        gpu_table = Table.grid(padding=1)
        gpu_table.add_column(style="bold magenta", justify="right")
        gpu_table.add_column()
        gpu_table.add_row("GPU Util:", f"{util}%")
        gpu_table.add_row("VRAM:", f"{m_used}MB / {m_tot}MB")
        gpu_table.add_row("Core Temp:", f"{temp}°C")
        layout["gpu_stats"].update(Panel(gpu_table, title="NVIDIA GTX 980 SUBSYSTEM", border_style="magenta"))
    else:
        layout["gpu_stats"].update(Panel("No valid NVIDIA hardware detected.", title="GPU SUBSYSTEM", border_style="magenta"))

    # Right Column: Network
    cur_recv, cur_sent = get_network_stats()
    dl_speed = (cur_recv - prev_recv) / 1024 / 1024 # MB/s
    up_speed = (cur_sent - prev_sent) / 1024 / 1024 # MB/s
    
    net_table = Table.grid(padding=1)
    net_table.add_column(style="bold blue", justify="right")
    net_table.add_column()
    net_table.add_row("Inbound:", f"[{'bold green' if dl_speed > 1 else 'dim'}]{dl_speed:.2f} MB/s[/]")
    net_table.add_row("Outbound:", f"[{'bold red' if up_speed > 1 else 'dim'}]{up_speed:.2f} MB/s[/]")
    layout["network_monitor"].update(Panel(net_table, title="NETWORK MATRIX (wlx74)", border_style="blue"))

    # Right Column: Agent Status
    agent_status = check_daemon_status()
    agent_table = Table.grid(padding=1)
    agent_table.add_column(style="bold green", justify="right")
    agent_table.add_column()
    agent_table.add_row("Ollama Inference Engine:", agent_status)
    agent_table.add_row("Llama3 Payload:", "Evaluating...")
    layout["agent_status"].update(Panel(agent_table, title="DAEMON INTEGRITY", border_style="green"))

    return layout, cur_recv, cur_sent

if __name__ == "__main__":
    prev_recv, prev_sent = get_network_stats()
    
    with Live(refresh_per_second=2, screen=True) as live:
        while True:
            time.sleep(1)
            layout, prev_recv, prev_sent = generate_dashboard(prev_recv, prev_sent)
            live.update(layout)
