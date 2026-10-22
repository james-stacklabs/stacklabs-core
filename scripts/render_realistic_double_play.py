import os
import subprocess

BRAIN_DIR = "/home/james/.gemini/antigravity-ide/brain/9f02b012-7c57-408f-a7a4-8f88aeb16754"

F1 = os.path.join(BRAIN_DIR, "dp_frame_1_grounder_1787355721595.jpg")
F2 = os.path.join(BRAIN_DIR, "dp_frame_2_second_base_flip_1787355743385.jpg")
F3 = os.path.join(BRAIN_DIR, "dp_frame_3_first_base_stretch_1787355765749.jpg")
F4 = os.path.join(BRAIN_DIR, "dp_frame_4_title_card_1787355787467.jpg")

OUT_19 = "/home/james/stacklabs/19_Sovereign_Sports/public/videos/double_play_flow.mp4"
OUT_DIST = "/home/james/stacklabs/19_Sovereign_Sports/dist/videos/double_play_flow.mp4"
OUT_15 = "/home/james/stacklabs/15_FanStack/public/videos/double_play_flow.mp4"

BACKUP_VIDEO = "/home/james/stacklabs/19_Sovereign_Sports/public/videos/double_play_flow_hallucination_backup.mp4"

TMP_DIR = "/tmp/dp_render"
os.makedirs(TMP_DIR, exist_ok=True)

# 1. Extract existing audio track from the original video if available
AUDIO_TRACK = os.path.join(TMP_DIR, "audio.aac")
if os.path.exists(BACKUP_VIDEO):
    subprocess.run([
        "ffmpeg", "-y", "-i", BACKUP_VIDEO, "-vn", "-c:a", "copy", AUDIO_TRACK
    ], check=False)

# 2. Render smooth animated video clips for each keyframe with professional broadcast Ken Burns push-in & zooms
# Segment 1: Grounder to Shortstop (1.25s)
SEG1 = os.path.join(TMP_DIR, "seg1.mp4")
subprocess.run([
    "ffmpeg", "-y", "-loop", "1", "-i", F1,
    "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+0.002,1.15)':d=75:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=60",
    "-t", "1.25", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "fast", SEG1
], check=True)

# Segment 2: 2B Flip & Leap over sliding runner (1.25s)
SEG2 = os.path.join(TMP_DIR, "seg2.mp4")
subprocess.run([
    "ffmpeg", "-y", "-loop", "1", "-i", F2,
    "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+0.003,1.2)':d=75:x='iw/2-(iw/zoom/2)+10':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=60",
    "-t", "1.25", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "fast", SEG2
], check=True)

# Segment 3: 1B Stretch & Umpire Out Call (1.3s)
SEG3 = os.path.join(TMP_DIR, "seg3.mp4")
subprocess.run([
    "ffmpeg", "-y", "-loop", "1", "-i", F3,
    "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+0.0025,1.18)':d=78:x='iw/2-(iw/zoom/2)-20':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=60",
    "-t", "1.3", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "fast", SEG3
], check=True)

# Segment 4: 3D "DOUBLE PLAY" Neon Title Card (2.2s)
SEG4 = os.path.join(TMP_DIR, "seg4.mp4")
subprocess.run([
    "ffmpeg", "-y", "-loop", "1", "-i", F4,
    "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+0.004,1.25)':d=132:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=60",
    "-t", "2.2", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "fast", SEG4
], check=True)

# 3. Concatenate segments
CONCAT_FILE = os.path.join(TMP_DIR, "concat.txt")
with open(CONCAT_FILE, "w") as f:
    f.write(f"file '{SEG1}'\nfile '{SEG2}'\nfile '{SEG3}'\nfile '{SEG4}'\n")

COMBINED_RAW = os.path.join(TMP_DIR, "combined_raw.mp4")
subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", CONCAT_FILE,
    "-c:v", "libx264", "-pix_fmt", "yuv420p", COMBINED_RAW
], check=True)

# 4. Merge with audio and export to targets
if os.path.exists(AUDIO_TRACK) and os.path.getsize(AUDIO_TRACK) > 100:
    subprocess.run([
        "ffmpeg", "-y", "-i", COMBINED_RAW, "-i", AUDIO_TRACK,
        "-c:v", "copy", "-c:a", "aac", "-shortest", OUT_19
    ], check=True)
else:
    subprocess.run([
        "ffmpeg", "-y", "-i", COMBINED_RAW, "-c:v", "copy", OUT_19
    ], check=True)

# Copy to dist & 15_FanStack
if os.path.exists(os.path.dirname(OUT_DIST)):
    subprocess.run(["cp", OUT_19, OUT_DIST])
if os.path.exists(os.path.dirname(OUT_15)):
    subprocess.run(["cp", OUT_19, OUT_15])

print(f"✅ Successfully rendered new Double Play video to:\n  - {OUT_19}\n  - {OUT_DIST}\n  - {OUT_15}")
