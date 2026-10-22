# 20-Year Trading Model Auditability & Veto Rules

- **Rule 1 (Zero Unexplained Logic):** No model weight or execution branch may enter production solely on backtest Sharpe improvement if its failure mode under a 3-sigma liquidity freeze cannot be written in plain prose.
- **Rule 2 (Asymmetric Bracket Discipline):** Enforce 2:1 asymmetric reward-to-risk brackets (+5.0% take-profit / -2.5% hard stop-loss) requiring only a 33.4% win rate for break-even survival.
- **Rule 3 (Human Veto Gate):** Preserving deliberate friction at the execution boundary prevents automated cascade faults.
