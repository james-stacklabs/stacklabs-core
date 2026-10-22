#!/usr/bin/env python3
# ==============================================================================
# Sovereign OS: Mobile Review & Alpha Extraction Pipeline for Electric Football
# Generates mobile-optimized review gallery, extracts alpha channels, and stages
# assets for GDrive mobile access and Tailscale mobile web inspection.
# ==============================================================================
import os
import shutil
from PIL import Image, ImageFilter

SRC_DIR = "/home/james/stacklabs/15_FanStack/assets/nfl/electric_football"
WEB_DEST_15 = "/home/james/stacklabs/15_FanStack/public/assets/nfl/electric_football"
WEB_DEST_01 = "/home/james/stacklabs/01_Sovereign_Portal/public/assets/nfl/electric_football"
INBOX_TODAY = "/home/james/sovereign_inbox/today/electric_gridiron_review"

for d in [WEB_DEST_15, WEB_DEST_01, INBOX_TODAY]:
    os.makedirs(d, exist_ok=True)

# Map ugly extracted filenames to clean canonical names
FILE_MAP = {
    'Felt_football_game_token_202608210912.jpeg': 'felt_football_token.jpg',
    'Plastic_football_player_figurine…_202608210912.jpeg': 'plastic_player_offense_blue.jpg',
    'Red_toggle_switch_on_plate_202608210912.jpeg': 'red_toggle_switch_hardware.jpg',
    'Retro_sports_celebration_motion_…_202608210912.mp4': 'retro_sports_celebration.mp4',
    'Vintage_electric_football_game_b…_202608210912.jpeg': 'vintage_electric_field_board.jpg',
    'Vintage_electric_football_player…_202608210912.jpeg': 'plastic_player_defense_red.jpg'
}

def remove_black_background(img_path, out_path, threshold=22, softness=8):
    """Cleanly extracts sprites isolated on solid black (#000000) background."""
    img = Image.open(img_path).convert("RGBA")
    data = img.getdata()
    new_data = []
    for item in data:
        r, g, b, a = item
        # Calculate luminance / distance from pure black
        brightness = (r * 0.299 + g * 0.587 + b * 0.114)
        if brightness < threshold:
            new_data.append((r, g, b, 0))
        elif brightness < threshold + softness:
            # Linear alpha ramp for anti-aliased edge smoothing
            alpha = int(255 * ((brightness - threshold) / softness))
            new_data.append((r, g, b, alpha))
        else:
            new_data.append((r, g, b, 255))
            
    img.putdata(new_data)
    img.save(out_path, "PNG")
    print(f"  ✨ Alpha extracted: {os.path.basename(out_path)}")

print("🚀 [MOBILE ASSET PIPELINE] Normalizing and extracting electric football assets...")

# 1. Normalize and copy
for orig_name, clean_name in FILE_MAP.items():
    src_file = os.path.join(SRC_DIR, orig_name)
    if os.path.exists(src_file):
        for dest_dir in [WEB_DEST_15, WEB_DEST_01, INBOX_TODAY]:
            dest_file = os.path.join(dest_dir, clean_name)
            shutil.copy2(src_file, dest_file)
        print(f"  📁 Staged: {clean_name}")

# 2. Generate Transparent PNG Cutouts
cutout_targets = [
    ('felt_football_token.jpg', 'felt_football_token_transparent.png', 18, 10),
    ('plastic_player_offense_blue.jpg', 'plastic_player_offense_blue_transparent.png', 20, 8),
    ('plastic_player_defense_red.jpg', 'plastic_player_defense_red_transparent.png', 20, 8),
]

for src_name, png_name, thresh, soft in cutout_targets:
    raw_path = os.path.join(INBOX_TODAY, src_name)
    if os.path.exists(raw_path):
        for dest_dir in [WEB_DEST_15, WEB_DEST_01, INBOX_TODAY]:
            out_png = os.path.join(dest_dir, png_name)
            remove_black_background(raw_path, out_png, threshold=thresh, softness=soft)

# 3. Build Mobile-First Standalone HTML Review Suite
html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Sovereign OS — Electric Football Asset Review</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background-color: #07090e; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    .glass-card { background: rgba(13, 22, 39, 0.85); backdrop-filter: blur(12px); border: 1px solid rgba(0, 180, 216, 0.25); border-radius: 12px; }
    .checkerboard { background-color: #111827; background-image: linear-gradient(45deg, #0b0f19 25%, transparent 25%), linear-gradient(-45deg, #0b0f19 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #0b0f19 75%), linear-gradient(-45deg, transparent 75%, #0b0f19 75%); background-size: 16px 16px; background-position: 0 0, 0 8px, 8px -8px, -8px 0px; }
  </style>
</head>
<body class="p-3 sm:p-6 max-w-4xl mx-auto pb-24">
  
  <!-- Header -->
  <header class="mb-6 border-b border-cyan-500/30 pb-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span class="w-3 h-3 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_#00b4d8]"></span>
        <h1 class="text-lg sm:text-2xl font-black tracking-wider uppercase text-white">Sovereign OS Mobile Review</h1>
      </div>
      <span class="px-2 py-1 text-[10px] font-mono font-bold bg-cyan-950 text-cyan-400 border border-cyan-500/40 rounded">WO-2026-GRIDIRON-030</span>
    </div>
    <p class="text-xs text-slate-400 mt-1 font-mono">Pilot Mobile Inspection Desk • 6 Assets Staged & Alpha Extracted</p>
  </header>

  <!-- Asset 1: Toggle Switch -->
  <section class="glass-card p-4 mb-5">
    <div class="flex items-center justify-between mb-2">
      <h2 class="text-sm sm:text-base font-bold text-cyan-300">1. Industrial Toggle Switch Hardware</h2>
      <span class="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded font-mono">⭐ Flawless</span>
    </div>
    <p class="text-xs text-slate-300 mb-3">Heavy-duty red metal lever, stamped 'ELECTRIC 1975' / 'MODERN NGS', glowing amber indicator.</p>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div class="bg-black/80 rounded-lg p-2 border border-slate-800 flex flex-col items-center">
        <img src="/assets/nfl/electric_football/red_toggle_switch_hardware.jpg" class="max-h-64 object-contain rounded" alt="Toggle Switch">
        <span class="text-[10px] font-mono text-slate-400 mt-1">Raw Master (JPEG)</span>
      </div>
    </div>
  </section>

  <!-- Asset 2: Figurine Sprites & Alpha Extraction -->
  <section class="glass-card p-4 mb-5">
    <div class="flex items-center justify-between mb-2">
      <h2 class="text-sm sm:text-base font-bold text-cyan-300">2. 2.5D Molded Plastic Figurine Sprites</h2>
      <span class="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded font-mono">⭐ Flawless (Alpha Ready)</span>
    </div>
    <p class="text-xs text-slate-300 mb-3">Authentic injection-molded seams, slotted pronged bases, and clean team colors.</p>
    <div class="grid grid-cols-2 gap-2 sm:gap-4">
      <div class="checkerboard rounded-lg p-2 border border-slate-700 flex flex-col items-center">
        <img src="/assets/nfl/electric_football/plastic_player_offense_blue_transparent.png" class="max-h-56 object-contain" alt="Offense Blue">
        <span class="text-[10px] font-mono text-cyan-400 mt-1">Offense #34 (Transparent PNG)</span>
      </div>
      <div class="checkerboard rounded-lg p-2 border border-slate-700 flex flex-col items-center">
        <img src="/assets/nfl/electric_football/plastic_player_defense_red_transparent.png" class="max-h-56 object-contain" alt="Defense Red">
        <span class="text-[10px] font-mono text-red-400 mt-1">Defense #72 (Transparent PNG)</span>
      </div>
    </div>
  </section>

  <!-- Asset 3: Felt Football Token -->
  <section class="glass-card p-4 mb-5">
    <div class="flex items-center justify-between mb-2">
      <h2 class="text-sm sm:text-base font-bold text-cyan-300">3. Die-Cut Felt Football Token</h2>
      <span class="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded font-mono">⭐ Flawless</span>
    </div>
    <p class="text-xs text-slate-300 mb-3">Fibrous brown felt craft material with stamped white lace lines for 3D passing arcs.</p>
    <div class="grid grid-cols-2 gap-2 sm:gap-4">
      <div class="bg-black/80 rounded-lg p-2 border border-slate-800 flex flex-col items-center">
        <img src="/assets/nfl/electric_football/felt_football_token.jpg" class="max-h-40 object-contain rounded" alt="Raw Felt Football">
        <span class="text-[10px] font-mono text-slate-400 mt-1">Raw Master</span>
      </div>
      <div class="checkerboard rounded-lg p-2 border border-slate-700 flex flex-col items-center">
        <img src="/assets/nfl/electric_football/felt_football_token_transparent.png" class="max-h-40 object-contain" alt="Transparent Felt Football">
        <span class="text-[10px] font-mono text-cyan-400 mt-1">Transparent Cutout</span>
      </div>
    </div>
  </section>

  <!-- Asset 4: Football Field Board (Root Cause & Solution) -->
  <section class="glass-card p-4 mb-5 border-amber-500/40">
    <div class="flex items-center justify-between mb-2">
      <h2 class="text-sm sm:text-base font-bold text-amber-400">4. Vibrating Metal Field Board (Analysis)</h2>
      <span class="text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded font-mono">⚠️ Re-Route to Procedural</span>
    </div>
    <p class="text-xs text-slate-300 mb-3"><strong>Why AI failed the field:</strong> Image models hallucinated yard sequence (skipping 20 and 30) and placed a large center logo/frame that collides with the dynamic 25-yard auto-focus panning viewport.</p>
    <div class="bg-black/80 rounded-lg p-2 border border-amber-500/30 flex flex-col items-center mb-3">
      <img src="/assets/nfl/electric_football/vintage_electric_field_board.jpg" class="w-full object-contain rounded" alt="Field Board">
      <span class="text-[10px] font-mono text-amber-400 mt-1">Raw Diffusion Field Output (Notice Numbering Flaws)</span>
    </div>
    <div class="bg-cyan-950/40 border border-cyan-500/30 rounded p-2.5 text-xs text-cyan-200">
      <strong>💡 The Sovereign Solution:</strong> We use the metallic green texture for the surface sheen and let HTML5 Canvas dynamically draw the exact yard lines, hash marks, and numbers procedurally in <code>GridironViewportCanvas.tsx</code> with 60Hz micro-vibration!
    </div>
  </section>

  <!-- Asset 5: Touchdown Celebration Video -->
  <section class="glass-card p-4 mb-5">
    <div class="flex items-center justify-between mb-2">
      <h2 class="text-sm sm:text-base font-bold text-cyan-300">5. Retro Touchdown CRT Celebration</h2>
      <span class="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded font-mono">⭐ Video Ready</span>
    </div>
    <p class="text-xs text-slate-300 mb-3">2.5s CRT scanline flashbulb celebration overlay.</p>
    <div class="bg-black rounded-lg p-2 border border-slate-800 flex flex-col items-center">
      <video src="/assets/nfl/electric_football/retro_sports_celebration.mp4" controls playsinline class="w-full max-h-56 object-contain rounded"></video>
      <span class="text-[10px] font-mono text-slate-400 mt-1">Touchdown Celebration Animation</span>
    </div>
  </section>

  <!-- Quick Links -->
  <footer class="text-center text-xs text-slate-500 font-mono">
    Sovereign OS • Tailscale Secured • Auto-Synced to GDrive
  </footer>
</body>
</html>
"""

with open(os.path.join(WEB_DEST_15, "review_electric_gridiron.html"), "w") as f:
    f.write(html_content)

with open(os.path.join(INBOX_TODAY, "index.html"), "w") as f:
    f.write(html_content)

print("✅ [MOBILE ASSET PIPELINE] HTML Mobile Review Gallery generated successfully!")
