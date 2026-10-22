import json

json_path = '/home/james/stacklabs/dna/dropzone/daily_28042026/sovereign_ai_bots_export.json'
md_path = '/home/james/stacklabs/dna/dropzone/daily_28042026/sovereign_ai_bots_export.md'

with open(json_path, 'r') as f:
    data = json.load(f)

md_content = "# Sovereign OS - AI Personas Export\n\n"

for p in data:
    md_content += f"## {p.get('user_name', '')}\n\n"
    # we don't need avatars hardcoded since they are handled dynamically
    # but I'll add a link to where they should be
    md_content += f"![{p.get('user_name', '')} Avatar](/avatars/{p.get('user_name', '')}.jpg)\n\n"
    
    md_content += f"**Title:** {p.get('title', '')}\n\n"
    md_content += f"**City:** {p.get('location', '')}\n\n"
    md_content += f"**Department:** {p.get('department', '')}\n\n"
    md_content += f"**Introduction:** {p.get('introduction', '')}\n\n"
    md_content += f"**Cadence:** {p.get('u_speech_cadence', '')}\n\n"
    
    sys_prompt = p.get('u_system_prompt', '')
    if sys_prompt:
        md_content += f"**System Prompt:**\n```\n{sys_prompt}\n```\n\n"
    md_content += "---\n\n"

with open(md_path, 'w') as f:
    f.write(md_content)

print("Generated MD file.")
