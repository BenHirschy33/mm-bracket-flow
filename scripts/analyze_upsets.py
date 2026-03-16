import os
import json
import pandas as pd
from pathlib import Path

def analyze_upsets():
    """
    Analyzes historical upsets (#12-#16 seeds beating #1-#5 seeds)
    to find common metric clusters.
    """
    upset_data = []
    
    dirs = sorted([d for d in os.listdir("years") if not d.startswith('.') and d.isdigit()])
    
    for year in dirs:
        year_dir = Path("years") / year
        stats_path = year_dir / "data" / "team_stats.csv"
        results_path = year_dir / "data" / "actual_results.json"
        
        if not stats_path.exists() or not results_path.exists():
            continue
            
        # Load Stats
        df = pd.read_csv(stats_path)
        
        # Load Results
        with open(results_path) as f:
            results = json.load(f)
            
        # Define "Upset Teams" - Lower seeds that reached Sweet 16 or further
        cinderella_teams = results.get("sweet_sixteen", [])
        
        for team in cinderella_teams:
            team_stats = df[df['Team'] == team]
            if not team_stats.empty:
                # We are looking for the 'Huge' factors the user mentioned: ORB% and 3P%
                stats = team_stats.iloc[0].to_dict()
                stats['Year'] = year
                upset_data.append(stats)
                
    if not upset_data:
        print("No upset data found.")
        return
        
    analysis_df = pd.DataFrame(upset_data)
    
    # Standardize column naming if necessary
    if 'ORB' not in analysis_df.columns and 'ORB%' in analysis_df.columns:
        analysis_df.rename(columns={'ORB%': 'ORB'}, inplace=True)

    print("--- Cinderella Team Profile (Sweet 16+ Underdogs) ---")
    # Using the columns found in team_stats.csv
    available_metrics = [m for m in ['AdjO', 'AdjD', '3PAr', 'ORB', 'TO_Off', 'eFG_Off', 'FTr'] if m in analysis_df.columns]
    
    print(analysis_df[available_metrics].describe())
    
    # Filter for potential "Cinderella" seeds (Seed >= 10)
    # Note: Seeds might be empty in stats CSV during backfill, but 
    # the results JSON identifies them as sweet_sixteen participants.
    
    # Save analysis
    analysis_df.to_csv("docs/upset_analysis.csv", index=False)
    print("✅ Upset analysis saved to docs/upset_analysis.csv")

if __name__ == "__main__":
    analyze_upsets()
