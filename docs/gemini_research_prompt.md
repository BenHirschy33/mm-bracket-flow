# Research Prompt for Gemini (External)

Copy the following block to your Gemini session to generate a list of advanced metrics for our next optimization cycle:

---

**PROMPT:**

I am building an advanced NCAA Tournament prediction engine called "March Madness Bracket Flow". We currently track:
- Net Efficiency (AdjO/AdjD)
- EFG%, TO Margin, SOS, Momentum
- Foul Drawing (FTr), 3P Volatility (3PAr), Star Reliance
- Luck (Pyth vs. Actual), Luck Regression, Road Dominance
- Bench Depth (AST% + TRB% synergy)

**Task:**
Identify 5-7 "Hidden" or advanced statistical metrics that historically predict tournament upsets (specifically #11-#15 seeds beating #1-#3 seeds) and second-weekend performance. 

**Criteria for new metrics:**
- Must have historical correlation with "Seed Fraud" (e.g., highly ranked teams that underperform in March).
- Must factor in situational variables like "Closer Efficiency" (performance in last 4 mins of close games) or "Coach Tournament Pedigree".
- Provide a brief logic for why these metrics are "Huge" drivers of success vs. the average.

**Format your response as:**
1. Metric Name
2. Theoretical Logic
3. Suggested Weighting Priority (High/Medium/Low)

---
