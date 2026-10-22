import json

with open('/home/james/stacklabs/dna/agents/SOVEREIGN_FANSTACK_ORACLE/payloads/master_fanstack_highlights.json', 'r') as f:
    highlights = json.load(f)

# Sort by length and caps ratio
def score(item):
    msg = item['msg']
    caps = sum(1 for c in msg if c.isupper())
    letters = sum(1 for c in msg if c.isalpha())
    ratio = caps / letters if letters > 0 else 0
    return ratio * min(len(msg), 200)

highlights.sort(key=score, reverse=True)

top_highlights = highlights[:50]

out_md = "# 🛸 FanStack Sovereign MARD Engine - Curated Highlight Reel\n\n"
out_md += "Here is the consolidated master list of the 50 most unhinged, fully-cascaded moments from your `FanCast_Export` datasets—perfect for narration through Glow Studios.\n\n"
out_md += "---\n\n"

for i, h in enumerate(top_highlights):
    out_md += f"### Highlight #{i+1} : Source `({h['date_source']})`\n"
    out_md += f"> \"{h['msg']}\"\n\n"

with open('/home/james/.gemini/antigravity/brain/4e6401f7-612e-4f97-a806-348ac765f755/fanstack_highlights_glow_studios.md', 'w') as out:
    out.write(out_md)
