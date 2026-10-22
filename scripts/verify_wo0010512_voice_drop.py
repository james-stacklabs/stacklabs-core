#!/usr/bin/env python3
"""
scripts/verify_wo0010512_voice_drop.py
=============================================================================
Verification & Gemini Multimodal Audit Gate for WO0010512
Task: Frictionless Voice Monologue Ingress & Automated Verbatim Transcription

Pipeline:
1. Synthesizes 5s spoken diligence monologue via /api/tts.
2. Posts audio payload to http://127.0.0.1:8088/api/upload.
3. Asserts status 200, is_audio=True, non-empty transcript, and on-disk companion artifacts.
4. Executes Playwright on Pegasus/local Chromium to capture:
   - pegasus_uat_wo0010512_voice_drop_idle_desktop.png
   - pegasus_uat_wo0010512_voice_drop_receipt_desktop.png
5. Invariant 49 Gemini 3.8 Flash Multimodal Cloud Vision ATF Audit Gate.
"""

import os
import sys
import json
import time
import shutil
import urllib.request
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/home/james/stacklabs/.env")

BASE_URL = "http://127.0.0.1:8088"
AUTH_QUERY = "?key=stacklabs2026&from=Pawel"
MOCKUPS_DIR = Path("/home/james/stacklabs/mockups")
TODAY_DIR = Path("/home/james/sovereign_inbox/today")

MOCKUPS_DIR.mkdir(parents=True, exist_ok=True)
TODAY_DIR.mkdir(parents=True, exist_ok=True)


def synthesize_test_audio() -> Path:
    """Synthesizes clean spoken diligence audio via server /api/tts."""
    test_wav = Path("/tmp/verify_wo0010512_monologue.wav")
    print("\n[STEP 1] Synthesizing spoken audio monologue via /api/tts...")
    payload = {
        "text": "Pawel Rudnicki here. Diligence report on Permian basin midstream infrastructure and unhedged natural gas differentials.",
        "voice": "Orbit"
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/tts",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        audio_data = resp.read()
        assert len(audio_data) > 10000, "Synthesized audio is too small"
        with open(test_wav, "wb") as f:
            f.write(audio_data)
    print(f"✅ Synthesized test audio: {test_wav} ({len(audio_data):,} bytes)")
    return test_wav


def upload_audio_monologue(audio_path: Path) -> dict:
    """Posts audio payload to /api/upload using multipart/form-data."""
    print("\n[STEP 2] Posting audio monologue to /api/upload...")
    boundary = "----WebKitFormBoundarySovereignVoiceVerification"
    body = bytearray()

    # Form field: sender
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="sender"\r\n\r\n')
    body.extend(b"Pawel Rudnicki\r\n")

    # Form field: memo
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="memo"\r\n\r\n')
    body.extend(b"WO0010512 Automated Verification Monologue\r\n")

    # Form field: folder
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="folder"\r\n\r\n')
    body.extend(b"incoming\r\n")

    # Form field: file
    filename = audio_path.name
    with open(audio_path, "rb") as f:
        file_bytes = f.read()

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: audio/wav\r\n\r\n")
    body.extend(file_bytes)
    body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        f"{BASE_URL}/api/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        status_code = resp.status
        resp_bytes = resp.read()
        resp_json = json.loads(resp_bytes.decode("utf-8"))

    print(f"[STEP 2] Response status code: {status_code}")
    assert status_code == 200, f"Expected 200, got {status_code}"
    return resp_json


def assert_ingress_and_disk_artifacts(resp_json: dict):
    """Asserts API response structure and companion files on metal."""
    print("\n[STEP 3] Asserting deterministic transcription and companion artifacts...")
    assert resp_json.get("status") == "success", "Response status is not success"
    assert resp_json.get("is_audio") is True, "Response does not flag is_audio: True"

    transcript = resp_json.get("transcript", "").strip()
    print(f"⚡ Verbatim Transcript Received: \"{transcript}\"")
    assert len(transcript) > 10, "Transcript is unexpectedly empty or too short"
    assert "sha256" in resp_json, "Missing SHA-256 hash in response"

    local_path = resp_json.get("local_path")
    assert local_path and os.path.exists(local_path), f"Audio file not found on disk: {local_path}"

    transcript_path = f"{local_path}.transcript.txt"
    assert os.path.exists(transcript_path), f"Transcript companion file missing: {transcript_path}"
    with open(transcript_path, "r", encoding="utf-8") as tf:
        disk_transcript = tf.read().strip()
    assert disk_transcript == transcript, "Transcript file content mismatch"

    meta_path = f"{local_path}.meta.json"
    assert os.path.exists(meta_path), f"Metadata companion file missing: {meta_path}"
    with open(meta_path, "r", encoding="utf-8") as mf:
        meta_data = json.load(mf)
    assert meta_data.get("is_audio") is True, "meta.json is_audio flag mismatch"
    assert meta_data.get("transcript") == transcript, "meta.json transcript mismatch"
    print(f"✅ On-disk artifacts validated: {local_path}, .transcript.txt, .meta.json")


def capture_playwright_twins(upload_resp: dict) -> dict:
    """Executes Playwright to capture idle and receipt visual twin states."""
    from playwright.sync_api import sync_playwright

    print("\n[STEP 4] Executing Playwright Chromium for dual visual twins...")
    dt_idle = MOCKUPS_DIR / "pegasus_uat_wo0010512_voice_drop_idle_desktop.png"
    dt_receipt = MOCKUPS_DIR / "pegasus_uat_wo0010512_voice_drop_receipt_desktop.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"]
        )
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = ctx.new_page()

        portal_url = f"{BASE_URL}/{AUTH_QUERY}"
        print(f"[PLAYWRIGHT] Navigating to {portal_url}...")
        resp = page.goto(portal_url, wait_until="networkidle", timeout=15000)
        assert resp.status == 200, f"Expected 200, got {resp.status}"

        # Ensure dark mode
        page.evaluate("setTheme('dark')")
        page.wait_for_timeout(400)

        # Assert voice recorder widget in idle state
        page.wait_for_selector("#voiceRecorderWidget", state="visible", timeout=5000)
        page.wait_for_selector("#startRecordBtn", state="visible", timeout=5000)
        print("[PLAYWRIGHT] Asserted #voiceRecorderWidget and #startRecordBtn are visible.")

        # Capture Twin 1: Idle state
        page.screenshot(path=str(dt_idle), full_page=False)
        shutil.copy(dt_idle, TODAY_DIR / dt_idle.name)
        print(f"📸 Captured Idle Twin -> {dt_idle}")

        # Render Receipt state using the upload response
        print("[PLAYWRIGHT] Evaluating renderReceipt with verified response payload...")
        page.evaluate(f"renderReceipt({json.dumps(upload_resp)}, null)")
        page.wait_for_timeout(500)

        # Assert Receipt elements
        page.wait_for_selector("#receiptCard", state="visible", timeout=5000)
        page.wait_for_selector("#receiptAudioSection", state="visible", timeout=5000)
        page.wait_for_selector("#receiptAudioPlayer", state="visible", timeout=5000)
        page.wait_for_selector("#receiptTranscriptSection", state="visible", timeout=5000)
        page.wait_for_selector("#copyTranscriptBtn", state="visible", timeout=5000)

        transcript_rendered = page.text_content("#receiptTranscriptText")
        assert transcript_rendered and len(transcript_rendered.strip()) > 5, "Transcript text not rendered in DOM"
        print(f"[PLAYWRIGHT] Asserted #receiptAudioSection and transcript rendered: \"{transcript_rendered.strip()[:60]}...\"")

        # Capture Twin 2: Receipt state
        page.screenshot(path=str(dt_receipt), full_page=False)
        shutil.copy(dt_receipt, TODAY_DIR / dt_receipt.name)
        print(f"📸 Captured Receipt Twin -> {dt_receipt}")

        ctx.close()
        browser.close()

    return {"idle": dt_idle, "receipt": dt_receipt}


def run_gemini_multimodal_audit(image_paths: dict):
    """
    Multimodal Visual Audit via Gemini 3.8 Flash (Invariant 49).
    Audits dark canvas depth, Vantablack styling, typography, and controls.
    """
    from google import genai
    from PIL import Image

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY missing from environment!")
        sys.exit(1)

    print("\n[STEP 5] Initializing Gemini 3.8 Flash Multimodal Cloud Vision Sentry (Invariant 49)...")
    client = genai.Client(api_key=api_key)

    idle_img = Image.open(image_paths["idle"])
    receipt_img = Image.open(image_paths["receipt"])

    prompt = """
You are the Sovereign OS Visual Sentry enforcing Invariant 49 (Multimodal Cloud Vision ATF Audit Gate) and 2014 Material Utility Card aesthetics on StackLabs web portals.

Inspect these two visual twin screenshots:
Image 1: StackLabs Diligence Drop Portal — Idle State (showing 1-Tap Voice Monologue Ingress Widget).
Image 2: StackLabs Diligence Drop Portal — Receipt State (showing Inline Native Audio Player & Verbatim Audio Transcript Card).

Audit the following criteria strictly:
1. THEME & CANVAS DEPTH PARITY:
   - Is the background a deep flat black void (#090A0F) rather than light mode or washed out gray?
   - Is the central card container a distinct matte flat black surface (#0B0D13) with hairline borders (#1E2330)?
   - Are there any un-themed white flashes (#FFFFFF) or floating light containers in dark mode? (Must be NO).
2. CONTEXTUAL TOOL GLOW & STATUS SPINE:
   - Does the card feature a prominent 6px left status spine (Emerald green)?
   - Is there an ambient radial ceiling aura visible at the top of the canvas?
3. TYPOGRAPHY & LAYOUT HARMONIZATION:
   - Does typography use clean Inter headings and JetBrains Mono badges/eyebrows?
   - Are text hierarchy and spacing neat, professional, and balanced?
4. VOICE MONOLOGUE WIDGET (Image 1):
   - Is the 'VOICE MONOLOGUE INGRESS' panel clearly visible with a prominent record button ('Record Voice Monologue') and subtitle?
5. RECEIPT AUDIO & TRANSCRIPT DISPLAY (Image 2):
   - Does the receipt display the native audio player controls and a dedicated 'Verbatim Audio Transcript' card with 'Copy Transcript' action?
   - Is the cryptographic SHA-256 provenance hash present and formatted cleanly?

Provide your structured audit findings. Conclude your response with exactly:
'VERDICT: PASS' or 'VERDICT: FAIL - [reason]'
"""

    print("[INVARIANT 49] Sending dual visual twins to gemini-3.8-flash for forensic visual evaluation...")
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[
            "Image 1: Voice Drop Idle State Screenshot",
            idle_img,
            "Image 2: Voice Drop Receipt State Screenshot",
            receipt_img,
            prompt
        ]
    )

    print("\n" + "=" * 70)
    print("🤖 GEMINI 3.8 FLASH VISUAL AUDIT REPORT:")
    print("=" * 70)
    print(response.text)
    print("=" * 70)

    assert "VERDICT: PASS" in response.text, f"Gemini 3.8 Flash Visual Audit did not pass: {response.text}"
    print("✅ [INVARIANT 49 GATE PASSED] Gemini Cloud Multimodal Vision verified visual parity on metal.")


def main():
    print("=" * 75)
    print("🚀 WO0010512: VOICE MONOLOGUE INGRESS & AUTO-TRANSCRIPTION VERIFICATION")
    print("=" * 75)

    # 1. Synthesize audio
    test_audio = synthesize_test_audio()

    try:
        # 2. Upload audio
        upload_resp = upload_audio_monologue(test_audio)

        # 3. Assert ingress & on-disk companion artifacts
        assert_ingress_and_disk_artifacts(upload_resp)

        # 4. Capture Playwright twins
        image_paths = capture_playwright_twins(upload_resp)

        # 5. Multimodal visual audit via Gemini 3.8 Flash
        run_gemini_multimodal_audit(image_paths)

        print("\n🎉 ALL ACCEPTANCE CRITERIA VERIFIED ON METAL (WO0010512 PASS).")

    finally:
        if test_audio.exists():
            test_audio.unlink()


if __name__ == "__main__":
    main()
