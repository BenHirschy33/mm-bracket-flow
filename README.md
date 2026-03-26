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

## 🏁 Marathon Completion (March 26, 2026)

The 2026 Optimization Marathon is officially complete. The engine has discovered and stabilized high-performance weights for all three target modes.

### 🏆 Final Peak Performance
- **Average Mode**: **211.41** (Elite Cubic Upside)
- **Perfect Mode**: **14,708.24** (Convex Power-Law)
- **Balanced Mode**: **99.44** (Synchronized Sync)

---

## 🛠 Operation & Maintenance

### 1. Repository Hygiene
As of March 26, all live logs and temporary artifacts have been removed. Mode-specific backups and checkpoints are archived in `agents/optimization/backups/`.

### 2. Standard Promotion
The final weights are stored in the master repository:
`agents/optimization/gold_standard.json`

---

*Mission Accomplished for the 2026 Tournament Cycle. V5 Marathon Architecture concludes March 26, 2026.*
