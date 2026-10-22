#!/usr/bin/env python3
"""
Sovereign OS: FanStack Static Tabloid & Vitals Compiler
Path: /home/james/stacklabs/scripts/build_fanstack_static.py

Compiles static HTML distribution for FanStack Edge Wire (fanstack.stacklabsllc.com).
Consumes data/barf_wire_payload.json and fanstack-wire/template.html, executes
template compilation, enforces Invariant 21 (Clean Room tenant isolation),
and outputs fanstack-wire/dist/index.html and fanstack-wire/dist/data.json.
"""

import os
import sys
import json
import shutil
import argparse
from typing import Dict, Any, List, Tuple

# Default canonical paths
DEFAULT_PAYLOAD_PATH = "/home/james/stacklabs/data/barf_wire_payload.json"
DEFAULT_TEMPLATE_PATH = "/home/james/stacklabs/fanstack-wire/template.html"
DEFAULT_DIST_DIR = "/home/james/stacklabs/fanstack-wire/dist"

# Invariant 21: Banned Corporate Compute Bleed Terms
BANNED_CORPORATE_TERMS = [
    "AMD Zen 4",
    "35W APU",
    "12.53-day payback",
    "12.53-day",
    "Model-S",
    "CapEx BOM",
    "Davidson Homes",
    "Woods Crossing",
    "Pawel Rudnicki",
    "Stephen Emery",
    "Jeremy Malone",
]


def validate_clean_room(content: str) -> Tuple[bool, List[str]]:
    """
    Validates Invariant 21 (Tenant Clean Room).
    Asserts that no corporate enterprise compute terms leak into public consumer sports assets.
    Returns (is_clean, list_of_violations).
    """
    content_lower = content.lower()
    violations = []
    for term in BANNED_CORPORATE_TERMS:
        if term.lower() in content_lower:
            violations.append(term)
    return (len(violations) == 0, violations)


def render_template(template_str: str, payload: Dict[str, Any]) -> str:
    """
    Renders the static template with payload data using Jinja2 if available,
    falling back to direct string placeholder replacement.
    """
    vitals = payload.get("daily_vitals", {})
    around_the_league = payload.get("around_the_league", [])

    # Format around_the_league_cards for direct string substitution fallback
    cards_html_list = []
    for item in around_the_league:
        team = item.get("team", "")
        sentiment = item.get("sentiment", "")
        take = item.get("take", "")
        card = f"""          <div class="take-card bg-[#151922] border border-[#242B38] hover:border-slate-600 rounded-xl p-4 transition shadow-lg flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between gap-2 mb-3">
                <span class="inline-flex items-center px-2.5 py-1 rounded text-xs font-metrics font-black tracking-wider bg-[#0A58CA] text-white shadow-sm">
                  {team}
                </span>
                <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-metrics font-bold tracking-widest bg-[#0B0D13] text-[#FFB020] border border-[#FFB020]/30">
                  {sentiment}
                </span>
              </div>
              <p class="text-xs text-slate-300 leading-relaxed font-sans">
                {take}
              </p>
            </div>
            <div class="mt-4 pt-2 border-t border-slate-800 text-[10px] font-metrics text-slate-500 flex items-center justify-between">
              <span>SCHADENFREUDE WIRE</span>
              <span class="text-[#FFB020]">VERIFIED AGONY</span>
            </div>
          </div>"""
        cards_html_list.append(card)
    around_the_league_cards = "\n".join(cards_html_list)

    context = {
        "headline": payload.get("headline", ""),
        "editorial_rant": payload.get("editorial_rant", ""),
        "systolic": vitals.get("systolic", ""),
        "diastolic": vitals.get("diastolic", ""),
        "pulse": vitals.get("pulse", ""),
        "pastrami_lbs": vitals.get("pastrami_lbs", ""),
        "panic_index": vitals.get("panic_index", ""),
        "doctor_shapiro_status": vitals.get("doctor_shapiro_status", ""),
        "mood_summary": vitals.get("mood_summary", ""),
        "date": payload.get("date", ""),
        "around_the_league": around_the_league,
        "around_the_league_cards": around_the_league_cards,
    }

    try:
        import jinja2
        template = jinja2.Template(template_str)
        rendered = template.render(**context)
    except ImportError:
        # Fallback string replacement
        rendered = template_str
        for k, v in context.items():
            if isinstance(v, (str, int, float)):
                rendered = rendered.replace(f"{{{{{k}}}}}", str(v))
                rendered = rendered.replace(f"{{{{ {k} }}}}", str(v))
        rendered = rendered.replace("{{around_the_league_cards}}", around_the_league_cards)
        rendered = rendered.replace("{{ around_the_league_cards }}", around_the_league_cards)

    return rendered


def build_fanstack_static(
    payload_path: str = DEFAULT_PAYLOAD_PATH,
    template_path: str = DEFAULT_TEMPLATE_PATH,
    dist_dir: str = DEFAULT_DIST_DIR
) -> Dict[str, Any]:
    """
    Executes the full static build pipeline:
    1. Loads payload JSON.
    2. Loads template HTML.
    3. Renders HTML.
    4. Validates Invariant 21 (Clean Room).
    5. Writes dist/index.html and dist/data.json.
    """
    if not os.path.exists(payload_path):
        raise FileNotFoundError(f"Payload not found at {payload_path}")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found at {template_path}")

    # Load payload
    with open(payload_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # Load template
    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()

    # Render
    rendered_html = render_template(template_str, payload)

    # Validate Clean Room Invariant 21
    is_clean, violations = validate_clean_room(rendered_html)
    if not is_clean:
        raise ValueError(
            f"Invariant 21 Clean Room Violation! Corporate compute terms found in output: {violations}"
        )

    # Prepare dist directory
    os.makedirs(dist_dir, exist_ok=True)
    index_html_path = os.path.join(dist_dir, "index.html")
    data_json_path = os.path.join(dist_dir, "data.json")

    # Copy avatar asset if available
    avatar_src = "/home/james/stacklabs/media_vault/03_Assets/barf_avatar.png"
    avatar_dst = os.path.join(dist_dir, "barf_avatar.png")
    if os.path.exists(avatar_src):
        shutil.copyfile(avatar_src, avatar_dst)

    # Write output files
    with open(index_html_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    with open(data_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    html_size = os.path.getsize(index_html_path)
    json_size = os.path.getsize(data_json_path)

    return {
        "success": True,
        "index_html_path": index_html_path,
        "data_json_path": data_json_path,
        "html_size_bytes": html_size,
        "json_size_bytes": json_size,
        "clean_room_verified": True,
        "date": payload.get("date"),
        "headline": payload.get("headline"),
    }


def main():
    parser = argparse.ArgumentParser(description="FanStack Static Tabloid & Vitals Compiler")
    parser.add_argument(
        "--payload",
        default=DEFAULT_PAYLOAD_PATH,
        help="Path to barf_wire_payload.json",
    )
    parser.add_argument(
        "--template",
        default=DEFAULT_TEMPLATE_PATH,
        help="Path to template.html",
    )
    parser.add_argument(
        "--dist",
        default=DEFAULT_DIST_DIR,
        help="Output dist directory",
    )
    args = parser.parse_args()

    try:
        res = build_fanstack_static(
            payload_path=args.payload,
            template_path=args.template,
            dist_dir=args.dist,
        )
        print("=" * 60)
        print("🏈 FANSTACK STATIC TABLOID & VITALS COMPILER // CLIO FORGE")
        print("=" * 60)
        print(f"Status:            SUCCESS")
        print(f"Output HTML:       {res['index_html_path']} ({res['html_size_bytes']} bytes)")
        print(f"Output Data JSON:  {res['data_json_path']} ({res['json_size_bytes']} bytes)")
        print(f"Clean Room Gate:   VERIFIED (0 corporate bleed terms)")
        print(f"Date:              {res['date']}")
        print(f"Headline:          {res['headline'][:60]}...")
        print("=" * 60)
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error during static compilation: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
