import os
import glob
import subprocess

CLIP1_LIST = glob.glob("/home/james/sovereign_inbox/pilot_drops/Theater-goers_racing_down_Broadw*.mp4")
CLIP2_LIST = glob.glob("/home/james/sovereign_inbox/pilot_drops/Red_curtains_parting_revealing_l*.mp4")

if not CLIP1_LIST or not CLIP2_LIST:
    print(f"Error finding clips: CLIP1={CLIP1_LIST}, CLIP2={CLIP2_LIST}")
    exit(1)

clip1 = CLIP1_LIST[0]
clip2 = CLIP2_LIST[0]

OUT_19 = "/home/james/stacklabs/19_Sovereign_Sports/public/videos/broadway_double_play.mp4"
OUT_DIST = "/home/james/stacklabs/19_Sovereign_Sports/dist/videos/broadway_double_play.mp4"
OUT_15 = "/home/james/stacklabs/15_FanStack/public/videos/broadway_double_play.mp4"

TMP_LIST = "/tmp/broadway_concat_list.txt"
with open(TMP_LIST, "w") as f:
    f.write(f"file '{clip1}'\nfile '{clip2}'\n")

# Run concat filter
subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", TMP_LIST,
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", OUT_19
], check=True)

if os.path.exists(os.path.dirname(OUT_DIST)):
    subprocess.run(["cp", OUT_19, OUT_DIST])
if os.path.exists(os.path.dirname(OUT_15)):
    subprocess.run(["cp", OUT_19, OUT_15])

print(f"✅ Successfully stitched Broadway Double Play to:\n  - {OUT_19}\n  - {OUT_DIST}\n  - {OUT_15}")
