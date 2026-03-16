#!/bin/bash
# PAUSE PROTOCOL SCRIPT
# Ensures all state is saved and documented for a session stop.

echo "--- MM-Bracket-Flow: Initializing Pause Protocol ---"

# 1. Capture background PIDs
if [ -f optimization_pid.txt ]; then
    OPT_PID=$(cat optimization_pid.txt)
    echo "Optimization Agent (PID $OPT_PID) is running. Storing status..."
    ps -p $OPT_PID > docs/pause_state.txt
fi

# 2. Update stats summary
echo "Current Dataset Status: 25 Seasons Backfilled" >> docs/pause_state.txt
ls -R years/*/data/team_stats.csv | wc -l >> docs/pause_state.txt

# 3. Stage changes
git add .
git commit -m "chore: autonomous state checkpoint [Supervisor]"

echo "✅ Pause Protocol Complete. State staged in docs/pause_state.txt"
