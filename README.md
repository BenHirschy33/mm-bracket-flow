# MM-Bracket-Flow 2026: The "Perfect Bracket" Marathon

**MM-Bracket-Flow** is a high-performance March Madness simulation engine. V5 marks the transition to an **Extreme Value Theory (EVT)** driven optimization architecture, designed to find the rare global maxima required for perfect bracket discovery.

---

## 🏔️ V5.7 Elite Optimization Marathon

As of March 24, 2026, the engine has been upgraded to **V5.7 "Elite Maximization"** mode, featuring a triple-lock discovery architecture.

### 🎯 1. Perfect Mode (Convex Power-Law)
- **Math**: $s^8$ reward on top 1% outcomes ($1,000,000$ tail multiplier).
- **Topology**: 500k iterations | **2,500 samples/year** | 50k snapback.
- **Goal**: Targeted discovery of extreme high-scoring anomalies.

### ⚖️ 2. Balanced Mode (Hybrid Accuracy)
- **Math**: Linear Log-Likelihood + $+10,000$ Accuracy bonus.
- **Topology**: 250k iterations | **750 samples/year** | 25k snapback.
- **Goal**: Strategic balance between points and the ultimate winner.

### 📈 3. Average Mode (Elite Cubic Upside)
- **Math**: Uses a **Cubic Power-Law** fitness: `(Avg_Score ^ 3) / 1,000,000`.
- **Topology**: 100k iterations | **150 samples/year** | 15k snapback.
- **Goal**: Maximizing the "Greatest Average Overall". No cap or penalty for exceeding 1000 points.

---

## 🏗 Architecture: Double-Hydration & Auto-Sync

### 🏆 Battle of the Titans (Startup Contest)
The engine no longer trusts a single record on boot. It performs a **Double-Hydration benchmark**:
1. Load `gold_standard.json` (Expert Baseline).
2. Load `checkpoint.json` (Live Session Peak).
3. **The Contest**: Whoever has the highest fitness under the current logic is promoted to "Current Best." 
4. **Benefit**: Hand-tuned brilliance is never overwritten by stale session data.

### ✨ Master Gold Standard Auto-Sync
The bridge between discovery and production is now automated. Every time a **NEW BEST** is found in any mode, the script instantly updates the master `agents/optimization/gold_standard.json` file. 

---

## 🛠 Operation & Maintenance

### 1. Starting / Resuming the Marathon
To start all three modes in the background (using unbuffered output for live monitoring):

```bash
python3 -u scripts/optimize_weights.py --mode average --resume > agents/optimization/refine_average.log 2>&1 &
python3 -u scripts/optimize_weights.py --mode balanced --resume > agents/optimization/refine_balanced.log 2>&1 &
python3 -u scripts/optimize_weights.py --mode perfect --resume > agents/optimization/refine_perfect.log 2>&1 &
```

### 2. Checking Status
Check the current iteration, best fitness, and checkpoint age for any mode:

```bash
python3 scripts/optimize_weights.py --mode perfect --status
python3 scripts/optimize_weights.py --mode balanced --status
```

To watch the discovery of new peaks live:
```bash
tail -f agents/optimization/refine_*.log
```

### 3. Stopping Safely (Soft Shutdown)
Sends a `SIGINT` signal to the scripts. They will immediately save a safety checkpoint and exit.

```bash
pkill -2 -f "optimize_weights.py"
```

---

## ⚖️ Implementation Rules (The "Zero-Weight" Policy)

- **New Metrics**: Any newly added variables in `SimulationWeights` MUST default to **0.0**.
- **Independence**: A new metric should have no effect on win probability until the Autonomous Optimizer has discovered a non-zero peak through exhaustive testing.
- **Process Stability**: Using individual processes per mode to prevent macOS kernel congestion.

---

*Verified for the 2026 Tournament Cycle. V5 Marathon Architecture deployed March 24, 2026.*
