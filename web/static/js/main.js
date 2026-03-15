async function fetchTeams(year) {
    const teamList = document.getElementById('team-list');
    teamList.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
        const response = await fetch(`/api/teams/${year}`);
        const teams = await response.json();
        
        teamList.innerHTML = '';
        teams.sort((a, b) => a.seed - b.seed).forEach(team => {
            const item = document.createElement('div');
            item.className = 'team-item';
            item.innerHTML = `
                <div class="team-info">
                    <span class="seed-num">${team.seed || '?'}</span>
                    <div>
                        <div style="font-weight: 600;">${team.name}</div>
                        <div class="stat-tag">AdjO: ${team.off_efficiency} | TRB: ${team.trb_pct}%</div>
                    </div>
                </div>
                ${team.intuition_score !== 0 ? `<div class="intuition-bubble">H: +${team.intuition_score}</div>` : ''}
            `;
            teamList.appendChild(item);
        });
    } catch (err) {
        teamList.innerHTML = `<div class="error">Failed to load teams: ${err.message}</div>`;
    }
}

async function runSimulation() {
    const year = document.getElementById('year-select').value;
    const bracketContainer = document.getElementById('bracket-container');
    bracketContainer.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
        const response = await fetch(`/api/simulation/full?year=${year}`);
        const data = await response.json();
        
        renderBracket(data);
    } catch (err) {
        bracketContainer.innerHTML = `<div class="error">Simulation failed: ${err.message}</div>`;
    }
}

function renderBracket(data) {
    const container = document.getElementById('bracket-container');
    container.innerHTML = '';
    container.className = 'bracket-view'; // Change grid layout

    // We'll show one region at a time or a summarized view
    const regions = Object.keys(data.regions);
    const regionNav = document.createElement('div');
    regionNav.className = 'region-nav';
    
    regions.forEach(r => {
        const btn = document.createElement('button');
        btn.textContent = r;
        btn.className = 'region-btn';
        btn.onclick = () => displayRegion(r, data.regions[r]);
        regionNav.appendChild(btn);
    });
    
    const displayArea = document.createElement('div');
    displayArea.id = 'region-display';
    displayArea.className = 'region-display';
    
    container.appendChild(regionNav);
    container.appendChild(displayArea);
    
    // Default to first region
    displayRegion(regions[0], data.regions[regions[0]]);
}

function displayRegion(name, rounds) {
    const displayArea = document.getElementById('region-display');
    displayArea.innerHTML = `<h3>${name} Region Flow</h3>`;
    
    const roundsContainer = document.createElement('div');
    roundsContainer.className = 'rounds-flex';
    
    rounds.forEach(r => {
        const roundDiv = document.createElement('div');
        roundDiv.className = 'round-column';
        roundDiv.innerHTML = `<h4>Round ${r.round}</h4>`;
        
        r.matchups.forEach(m => {
            const mDiv = document.createElement('div');
            mDiv.className = 'matchup-card';
            const prob = (m.probability * 100).toFixed(1);
            mDiv.innerHTML = `
                <div class="team-line ${m.winner === m.team_a ? 'winner' : ''}">
                    <span>(${m.seed_a}) ${m.team_a}</span>
                    ${m.winner === m.team_a ? `<span class="prob-tag">${prob}% Why?</span>` : ''}
                </div>
                <div class="team-line ${m.winner === m.team_b ? 'winner' : ''}">
                    <span>(${m.seed_b}) ${m.team_b}</span>
                    ${m.winner === m.team_b ? `<span class="prob-tag">${(100 - prob).toFixed(1)}% Why?</span>` : ''}
                </div>
            `;
            roundDiv.appendChild(mDiv);
        });
        roundsContainer.appendChild(roundDiv);
    });
    
    displayArea.appendChild(roundsContainer);
}

document.addEventListener('DOMContentLoaded', () => {
    const yearSelect = document.getElementById('year-select');
    fetchTeams(yearSelect.value);
    
    yearSelect.addEventListener('change', (e) => {
        fetchTeams(e.target.value);
    });
    
    document.getElementById('run-sim-btn').addEventListener('click', runSimulation);
});
