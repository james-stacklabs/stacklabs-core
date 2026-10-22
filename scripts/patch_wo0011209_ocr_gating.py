#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Atomic Patch: Gated OCR & Photo Drop Decoupling
Modifies scripts/blueprints/cockpit_bp.py to gate OCR behind explicit opt-in
or screenshot/document classification, and sanitizes pilot_scratch_pad.md.
"""
import os
import sys
import re
from pathlib import Path

BP_PATH = Path("/home/james/stacklabs/scripts/blueprints/cockpit_bp.py")
SCRATCH_PATH = Path("/home/james/stacklabs/pilot_drops/pilot_scratch_pad.md")

def patch_cockpit_bp():
    if not BP_PATH.exists():
        print(f"ERROR: {BP_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    code = BP_PATH.read_text(encoding="utf-8")

    # Define replacement block for api_cockpit_file_drop
    old_target = '''@bp.route('/api/cockpit/file_drop', methods=['POST'])
def api_cockpit_file_drop():
    base_dir = Path("/home/james/stacklabs/pilot_drops")
    base_dir.mkdir(parents=True, exist_ok=True)
    ocr_stream_file = base_dir / "pilot_ocr_stream.md"
    scratch_file = base_dir / "pilot_scratch_pad.md"
    
    uploaded = []
    routes = []
    ocr_results = []
    files = request.files.getlist("files") or request.files.getlist("file")
    if not files and request.files:
        files = list(request.files.values())
        
    if not files:
        return jsonify({"status": "error", "message": "No files provided"}), 400

    image_exts = {".png", ".jpg", ".jpeg", ".webp"}
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for f in files:
        if f and f.filename:
            safe_name = secure_filename(f.filename) or f"drop_{int(time.time())}"
            subfolder = resolve_pilot_drop_subfolder(safe_name)
            dest_dir = base_dir / subfolder
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            dest_path = dest_dir / safe_name
            f.save(str(dest_path))
            uploaded.append(safe_name)
            routes.append(f"{subfolder}/{safe_name}")

            if dest_path.suffix.lower() in image_exts:
                ocr_text = run_clio_ocr(dest_path)
                if ocr_text and not ocr_text.startswith("[OCR Error:"):
                    ocr_filename = f"{dest_path.stem}_ocr.txt"
                    ocr_path = dest_dir / ocr_filename
                    try:
                        ocr_path.write_text(ocr_text, encoding="utf-8")
                    except Exception as e:
                        logger.warning(f"Could not write {ocr_path}: {e}")

                    # 1. Append to dedicated pilot_ocr_stream.md
                    ocr_entry = (
                        f"\\n\\n### [SCREENSHOT OCR: {safe_name}] ({timestamp})\\n"
                        f"- **Image**: [`{subfolder}/{safe_name}`]({subfolder}/{safe_name})\\n"
                        f"- **Text File**: [`{subfolder}/{ocr_filename}`]({subfolder}/{ocr_filename})\\n"
                        f"- **Characters**: {len(ocr_text)}\\n\\n"
                        f"```text\\n{ocr_text}\\n```\\n\\n---\\n"
                    )
                    try:
                        with open(ocr_stream_file, "a", encoding="utf-8") as ocr_f:
                            ocr_f.write(ocr_entry)
                    except Exception as e:
                        logger.warning(f"Could not append to pilot_ocr_stream: {e}")

                    # 2. Append clean 1-line link to pilot_scratch_pad.md
                    scratch_link = (
                        f"\\n\\n> 📷 **Screenshot OCR**: [`{safe_name}`]({subfolder}/{safe_name}) "
                        f"&bull; Extracted {len(ocr_text)} chars &bull; "
                        f"Logged to [`pilot_ocr_stream.md`](pilot_ocr_stream.md) ({timestamp})\\n"
                    )
                    try:
                        with open(scratch_file, "a", encoding="utf-8") as sf:
                            sf.write(scratch_link)
                    except Exception as e:
                        logger.warning(f"Could not append reference to scratchpad: {e}")

                    ocr_results.append({
                        "file": safe_name,
                        "subfolder": subfolder,
                        "text_file": ocr_filename,
                        "text": ocr_text,
                        "length": len(ocr_text)
                    })
                elif ocr_text and ocr_text.startswith("[OCR Error:"):
                    ocr_results.append({
                        "file": safe_name,
                        "subfolder": subfolder,
                        "error": ocr_text
                    })

    return jsonify({
        "status": "success",
        "uploaded": uploaded,
        "routes": routes,
        "ocr_results": ocr_results
    })'''

    new_replacement = '''@bp.route('/api/cockpit/file_drop', methods=['POST'])
def api_cockpit_file_drop():
    base_dir = Path("/home/james/stacklabs/pilot_drops")
    base_dir.mkdir(parents=True, exist_ok=True)
    ocr_stream_file = base_dir / "pilot_ocr_stream.md"
    
    uploaded = []
    routes = []
    ocr_results = []
    files = request.files.getlist("files") or request.files.getlist("file")
    if not files and request.files:
        files = list(request.files.values())
        
    if not files:
        return jsonify({"status": "error", "message": "No files provided"}), 400

    image_exts = {".png", ".jpg", ".jpeg", ".webp"}
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Explicit OCR gating control:
    # - If query param 'ocr' or form param 'ocr' or header 'X-Run-OCR' is provided, respect it strictly.
    # - Otherwise, DEFAULT:
    #     * subfolder == "photos" -> OCR is FALSE (decoupled, no auto-OCR on camera/gallery photos)
    #     * subfolder in ("screenshots", "documents") -> OCR is TRUE
    ocr_req = request.args.get("ocr") or request.form.get("ocr") or request.headers.get("X-Run-OCR")
    explicit_ocr = None
    if ocr_req is not None:
        explicit_ocr = ocr_req.strip().lower() in ("1", "true", "yes", "on")

    for f in files:
        if f and f.filename:
            safe_name = secure_filename(f.filename) or f"drop_{int(time.time())}"
            subfolder = resolve_pilot_drop_subfolder(safe_name)
            dest_dir = base_dir / subfolder
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            dest_path = dest_dir / safe_name
            f.save(str(dest_path))
            uploaded.append(safe_name)
            routes.append(f"{subfolder}/{safe_name}")

            # Determine whether to execute OCR
            run_ocr = explicit_ocr if explicit_ocr is not None else (subfolder in ("screenshots", "documents"))

            if run_ocr and dest_path.suffix.lower() in image_exts:
                ocr_text = run_clio_ocr(dest_path)
                if ocr_text and not ocr_text.startswith("[OCR Error:"):
                    ocr_filename = f"{dest_path.stem}_ocr.txt"
                    ocr_path = dest_dir / ocr_filename
                    try:
                        ocr_path.write_text(ocr_text, encoding="utf-8")
                    except Exception as e:
                        logger.warning(f"Could not write {ocr_path}: {e}")

                    # Append to dedicated pilot_ocr_stream.md
                    ocr_entry = (
                        f"\\n\\n### [SCREENSHOT OCR: {safe_name}] ({timestamp})\\n"
                        f"- **Image**: [`{subfolder}/{safe_name}`]({subfolder}/{safe_name})\\n"
                        f"- **Text File**: [`{subfolder}/{ocr_filename}`]({subfolder}/{ocr_filename})\\n"
                        f"- **Characters**: {len(ocr_text)}\\n\\n"
                        f"```text\\n{ocr_text}\\n```\\n\\n---\\n"
                    )
                    try:
                        with open(ocr_stream_file, "a", encoding="utf-8") as ocr_f:
                            ocr_f.write(ocr_entry)
                    except Exception as e:
                        logger.warning(f"Could not append to pilot_ocr_stream: {e}")

                    # Note: pilot_scratch_pad.md is permanently protected from OCR dumps.

                    ocr_results.append({
                        "file": safe_name,
                        "subfolder": subfolder,
                        "text_file": ocr_filename,
                        "text": ocr_text,
                        "length": len(ocr_text)
                    })
                elif ocr_text and ocr_text.startswith("[OCR Error:"):
                    ocr_results.append({
                        "file": safe_name,
                        "subfolder": subfolder,
                        "error": ocr_text
                    })

    return jsonify({
        "status": "success",
        "uploaded": uploaded,
        "routes": routes,
        "ocr_results": ocr_results
    })'''

    if old_target not in code:
        print("ERROR: old_target block not found in cockpit_bp.py", file=sys.stderr)
        sys.exit(1)

    code = code.replace(old_target, new_replacement)
    BP_PATH.write_text(code, encoding="utf-8")
    print(f"✓ Patched {BP_PATH} with gated OCR routing.")

def clean_scratchpad():
    if not SCRATCH_PATH.exists():
        return
    lines = SCRATCH_PATH.read_text(encoding="utf-8").splitlines()
    cleaned = [l for l in lines if not l.strip().startswith("> 📷 **Screenshot OCR**:")]
    SCRATCH_PATH.write_text("\n".join(cleaned).strip() + "\n", encoding="utf-8")
    print(f"✓ Cleaned stray OCR entries from {SCRATCH_PATH}.")

def main():
    patch_cockpit_bp()
    clean_scratchpad()

if __name__ == "__main__":
    main()
