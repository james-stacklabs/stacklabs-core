"""
Briefing Blueprint -- Executive Audio Briefing, Episode Manifest & Apple Podcasts / CarPlay RSS.
Path: /home/james/stacklabs/scripts/blueprints/briefing_bp.py
Work Order: WO0010526
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from flask import Blueprint, jsonify, request, Response, send_from_directory, abort

logger = logging.getLogger("stacklabs_ingress")

bp = Blueprint('briefing_bp', __name__)

EPISODES_DIR = "/home/james/sovereign_inbox/pilot_drops/episodes"
EPISODES_MANIFEST = os.path.join(EPISODES_DIR, "episodes.json")

# Default seed manifest if file doesn't exist yet
DEFAULT_EPISODES = [
    {
        "id": "ep2",
        "number": 2,
        "title": "The Matrix of Market Panic: Stigmergy & The Monday Soak",
        "date": "2026-10-03",
        "date_display": "TODAY • OCT 03, 2026",
        "duration": "11:24",
        "duration_seconds": 684,
        "audio_file": "episode_02_matrix_of_market_panic.m4a",
        "audio_url": "/drops/episodes/episode_02_matrix_of_market_panic.m4a",
        "instant_brief": [
            "Escaping the Technical Analysis Matrix: Traditional indicators (RSI, Moving Averages) measure price after the crowd moves—literally inspecting skid marks on the road after the collision. Stigmergic ant colonies model biological pheromone amplification to predict capitulation bounces before the first green candle prints.",
            "A100 GPU Fine-Tuning Convergence: Trained custom Qwen2.5-3B model on an 80GB Nvidia A100 SXM4 GPU via QLoRA. Training loss collapsed from 1.54 to 0.026 (~99.8% token accuracy). Quantized to 1.93 GB 4-bit GGUF running at 35–50 t/s on pure CPU.",
            "The Desk Node Hardware Appliance: Institutional trading desks will not risk proprietary order flow or prompts on third-party cloud hyperscalers. StackLabs dropships pre-flashed, air-gapped Mini PC appliances ($160 BOM, $2,500/yr lease) directly to trader desks for zero-cloud data privacy and edge security."
        ],
        "chapters": [
            {"time": 0, "label": "00:00 Intro & Setup"},
            {"time": 145, "label": "02:25 The Skid Mark Fallacy"},
            {"time": 320, "label": "05:20 A100 Loss 0.026"},
            {"time": 510, "label": "08:30 Desk Node Appliance"}
        ],
        "summary": "Forensic breakdown of biological stigmergy in financial order books, the A100 Qwen-3B fine-tuning run tonight, and the air-gapped Desk Node hardware appliance.",
        "published": True
    },
    {
        "id": "ep1",
        "number": 1,
        "title": "The Pendulum & The Algorithm: Crowd Mechanics in Energy Trading",
        "date": "2026-10-01",
        "date_display": "OCT 01, 2026",
        "duration": "09:15",
        "duration_seconds": 555,
        "audio_file": "episode_01_pendulum_and_algorithm.m4a",
        "audio_url": "/drops/episodes/episode_01_pendulum_and_algorithm.m4a",
        "instant_brief": [
            "The Energy Volatility Pendulum: How crowd overreaction in crude and natural gas spreads creates deterministic mean-reversion brackets.",
            "Algorithmic Crowding vs. Real Asset Fundamentals: Why systematic trend-followers amplify panic in pipeline and E&P equities.",
            "The Zero-Retention Diligence Architecture: How StackLabs edge pipelines isolate proprietary trading theses without cloud exposure."
        ],
        "chapters": [
            {"time": 0, "label": "00:00 Introduction"},
            {"time": 120, "label": "02:00 The Pendulum Swing"},
            {"time": 300, "label": "05:00 Algorithmic Crowding"}
        ],
        "summary": "Deep dive into crowd mechanics, commodity volatility pendulums, and StackLabs edge trading architecture.",
        "published": True
    }
]


def load_episodes():
    """Load episodes from manifest or return defaults."""
    if os.path.exists(EPISODES_MANIFEST):
        try:
            with open(EPISODES_MANIFEST, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading episodes manifest: {e}")
    return DEFAULT_EPISODES


@bp.route('/api/briefing/episodes', methods=['GET'])
def get_episodes():
    """Return JSON list of published audio briefing episodes."""
    episodes = load_episodes()
    published = [e for e in episodes if e.get('published', True)]
    return jsonify({
        "status": "success",
        "count": len(published),
        "episodes": published
    })


@bp.route('/api/briefing/feed.xml', methods=['GET'])
def get_podcast_feed():
    """Generate dynamic Apple Podcasts / CarPlay compatible RSS 2.0 feed."""
    episodes = load_episodes()
    published = [e for e in episodes if e.get('published', True)]
    
    base_url = request.host_url.rstrip('/')
    if request.headers.get('X-Forwarded-Proto') == 'https' or request.is_secure:
        base_url = base_url.replace('http://', 'https://')
    
    rss_items = []
    for ep in published:
        audio_url = f"{base_url}{ep['audio_url']}"
        guid = f"stacklabs-briefing-{ep['id']}"
        try:
            pub_date = datetime.strptime(ep['date'], "%Y-%m-%d").strftime("%a, %d %b %Y 06:00:00 GMT")
        except Exception:
            pub_date = "Sat, 03 Oct 2026 06:00:00 GMT"
        bullet_html = "".join([f"&lt;li&gt;{b}&lt;/li&gt;" for b in ep.get('instant_brief', [])])
        desc = f"{ep.get('summary', '')}&lt;br/&gt;&lt;br/&gt;&lt;strong&gt;Executive Brief:&lt;/strong&gt;&lt;ul&gt;{bullet_html}&lt;/ul&gt;"
        
        rss_items.append(f"""    <item>
      <title>{ep['title']}</title>
      <description>{desc}</description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="false">{guid}</guid>
      <enclosure url="{audio_url}" length="10485760" type="audio/x-m4a"/>
      <itunes:duration>{ep.get('duration', '10:00')}</itunes:duration>
      <itunes:author>StackLabs LLC</itunes:author>
      <itunes:explicit>no</itunes:explicit>
    </item>""")

    items_block = "\n".join(rss_items)
    feed_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>StackLabs • Executive Briefing</title>
    <link>{base_url}</link>
    <language>en-us</language>
    <copyright>Copyright 2026 StackLabs LLC</copyright>
    <itunes:author>StackLabs LLC</itunes:author>
    <itunes:summary>Restricted daily intelligence, quantitative research, and edge compute briefings.</itunes:summary>
    <description>Restricted daily intelligence, quantitative research, and edge compute briefings from StackLabs LLC.</description>
    <itunes:owner>
      <itunes:name>StackLabs LLC</itunes:name>
      <itunes:email>james@stacklabsllc.com</itunes:email>
    </itunes:owner>
    <itunes:category text="Business">
      <itunes:category text="Investing"/>
    </itunes:category>
    <itunes:explicit>no</itunes:explicit>
{items_block}
  </channel>
</rss>"""
    return Response(feed_xml, mimetype='application/rss+xml')


@bp.route('/drops/episodes/<path:filename>', methods=['GET'])
def serve_episode_audio(filename):
    """Serve episode audio file from EPISODES_DIR with byte-range support."""
    os.makedirs(EPISODES_DIR, exist_ok=True)
    target_path = os.path.join(EPISODES_DIR, filename)
    if not os.path.exists(target_path):
        abort(404, description="Audio file pending staging.")
    return send_from_directory(EPISODES_DIR, filename)
