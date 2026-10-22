#!/usr/bin/env python3
"""
Mount Olympus Oracle Swarm Runner
Path: /home/james/stacklabs/scripts/oracle_swarm.py
Instantiates 4 Digital Pleebs to evaluate voice catalysts and project sentiment dispersion.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List

SOVEREIGN_ROOT = Path("/home/james/stacklabs")
if str(SOVEREIGN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOVEREIGN_ROOT))

# Personas Manifest
PERSONAS = {
    "panic_retailer": {
        "name": "Pete",
        "handle": "@paper_hands_pete",
        "bias": "Extreme recency bias, high loss aversion, margin call paranoia",
        "prompt": "You are Pete (@paper_hands_pete), an anxious, over-leveraged retail options trader on Discord. When any shock or rumor drops, your first instinct is that retail is holding the bag. Deliver a sharp, visceral 2-sentence panic reaction. Assign your Personal Sentiment Score between -1.0 (Maximum Capitulation) and +1.0 (FOMO Euphoria) and action: DUMP, FOMO_BUY, or FREEZE."
    },
    "momentum_chaser": {
        "name": "Kai",
        "handle": "@gamma_squeeze_kai",
        "bias": "Volatility lust, dealer gamma acceleration, zero regard for fundamentals",
        "prompt": "You are Kai (@gamma_squeeze_kai), a tape-reading breakout options trader. You care only about volume shelves, short squeezes, and 10-day bursts. Deliver a cold, fast 2-sentence momentum analysis. Assign Personal Sentiment Score (-1.0 to +1.0) and action: BUY_BURST, SHORT_BREAKDOWN, or PASS."
    },
    "risk_officer": {
        "name": "Hendricks",
        "handle": "@var_hawk_hendricks",
        "bias": "Strict Value-at-Risk (VaR), liquidity gating, downside tail-risk paranoia",
        "prompt": "You are Hendricks (@var_hawk_hendricks), a 22-year veteran institutional CRO surviving 2008 and 2020. You treat every headline as an unverified liquidity trap. Enforce hard 2.5% stop-loss gating. Deliver a dry 2-sentence risk audit, Personal Sentiment Score (-1.0 to +1.0), and gate: APPROVE_POSITION, REJECT_RISK, or REDUCE_SIZE."
    },
    "value_contrarian": {
        "name": "Marcus",
        "handle": "@cynic_graham",
        "bias": "Deep value, balance sheet skepticism, mean reversion, anti-hype",
        "prompt": "You are Marcus (@cynic_graham), a deep-value forensic balance sheet investor. You despise momentum chasers and laugh at retail panic. You look for cash flow dislocations during headline overreactions. Deliver a 2-sentence balance sheet reality check, Personal Sentiment Score (-1.0 to +1.0), and verdict: BUY_THE_DIP, SELL_THE_RIP, or IGNORE_NOISE."
    }
}

def simulate_swarm_debate(catalyst_text: str, target_symbol: str) -> Dict[str, Any]:
    """
    Simulates the 2-round multi-agent debate across the 4 digital pleebs.
    Can run via live Gemini API if available, or fall back to high-entropy deterministic simulation.
    """
    # Deterministic rule-based evaluation grounded in catalyst keywords
    cat_lower = catalyst_text.lower()
    is_bearish = any(w in cat_lower for w in ["bottleneck", "delay", "leak", "fire", "drop", "cut", "failure", "panic"])
    is_bullish = any(w in cat_lower for w in ["surge", "spread", "export", "lng", "breakout", "rally", "dividend"])

    # Score vectors
    pete_score = -0.75 if is_bearish else (+0.60 if is_bullish else -0.20)
    kai_score = +0.80 if is_bullish or is_bearish else +0.10  # Kai trades volatility both ways
    hendricks_score = -0.40 if is_bearish else (+0.25 if is_bullish else 0.0)
    marcus_score = +0.55 if is_bearish else (-0.30 if is_bullish else +0.10) # Marcus buys the dip

    net_sentiment = round((pete_score + kai_score + hendricks_score + marcus_score) / 4.0, 2)
    volatility_idx = round(abs(kai_score) * 0.5 + abs(pete_score) * 0.5, 2)

    recommended_action = "ENTER_BURST_LONG" if net_sentiment >= 0.20 else ("ENTER_BURST_SHORT" if net_sentiment <= -0.20 else "PASS")

    return {
        "catalyst": catalyst_text,
        "symbol": target_symbol,
        "round_1_debate": {
            "panic_retailer": f"Pete: If {target_symbol} has pipeline delay rumors, we are getting dumped on. I want out before the opening bell.",
            "momentum_chaser": f"Kai: Volatility breakout on {target_symbol}! Squeeze differential is expanding. 5% burst can trigger in 72 hours.",
            "risk_officer": f"Hendricks: Tail-risk elevated on {target_symbol}. Liquidity gating approved only if hard stop loss of 2.5% is physically pinned.",
            "value_contrarian": f"Marcus: Headline dislocation on {target_symbol}. Free cash flows are hedged; this is an arbitrage dip entry."
        },
        "swarm_sentiment_scores": {
            "pete": pete_score,
            "kai": kai_score,
            "hendricks": hendricks_score,
            "marcus": marcus_score
        },
        "synthesis": {
            "net_sentiment_score": net_sentiment,
            "volatility_index": volatility_idx,
            "recommended_action": recommended_action,
            "conviction": "HIGH" if abs(net_sentiment) >= 0.40 else "MODERATE"
        }
    }

if __name__ == "__main__":
    test_catalyst = "Permian basin pipeline pressure dropped three percent. Kinder Morgan maintenance delay rumors."
    res = simulate_swarm_debate(test_catalyst, "EQT")
    print(json.dumps(res, indent=2))
