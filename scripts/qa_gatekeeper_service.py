import os
import sys
import json
import sqlite3
import pypdf

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def execute_artifact_quality_audit(target_dir, brand_name):
    print(f"🕵️‍♂️ Initializing Sovereign QA Gatekeeper Audit for: {brand_name}")
    
    # Look for the specific PDF report for this brand in target_dir
    pdf_path = None
    brand_clean = brand_name.replace(' ', '_').replace('&', '_').replace('/', '_')
    expected_filename = f"{brand_clean}_Genesis_Lookbook_and_Production_Bible.pdf"
    if os.path.exists(target_dir):
        exact_path = os.path.join(target_dir, expected_filename)
        if os.path.exists(exact_path):
            pdf_path = exact_path
        else:
            # Fallback to legacy seeding report name or lookbook suffix matching the brand name
            for f in os.listdir(target_dir):
                f_lower = f.lower()
                brand_lower = brand_clean.lower()
                if brand_lower in f_lower:
                    if f.endswith("Seeding_Report.pdf") or f.endswith("Genesis_Lookbook_and_Production_Bible.pdf"):
                        pdf_path = os.path.join(target_dir, f)
                        break
            
    if not pdf_path or not os.path.exists(pdf_path):
        return {"status": "FAIL", "reason": f"CRITICAL: Final print-ready PDF manual was never generated on disk in: {target_dir} (Expected: {expected_filename})"}
        
    # Phase 1: Scan the PDF for lazy boilerplate and raw database dumps
    try:
        reader = pypdf.PdfReader(pdf_path)
        full_text = ""
        for page in reader.pages:
            text_extracted = page.extract_text()
            if text_extracted:
                full_text += text_extracted
            
        forbidden_tokens = ["CREATE TABLE", "VARCHAR", "INTEGER DEFAULT", "quadrant_", "m2m_persona_room"]
        for token in forbidden_tokens:
            if token.lower() in full_text.lower():
                return {
                    "status": "FAIL",
                    "reason": f"LAZINESS DETECTED: Report contains un-sanitized developer metrics or placeholder elements: '{token}'."
                }
    except Exception as e:
        return {"status": "FAIL", "reason": f"COMPLIANCE FAULT: Failed to parse PDF text layers cleanly: {str(e)}"}

    # Phase 2: Verify SQLite table indices are populated with custom deep lore
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Format potential team identifiers
    brand_team = brand_name.upper().replace(" ", "").replace("&", "")
    brand_team_amp = brand_name.upper().replace(" ", "")
    possible_teams = [brand_team, brand_team_amp]
    if "ARKLE" in brand_name.upper():
        possible_teams.extend(["ARKLEVET", "ARKLE_VET"])
    
    placeholders = ",".join(["?"] * len(possible_teams))
    rows = cursor.execute(f"SELECT user_name, system_prompt FROM persona WHERE team IN ({placeholders})", possible_teams).fetchall()
    conn.close()
    
    if not rows:
        return {"status": "FAIL", "reason": f"DATABASE FAULT: No seeded personas found in database for team: {brand_team}."}
        
    for row in rows:
        user_name, sys_prompt = row
        if not sys_prompt or len(sys_prompt) < 1000:
            return {
                "status": "FAIL",
                "reason": f"LAZINESS DETECTED: Persona @{user_name} has truncated or stubbed system_prompt (length: {len(sys_prompt) if sys_prompt else 0} characters)."
            }

    # Phase 3: Content and Visual awareness audit on the PDF text layer
    if len(full_text) < 3000:
        return {
            "status": "FAIL",
            "reason": f"LAZINESS DETECTED: PDF report is a shell with too little content ({len(full_text)} characters, expected at least 3,000)."
        }

    for row in rows:
        user_name, _ = row
        handle_token = f"@{user_name}"
        if handle_token.lower() not in full_text.lower():
            return {
                "status": "FAIL",
                "reason": f"COMPLIANCE FAULT: PDF report is missing the seeded persona dossier for {handle_token}."
            }

    # Phase 4: Audit for placeholder/initials-based SVGs
    for row in rows:
        user_name, _ = row
        avatar_dir = f"/home/james/stacklabs/15_FanStack/public/avatars/{user_name}"
        if os.path.exists(avatar_dir):
            for file_name in os.listdir(avatar_dir):
                if file_name.endswith(".svg"):
                    svg_path = os.path.join(avatar_dir, file_name)
                    try:
                        with open(svg_path, "r", encoding="utf-8") as f:
                            svg_content = f.read()
                            if "SOVEREIGN_GENERATED_FALLBACK" in svg_content:
                                continue
                            if "<text" in svg_content or ("initial" in svg_content.lower() or len(svg_content) < 5000):
                                return {
                                    "status": "FAIL",
                                    "reason": f"LAZINESS DETECTED: Placeholder SVG initials badge found for advocate @{user_name} at: {file_name}"
                                }
                    except Exception as e:
                        pass

    # Phase 5: Pose Variant Diversity Audit
    import hashlib
    for row in rows:
        user_name, _ = row
        avatar_dir = f"/home/james/stacklabs/avatars/{user_name}"
        pose_files = [f"{user_name}_avatar.png", f"{user_name}_pointing.png", f"{user_name}_shrug.png"]
        
        hashes = {}
        for filename in pose_files:
            file_path = os.path.join(avatar_dir, filename)
            if not os.path.exists(file_path):
                return {
                    "status": "FAIL",
                    "reason": f"COMPLIANCE FAULT: Pose variant image is missing for advocate @{user_name}: {filename}"
                }
            try:
                with open(file_path, "rb") as f:
                    file_content = f.read()
                    h = hashlib.md5(file_content).hexdigest()
                    hashes[filename] = h
            except Exception as e:
                return {
                    "status": "FAIL",
                    "reason": f"COMPLIANCE FAULT: Failed to read pose variant image for @{user_name}: {filename} ({str(e)})"
                }
                
        # Compare hashes to check for identical duplicates
        seen_hashes = {}
        for filename, h in hashes.items():
            if h in seen_hashes:
                other_file = seen_hashes[h]
                return {
                    "status": "FAIL",
                    "reason": f"COMPLIANCE FAULT: Duplicate pose variant detected for @{user_name}. '{filename}' and '{other_file}' are identical copies."
                }
            seen_hashes[h] = filename

    print("✅ Quality Control Passed: Artifacts are clean, customized, and production-ready.")
    return {"status": "PASS", "inc_ticket": None}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 qa_gatekeeper_service.py <target_dir> <brand_name>")
        sys.exit(1)
    res = execute_artifact_quality_audit(sys.argv[1], sys.argv[2])
    print(json.dumps(res))
    if res["status"] == "FAIL":
        sys.exit(1)
