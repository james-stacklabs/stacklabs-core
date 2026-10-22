import sqlite3
import os
from datetime import datetime

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
MD_REPORT_PATH = "/home/james/sovereign_inbox/sdlc_board_status_report.md"
HTML_REPORT_PATH = "/home/james/sovereign_inbox/sdlc_board_status_report.html"

def map_state(state):
    s = str(state)
    if s == "0": return "Planning"
    if s == "1": return "Open"
    if s == "2": return "In Progress"
    if s == "3": return "Testing"
    if s == "4": return "Resolved"
    if s == "5": return "Closed"
    return "Unknown"

def map_priority(priority):
    p = str(priority)
    if p == "1": return "🔥 P1 - Critical"
    if p == "2": return "⚡ P2 - High"
    if p == "3": return "🟢 P3 - Moderate"
    return "P3 - Moderate"

def main():
    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query all open tickets (state in 0, 1, 2, 3)
    cursor.execute("""
        SELECT number, type, short_description, description, state, priority, assigned_to, cmdb_ci, sys_created_on, sys_updated_on
        FROM sovereign_tickets
        WHERE state IN (0, 1, 2, 3)
        ORDER BY priority ASC, type ASC, number DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    # Grouping
    incidents = []
    defects = []
    enhancements = []
    stories = []

    for r in rows:
        t_type = r['type'].upper()
        ticket = {
            'number': r['number'],
            'type': r['type'],
            'short_description': r['short_description'] or 'No description provided',
            'description': r['description'] or '',
            'state': map_state(r['state']),
            'priority': map_priority(r['priority']),
            'priority_raw': r['priority'],
            'assigned_to': r['assigned_to'] or 'UNASSIGNED',
            'cmdb_ci': r['cmdb_ci'] or 'General',
            'created': r['sys_created_on'],
            'updated': r['sys_updated_on']
        }
        if t_type == 'INC':
            incidents.append(ticket)
        elif t_type == 'DFCT':
            defects.append(ticket)
        elif t_type == 'ENHC':
            enhancements.append(ticket)
        else:
            stories.append(ticket)

    total_open = len(rows)

    # 1. GENERATE MARKDOWN REPORT
    md_lines = [
        "# 📊 Sovereign OS SDLC Board Status Report",
        f"**Compiled At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Total Open Tickets:** {total_open} (🔥 {len(incidents)} Incidents | ⚡ {len(defects)} Defects | 💎 {len(enhancements)} Enhancements | 📝 {len(stories)} Stories)\n",
        "---",
        "\n## 🔥 Active Incidents (P1/Critical Outages)",
        "These require immediate pilot triage or system intervention to restore telemetry/services.\n"
    ]

    if not incidents:
        md_lines.append("*No active incidents on the board.*")
    else:
        md_lines.append("| Number | Priority | State | CMDB CI | Short Description |")
        md_lines.append("|---|---|---|---|---|")
        for inc in incidents:
            md_lines.append(f"| `{inc['number']}` | {inc['priority']} | **{inc['state']}** | `{inc['cmdb_ci']}` | {inc['short_description']} |")

    md_lines.append("\n## ⚡ Defects / Bugs")
    md_lines.append("Functional failures and logic mismatches backlogged for resolution.\n")
    if not defects:
        md_lines.append("*No open defects on the board.*")
    else:
        md_lines.append("| Number | Priority | State | CMDB CI | Short Description |")
        md_lines.append("|---|---|---|---|---|")
        for dfct in defects:
            md_lines.append(f"| `{dfct['number']}` | {dfct['priority']} | **{dfct['state']}** | `{dfct['cmdb_ci']}` | {dfct['short_description']} |")

    md_lines.append("\n## 💎 Enhancements")
    md_lines.append("Approved feature expansions and premium visual optimizations.\n")
    if not enhancements:
        md_lines.append("*No open enhancements on the board.*")
    else:
        md_lines.append("| Number | Priority | State | CMDB CI | Short Description |")
        md_lines.append("|---|---|---|---|---|")
        for enh in enhancements:
            md_lines.append(f"| `{enh['number']}` | {enh['priority']} | **{enh['state']}** | `{enh['cmdb_ci']}` | {enh['short_description']} |")

    md_lines.append("\n## 📝 Active Stories (Top 25 Sorted by Priority)")
    md_lines.append("General task items and brand onboardings.\n")
    if not stories:
        md_lines.append("*No open stories on the board.*")
    else:
        md_lines.append("| Number | Priority | State | Assignee | CMDB CI | Short Description |")
        md_lines.append("|---|---|---|---|---|---|")
        for st in stories[:25]:
            md_lines.append(f"| `{st['number']}` | {st['priority']} | **{st['state']}** | *{st['assigned_to']}* | `{st['cmdb_ci']}` | {st['short_description']} |")
        if len(stories) > 25:
            md_lines.append(f"\n*...and {len(stories) - 25} more stories in the backlog. Open the HTML version in Chrome to view the full catalog.*")

    with open(MD_REPORT_PATH, 'w') as f:
        f.write('\n'.join(md_lines))
    print(f"Generated Markdown report at: {MD_REPORT_PATH}")

    # 2. GENERATE PREMIUM INTERACTIVE HTML REPORT
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sovereign OS SDLC Board Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-void: #07090e;
            --bg-space: #0c0f17;
            --glass-bg: rgba(13, 18, 28, 0.75);
            --glass-border: rgba(255, 255, 255, 0.08);
            --glow-red: #ef4444;
            --glow-orange: #ff5910;
            --glow-magenta: #d946ef;
            --glow-blue: #38bdf8;
            --glow-green: #10b981;
            --text-main: #f3f4f6;
            --text-dim: rgba(243, 244, 246, 0.6);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: var(--bg-void);
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            min-height: 100vh;
            padding: 40px 20px;
            overflow-x: hidden;
            background-image: radial-gradient(circle at 50% 20%, rgba(56, 189, 248, 0.05) 0%, transparent 60%);
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            margin-bottom: 50px;
            position: relative;
        }}

        .system-banner {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: var(--glow-blue);
            letter-spacing: 0.4em;
            text-transform: uppercase;
            margin-bottom: 12px;
            text-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
        }}

        h1 {{
            font-size: 3rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #fff 30%, var(--text-dim) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }}

        .compiled-at {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: var(--text-dim);
        }}

        /* Metrics Dashboard */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .metric-card {{
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 24px;
            backdrop-filter: blur(12px);
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}

        .metric-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
        }}

        .metric-card.total::before {{ background: linear-gradient(90deg, var(--glow-blue), var(--glow-magenta)); }}
        .metric-card.incidents::before {{ background: var(--glow-red); }}
        .metric-card.defects::before {{ background: var(--glow-magenta); }}
        .metric-card.enhancements::before {{ background: var(--glow-blue); }}
        .metric-card.stories::before {{ background: var(--glow-green); }}

        .metric-value {{
            font-size: 2.8rem;
            font-weight: 800;
            line-height: 1;
            margin-bottom: 8px;
        }}

        .metric-card.total .metric-value {{ color: #fff; }}
        .metric-card.incidents .metric-value {{ color: var(--glow-red); text-shadow: 0 0 15px rgba(239, 68, 68, 0.2); }}
        .metric-card.defects .metric-value {{ color: var(--glow-magenta); text-shadow: 0 0 15px rgba(217, 70, 239, 0.2); }}
        .metric-card.enhancements .metric-value {{ color: var(--glow-blue); text-shadow: 0 0 15px rgba(56, 189, 248, 0.2); }}
        .metric-card.stories .metric-value {{ color: var(--glow-green); text-shadow: 0 0 15px rgba(16, 185, 129, 0.2); }}

        .metric-label {{
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-dim);
            font-weight: 600;
        }}

        /* Navigation Tabs */
        .tabs {{
            display: flex;
            justify-content: center;
            gap: 12px;
            margin-bottom: 40px;
            background: rgba(0,0,0,0.3);
            padding: 6px;
            border-radius: 50px;
            width: max-content;
            margin-left: auto;
            margin-right: auto;
            border: 1px solid var(--glass-border);
        }}

        .tab-btn {{
            background: transparent;
            border: none;
            color: var(--text-dim);
            font-family: 'Outfit', sans-serif;
            font-size: 0.9rem;
            font-weight: 600;
            padding: 10px 24px;
            cursor: pointer;
            border-radius: 50px;
            transition: all 0.2s ease;
        }}

        .tab-btn:hover {{
            color: #fff;
        }}

        .tab-btn.active {{
            background: var(--glow-blue);
            color: #07090e;
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.4);
        }}

        /* Ticket Grid */
        .ticket-section {{
            display: none;
        }}

        .ticket-section.active {{
            display: block;
            animation: fadeIn 0.4s ease-out;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .section-header {{
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .section-title {{
            font-size: 1.5rem;
            font-weight: 600;
            letter-spacing: -0.01em;
        }}

        .section-count {{
            font-family: 'JetBrains Mono', monospace;
            background: rgba(255,255,255,0.05);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            color: var(--text-dim);
            border: 1px solid var(--glass-border);
        }}

        .ticket-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 20px;
        }}

        .ticket-card {{
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 24px;
            backdrop-filter: blur(12px);
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
        }}

        .ticket-card:hover {{
            transform: translateY(-4px);
            border-color: rgba(255,255,255,0.15);
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}

        .card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
        }}

        .ticket-id {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            font-weight: 700;
            color: var(--glow-blue);
        }}

        .incidents .ticket-id {{ color: var(--glow-red); }}
        .defects .ticket-id {{ color: var(--glow-magenta); }}
        .enhancements .ticket-id {{ color: var(--glow-blue); }}
        .stories .ticket-id {{ color: var(--glow-green); }}

        .badge-row {{
            display: flex;
            gap: 8px;
        }}

        .badge {{
            font-size: 0.7rem;
            text-transform: uppercase;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 50px;
            font-family: 'JetBrains Mono', monospace;
        }}

        .badge.p1 {{ background: rgba(239, 68, 68, 0.1); color: var(--glow-red); border: 1px solid rgba(239, 68, 68, 0.2); }}
        .badge.p2 {{ background: rgba(255, 89, 16, 0.1); color: var(--glow-orange); border: 1px solid rgba(255, 89, 16, 0.2); }}
        .badge.p3 {{ background: rgba(255,255,255,0.05); color: var(--text-dim); border: 1px solid var(--glass-border); }}

        .badge.state {{ background: rgba(56, 189, 248, 0.1); color: var(--glow-blue); border: 1px solid rgba(56, 189, 248, 0.2); }}

        .card-title {{
            font-size: 1.15rem;
            font-weight: 600;
            line-height: 1.4;
            color: #fff;
            margin-bottom: 12px;
        }}

        .card-desc {{
            font-size: 0.85rem;
            color: var(--text-dim);
            line-height: 1.6;
            margin-bottom: 20px;
            flex-grow: 1;
        }}

        .card-footer {{
            border-top: 1px solid var(--glass-border);
            padding-top: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.8rem;
        }}

        .ci-tag {{
            font-family: 'JetBrains Mono', monospace;
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--glass-border);
            padding: 4px 10px;
            border-radius: 6px;
            color: var(--text-dim);
        }}

        .assignee {{
            font-weight: 600;
            color: var(--text-dim);
        }}

        .assignee span {{
            color: #fff;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="system-banner">Sovereign OS Command Center</div>
            <h1>SDLC Backlog Dashboard</h1>
            <div class="compiled-at">Mesh Telemetry Synchronized: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </header>

        <!-- Metrics Section -->
        <div class="metrics-grid">
            <div class="metric-card total">
                <div class="metric-value">{total_open}</div>
                <div class="metric-label">Total Open</div>
            </div>
            <div class="metric-card incidents">
                <div class="metric-value">{len(incidents)}</div>
                <div class="metric-label">Incidents</div>
            </div>
            <div class="metric-card defects">
                <div class="metric-value">{len(defects)}</div>
                <div class="metric-label">Defects</div>
            </div>
            <div class="metric-card enhancements">
                <div class="metric-value">{len(enhancements)}</div>
                <div class="metric-label">Enhancements</div>
            </div>
            <div class="metric-card stories">
                <div class="metric-value">{len(stories)}</div>
                <div class="metric-label">Stories</div>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('all')">Show All</button>
            <button class="tab-btn" onclick="switchTab('incidents')">Incidents ({len(incidents)})</button>
            <button class="tab-btn" onclick="switchTab('defects')">Defects ({len(defects)})</button>
            <button class="tab-btn" onclick="switchTab('enhancements')">Enhancements ({len(enhancements)})</button>
            <button class="tab-btn" onclick="switchTab('stories')">Stories ({len(stories)})</button>
        </div>

        <!-- INCIDENTS SECTION -->
        <div id="incidents-sect" class="ticket-section active">
            <div class="section-header">
                <div class="section-title">🔥 Critical Incidents</div>
                <div class="section-count">{len(incidents)} items</div>
            </div>
            <div class="ticket-grid incidents">
                {"".join(f'''
                <div class="ticket-card">
                    <div class="card-header">
                        <span class="ticket-id">{inc['number']}</span>
                        <div class="badge-row">
                            <span class="badge p1">P1 - Critical</span>
                            <span class="badge state">{inc['state']}</span>
                        </div>
                    </div>
                    <div class="card-title">{inc['short_description']}</div>
                    <div class="card-desc">{inc['description']}</div>
                    <div class="card-footer">
                        <span class="ci-tag">{inc['cmdb_ci']}</span>
                        <span class="assignee">Assignee: <span>{inc['assigned_to']}</span></span>
                    </div>
                </div>
                ''' for inc in incidents) if incidents else '<div style="color:var(--text-dim);font-style:italic;grid-column:1/-1;text-align:center;padding:40px;">No open incidents on the board.</div>'}
            </div>
        </div>

        <!-- DEFECTS SECTION -->
        <div id="defects-sect" class="ticket-section active">
            <div style="margin-top: 40px;" class="section-header">
                <div class="section-title">⚡ Functional Defects</div>
                <div class="section-count">{len(defects)} items</div>
            </div>
            <div class="ticket-grid defects">
                {"".join(f'''
                <div class="ticket-card">
                    <div class="card-header">
                        <span class="ticket-id">{df['number']}</span>
                        <div class="badge-row">
                            <span class="badge {'p1' if df['priority_raw'] == 1 else 'p2' if df['priority_raw'] == 2 else 'p3'}">{df['priority']}</span>
                            <span class="badge state">{df['state']}</span>
                        </div>
                    </div>
                    <div class="card-title">{df['short_description']}</div>
                    <div class="card-desc">{df['description']}</div>
                    <div class="card-footer">
                        <span class="ci-tag">{df['cmdb_ci']}</span>
                        <span class="assignee">Assignee: <span>{df['assigned_to']}</span></span>
                    </div>
                </div>
                ''' for df in defects) if defects else '<div style="color:var(--text-dim);font-style:italic;grid-column:1/-1;text-align:center;padding:40px;">No open defects on the board.</div>'}
            </div>
        </div>

        <!-- ENHANCEMENTS SECTION -->
        <div id="enhancements-sect" class="ticket-section active">
            <div style="margin-top: 40px;" class="section-header">
                <div class="section-title">💎 Approved Enhancements</div>
                <div class="section-count">{len(enhancements)} items</div>
            </div>
            <div class="ticket-grid enhancements">
                {"".join(f'''
                <div class="ticket-card">
                    <div class="card-header">
                        <span class="ticket-id">{en['number']}</span>
                        <div class="badge-row">
                            <span class="badge {'p1' if en['priority_raw'] == 1 else 'p2' if en['priority_raw'] == 2 else 'p3'}">{en['priority']}</span>
                            <span class="badge state">{en['state']}</span>
                        </div>
                    </div>
                    <div class="card-title">{en['short_description']}</div>
                    <div class="card-desc">{en['description']}</div>
                    <div class="card-footer">
                        <span class="ci-tag">{en['cmdb_ci']}</span>
                        <span class="assignee">Assignee: <span>{en['assigned_to']}</span></span>
                    </div>
                </div>
                ''' for en in enhancements) if enhancements else '<div style="color:var(--text-dim);font-style:italic;grid-column:1/-1;text-align:center;padding:40px;">No open enhancements on the board.</div>'}
            </div>
        </div>

        <!-- STORIES SECTION -->
        <div id="stories-sect" class="ticket-section active">
            <div style="margin-top: 40px;" class="section-header">
                <div class="section-title">📝 Active Stories</div>
                <div class="section-count">{len(stories)} items</div>
            </div>
            <div class="ticket-grid stories">
                {"".join(f'''
                <div class="ticket-card">
                    <div class="card-header">
                        <span class="ticket-id">{st['number']}</span>
                        <div class="badge-row">
                            <span class="badge {'p1' if st['priority_raw'] == 1 else 'p2' if st['priority_raw'] == 2 else 'p3'}">{st['priority']}</span>
                            <span class="badge state">{st['state']}</span>
                        </div>
                    </div>
                    <div class="card-title">{st['short_description']}</div>
                    <div class="card-desc">{st['description']}</div>
                    <div class="card-footer">
                        <span class="ci-tag">{st['cmdb_ci']}</span>
                        <span class="assignee">Assignee: <span>{st['assigned_to']}</span></span>
                    </div>
                </div>
                ''' for st in stories) if stories else '<div style="color:var(--text-dim);font-style:italic;grid-column:1/-1;text-align:center;padding:40px;">No open stories on the board.</div>'}
            </div>
        </div>
    </div>

    <script>
        function switchTab(type) {{
            // Button active class toggle
            const buttons = document.querySelectorAll('.tab-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            
            // Find target index/button
            const eventMap = {{
                'all': 0,
                'incidents': 1,
                'defects': 2,
                'enhancements': 3,
                'stories': 4
            }};
            buttons[eventMap[type]].classList.add('active');

            // Hide/Show sections
            const sections = document.querySelectorAll('.ticket-section');
            if (type === 'all') {{
                sections.forEach(sec => sec.style.display = 'block');
            }} else {{
                sections.forEach(sec => sec.style.display = 'none');
                if (type === 'incidents') document.getElementById('incidents-sect').style.display = 'block';
                if (type === 'defects') document.getElementById('defects-sect').style.display = 'block';
                if (type === 'enhancements') document.getElementById('enhancements-sect').style.display = 'block';
                if (type === 'stories') document.getElementById('stories-sect').style.display = 'block';
            }}
        }}
    </script>
</body>
</html>
"""

    with open(HTML_REPORT_PATH, 'w') as f:
        f.write(html_content)
    print(f"Generated HTML report at: {HTML_REPORT_PATH}")

if __name__ == "__main__":
    main()
