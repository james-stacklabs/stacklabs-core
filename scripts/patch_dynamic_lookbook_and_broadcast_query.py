#!/home/james/stacklabs/.venv/bin/python3
"""
WO0011251 Artifact 2:
Patches scripts/faas_server.py and scripts/broadcast_intelligence_engine.py so:
1. /api/lookbook/latest.pdf dynamically resolves the newest *LOOKBOOK*.pdf via filesystem mtime/date slug
   (serving pilot_drops/MCAFEE_POST_SHOW_LOOKBOOK_2026_10_19.pdf instead of hardcoded 2026_10_05).
2. /api/broadcast/query dynamically searches the newest transcript/intelligence files (2026_10_19 first)
   when date is omitted or 'latest', with strict line-level deduplication.
"""
import os
import re
from pathlib import Path

FAAS_SERVER = Path("/home/james/stacklabs/scripts/faas_server.py")
BROADCAST_ENGINE = Path("/home/james/stacklabs/scripts/broadcast_intelligence_engine.py")


DYNAMIC_HELPER_BLOCK = '''
# --- WO0011251 DYNAMIC LOOKBOOK & BROADCAST SEARCH HELPERS ---
def _resolve_latest_lookbook_pdf() -> Path:
    search_dirs = [
        Path("/home/james/stacklabs/pilot_drops"),
        Path("/home/james/stacklabs/data/lookbooks"),
        Path("/home/james/stacklabs/reports"),
        Path("/home/james/stacklabs"),
    ]
    candidates = []
    for d in search_dirs:
        if d.exists():
            candidates.extend(d.glob("*LOOKBOOK*.pdf"))
            candidates.extend(d.glob("*lookbook*.pdf"))
    if not candidates:
        raise FileNotFoundError("No lookbook PDF files found in canonical directories.")
    candidates.sort(key=lambda p: (p.name, p.stat().st_mtime), reverse=True)
    return candidates[0]
# --- END WO0011251 HELPERS ---
'''


def patch_server() -> None:
    if not FAAS_SERVER.exists():
        raise FileNotFoundError(f"Missing {FAAS_SERVER}")

    content = FAAS_SERVER.read_text(encoding="utf-8")

    if "_resolve_latest_lookbook_pdf" not in content:
        anchor = "app = FastAPI"
        if anchor in content:
            idx = content.index(anchor)
            content = content[:idx] + DYNAMIC_HELPER_BLOCK + "\n" + content[idx:]
        else:
            content = DYNAMIC_HELPER_BLOCK + "\n" + content

    # Replace hardcoded 2026_10_05 lookbook path in get_latest_lookbook_pdf
    old_route_pattern = re.compile(
        r'@app\.api_route\("/api/lookbook/latest\.pdf",\s*methods=\["GET",\s*"HEAD"\]\)\s*def get_latest_lookbook_pdf\(\):.*?raise HTTPException\(status_code=404,\s*detail="Lookbook PDF not found"\)',
        re.DOTALL,
    )
    new_route_code = '''@app.api_route("/api/lookbook/latest.pdf", methods=["GET", "HEAD"])
def get_latest_lookbook_pdf():
    try:
        latest_pdf = _resolve_latest_lookbook_pdf()
        if latest_pdf.exists():
            return FileResponse(latest_pdf, media_type="application/pdf", filename=latest_pdf.name)
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="Lookbook PDF not found")'''

    if old_route_pattern.search(content):
        content = old_route_pattern.sub(new_route_code, content)
    else:
        content = re.sub(
            r'["\'][^"\']*MCAFEE_POST_SHOW_LOOKBOOK_2026_10_05\.pdf["\']',
            'str(_resolve_latest_lookbook_pdf())',
            content,
        )

    content = content.replace('"10052026"', '""').replace("'10052026'", "''")
    content = content.replace("2026_10_05", "2026_10_19")

    tmp = FAAS_SERVER.with_suffix(".py.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, FAAS_SERVER)
    print("Patched faas_server.py with dynamic mtime lookbook resolution and 2026_10_19 default transcript anchor.")


def patch_broadcast_engine() -> None:
    if not BROADCAST_ENGINE.exists():
        return
    src = BROADCAST_ENGINE.read_text(encoding="utf-8")
    updated = src.replace('"date": date_str or "2026-10-06"', '"date": date_str or "2026-10-19"')
    updated = updated.replace(
        "# Deduplicate while preserving order\n        candidate_files = list(dict.fromkeys(candidate_files))",
        "# Deduplicate and sort newest files (2026_10_19) first\n        candidate_files = sorted(set(candidate_files), key=lambda p: (Path(p).name, Path(p).stat().st_mtime if Path(p).exists() else 0), reverse=True)",
    )
    if '"results": flat_hits,' not in updated:
        target_payload = '"file_matches": results[:3],'
        replacement_payload = '''"file_matches": results[:5],
            "results": [
                {"timestamp": tc, "text": txt, "speaker": f"PAT MCAFEE SHOW • {fm['file']}"}
                for fm in results[:5]
                for tc, txt in fm.get("matches", [])
            ],
            "summary": summary_desc,'''
        updated = updated.replace(target_payload, replacement_payload)

    if updated != src:
        tmp = BROADCAST_ENGINE.with_suffix(".py.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(updated)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, BROADCAST_ENGINE)
        print("Patched broadcast_intelligence_engine.py with 2026-10-19 priority sort and flattened results.")


if __name__ == "__main__":
    patch_server()
    patch_broadcast_engine()
