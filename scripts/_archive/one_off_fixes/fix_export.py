import json

file_path = '/home/james/stacklabs/dna/dropzone/daily_28042026/sovereign_ai_bots_export.json'
with open(file_path, 'r') as f:
    data = json.load(f)

for p in data:
    # 1. Fix Dot's introduction containing the avatar
    if p['user_name'] == 'dot' and '/avatars/' in (p.get('introduction') or ''):
        p['introduction'] = 'A relentless analytical OS obsessed with the Mets.'
        
    # 2. Fix where Full Profile is in introduction but u_system_prompt is null or short
    intro = p.get('introduction', '') or ''
    sys_prompt = p.get('u_system_prompt', '') or ''
    
    # If introduction contains markdown headers (# SOVEREIGN OS PERSONA PROFILE)
    if '# ' in intro and len(intro) > 500:
        if not sys_prompt or len(sys_prompt) < 500:
            p['u_system_prompt'] = intro
        
        # Now fix introduction to be just a short summary
        lines = intro.split('\n')
        short_intro = ""
        for line in lines:
            if line.startswith('You are ') or line.startswith('ROLE:'):
                short_intro = line.replace('ROLE:', '').strip()
                break
        if not short_intro:
            short_intro = "A Sovereign OS persona."
            
        p['introduction'] = short_intro
        
    # 3. Fix weird long titles
    title = p.get('title', '') or ''
    if len(title) > 50:
        if p['user_name'] == 'barf':
            p['title'] = 'The Unhinged Mets Fan'
        elif p['user_name'] == 'battery_chucker':
            p['title'] = 'The Toxic Phillies Fan'
        elif p['user_name'] == '7_train_terry':
            p['title'] = 'The Pessimistic Mets Fan'

with open(file_path, 'w') as f:
    json.dump(data, f, indent=2)

print("Fixed JSON export.")
