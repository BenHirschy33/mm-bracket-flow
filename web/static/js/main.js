const appState = {
    mode: 'deterministic',
    year: '2026',
    locks: {
        regions: {},
        final_four: {},
        championship: {}
    },
    optimalWeights: {
        trb: 1.763,
        to: 0.639,
        sos: 7.365,
        momentum: 0.021,
        efficiency: 0.039
    },
    teams: {},
    currentData: null,
    simTimer: null
};

// --- Core Logic ---

function debounceSim() {
    clearTimeout(appState.simTimer);
    appState.simTimer = setTimeout(runSimulation, 400);
}

function resetToOptimal() {
    const w = appState.optimalWeights;
    document.getElementById('weight-sos').value = w.sos;
    document.getElementById('weight-trb').value = w.trb;
    document.getElementById('weight-to').value = w.to;
    document.getElementById('weight-eff').value = w.efficiency;
    document.getElementById('weight-momentum').value = w.momentum;
    
    // Update labels
    document.getElementById('val-sos').textContent = w.sos;
    document.getElementById('val-trb').textContent = w.trb;
    document.getElementById('val-to').textContent = w.to;
    document.getElementById('val-eff').textContent = w.efficiency;
    document.getElementById('val-momentum').textContent = w.momentum;
    
    runSimulation();
}

function toggleLock(region, round, teamName) {
    if (region === 'final_four' || region === 'championship') {
        if (appState.locks[region][teamName]) {
            delete appState.locks[region][teamName];
        } else {
            // Lock only one per region round in FF/Champ for simplicity
            appState.locks[region] = { [teamName]: true };
        }
    } else {
        if (!appState.locks.regions[region]) appState.locks.regions[region] = {};
        if (!appState.locks.regions[region][round]) appState.locks.regions[region][round] = {};
        
        if (appState.locks.regions[region][round][teamName]) {
            delete appState.locks.regions[region][round][teamName];
        } else {
            appState.locks.regions[region][round][teamName] = true;
        }
    }
    runSimulation(); // Immediate re-sim on lock
}

function isLocked(region, round, teamName) {
    if (region === 'final_four' || region === 'championship') {
        return !!(appState.locks[region] && appState.locks[region][teamName]);
    }
    return !!(appState.locks.regions[region] && 
              appState.locks.regions[region][round] && 
              appState.locks.regions[region][round][teamName]);
}

// --- API Calls ---

async function fetchTeams(year) {
    const teamList = document.getElementById('team-list');
    teamList.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
        const response = await fetch(`/api/teams/${year}`);
        const teams = await response.json();
        
        teamList.innerHTML = '';
        appState.teams = {};
        teams.forEach(t => appState.teams[t.name] = t);

        teams.sort((a, b) => a.seed - b.seed).forEach(team => {
            const item = document.createElement('div');
            item.className = 'team-item';
            item.innerHTML = `
                <div class="team-info">
                    <span class="seed-num">${team.seed || '?'}</span>
                    <div>
                        <div style="font-weight: 600; font-size: 0.9rem;">${team.name}</div>
                        <div class="stat-tag">Eff: ${team.off_efficiency} | Mom: ${team.momentum.toFixed(2)}</div>
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
    const bracketContainer = document.getElementById('bracket-container');
    const weights = {
        sos: parseFloat(document.getElementById('weight-sos').value),
        trb: parseFloat(document.getElementById('weight-trb').value),
        to: parseFloat(document.getElementById('weight-to').value),
        efficiency: parseFloat(document.getElementById('weight-eff').value),
        momentum: parseFloat(document.getElementById('weight-momentum').value)
    };
    
    try {
        const response = await fetch(`/api/simulation/full`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                year: parseInt(appState.year),
                mode: appState.mode,
                weights: weights,
                locks: appState.locks
            })
        });
        const data = await response.json();
        
        if (data.error) {
            bracketContainer.innerHTML = `<div class="error-card"><h3>Simulation Error</h3><p>${data.error}</p></div>`;
            return;
        }
        
        appState.currentData = data;
        renderBracket(data);
    } catch (err) {
        console.error("Simulation failed", err);
    }
}

// --- Rendering ---

function renderBracket(data) {
    const container = document.getElementById('bracket-container');
    container.innerHTML = '';
    container.className = 'bracket-view';

    const regions = Object.keys(data.regions);
    
    // Header for Global View
    const header = document.createElement('div');
    header.className = 'view-header';
    header.innerHTML = `<h3>Full Tournament Flow</h3>`;
    container.appendChild(header);

    regions.forEach(regionName => {
        const regionBlock = document.createElement('div');
        regionBlock.className = 'region-block';
        regionBlock.innerHTML = `<h3>${regionName} Region</h3>`;
        
        const displayArea = document.createElement('div');
        displayArea.className = 'region-display';
        
        const rounds = data.regions[regionName];
        const roundsContainer = document.createElement('div');
        roundsContainer.className = 'rounds-flex';
        
        rounds.forEach((r, roundIdx) => {
            const roundDiv = document.createElement('div');
            roundDiv.className = `round-column round-${r.round}`;
            
            r.matchups.forEach((m, matchIdx) => {
                const matchupWrapper = document.createElement('div');
                matchupWrapper.className = 'matchup-wrapper';
                
                const mCard = document.createElement('div');
                // Determine CSS classes for connectors
                const isUpper = matchIdx % 2 === 0;
                const hasNext = roundIdx < rounds.length - 1;
                mCard.className = `matchup-card ${isUpper ? 'upper' : 'lower'} ${hasNext ? 'has-next' : ''}`;
                
                // Add progressive spacing variable for lines
                if (hasNext) {
                    const spacing = calculateLineSpacing(r.round);
                    mCard.style.setProperty('--spacing', `${spacing}px`);
                }

                const prob = (m.probability * 100).toFixed(0);
                mCard.appendChild(createTeamLine(regionName, r.round, m.team_a, m.seed_a, m.winner === m.team_a, prob));
                mCard.appendChild(createTeamLine(regionName, r.round, m.team_b, m.seed_b, m.winner === m.team_b, 100 - prob));
                
                matchupWrapper.appendChild(mCard);
                roundDiv.appendChild(matchupWrapper);
            });
            roundsContainer.appendChild(roundDiv);
        });
        
        displayArea.appendChild(roundsContainer);
        regionBlock.appendChild(displayArea);
        container.appendChild(regionBlock);
    });

    // Final Four Section
    renderFinalFourBlock(data.final_four, data.championship, container);
}

function calculateLineSpacing(round) {
    // Spacing increases exponentially with rounds to match progressive gap
    const base = 20;
    return Math.pow(2, round - 1) * base;
}

function renderFinalFourBlock(ff, champ, container) {
    const ffBlock = document.createElement('div');
    ffBlock.className = 'region-block final-four-block';
    ffBlock.innerHTML = `<h3>National Championship Flow</h3>`;
    
    const displayArea = document.createElement('div');
    displayArea.className = 'region-display';
    
    const roundsContainer = document.createElement('div');
    roundsContainer.className = 'rounds-flex';
    
    // FF Round
    const ffDiv = document.createElement('div');
    ffDiv.className = 'round-column round-5';
    ff.forEach(m => {
        const mDiv = document.createElement('div');
        mDiv.className = 'matchup-card';
        mDiv.appendChild(createTeamLine('final_four', 1, m.team_a, '', m.winner === m.team_a, ''));
        mDiv.appendChild(createTeamLine('final_four', 1, m.team_b, '', m.winner === m.team_b, ''));
        ffDiv.appendChild(mDiv);
    });
    
    // Champ Round
    const champDiv = document.createElement('div');
    champDiv.className = 'round-column round-6';
    const cDiv = document.createElement('div');
    cDiv.className = 'matchup-card';
    cDiv.appendChild(createTeamLine('championship', 1, champ.team_a, '', champ.winner === champ.team_a, ''));
    cDiv.appendChild(createTeamLine('championship', 1, champ.team_b, '', champ.winner === champ.team_b, ''));
    
    const trophy = document.createElement('div');
    trophy.className = 'champ-winner-glow';
    trophy.style = "margin-top: 2rem; font-size: 1.5rem; font-weight: 800; color: var(--accent-gold); text-align: center; text-shadow: 0 0 20px var(--accent-gold-glow);";
    trophy.innerHTML = `🏆 CHAMPS: ${champ.winner} 🏆`;
    cDiv.appendChild(trophy);
    
    champDiv.appendChild(cDiv);
    roundsContainer.appendChild(ffDiv);
    roundsContainer.appendChild(champDiv);
    displayArea.appendChild(roundsContainer);
    ffBlock.appendChild(displayArea);
    container.appendChild(ffBlock);
}

function createTeamLine(region, round, teamName, seed, isWinner, prob) {
    const line = document.createElement('div');
    const locked = isLocked(region, round, teamName) ? 'locked' : '';
    line.className = `team-line ${isWinner ? 'winner' : ''} ${locked}`;
    
    // Add tooltip info
    const team = appState.teams[teamName];
    let tooltip = '';
    if (team) {
        tooltip = `Eff: ${team.off_efficiency} | SOS: ${team.sos?.toFixed(1) || 'N/A'} | Mom: ${team.momentum?.toFixed(2)}`;
    }

    line.innerHTML = `
        <span>(${seed}) ${teamName} <span class="lock-icon">🔒</span></span>
        ${isWinner && prob ? `<span class="prob-tag" title="${tooltip}">${prob}%</span>` : ''}
    `;
    line.onclick = () => toggleLock(region, round, teamName);
    return line;
}

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    // Basic event setup
    const yearSelect = document.getElementById('year-select');
    appState.year = yearSelect.value;
    fetchTeams(appState.year);
    
    yearSelect.addEventListener('change', (e) => {
        appState.year = e.target.value;
        fetchTeams(appState.year);
        runSimulation();
    });
    
    document.getElementById('run-sim-btn').addEventListener('click', runSimulation);
    document.getElementById('reset-optimal').addEventListener('click', resetToOptimal);
    
    // Tab controls for mode
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            appState.mode = btn.getAttribute('data-mode');
            runSimulation();
        });
    });

    // Real-time Slider updates (debounced)
    const sliders = ['weight-sos', 'weight-trb', 'weight-to', 'weight-eff', 'weight-momentum'];
    sliders.forEach(id => {
        const slider = document.getElementById(id);
        const label = document.getElementById('val-' + id.split('-')[1]);
        slider.addEventListener('input', (e) => {
            label.textContent = e.target.value;
            debounceSim();
        });
    });

    // Initial run
    setTimeout(runSimulation, 500);
});
