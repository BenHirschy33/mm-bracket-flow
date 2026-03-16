# MM-Bracket-Flow: High-Fidelity Research Prompt

Copy and paste this into your Gemini 1.5 Pro / Flash session.

---

**Prompt**:
I am optimizing a March Madness bracket simulation engine. I have a 25-year historical dataset (2000-2025) of team statistics. I need to identify the "Upset Profile"—the specific metric clusters that differentiate "Cinderella" teams (#11-#15 seeds reaching the Sweet 16 or further) from standard early-exit underdogs.

Please perform a deep-dive research analysis on the following:

1. **The "Huge" Factors**: 
   - Analyze how **Offensive Rebound Percentage (ORB%)** and **3-Point Attempt Rate (3PAr)** correlate specifically with tournament upsets versus regular season success. Is there a "Chaos Threshold" for 3PAr where volatility becomes a net positive in a single-elimination context?
   
2. **Venue Impact**:
   - Recent data suggests neutral sites in the tournament don't behave like a perfect 50/50 home/away split. They often behave more like "Away" games for the higher seed. Extract any research or data on win-rate shifts for #1-#4 seeds on neutral courts compared to their true away records.
   
3. **Data Resilience & Historical Eras**:
   - How should a model handle missing advanced metrics from the early 2000s (pre-KenPom era)? Are there reliable proxies (e.g., using "Points per Possession" derived from raw totals) that maintain predictive power across eras?
   
4. **The "Perfect Bracket" Alpha**:
   - What are the 3 most "underrated" metrics that standard "chalk-favoring" models (like KenPom or Torvik) might miss when predicting a "Perfect Bracket" (maximizing for ceiling rather than average EV)? Look for things like **Foul Drawing Rate**, **Luck Regression**, or **Usage Concentration**.

**Output Format**:
Please provide a structured summary including "Numerical Multipliers/Weights" that I can apply to my Log5 simulation engine.

---
