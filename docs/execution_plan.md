# EXECUTION PLAN: Phase 2 Initialization

To start this autonomous specialized workflow:

1. **Manager Init (Supervisor)**:
   - Perform `/init-session` to standardize the environment.
   - Sync current 25-year data into all worktrees.
   
2. **Specialized Launch**:
   - **Optimization**: Launch on `feature/p2-optimization`. Start the 10,000-iteration Monte Carlo sweep for EV vs. Hit Rate.
   - **Web**: Launch on `feature/p2-web`. Build the Deep-Dive Modal. Use `browser_subagent` for visual verification.
   - **Research**: Launch on `feature/p2-research`. Search web/podcasts for "2025 Tournament Volatility" and "Foul Drawing Factors".
   
3. **Synchronization Loop**:
   - Every 30 minutes, the Supervisor reviews worker branches. 
   - Research findings are written to `docs/research_sync.json` for the Optimization agent to ingest.
   - UI metrics from Optimization are passed to the Web agent for the "Metric Explainer".

4. **Pausing Point**:
   - If the USER signals a halt or time expires:
     - Push all local state.
     - Consolidate `walkthrough.md`.
     - Output a "Resumption Token" for the manager's next init.

---

### Step 1 Action:
I am now creating the specific agent prompts tailored for this external-research and cross-agent communication model.
