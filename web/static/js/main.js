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
        efficiency: 0.039,
        ft: 0.881,
        def_premium: 6.479
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
    const weights = appState.optimalWeights;
    const mapping = {
        'weight-sos': weights.sos,
        'weight-trb': weights.trb,
        'weight-to': weights.to,
        'weight-eff': weights.efficiency,
        'weight-momentum': weights.momentum,
        'weight-ft': weights.ft,
        'weight-def-premium': weights.def_premium
    };

    for (const [id, val] of Object.entries(mapping)) {
        const slider = document.getElementById(id);
        // Extract the stat name (e.g., 'sos' from 'weight-sos')
        const statName = id.split('-')[1];
        const numInput = document.getElementById('num-' + statName);
        const valLabel = document.getElementById('val-' + statName);

        if (slider) slider.value = val;
        if (numInput) numInput.value = val;
        if (valLabel) valLabel.textContent = val; // Update the display label
    }
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

async function initWeights() {
    try {
        const response = await fetch('/api/weights/optimal');
        const weights = await response.json();
        appState.optimalWeights = weights;
        resetToOptimal(); // Apply fetched weights immediately
    } catch (err) {
        console.error("Failed to fetch optimal weights", err);
    }
}

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
        momentum: parseFloat(document.getElementById('weight-momentum').value),
        ft: parseFloat(document.getElementById('weight-ft').value),
        def_premium: parseFloat(document.getElementById('weight-def-premium').value)
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
        
        // Waterfall Rendering: Reveal rounds with a slight delay for "Discovery" feel
        renderBracketWaterfall(data);
    } catch (err) {
        console.error("Simulation failed", err);
    }
}

// --- Rendering ---

async function renderBracketWaterfall(data) {
    const container = document.getElementById('bracket-container');
    container.innerHTML = '';
    container.className = 'bracket-view';

    // Header for Global View
    const header = document.createElement('div');
    header.className = 'view-header';
    header.style.opacity = '0';
    header.style.transition = 'opacity 0.8s ease';
    header.innerHTML = `<h3 class="glow-text">Tournament Intelligence Matrix</h3>`;
    container.appendChild(header);
    setTimeout(() => header.style.opacity = '1', 50);

    const regions = Object.keys(data.regions);
    
    for (const regionName of regions) {
        const regionBlock = document.createElement('div');
        regionBlock.className = 'region-block';
        regionBlock.style.opacity = '0';
        regionBlock.style.transform = 'translateY(20px)';
        regionBlock.style.transition = 'all 0.6s cubic-bezier(0.19, 1, 0.22, 1)';
        regionBlock.innerHTML = `<h3>${regionName} Region</h3>`;
        
        const displayArea = document.createElement('div');
        displayArea.className = 'region-display';
        
        const rounds = data.regions[regionName];
        const roundsContainer = document.createElement('div');
        roundsContainer.className = 'rounds-flex';
        
        for (const [roundIdx, r] of rounds.entries()) {
            const roundDiv = document.createElement('div');
            roundDiv.className = `round-column round-${r.round}`;
            roundDiv.style.opacity = '0';
            roundDiv.style.transition = `opacity 0.5s ease ${roundIdx * 0.2}s`;
            
            r.matchups.forEach((m, matchIdx) => {
                const matchupWrapper = document.createElement('div');
                matchupWrapper.className = 'matchup-wrapper';
                
                const mCard = document.createElement('div');
                const isUpper = matchIdx % 2 === 0;
                const hasNext = roundIdx < rounds.length - 1;
                mCard.className = `matchup-card ${isUpper ? 'upper' : 'lower'} ${hasNext ? 'has-next' : ''}`;
                
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
            setTimeout(() => roundDiv.style.opacity = '1', 100);
        }
        
        displayArea.appendChild(roundsContainer);
        regionBlock.appendChild(displayArea);
        container.appendChild(regionBlock);
        
        setTimeout(() => {
            regionBlock.style.opacity = '1';
            regionBlock.style.transform = 'translateY(0)';
        }, 300);
    }

    // Final Four Section
    setTimeout(() => {
        renderFinalFourBlock(data.final_four, data.championship, container);
    }, 1200);
}

function renderBracket(data) {
    // Basic fallback or initial render
    renderBracketWaterfall(data);
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
        tooltip = `Eff: ${team.off_efficiency} | SOS: ${team.sos?.toFixed(1) || 'N/A'} | Mom: ${team.momentum?.toFixed(2)} | FT: ${team.off_ft_pct}%`;
    }

    line.innerHTML = `
        <span>(${seed}) ${teamName} <span class="lock-icon" onclick="event.stopPropagation()">🔒</span></span>
        ${isWinner && prob ? `<span class="prob-tag" title="${tooltip}">${prob}%</span>` : ''}
    `;
    line.onclick = (e) => {
        if (e.target.classList.contains('lock-icon')) {
            toggleLock(region, round, teamName);
        } else {
            // Find the opponent
            let opponent = "TBD";
            const currentRound = appState.currentData?.regions[region]?.[round-1];
            if (currentRound) {
                const matchup = currentRound.matchups.find(m => m.team_a === teamName || m.team_b === teamName);
                if (matchup) {
                    opponent = matchup.team_a === teamName ? matchup.team_b : matchup.team_a;
                }
            }
            openMatchupModal(teamName, opponent);
        }
    };
    return line;
}

// --- Modal Logic ---
async function openMatchupModal(teamA, teamB) {
    if (teamA === "TBD" || teamB === "TBD") return;
    
    const modal = document.getElementById('matchup-modal');
    modal.classList.add('active');
    
    // Set loading state
    document.getElementById('why-list').innerHTML = '<div class="loading-spinner"></div>';
    
    const weights = {
        sos: parseFloat(document.getElementById('weight-sos').value),
        trb: parseFloat(document.getElementById('weight-trb').value),
        to: parseFloat(document.getElementById('weight-to').value),
        eff: parseFloat(document.getElementById('weight-eff').value),
        momentum: parseFloat(document.getElementById('weight-momentum').value),
        ft: parseFloat(document.getElementById('weight-ft').value),
        def_premium: parseFloat(document.getElementById('weight-def-premium').value)
    };

    try {
        const response = await fetch(`/api/matchup/detail?team_a=${teamA}&team_b=${teamB}&year=${appState.year}&sos=${weights.sos}&trb=${weights.trb}&to=${weights.to}&eff=${weights.eff}&momentum=${weights.momentum}&ft=${weights.ft}&def_premium=${weights.def_premium}`);
        const data = await response.json();
        
        renderModalData(data);
    } catch (err) {
        console.error("Matchup detail fetch failed", err);
    }
}

function renderModalData(data) {
    document.getElementById('modal-prob').textContent = `${(data.probability * 100).toFixed(0)}% Win Prob`;
    
    const renderTeam = (id, team) => {
        const div = document.getElementById(id);
        div.className = 'team-card-modal';
        div.innerHTML = `
            <div class="name">(${team.seed}) ${team.name}</div>
            <div class="stat-bubbles">
                <div class="stat-bubble">Off: ${team.off_eff.toFixed(1)}</div>
                <div class="stat-bubble">Def: ${team.def_eff.toFixed(1)}</div>
                <div class="stat-bubble">SOS: ${team.sos.toFixed(1)}</div>
            </div>
        `;
    };
    
    renderTeam('modal-team-a', data.team_a);
    renderTeam('modal-team-b', data.team_b);
    
    // Render "The Why"
    const whyList = document.getElementById('why-list');
    whyList.innerHTML = data.analysis.map(item => `
        <div class="why-item">
            <strong>${item.factor} (${item.importance})</strong>
            <p>${item.description}</p>
        </div>
    `).join('') || '<p>No significant analytical outliers found for this matchup.</p>';
    
    // Render Bars
    const metrics = [
        { label: 'Off. Efficiency', key: 'off_eff', max: 130 },
        { label: 'Def. Efficiency', key: 'def_eff', max: 120, inverse: true },
        { label: 'SOS Rating', key: 'sos', max: 15 },
        { label: 'Rebounding', key: 'trb', max: 60 }
    ];
    
    const barContainer = document.getElementById('comparison-bars');
    barContainer.innerHTML = metrics.map(m => {
        let valA = data.team_a[m.key];
        let valB = data.team_b[m.key];
        
        const pctA = (valA / m.max) * 100;
        const pctB = (valB / m.max) * 100;
        
        return `
            <div class="stat-bar-row">
                <div class="stat-header">
                    <span class="val-a">${valA.toFixed(1)}</span>
                    <span class="stat-label">${m.label}</span>
                    <span class="val-b">${valB.toFixed(1)}</span>
                </div>
                <div class="bar-wrapper">
                    <div class="bar-fill team-a" style="width: 0%"></div>
                    <div class="bar-fill team-b" style="width: 0%"></div>
                </div>
            </div>
        `;
    }).join('');

    // Animate bars after render
    setTimeout(() => {
        const barsA = document.querySelectorAll('.bar-fill.team-a');
        const barsB = document.querySelectorAll('.bar-fill.team-b');
        metrics.forEach((m, i) => {
            const pctA = (data.team_a[m.key] / m.max) * 100;
            const pctB = (data.team_b[m.key] / m.max) * 100;
            barsA[i].style.width = `${pctA}%`;
            barsB[i].style.width = `${pctB}%`;
        });
    }, 100);
}

function closeMatchupModal() {
    document.getElementById('matchup-modal').classList.remove('active');
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

    // Real-time Slider & Number updates (bidirectional sync)
    const factorIds = ['sos', 'trb', 'to', 'eff', 'momentum', 'ft', 'def-premium'];
    factorIds.forEach(id => {
        const slider = document.getElementById(`weight-${id}`);
        const numInput = document.getElementById(`num-${id}`);
        
        // Sync Slider -> Number
        slider.addEventListener('input', (e) => {
            numInput.value = e.target.value;
            debounceSim();
        });
        
        // Sync Number -> Slider
        numInput.addEventListener('input', (e) => {
            slider.value = e.target.value;
            debounceSim();
        });
    });

    document.getElementById('close-modal').addEventListener('click', closeMatchupModal);
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal-overlay')) closeMatchupModal();
    });

    initWeights(); // Load optimal weights from API

    // System Dark Mode sync (subtle bridge)
    const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleTheme = (e) => {
        document.body.classList.toggle('system-dark', e.matches);
    };
    darkModeQuery.addListener(handleTheme);
    handleTheme(darkModeQuery);

    // Initial run
    setTimeout(runSimulation, 500);
});

// Expose for debugging/subagents
window.appState = appState;
window.runSimulation = runSimulation;
window.renderBracket = renderBracket;
