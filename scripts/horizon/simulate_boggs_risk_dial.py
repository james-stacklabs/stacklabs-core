#!/usr/bin/env python3
"""
HORIZON BOGGS CONVEXITY SIMULATOR: PAWEL'S "FROGGY" RISK DIAL
Simulates the 5 Tiers of the Boggs Risk Dial for Pawel Rudnicki:
Level 1: Conservative (Pawel Baseline: 2:1 Asymmetry, +5% / -2.5%)
Level 2: Moderate Edge (3:1 Asymmetry, +7.5% / -2.5%)
Level 3: Catalyst Runner (5:1 Asymmetry, +15% / -3.0%)
Level 4: Options Debit Convexity (8:1 Asymmetry, $250 risk / $2000 payout)
Level 5: Max Boggs Froggy (15:1 Tail Squeeze, $500 risk / $7500 payout)
"""

import numpy as np
import json

def run_simulation(name, win_rate, win_payout, loss_amount, n_trades=100, n_sims=10000, initial_capital=10000.0):
    # n_sims iterations of n_trades
    outcomes = np.random.binomial(1, win_rate, (n_sims, n_trades))
    pnl = np.where(outcomes == 1, win_payout, -loss_amount)
    
    cumulative_pnl = np.cumsum(pnl, axis=1)
    final_pnl = cumulative_pnl[:, -1]
    final_equity = initial_capital + final_pnl
    
    # Calculate metrics
    ev_per_trade = (win_rate * win_payout) - ((1 - win_rate) * loss_amount)
    break_even_win_rate = loss_amount / (win_payout + loss_amount)
    median_final_pnl = np.median(final_pnl)
    percentile_5 = np.percentile(final_pnl, 5)
    percentile_95 = np.percentile(final_pnl, 95)
    
    # Max drawdown per sim
    running_max = np.maximum.accumulate(initial_capital + cumulative_pnl, axis=1)
    drawdowns = (running_max - (initial_capital + cumulative_pnl)) / running_max
    max_drawdown = np.median(np.max(drawdowns, axis=1)) * 100
    
    # Ruin probability (equity dropping below 50% of initial)
    ruin_prob = np.mean(np.any((initial_capital + cumulative_pnl) < (initial_capital * 0.5), axis=1)) * 100
    
    return {
        "tier": name,
        "win_rate": f"{win_rate * 100:.1f}%",
        "break_even_win_rate": f"{break_even_win_rate * 100:.1f}%",
        "win_payout": f"+${win_payout:.2f}",
        "loss_amount": f"-${loss_amount:.2f}",
        "risk_reward_ratio": f"{win_payout / loss_amount:.1f}:1",
        "expected_value_per_trade": f"+${ev_per_trade:.2f}",
        "median_profit_100_trades": f"+${median_final_pnl:.2f}",
        "pnl_90_pct_confidence": f"[${percentile_5:.2f} to +${percentile_95:.2f}]",
        "median_max_drawdown": f"{max_drawdown:.1f}%",
        "ruin_probability_sub_50pct": f"{ruin_prob:.1f}%"
    }

if __name__ == "__main__":
    np.random.seed(42)
    
    configs = [
        ("Level 1: Conservative (Pawel Baseline)", 0.38, 50.0, 25.0),
        ("Level 2: Moderate Edge", 0.32, 75.0, 25.0),
        ("Level 3: Catalyst Runner", 0.26, 150.0, 30.0),
        ("Level 4: Options Convexity", 0.20, 2000.0, 250.0),
        ("Level 5: Max Boggs Froggy", 0.12, 7500.0, 500.0),
    ]
    
    results = []
    print("=" * 80)
    print("HORIZON VECTOR 6 // BOGGS RISK DIAL SIMULATION (10,000 MONTE CARLO RUNS)")
    print("=" * 80)
    
    for name, wr, wp, la in configs:
        res = run_simulation(name, wr, wp, la)
        results.append(res)
        print(f"\n⚡ {res['tier']}")
        print(f"   • Win Rate: {res['win_rate']} (Break-even threshold: {res['break_even_win_rate']})")
        print(f"   • Asymmetry: {res['risk_reward_ratio']} ({res['win_payout']} / {res['loss_amount']})")
        print(f"   • Expected Value / Trade: {res['expected_value_per_trade']}")
        print(f"   • Median 100-Trade Return: {res['median_profit_100_trades']} on $10,000 bankroll")
        print(f"   • 90% Range: {res['pnl_90_pct_confidence']}")
        print(f"   • Median Max Drawdown: {res['median_max_drawdown']}")
        print(f"   • Capital Ruin Risk (<$5k): {res['ruin_probability_sub_50pct']}")

    with open("/home/james/stacklabs/ground_truth/assets/boggs_simulation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\n[SUCCESS] Emitted simulation results to ground_truth/assets/boggs_simulation_results.json")
