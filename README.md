# MM-Bracket-Flow V2: Calibrated & Optimized

**MM-Bracket-Flow** is a professional-grade March Madness simulation engine that bridges pure statistical efficiency with human intuition. It uses a calibrated Logistic (Sigmoid) model to provide realistic upset probabilities and dual-mode optimization for targeted bracket strategies.

## 🚀 Key Features (V2)

### 1. The Sigmoid Simulation Engine
Unlike many simulators that use additive win probabilities (which often saturate at 99.9% for elite teams), MM-Bracket-Flow V2 uses a **Logistic (Sigmoid) function**.
- **Calibration**: Probabilities are naturally scaled, ensuring that even #1 seeds have a realistic "Upset Risk" (e.g., 85-90% instead of 99%).
- **Round Weighting**: Defensive premiums and "Star Reliance" factors scale automatically with tournament depth.

### 2. Dual-Mode Optimization ("Gold Standard")
The system maintains two distinct "Gold Standard" weight sets, optimized across 24 years of historical data (2000-2024):
- **Max Average (MAX_AVG)**: Designed for stable, high-performance pool scoring. Targets the highest expected ESPN score.
- **Perfectionist (MAX_PERFECT)**: Uses a rigorous **Analytic Log-Likelihood** model to maximize the joint probability of getting every single pick correct (1920 points).

### 3. The Intuition Factor
Inject your own "Gut Feeling" via `core/intuition_config.yaml`. Any team can be assigned an Intuition Score from `-10` to `+10`, which shifts their win probability in the simulation.

---

## 🛠 Installation & Setup

### 1. Prerequisites
- Python 3.10+
- `pip install -e .`
- Recommended: `ruff` for linting.

### 2. Running Simulation
```bash
# Start the web interface
python web/app.py
```
Open `http://localhost:5001` to access the interactive dashboard.

### 3. Running Optimizer
If you have new data and want to re-train the "Gold Standard" weights:
```bash
PYTHONPATH=. python3 scripts/dual_mode_optimizer.py --iterations 1000 --mode both
```

---

## 📈 Metric Dictionary
- **Defense Premium**: Weight given to `def_efficiency` (KenPom style). Highly effective in later rounds.
- **Momentum Regression**: Penalty for teams that were "Lucky" (high W-L% vs SRS) entering the tournament.
- **3PAr Volatility**: Increases the chance of upsets for high-volume 3-point shooting teams.
- **Intuition Weight**: Scaling factor for the user's manual adjustments in `intuition_config.yaml`.

---

## 🎓 Future Educational & Research Ideas
For next season, we aim to expand the educational scope of the project:
1. **Machine Learning Feature Importance**: Use XGBoost to rank which metrics (e.g., Turnovers vs. SOS) are the true predictors of tournament success.
2. **Bayesian Optimization**: Transition the current Annealing script to a Gaussian Process model for even faster weight convergence.
3. **LLM "Aura" Analysis**: Integrate an LLM agent to scrape team news and sentiment to generate the "Intuition Factor" automatically.
4. **Game Theory / Minimax**: Implement a bracket-pool "Contrarian Strategy" optimizer that favors picks that other humans in a pool are likely to miss.

---

## 📅 Roadmap & Next Steps (2025/2026)
- [ ] **Real-Time Live Updates**: Automated ingestion of tournament scores for "Second Chance" re-simulations.
- [ ] **NIL/Portal Stability Index**: New metrics to track team cohesion in the transfer portal era.
- [ ] **Visual Bracket Editor**: Drag-and-drop UI for locking specific path results.

---

*This project is built for longevity. Year-specific data resides in `/years/YYYY/`, ensuring the core logic remains evergreen.*
