---
description: Run the MM-Bracket-Flow tournament simulation for a specific year
---

This workflow executes the baseline simulation prediction against the designated year's chalk bracket.

1. Ensure the bracket data is populated (e.g., in `years/2026/data/chalk_bracket.json`).
// turbo-all
2. Run the simulation script: `PYTHONPATH=. python3 scripts/run_bracket.py --year 2026` (change the `--year` parameter if running a different season).
3. Review the terminal output to analyze the round-by-round predictions and Final Four outcomes!
