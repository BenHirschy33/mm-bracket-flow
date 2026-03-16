const appState = {
    locks: {
        regions: {},
        final_four: {},
        championship: {}
    }
};

function toggleLock(region, round, teamName) {
    if (region === 'final_four' || region === 'championship') {
        if (!appState.locks[region]) appState.locks[region] = {};
        if (appState.locks[region][teamName]) {
            delete appState.locks[region][teamName];
        } else {
            appState.locks[region][teamName] = true;
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
}

function isLocked(region, round, teamName) {
    if (region === 'final_four' || region === 'championship') {
        return !!(appState.locks[region] && appState.locks[region][teamName]);
    }
    return !!(appState.locks.regions[region] && 
              appState.locks.regions[region][round] && 
              appState.locks.regions[region][round][teamName]);
}

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
    
    // Get weights from sliders
    const weightSos = document.getElementById('weight-sos').value;
    const weightTrb = document.getElementById('weight-trb').value;
    const weightTo = document.getElementById('weight-to').value;
    const weightEff = document.getElementById('weight-eff').value;
    
    bracketContainer.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
        const reqBody = {
            year: parseInt(year),
            weights: {
                sos: parseFloat(weightSos),
                trb: parseFloat(weightTrb),
                to: parseFloat(weightTo),
                efficiency: parseFloat(weightEff)
            },
            locks: appState.locks
        };
        
        const response = await fetch(`/api/simulation/full`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(reqBody)
        });
        const data = await response.json();
        
        if (data.error) {
            bracketContainer.innerHTML = `<div class="error-card">
                <h3>Simulation Error</h3>
                <p>${data.error}</p>
                <p class="hint">Ensure that the chalk_bracket.json exists for ${year}.</p>
            </div>`;
            return;
        }
        
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
        btn.onclick = () => {
            document.querySelectorAll('.region-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            displayRegion(r, data.regions[r]);
        };
        regionNav.appendChild(btn);
    });
    
    const ffBtn = document.createElement('button');
    ffBtn.textContent = 'Final Four';
    ffBtn.className = 'region-btn';
    ffBtn.onclick = () => {
        document.querySelectorAll('.region-btn').forEach(b => b.classList.remove('active'));
        ffBtn.classList.add('active');
        displayFinalFour(data.final_four, data.championship);
    };
    regionNav.appendChild(ffBtn);
    
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
            
            const lockedA = isLocked(name, r.round, m.team_a) ? 'locked' : '';
            const lockedB = isLocked(name, r.round, m.team_b) ? 'locked' : '';

            mDiv.innerHTML = `
                <div class="team-line ${m.winner === m.team_a ? 'winner' : ''} ${lockedA}" data-region="${name}" data-round="${r.round}" data-team="${m.team_a}">
                    <span>(${m.seed_a}) ${m.team_a} <span class="lock-icon">🔒</span></span>
                    ${m.winner === m.team_a ? `<span class="prob-tag">${prob}%</span>` : ''}
                </div>
                <div class="team-line ${m.winner === m.team_b ? 'winner' : ''} ${lockedB}" data-region="${name}" data-round="${r.round}" data-team="${m.team_b}">
                    <span>(${m.seed_b}) ${m.team_b} <span class="lock-icon">🔒</span></span>
                    ${m.winner === m.team_b ? `<span class="prob-tag">${(100 - prob).toFixed(1)}%</span>` : ''}
                </div>
            `;
            roundDiv.appendChild(mDiv);
        });
        roundsContainer.appendChild(roundDiv);
    });
    
    displayArea.appendChild(roundsContainer);
    
    document.querySelectorAll('.team-line').forEach(el => {
        el.addEventListener('click', () => {
             const rg = el.getAttribute('data-region');
             const rd = el.getAttribute('data-round');
             const tm = el.getAttribute('data-team');
             if(!tm) return;
             toggleLock(rg, rd, tm);
             el.classList.toggle('locked');
        });
    });
}


function displayFinalFour(ff, champ) {
    const displayArea = document.getElementById('region-display');
    displayArea.innerHTML = `<h3>Final Four & Championship</h3>`;
    
    const roundsContainer = document.createElement('div');
    roundsContainer.className = 'rounds-flex';
    
    // Final Four Setup
    const ffDiv = document.createElement('div');
    ffDiv.className = 'round-column';
    ffDiv.innerHTML = `<h4>National Semifinals</h4>`;
    
    ff.forEach((m) => {
        const mDiv = document.createElement('div');
        mDiv.className = 'matchup-card';
        const lockedA = isLocked('final_four', 1, m.team_a) ? 'locked' : '';
        const lockedB = isLocked('final_four', 1, m.team_b) ? 'locked' : '';
        mDiv.innerHTML = `
            <div class="team-line ${m.winner === m.team_a ? 'winner' : ''} ${lockedA}" data-region="final_four" data-round="1" data-team="${m.team_a}">
                <span>${m.team_a} <span class="lock-icon">🔒</span></span>
            </div>
            <div class="team-line ${m.winner === m.team_b ? 'winner' : ''} ${lockedB}" data-region="final_four" data-round="1" data-team="${m.team_b}">
                <span>${m.team_b} <span class="lock-icon">🔒</span></span>
            </div>
        `;
        ffDiv.appendChild(mDiv);
    });
    roundsContainer.appendChild(ffDiv);
    
    // Championship
    const champDiv = document.createElement('div');
    champDiv.className = 'round-column';
    champDiv.innerHTML = `<h4>National Championship</h4>`;
    const mDiv = document.createElement('div');
    mDiv.className = 'matchup-card';
    const lockedC_A = isLocked('championship', 1, champ.team_a) ? 'locked' : '';
    const lockedC_B = isLocked('championship', 1, champ.team_b) ? 'locked' : '';
    mDiv.innerHTML = `
        <div class="team-line ${champ.winner === champ.team_a ? 'winner' : ''} ${lockedC_A}" data-region="championship" data-round="1" data-team="${champ.team_a}">
            <span>${champ.team_a} <span class="lock-icon">🔒</span></span>
        </div>
        <div class="team-line ${champ.winner === champ.team_b ? 'winner' : ''} ${lockedC_B}" data-region="championship" data-round="1" data-team="${champ.team_b}">
            <span>${champ.team_b} <span class="lock-icon">🔒</span></span>
        </div>
        <div class="champ-winner" style="margin-top: 1rem; font-weight: 800; color: var(--accent-gold); text-align: center;">
            👑 ${champ.winner}
        </div>
    `;
    champDiv.appendChild(mDiv);
    roundsContainer.appendChild(champDiv);
    
    displayArea.appendChild(roundsContainer);
    
    document.querySelectorAll('.team-line').forEach(el => {
        el.addEventListener('click', () => {
             const rg = el.getAttribute('data-region');
             const rd = el.getAttribute('data-round');
             const tm = el.getAttribute('data-team');
             if(!tm) return;
             toggleLock(rg, rd, tm);
             el.classList.toggle('locked');
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const yearSelect = document.getElementById('year-select');
    fetchTeams(yearSelect.value);
    
    yearSelect.addEventListener('change', (e) => {
        fetchTeams(e.target.value);
    });
    
    document.getElementById('run-sim-btn').addEventListener('click', runSimulation);

    // Slider Label Updates
    const sliders = [
        {id: 'weight-sos', val: 'val-sos'},
        {id: 'weight-trb', val: 'val-trb'},
        {id: 'weight-to', val: 'val-to'},
        {id: 'weight-eff', val: 'val-eff'}
    ];

    sliders.forEach(s => {
        const slider = document.getElementById(s.id);
        const label = document.getElementById(s.val);
        slider.addEventListener('input', (e) => {
            label.textContent = e.target.value;
        });
    });
});
