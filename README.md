# MM-Bracket-Flow 2026: The "Perfect Bracket" Frontier

**MM-Bracket-Flow** is a high-fidelity March Madness simulation engine. V4 represents the final "Heuristic Era" milestone, utilizing a calibrated 140+ variable model to bridge pure efficiency metrics with tournament chaos.

---

## 🏔️ 2026 Season Status: Fully Calibrated
As of late March 2026, the engine is in **Autonomous Optimization Mode**.
- **Window**: 11-Year Historical Ground Truth (2015-2025).
- **Goal**: Maximizing the joint probability of a **Perfect Bracket** (1920 points) while maintaining a balanced "Smart Money" fallback.
- **Metrics**: Full integration of **ShotQuality Delta**, **Kill Shot Efficiency**, and **Rim-and-3 Rate** volatility scaling.

---

## 📊 Core Simulation Presets
The UI communicates with `gold_standard.json` via three primary optimized payloads:
1. **Highest Average (`max_avg`)**: Tuned to maximize the expected total points in a standard pool.
2. **Balanced (`max_balanced`)**: A robust mix of efficiency and reliability.
3. **Perfect Bracket (`max_perfect`)**: [NEW] High-variance model optimized specifically for the "one-in-a-quintillion" perfect path using Log-Likelihood maximization.

---

## 🛠 Repository Structure & Maintenance
- `/core`: Simulation logic and Sigmoid-based resolution engine.
- `/web`: Flask-based UI with real-time reactivity.
- `/scripts`: Data synchronization and autonomous optimization tools.
- `/years`: Historical data (2015-2025) used for authoritative back-testing.

### Running the Optimizer (2025 Standard)
The most authoritative way to run the simulation is via the **Phase 14 Epoch Pipeline**:
```bash
# RECOMMENDED: Runs Scout (250k) -> Fork (Polish/Deep Space)
python3 scripts/autonomous_optimizer.py --pipeline
```

### Log Maintenance
- Optimization logs are stored in `agents/optimization/`.
- Timestamped logs (e.g., `autonomous_optimizer_YYYYMMDD_HHMMSS.log`) are generated per run.
- It is safe to delete old `.log` files and the `heartbeat.log` at any time to save space.
- Keep the `.json` files as they contain the actual optimized weights.

### 🦾 Maintenance & Process Control
```bash
# RECOVERY: Kill existing and start parallel sweeps (Manual)
python3 scripts/relaunch_optimizer.py

# EMERGENCY: Kill all optimization workers
pkill -f scripts/optimize_weights.py && pkill -f scripts/autonomous_optimizer.py
```

### 🏔️ Optimizer Resilience & MacBook Settings
The optimizer is built to be **indestructible** and **resumeable**:
1. **Resume Logic**: Every time the script starts, it reads `gold_standard.json` to load your current high scores. It never starts from zero; it only tries to beat its current record.
2. **MacBook Sleep**: If the laptop deep-sleeps, the process will pause.
   - **Recommendation**: Leave the lid **open** and go to *System Settings > Battery* to prevent sleeping while on power.
   - **Recovery**: If it stops, just run `python3 scripts/relaunch_optimizer.py`. It will clean up any zombie processes and resume exactly where it left off.
3. **CPU Safety**: We use a surgical process manager. `scripts/relaunch_optimizer.py` ensures that only the optimizer is restarted, leaving your UI and other Python projects untouched.

---

## 📈 Behavior Notes
- **Update Frequency**: You may notice `max_perfect` updating more often than `max_avg`. This is expected! "Perfect" mode chases high-variance breakthroughs, while "Average" mode focuses on stable statistical gains, which are harder to "beat" once a strong baseline is found.

---

## 🚀 2027 Roadmap: The ML Transition
*This version marks the completion of manual heuristic balancing. The next phase of development will focus on:*
- **Neural Weight Initialization**: Moving from Simulated Annealing to Deep Learning for weight discovery.
- **LLM Intuition Layer**: Integrating real-time social sentiment and "Aura" analysis into the volatility index.
- **Live-Streaming Simulations**: Real-time bracket updating as games conclude.

## ⚖️ Implementation Rules (The "Zero-Weight" Policy)
To maintain the integrity of the calibrated baseline:
- **New Metrics**: Any newly added variables in `SimulationWeights` MUST default to **0.0**.
- **Independence**: A new metric should have no effect on win probability until the Autonomous Optimizer has discovered a non-zero peak through exhaustive testing.
- **Process Stability**: Using **V4 Linear Stable Optimization** (Single-process per mode) to prevent macOS kernel congestion.

---

*Verified for the 2026 Tournament Cycle. Stabilized V4 deployed March 23, 2026.*
