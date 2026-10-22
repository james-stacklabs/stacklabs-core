#!/usr/bin/env python3
"""
Sovereign OS: Master Chronicle & Conversation History Compiler (Zero-Gap 4-Tier Engine)
Path: /home/james/stacklabs/scripts/compile_conversation_history.py

Governed by WO-20260818-ANTIGRAVITY-BRAIN-HARVEST.
Unifies all historical pair-programming dialogue and architectural chronicles:
- Tier 1: Google Takeout Gemini Archives (March 10 – April 2026)
- Tier 2: Early Antigravity Step/Artifact Sessions (April 1 – April 20, 2026)
- Tier 3: Legacy Antigravity IDE Overview Logs (April 21 – August 18, 2026)
- Tier 4: Modern Antigravity IDE v2.5.5 Transcript Logs (August 18, 2026 – Present)

Chronologically sorts all unified sessions and chunks them into 450,000-character files
for Google Drive / NotebookLM / Spark consumption.
"""

import os
import sys
import json
import glob
import zipfile
import datetime

OUTPUT_DIR = "/home/james/sovereign_inbox/notebook_sync/Sovereign_Raw_Transcripts"
LEGACY_DIR = "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal"
TAKEOUT_DIR = "/home/james/sovereign_inbox/takeout"
EXTRACTED_TAKEOUT = "/home/james/sovereign_inbox/takeout/extracted_gemini"
LEGACY_BRAIN_DIR = "/home/james/.gemini/antigravity/brain"
IDE2_BRAIN_DIR = "/home/james/.gemini/antigravity-ide/brain"
CHUNK_SIZE_LIMIT = 1500000

os.makedirs(OUTPUT_DIR, exist_ok=True)

def parse_iso_time(ts_str: str) -> float:
    if not ts_str:
        return 0.0
    ts_clean = ts_str.strip().replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(ts_clean)
        return dt.timestamp()
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(ts_str[:19], fmt)
            return dt.replace(tzinfo=datetime.timezone.utc).timestamp()
        except Exception:
            pass
    return 0.0

def ensure_takeout_extracted():
    os.makedirs(EXTRACTED_TAKEOUT, exist_ok=True)
    zip_candidates = [
        os.path.join(TAKEOUT_DIR, "jcc2pointzero_takeout-20260818T210404Z-1-001.zip"),
        os.path.join(TAKEOUT_DIR, "sovereign.os.v1-takeout-20260818T214735Z-1-001.zip")
    ]
    target_history_dir = os.path.join(EXTRACTED_TAKEOUT, "Takeout", "Gemini in Workspace", "Conversation History")
    if os.path.exists(target_history_dir) and len(os.listdir(target_history_dir)) > 10:
        return

    print("Extracting Takeout conversation archives...")
    for zpath in zip_candidates:
        if not os.path.exists(zpath):
            continue
        try:
            with zipfile.ZipFile(zpath, "r") as z:
                for member in z.namelist():
                    if "Takeout/Gemini in Workspace/Conversation History/" in member and member.endswith(".txt"):
                        z.extract(member, EXTRACTED_TAKEOUT)
        except Exception as e:
            print(f"Warning: error extracting {zpath}: {e}", file=sys.stderr)

def harvest_tier0_gemini_apps_activity():
    """Tier 0: Harvest Takeout MyActivity.html files (January 2026 – August 2026)."""
    import html
    import re
    from collections import defaultdict

    html_paths = [
        "/home/james/stacklabs/archives/takeout_raw/jcc2pointzero_takeout/Takeout/My Activity/Gemini Apps/MyActivity.html",
        "/home/james/stacklabs/archives/takeout_raw/sovereign.os.v1/Takeout/My Activity/Gemini Apps/MyActivity.html"
    ]

    day_sessions = defaultdict(list)
    for hpath in html_paths:
        if not os.path.exists(hpath):
            continue
        account = "sovereign.os.v1" if "sovereign.os.v1" in hpath else "jcc2pointzero"
        try:
            with open(hpath, "r", encoding="utf-8", errors="ignore") as fp:
                raw = fp.read()
            cells = raw.split('<div class="outer-cell')
            for c in cells[1:]:
                date_match = re.search(r'([A-Za-z]{3,9}\s+\d{1,2},\s+2026,\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M\s+[A-Z]{3,4})', c)
                date_str = date_match.group(1) if date_match else ''
                clean_ds = re.sub(r'\s+[A-Z]{3,4}$', '', date_str.replace('\u202f', ' ').strip())
                ts_val = 0.0
                for fmt in ('%b %d, %Y, %I:%M:%S %p', '%B %d, %Y, %I:%M:%S %p', '%Y-%m-%d %H:%M:%S'):
                    try:
                        dt = datetime.datetime.strptime(clean_ds, fmt)
                        ts_val = dt.replace(tzinfo=datetime.timezone.utc).timestamp()
                        break
                    except Exception:
                        pass

                if not ts_val:
                    continue

                dt_iso = datetime.datetime.fromtimestamp(ts_val, tz=datetime.timezone.utc).strftime('%Y-%m-%d')
                prompt_match = re.search(r'Prompted\s*(.*?)(?:<br>|</p>|</div>)', c, re.DOTALL)
                prompt = html.unescape(prompt_match.group(1)).strip() if prompt_match else ''

                resp_match = re.search(r'(?:<br>|\n)(<p>|<h2>|<ul>|<ol>)(.*?)(?:<br></div><div class="content-cell)', c, re.DOTALL)
                resp = ''
                if resp_match:
                    resp = html.unescape(re.sub(r'<[^>]+>', '\n', resp_match.group(0))).strip()
                    resp = re.sub(r'\n+', '\n', resp)

                if prompt or resp:
                    day_sessions[(dt_iso, account)].append((ts_val, date_str, prompt, resp))
        except Exception as e:
            print(f"Error parsing MyActivity {hpath}: {e}", file=sys.stderr)

    sessions = []
    for (dt_iso, account), turns in day_sessions.items():
        turns.sort(key=lambda x: x[0])
        earliest_ts = turns[0][0]
        first_time_str = turns[0][1]

        conv_log = [
            "---",
            f"# 💬 DAILY GEMINI CHAT ACTIVITY: {dt_iso} ({account})",
            f"**SESSION DATE:** {first_time_str}\n"
        ]
        for t_val, d_str, prompt, resp in turns:
            if prompt:
                conv_log.append(f"### 👤 USER ({d_str}):")
                conv_log.append(prompt)
                conv_log.append("")
            if resp:
                conv_log.append(f"### 🤖 GEMINI ({d_str}):")
                conv_log.append(resp)
                conv_log.append("")

        sessions.append((earliest_ts, f"activity_{dt_iso}_{account}", "\n".join(conv_log)))

    return sessions

def harvest_tier1_takeout():
    """Tier 1: Harvest Takeout JSON conversation files (March – April 2026)."""
    ensure_takeout_extracted()
    history_dir = os.path.join(EXTRACTED_TAKEOUT, "Takeout", "Gemini in Workspace", "Conversation History")
    if not os.path.exists(history_dir):
        return []

    sessions = []
    for fpath in glob.glob(os.path.join(history_dir, "conversation_*.txt")):
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            turns = data.get("conversation_turns", [])
            if not turns:
                continue

            conv_log = []
            earliest_ts = None
            first_time_str = ""

            for turn in turns:
                if "user_turn" in turn:
                    ut = turn["user_turn"]
                    prompt = ut.get("prompt", "").strip()
                    ts_str = ut.get("turn_last_modified", "")
                    ts_val = parse_iso_time(ts_str)
                    if ts_val and (earliest_ts is None or ts_val < earliest_ts):
                        earliest_ts = ts_val
                        first_time_str = ts_str
                    if prompt:
                        conv_log.append(f"### 👤 USER ({ts_str}):")
                        conv_log.append(prompt)
                        conv_log.append("")

                if "system_turn" in turn:
                    st = turn["system_turn"]
                    text_parts = [t.get("data", "") for t in st.get("text", []) if t.get("data")]
                    citations = [c.get("display_text", "") for c in st.get("citations", []) if c.get("display_text")]
                    ts_str = st.get("turn_last_modified", "")
                    ts_val = parse_iso_time(ts_str)
                    if ts_val and (earliest_ts is None or ts_val < earliest_ts):
                        earliest_ts = ts_val
                        first_time_str = ts_str

                    combined_text = "\n\n".join(text_parts).strip()
                    if citations:
                        combined_text += "\n\n*Referenced Docs:* " + ", ".join(citations)

                    if combined_text:
                        conv_log.append(f"### 🤖 GEMINI ({ts_str}):")
                        conv_log.append(combined_text)
                        conv_log.append("")

            if not conv_log:
                continue

            if earliest_ts is None:
                earliest_ts = os.path.getmtime(fpath)
                first_time_str = datetime.datetime.fromtimestamp(earliest_ts, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            filename = os.path.basename(fpath)
            header = [
                "---",
                f"# 💬 CONVERSATION ID: {filename} (Gemini Inception Archive)",
                f"**SESSION DATE:** {first_time_str} UTC\n"
            ]
            full_session_text = "\n".join(header + conv_log)
            sessions.append((earliest_ts, filename, full_session_text))
        except Exception as e:
            print(f"Error parsing Takeout file {fpath}: {e}", file=sys.stderr)

    return sessions

def harvest_tier2_early_antigravity():
    """Tier 2: Early Antigravity Sessions without overview.txt (April 1 – April 20, 2026)."""
    if not os.path.exists(LEGACY_BRAIN_DIR):
        return []

    sessions = []
    for subdir in glob.glob(os.path.join(LEGACY_BRAIN_DIR, "*")):
        if not os.path.isdir(subdir):
            continue
        conv_id = os.path.basename(subdir)
        if conv_id in ("tempmediaStorage", ".system_generated"):
            continue

        overview_path = os.path.join(subdir, ".system_generated", "logs", "overview.txt")
        if os.path.exists(overview_path) and os.path.getsize(overview_path) > 0:
            # Handled in Tier 3
            continue

        # Look for artifacts and step logs
        artifacts = []
        for fname in sorted(os.listdir(subdir)):
            if fname.endswith(".md") and not fname.endswith(".resolved") and not fname.endswith(".metadata.json"):
                fpath = os.path.join(subdir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as af:
                        content = af.read().strip()
                        if content:
                            artifacts.append((fname, content))
                except Exception:
                    pass

        # Look for step markdown logs
        step_logs = []
        for step_path in sorted(glob.glob(os.path.join(subdir, ".system_generated", "steps", "*", "content.md"))):
            try:
                with open(step_path, "r", encoding="utf-8", errors="replace") as sf:
                    content = sf.read().strip()
                    if content:
                        step_logs.append(content)
            except Exception:
                pass

        if not artifacts and not step_logs:
            continue

        mtime = os.path.getmtime(subdir)
        mtime_str = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        conv_log = []
        conv_log.append("---")
        conv_log.append(f"# 💬 CONVERSATION ID: {conv_id} (Antigravity v0/v1 Early Inception)")
        conv_log.append(f"**LAST MODIFIED:** {mtime_str} UTC\n")

        for fname, acontent in artifacts:
            conv_log.append(f"### 📄 ARTIFACT: `{fname}`")
            conv_log.append(acontent)
            conv_log.append("")

        for scontent in step_logs:
            conv_log.append(f"### 🤖 ANTIGRAVITY STEP LOG:")
            conv_log.append(scontent)
            conv_log.append("")

        sessions.append((mtime, conv_id, "\n".join(conv_log)))

    return sessions

def harvest_tier3_legacy_overview():
    """Tier 3: Legacy Antigravity IDE Overview Logs (April 21 – August 18, 2026)."""
    if not os.path.exists(LEGACY_BRAIN_DIR):
        return []

    sessions = []
    for subdir in glob.glob(os.path.join(LEGACY_BRAIN_DIR, "*")):
        if not os.path.isdir(subdir):
            continue
        conv_id = os.path.basename(subdir)
        if conv_id in ("tempmediaStorage", ".system_generated"):
            continue

        overview_path = os.path.join(subdir, ".system_generated", "logs", "overview.txt")
        if not os.path.exists(overview_path) or os.path.getsize(overview_path) == 0:
            continue

        mtime = os.path.getmtime(overview_path)
        mtime_str = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        conv_log = []
        earliest_ts = None

        try:
            with open(overview_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except Exception:
                        continue

                    source = data.get("source")
                    created_at = data.get("created_at", "")
                    content = data.get("content", "")

                    ts_val = parse_iso_time(created_at)
                    if ts_val and (earliest_ts is None or ts_val < earliest_ts):
                        earliest_ts = ts_val

                    if not content:
                        continue

                    if source == "USER_EXPLICIT":
                        conv_log.append(f"### 👤 USER ({created_at}):")
                        conv_log.append(content.strip())
                        conv_log.append("")
                    elif source == "MODEL":
                        conv_log.append(f"### 🤖 ANTIGRAVITY ({created_at}):")
                        conv_log.append(content.strip())
                        conv_log.append("")
        except Exception as e:
            print(f"Error parsing overview {overview_path}: {e}", file=sys.stderr)
            continue

        if not conv_log:
            continue

        sort_ts = earliest_ts if earliest_ts else mtime

        session_block = [
            "---",
            f"# 💬 CONVERSATION ID: {conv_id}",
            f"**LAST MODIFIED:** {mtime_str} UTC\n"
        ]
        session_block.extend(conv_log)
        sessions.append((sort_ts, conv_id, "\n".join(session_block)))

    return sessions

def harvest_tier4_ide2_transcripts():
    """Tier 4: Modern Antigravity IDE v2.5.5 Transcripts (August 18, 2026 – Present)."""
    brain_dirs = [d for d in [IDE2_BRAIN_DIR, LEGACY_BRAIN_DIR] if os.path.exists(d)]
    if not brain_dirs:
        return []

    sessions = []
    seen_convs = set()
    for bdir in brain_dirs:
        for subdir in glob.glob(os.path.join(bdir, "*")):
            if not os.path.isdir(subdir):
                continue
            conv_id = os.path.basename(subdir)
            if conv_id in ("tempmediaStorage", ".system_generated") or conv_id in seen_convs:
                continue
            seen_convs.add(conv_id)

            transcript_path = os.path.join(subdir, ".system_generated", "logs", "transcript.jsonl")
            transcript_full_path = os.path.join(subdir, ".system_generated", "logs", "transcript_full.jsonl")

            target_file = None
            if os.path.exists(transcript_path) and os.path.getsize(transcript_path) > 0:
                target_file = transcript_path
            elif os.path.exists(transcript_full_path) and os.path.getsize(transcript_full_path) > 0:
                target_file = transcript_full_path

            if not target_file:
                continue

            mtime = os.path.getmtime(target_file)
            mtime_str = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            conv_log = []
            earliest_ts = None

            try:
                with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except Exception:
                            continue

                        source = data.get("source")
                        msg_type = data.get("type")
                        created_at = data.get("created_at", "")
                        content = data.get("content", "")

                        ts_val = parse_iso_time(created_at)
                        if ts_val and (earliest_ts is None or ts_val < earliest_ts):
                            earliest_ts = ts_val

                        if not content:
                            continue

                        if msg_type == "USER_INPUT" or (source == "USER_EXPLICIT" and msg_type in (None, "USER_INPUT")):
                            conv_log.append(f"### 👤 USER ({created_at}):")
                            conv_log.append(content.strip())
                            conv_log.append("")
                        elif msg_type == "PLANNER_RESPONSE" or (source == "MODEL" and msg_type in (None, "PLANNER_RESPONSE")):
                            conv_log.append(f"### 🤖 ANTIGRAVITY ({created_at}):")
                            conv_log.append(content.strip())
                            conv_log.append("")
            except Exception as e:
                print(f"Error parsing IDE2 transcript {target_file}: {e}", file=sys.stderr)
                continue

            if not conv_log:
                continue

            sort_ts = earliest_ts if earliest_ts else mtime

            session_block = [
                "---",
                f"# 💬 CONVERSATION ID: {conv_id} (Antigravity IDE v2.5.5)",
                f"**LAST MODIFIED:** {mtime_str} UTC\n"
            ]
            session_block.extend(conv_log)
            sessions.append((sort_ts, conv_id, "\n".join(session_block)))

    return sessions

def compile_conversations():
    print("🚀 Initializing Master Chronicle Unified Ingestion Engine...")

    t0_sessions = harvest_tier0_gemini_apps_activity()
    print(f"✅ Tier 0 (Takeout Gemini Apps Activity Jan-Aug 2026): {len(t0_sessions)} daily sessions")

    t1_sessions = harvest_tier1_takeout()
    print(f"✅ Tier 1 (Takeout Gemini Inception): {len(t1_sessions)} conversations")

    t2_sessions = harvest_tier2_early_antigravity()
    print(f"✅ Tier 2 (Early Antigravity v0/v1): {len(t2_sessions)} sessions")

    t3_sessions = harvest_tier3_legacy_overview()
    print(f"✅ Tier 3 (Legacy Antigravity Overview): {len(t3_sessions)} sessions")

    t4_sessions = harvest_tier4_ide2_transcripts()
    print(f"✅ Tier 4 (Modern Antigravity IDE v2.5.5): {len(t4_sessions)} sessions")

    all_sessions = t0_sessions + t1_sessions + t2_sessions + t3_sessions + t4_sessions
    print(f"\n📊 Total Combined Sessions Discovered: {len(all_sessions)}")

    # Deduplicate by conversation ID / signature while preserving chronological order
    unique_sessions = {}
    for sort_ts, conv_id, text in all_sessions:
        if conv_id not in unique_sessions:
            unique_sessions[conv_id] = (sort_ts, text)
        else:
            # Keep the longer or earlier version
            prev_ts, prev_text = unique_sessions[conv_id]
            if len(text) > len(prev_text):
                unique_sessions[conv_id] = (min(sort_ts, prev_ts), text)

    sorted_sessions = sorted(unique_sessions.values(), key=lambda x: x[0])
    print(f"📚 Unique Populated Transcripts: {len(sorted_sessions)}")

    if sorted_sessions:
        first_date = datetime.datetime.fromtimestamp(sorted_sessions[0][0], tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        last_date = datetime.datetime.fromtimestamp(sorted_sessions[-1][0], tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"⏳ Chronicle Time Span: {first_date} UTC  ──►  {last_date} UTC (Zero Gaps)")

    # Build monolithic document
    full_history = [
        "# 📜 SOVEREIGN OS MASTER CHRONICLE & CONVERSATION HISTORY",
        "Complete, gapless chronological transcript spanning all historical Gemini and Antigravity IDE pair-programming sessions.",
        f"Generated: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
    ]

    for _, text in sorted_sessions:
        full_history.append(text)

    history_content = "\n".join(full_history)
    print(f"📝 Total Compiled Text Volume: {len(history_content):,} characters")

    # Purge old parts from output directory and legacy directory
    for clean_dir in (OUTPUT_DIR, LEGACY_DIR):
        if os.path.exists(clean_dir):
            for old_part in glob.glob(os.path.join(clean_dir, "SOVEREIGN_OS_CONVERSATION_HISTORY_PART_*.txt")):
                try:
                    os.remove(old_part)
                except Exception:
                    pass

    # Split into 450,000-character chunks
    chunks = []
    current_chunk = []
    current_len = 0

    for line in history_content.splitlines():
        line_len = len(line) + 1
        if current_len + line_len > CHUNK_SIZE_LIMIT and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_len = line_len
        else:
            current_chunk.append(line)
            current_len += line_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    # Write output parts
    written_files = []
    for i, chunk_content in enumerate(chunks, 1):
        part_path = os.path.join(OUTPUT_DIR, f"SOVEREIGN_OS_CONVERSATION_HISTORY_PART_{i}.txt")
        with open(part_path, "w", encoding="utf-8") as out_f:
            out_f.write(chunk_content)
        size_bytes = os.path.getsize(part_path)
        written_files.append((part_path, len(chunk_content), size_bytes))
        print(f"  ✅ Chunk {i}: {os.path.basename(part_path)} ({len(chunk_content):,} chars, {size_bytes:,} bytes)")

    print(f"\n🎉 Successfully compiled {len(written_files)} parts to {OUTPUT_DIR}")
    return written_files

if __name__ == "__main__":
    compile_conversations()
