"""
Sovereign Neural Flywheel: Dataset Generator for StackLabs-BrandForge-8B
Path: /home/james/stacklabs/scripts/training/generate_brandforge_dataset.py

Synthesizes instruction/response pairs in ShareGPT/Alpaca format
transforming natural language brand concepts into production-ready Brand Bibles:
- 5-color WCAG-compliant palette
- Google Font pairings
- Standalone SVG logo vector code
- Voice and tone guidelines
Target Model: Qwen/Qwen2.5-7B-Instruct or Qwen2.5-14B-Instruct
"""

import json
from pathlib import Path

OUTPUT_DIR = Path("/home/james/sovereign_inbox/tickets/ENHC0010022-QWEN-A100-NEURAL-FLYWHEEL-PILOT")
OUTPUT_FILE = OUTPUT_DIR / "brandforge_dataset.jsonl"

SYSTEM_PROMPT = """You are StackLabs-BrandForge-8B, an elite autonomous brand architect and design system engineer.
When given a brand brief or business concept, you generate a complete, production-ready Brand Bible containing:
1. 5-Color Palette: Hex codes, RGB, semantic UI roles (Void, Surface, Accent, Primary, Text), and WCAG contrast ratings.
2. Typography Pairings: Curated Google Fonts (Header + Body + Monospace) with CSS imports and weights.
3. SVG Vector Asset: Clean, responsive, self-contained SVG markup for the brand's primary emblem or icon.
4. Brand Persona & Voice: Tone, 3 golden rules, and tagline."""

EXAMPLES = [
    {
        "instruction": "Generate a complete Brand Bible for 'Sovereign Sentinel': An enterprise ranch and livestock AI telemetry monitoring system tracking Longhorn cattle health and water security.",
        "output": """# 🧬 BRAND BIBLE: SOVEREIGN SENTINEL
**Tagline**: *Rugged Edge Telemetry for the High Plains.*

---

## 🎨 1. Five-Color Semantic Palette

| Token | Name | Hex | Semantic Role | WCAG Contrast |
| :--- | :--- | :--- | :--- | :--- |
| `void-bg` | **Texas Night** | `#0B0E14` | Primary Viewport & Canvas | 18.2:1 (AAA vs Text) |
| `surface-panel` | **Corral Iron** | `#1A202C` | Glassmorphic Cards & Headers | 14.5:1 (AAA) |
| `accent-glow` | **Neon Longhorn** | `#00E5FF` | Active Radar, Beacon, Live Vectors | 8.1:1 (AAA) |
| `alert-amber` | **Sunburst Ochre** | `#F59E0B` | Separation & Dystocia Warning | 4.8:1 (AA) |
| `text-primary` | **Plains Mist** | `#F8FAFC` | High-Legibility Headings & Data | 18.2:1 (AAA) |

---

## ✍️ 2. Typography Hierarchy (Google Fonts)

* **Header Font**: `Outfit` (700 Bold / 500 Medium)
  * *CSS Import*: `@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;700&display=swap');`
* **Body / Telemetry Font**: `'JetBrains Mono'` (400 Regular / 600 Semi-Bold)
  * *CSS Import*: `@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');`

---

## 🛡️ 3. Primary SVG Emblem (Vector Markup)

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%" fill="none">
  <!-- Outer Shield Grid -->
  <path d="M50 8 L85 24 V52 C85 72 50 92 50 92 C50 92 15 72 15 52 V24 L50 8Z" 
        stroke="#00E5FF" stroke-width="2.5" fill="#0B0E14" fill-opacity="0.85"/>
  <!-- Stylized Longhorn Horns Arc -->
  <path d="M22 34 C32 20 44 38 50 48 C56 38 68 20 78 34" 
        stroke="#F8FAFC" stroke-width="3" stroke-linecap="round"/>
  <!-- Radar Target / Head Ring -->
  <circle cx="50" cy="52" r="12" stroke="#00E5FF" stroke-width="1.5" stroke-dasharray="2 2"/>
  <circle cx="50" cy="52" r="4" fill="#00E5FF"/>
  <!-- GPS Vector Crosshair -->
  <line x1="50" y1="36" x2="50" y2="42" stroke="#00E5FF" stroke-width="1.5"/>
  <line x1="50" y1="62" x2="50" y2="68" stroke="#00E5FF" stroke-width="1.5"/>
</svg>
```

---

## 🎙️ 4. Persona & Voice Directives
1. **Plain-Spoken Authority**: No corporate fluff. Speak like an experienced ranch foreman who also understands telemetry pipelines.
2. **Deterministic Reliability**: Ground all statements in verified GPS coordinates, ambient heat index, and pasture telemetry.
3. **Action-Oriented Triage**: Always propose the exact physical or software resolution step first."""
    }
]

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for ex in EXAMPLES:
            payload = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": ex["instruction"]},
                    {"role": "assistant", "content": ex["output"]}
                ]
            }
            f.write(json.dumps(payload) + "\n")
    print(f"✅ Generated {len(EXAMPLES)} training examples -> {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
