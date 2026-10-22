import base64
import re
from markdown_it import MarkdownIt

# Read the markdown file
with open('/home/james/.gemini/antigravity/brain/e13ba02f-e5cd-4595-b116-90d931aa6f8a/Sovereign_OS_Enterprise_Valuation.md', 'r') as f:
    md_content = f.read()

# Find all image paths
def encode_image(match):
    alt_text = match.group(1)
    img_path = match.group(2)
    try:
        with open(img_path, 'rb') as img_f:
            b64 = base64.b64encode(img_f.read()).decode('utf-8')
        return f"![{alt_text}](data:image/png;base64,{b64})"
    except Exception as e:
        print(f"Error encoding {img_path}: {e}")
        return match.group(0)

# Replace image paths with base64
md_content = re.sub(r'!\[(.*?)\]\((/home/james.*?\.png)\)', encode_image, md_content)

# Convert to HTML
md = MarkdownIt()
html_body = md.render(md_content)

# Wrap in basic HTML structure
html_out = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Sovereign OS Prospectus</title>
<style>
  body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 20px; color: #333; }}
  h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
  h2 {{ color: #34495e; margin-top: 30px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
  img {{ max-width: 100%; height: auto; display: block; margin: 20px auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
  table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
  th {{ background-color: #f8f9fa; color: #333; }}
  .highlight {{ background-color: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; margin: 20px 0; }}
</style>
</head>
<body>
{html_body}
</body>
</html>
"""

with open('/home/james/stacklabs/dna/dropzone/daily_02052026/Sovereign_Prospectus_With_Images.html', 'w') as f:
    f.write(html_out)

print("HTML generated successfully from MD!")
