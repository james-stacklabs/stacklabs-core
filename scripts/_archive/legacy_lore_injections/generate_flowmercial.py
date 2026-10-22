import subprocess
import os

input_vid = "/home/james/stacklabs/dna/dropzone/daily_23042026/PXL_20260424_021650494.mp4"
output_vid = "/home/james/stacklabs/dna/dropzone/daily_23042026/FINAL_FLOWMERCIAL_Vientos.mp4"

# The Llama-generated script for Uncle Stevie
top_text = "VIENTOS REDEMPTION ARC"
bottom_text = "YOU SEE THAT?! THE KID STILL HAS IT! #METS"

# FFmpeg command to add text overlay
# Using a basic drawtext filter. We will scale the video to 1080p if needed, but let's just add text.
# We need to escape colons and other special chars in text
top_escaped = top_text.replace("'", "\\'")
bottom_escaped = bottom_text.replace("'", "\\'").replace("!", "\\!")

# Use a built-in font or generic sans-serif
font = "sans-serif"

drawtext_top = f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='{top_escaped}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=50:shadowcolor=black:shadowx=2:shadowy=2"
drawtext_bottom = f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='{bottom_escaped}':fontcolor=yellow:fontsize=40:x=(w-text_w)/2:y=h-100:shadowcolor=black:shadowx=2:shadowy=2"

# Ensure fonts exist, if not fallback to default
if not os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
    drawtext_top = f"drawtext=text='{top_escaped}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=50:box=1:boxcolor=black@0.5:boxborderw=5"
    drawtext_bottom = f"drawtext=text='{bottom_escaped}':fontcolor=yellow:fontsize=40:x=(w-text_w)/2:y=h-100:box=1:boxcolor=black@0.5:boxborderw=5"

cmd = [
    "ffmpeg", "-y", "-i", input_vid,
    "-vf", f"{drawtext_top},{drawtext_bottom}",
    "-c:a", "copy",
    output_vid
]

print("Executing FFmpeg Flowmercial Rendering Engine...")
subprocess.run(cmd)
print(f"Flowmercial complete: {output_vid}")
