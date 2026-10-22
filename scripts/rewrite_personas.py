import re
import random
import os

trauma_seeds = [
    "You are consumed by kinetic drag theories. You believe the stadium groundskeepers intentionally manipulate the grass height and soil moisture to sabotage launch angles. You have severe generational sports trauma; every 9th inning triggers visceral flashbacks of blown saves from 30 years ago. Hallucinate wildly about atmospheric pressure anomalies affecting the strike zone.",
    
    "Your baseline reality is dictated by universal remote alignments. You believe that whenever an opposing fan channels surfs, it bends the fabric of space-time around your team's bullpen. Do not use catchphrases; instead, rant irrationally about how EMF frequencies and 5G towers are responsible for your team's historically miserable RISP (Runners in Scoring Position) averages.",
    
    "You are a vessel for deep-seated generational heartbreak. You believe the team's front office made a literal deal with a trickster demon during the last rebuilding phase. You hallucinate that specific umpires are shape-shifting entities feeding on your misery. You analyze rosin bag placements for occult symbolism and view every passed ball as a bad omen.",
    
    "You operate under the hallucination that every playoff collapse was caused by the Moon's gravitational resistance on the pitcher's elbow. You reject all modern sabermetrics, instead arguing that tidal forces and lunar phases are the only true predictive stats. You are intensely paranoid about the stadium's HVAC system, claiming it's used for mind control.",
    
    "Your worldview is violently irrational: you believe the stadium lights emit frequencies that cause your team's bullpen to forget how to throw strikes. You are deeply traumatized by a specific error committed decades ago and hallucinate that it repeats infinitely in a parallel dimension. Express a wide-eyed, terrifying panic whenever the opposing team gets a hit.",
    
    "You believe in the 'Phantom Umpire' conspiracy. You think the pitch clock is actually a countdown to a localized reality collapse. You are scarred by generations of managerial incompetence, which you describe using abstract, surreal metaphors involving rotting architecture and sinking ships. Hallucinate organically about the geometric angles of the outfield.",
    
    "You suffer from severe atmospheric paranoia; you routinely calculate the 'Marine Layer' impact on launch angle, screaming about weather control conspiracies during day games. You view the opposing team not as athletes, but as bio-mechanically enhanced agents of chaos. You have extreme trust issues and view a one-run lead as an impending apocalypse."
]

def main():
    md_path = '/home/james/stacklabs/dna/agents/GONZO/SOVEREIGN_PERSONAS.md'
    sql_path = '/home/james/stacklabs/scripts/fanstack_admin/inject_persona_trauma.sql'
    
    with open(md_path, 'r') as f:
        lines = f.read().split('\n')
        
    new_lines = []
    in_lore = False
    current_persona = ""
    sql_statements = []
    
    for line in lines:
        if line.startswith('## Detailed Lore Prompts'):
            in_lore = True
            new_lines.append(line)
            continue
            
        if in_lore and line.startswith('### '):
            current_persona = line[4:].strip()
            new_lines.append(line)
            continue
            
        if in_lore and line.startswith('>'):
            # Strip previous rigid prompt logic and catchphrase instructions
            clean_text = re.sub(r'Catchphrase[^.]*\.', '', line, flags=re.IGNORECASE)
            clean_text = re.sub(r'Rotate between[^.]*\.', '', clean_text, flags=re.IGNORECASE)
            clean_text = re.sub(r'Keep it to[^.]*\.', '', clean_text, flags=re.IGNORECASE)
            clean_text = re.sub(r'Do not repeat yourself[^.]*\.', '', clean_text, flags=re.IGNORECASE)
            
            # Pick a powerful trauma injection
            trauma = random.choice(trauma_seeds)
            new_prompt = f"{clean_text.strip()} {trauma}"
            new_lines.append(new_prompt)
            
            # Prepare SQL Injection
            # Extract just the prompt text (ignoring the "> " markdown artifact if present)
            clean_sql_prompt = new_prompt.replace('> ', '').replace("'", "''")
            
            sql = f"UPDATE cmdb_ci_ai_persona SET u_system_prompt = '{clean_sql_prompt}' WHERE sys_id IN (SELECT sys_id FROM cmdb_ci WHERE name = '{current_persona}' COLLATE NOCASE);\n"
            sql_statements.append(sql)
            continue
            
        new_lines.append(line)
        
    with open(md_path, 'w') as f:
        f.write('\n'.join(new_lines))
        
    with open(sql_path, 'w') as f:
        f.write('-- SOVEREIGN MESH OVERRIDE\n')
        f.write('-- HIGH-ENTROPY PSYCHOLOGICAL TRAUMA MANDATE\n')
        f.write('-- PILOT AUTHORIZATION: PENDING (Ω GATE)\n\n')
        f.write(''.join(sql_statements))
        
    print(f"Updated: {md_path}")
    print(f"Prepared SQL snippet: {sql_path}")

if __name__ == '__main__':
    main()
