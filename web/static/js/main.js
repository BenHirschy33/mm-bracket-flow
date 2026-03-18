const appState = {
    mode: 'custom',
    year: '2026',
    volatility: 0,
    filter: {
        region: 'all',
        round: 'all'
    },
    locks: {
        regions: {},
        final_four: {},
        championship: {}
    },
    optimalWeights: {},
    perfectWeights: {
        efficiency: 0.25,
        momentum: 0.15,
        sos: 0.4,
        intuition_factor_weight: 0.8,
        upset_delta_weight: 0.9,
        composure_index_weight: 0.7
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
        'weight-def-premium': weights.def_premium,
        'weight-intuition-factor': 0,
        'weight-composure-index-weight': 0,
        'weight-upset-delta-weight': 0
    };

    for (const [id, val] of Object.entries(mapping)) {
        const slider = document.getElementById(id);
        const statName = id.replace('weight-', '');
        const numInput = document.getElementById('num-' + statName);
        const valLabel = document.getElementById('val-' + statName);

        if (slider) slider.value = val;
        if (numInput) numInput.value = val;
        if (valLabel) valLabel.textContent = val;
    }
    
    // Reset chaos metrics specifically
    appState.volatility = 0;
    const volSlider = document.getElementById('weight-volatility');
    if (volSlider) volSlider.value = 0;
    const volVal = document.getElementById('val-volatility');
    if (volVal) volVal.textContent = '0';

    runSimulation();
}

function applyWeights(weights) {
    const mapping = {
        'weight-eff': weights.efficiency,
        'weight-sos': weights.sos,
        'weight-trb': weights.trb,
        'weight-momentum': weights.momentum,
        'weight-def-premium': weights.def_premium,
        'weight-intuition-factor': weights.intuition_factor_weight,
        'weight-composure-index-weight': weights.composure_index_weight,
        'weight-upset-delta-weight': weights.upset_delta_weight
    };

    for (const [id, val] of Object.entries(mapping)) {
        const slider = document.getElementById(id);
        const statName = id.replace('weight-', '');
        const numInput = document.getElementById('num-' + statName);
        const valLabel = document.getElementById('val-' + statName);

        // Even if val is undefined, we might want to reset to 0 in non-custom mode
        const finalVal = val !== undefined ? val : (appState.mode !== 'custom' ? 0 : null);
        
        if (finalVal !== null && slider) {
            slider.value = finalVal;
            if (numInput) numInput.value = finalVal;
            if (valLabel) valLabel.textContent = finalVal;
        }
    }

    runSimulation();
}

function switchToCustom() {
    if (appState.mode !== 'custom') {
        appState.mode = 'custom';
        document.querySelectorAll('.tab-btn').forEach(b => {
            b.classList.toggle('active', b.getAttribute('data-mode') === 'custom');
        });
    }
}

function toggleLock(region, round, teamName) {
    if (region === 'final_four' || region === 'championship') {
        if (appState.locks[region][teamName]) {
            delete appState.locks[region][teamName];
        } else {
            appState.locks[region] = { [teamName]: true };
        }
    } else {
        if (!appState.locks.regions[region]) appState.locks.regions[region] = {};
        if (!appState.locks.regions[region][round]) appState.locks.regions[region][round] = {};
        
        const isCurrentlyLocked = appState.locks.regions[region][round][teamName];
        
        if (isCurrentlyLocked) {
            for (let r = round; r <= 6; r++) {
                if (appState.locks.regions[region]?.[r]) {
                    delete appState.locks.regions[region][r][teamName];
                }
            }
            delete appState.locks.final_four[teamName];
            delete appState.locks.championship[teamName];
        } else {
            const currentMatchups = appState.currentData?.regions?.[region]?.[round - 1]?.matchups;
            if (currentMatchups) {
                const matchup = currentMatchups.find(m => m.team_a === teamName || m.team_b === teamName);
                if (matchup) {
                    const opponent = matchup.team_a === teamName ? matchup.team_b : matchup.team_a;
                    delete appState.locks.regions[region][round][opponent];
                }
            }
            for (let r = 1; r <= round; r++) {
                if (!appState.locks.regions[region][r]) appState.locks.regions[region][r] = {};
                appState.locks.regions[region][r][teamName] = true;
            }
        }
    }
    runSimulation();
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
        resetToOptimal();
    } catch (err) {
        console.error("Failed to fetch optimal weights", err);
    }
}

async function fetchTeams(year) {
    const teamList = document.getElementById('team-list');
    if (teamList) teamList.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
        const response = await fetch(`/api/teams/${year}`);
        const teams = await response.json();
        
        if (teamList) teamList.innerHTML = '';
        appState.teams = {};
        teams.forEach(t => appState.teams[t.name] = t);

        if (teamList) {
            teams.sort((a, b) => a.seed - b.seed).forEach(team => {
                const item = document.createElement('div');
                item.className = 'team-item';
                item.innerHTML = `
                    <div class="team-info">
                        <span class="seed-num">${team.seed || '?'}</span>
                        <div>
                            <div style="font-weight: 600; font-size: 0.9rem; display: flex; align-items: center;">
                                ${team.name}
                                ${team.archetype !== 'Standard' ? `<span class="archetype-tag ${team.archetype.toLowerCase().replace(' ', '-')}">${team.archetype}</span>` : ''}
                            </div>
                            <div class="stat-tag">Eff: ${team.off_efficiency || 'N/A'}</div>
                        </div>
                    </div>
                `;
                teamList.appendChild(item);
            });
        }
    } catch (err) {
        if (teamList) teamList.innerHTML = `<div class="error">Failed to load teams: ${err.message}</div>`;
    }
}

async function runSimulation() {
    const weights = {};
    const weightInputs = document.querySelectorAll('input[id^="weight-"]');
    weightInputs.forEach(input => {
        const id = input.id.replace('weight-', '').replace(/-/g, '_');
        let key = id;
        if (key === 'eff') key = 'efficiency';
        weights[key] = parseFloat(input.value);
    });
    
    try {
        const response = await fetch(`/api/simulation/full`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                year: parseInt(appState.year),
                mode: appState.mode,
                volatility: appState.volatility / 100,
                weights: weights,
                locks: appState.locks
            })
        });
        const data = await response.json();
        appState.currentData = data;
        renderBracketWaterfall(data);
    } catch (err) {
        console.error("Simulation failed", err);
    }
}

// --- Rendering ---

function renderBracketWaterfall(data) {
    const container = document.getElementById('bracket-container');
    if (!container) return;
    container.innerHTML = '';
    
    const regionsOrder = ['East', 'South', 'West', 'Midwest'];
    
    const regionsColumn = document.createElement('div');
    regionsColumn.className = 'regions-column';
    
    regionsOrder.forEach(regionName => {
        const rounds = data.regions[regionName];
        if (!rounds) return;

        const regionBlock = document.createElement('div');
        regionBlock.className = 'region-block';
        regionBlock.setAttribute('data-region', regionName);

        // Add Regional Label
        const label = document.createElement('h2');
        label.className = 'region-label-v2';
        label.style.color = 'var(--accent-gold)';
        label.style.fontSize = '1.5rem';
        label.style.fontWeight = '800';
        label.style.margin = '2rem 0 1rem 4rem';
        label.style.letterSpacing = '0.1em';
        label.textContent = `${regionName.toUpperCase()} REGION`;
        regionBlock.appendChild(label);
        
        const displayArea = document.createElement('div');
        displayArea.className = 'region-display';
        
        const roundsContainer = document.createElement('div');
        roundsContainer.className = 'rounds-flex';
        
        rounds.forEach((r) => {
            const roundDiv = document.createElement('div');
            roundDiv.className = `round-column round-${r.round}`;
            
            roundDiv.style.gridColumn = r.round;
            
            const span = Math.pow(2, r.round);
            
            r.matchups.forEach((m, idx) => {
                const mCard = document.createElement('div');
                mCard.className = 'matchup-card';
                const start = (idx * span) + 1;
                mCard.style.gridRow = `${start} / span ${span}`;
                
                const vol = appState.volatility / 100;
                let probA = m.probability || 0.5;
                let blendedA = ((1.0 - vol) * probA) + (vol * 0.5);
                
                mCard.appendChild(createTeamLine(regionName, r.round, m.team_a, m.seed_a, m.winner === m.team_a, (blendedA * 100).toFixed(0)));
                mCard.appendChild(createTeamLine(regionName, r.round, m.team_b, m.seed_b, m.winner === m.team_b, ((1-blendedA) * 100).toFixed(0)));
                
                roundDiv.appendChild(mCard);
            });
            roundsContainer.appendChild(roundDiv);
        });
        
        displayArea.appendChild(roundsContainer);
        regionBlock.appendChild(displayArea);
        regionsColumn.appendChild(regionBlock);
    });

    container.appendChild(regionsColumn);

    // Integrate Finale into the vertical column
    renderFinalFourBlock(data.final_four, data.championship, regionsColumn);
    
    if (appState.filter.region !== 'all') {
        zoomToRound('all'); // Default to full overview
    }
}

function renderFinalFourBlock(ff, champ, container) {
    const ffBlock = document.createElement('div');
    ffBlock.className = 'final_four_block';
    
    const title = document.createElement('div');
    title.className = 'region-grid-title';
    title.textContent = 'National Championship';
    ffBlock.appendChild(title);
    
    const ffFlex = document.createElement('div');
    ffFlex.className = 'ff-flex-row';
    ffFlex.style.display = 'flex';
    ffFlex.style.alignItems = 'center';
    ffFlex.style.gap = '3rem';
    
    if (ff[0]) {
        const mDiv = document.createElement('div');
        mDiv.className = 'matchup-card ff-matchup';
        mDiv.appendChild(createTeamLine('final_four', 1, ff[0].team_a, ff[0].seed_a, ff[0].winner === ff[0].team_a, ''));
        mDiv.appendChild(createTeamLine('final_four', 1, ff[0].team_b, ff[0].seed_b, ff[0].winner === ff[0].team_b, ''));
        ffFlex.appendChild(mDiv);
    }
    
    const cCard = document.createElement('div');
    cCard.className = 'matchup-card champ-matchup';
    cCard.style.border = '2px solid var(--accent-gold)';
    cCard.appendChild(createTeamLine('championship', 1, champ.team_a, champ.seed_a, champ.winner === champ.team_a, ''));
    cCard.appendChild(createTeamLine('championship', 1, champ.team_b, champ.seed_b, champ.winner === champ.team_b, ''));
    
    if (champ.winner) {
        const trophy = document.createElement('div');
        trophy.className = 'champ-winner-glow';
        trophy.innerHTML = `🏆 ${champ.winner} 🏆`;
        cCard.appendChild(trophy);
    }
    ffFlex.appendChild(cCard);

    if (ff[1]) {
        const mDiv = document.createElement('div');
        mDiv.className = 'matchup-card ff-matchup';
        mDiv.appendChild(createTeamLine('final_four', 1, ff[1].team_a, ff[1].seed_a, ff[1].winner === ff[1].team_a, ''));
        mDiv.appendChild(createTeamLine('final_four', 1, ff[1].team_b, ff[1].seed_b, ff[1].winner === ff[1].team_b, ''));
        ffFlex.appendChild(mDiv);
    }
    
    ffBlock.appendChild(ffFlex);
    container.appendChild(ffBlock);
}

function createTeamLine(region, round, teamName, seed, isWinner, prob) {
    const line = document.createElement('div');
    const team = teamName || "TBD";
    const locked = isLocked(region, round, team) ? 'locked' : '';
    line.className = `team-line ${isWinner ? 'winner' : ''} ${locked} ${team === "TBD" ? 'tbd' : ''}`;
    
    line.innerHTML = `
        <span class="team-content">
            <span class="seed">${seed || '?'}</span>
            <span class="name">${team}</span>
            ${team !== "TBD" ? `<span class="lock-icon ${locked ? 'active' : ''}" title="Lock team to advance">🔒</span>` : ''}
        </span>
        ${isWinner && prob ? `<span class="prob-tag">${prob}%</span>` : ''}
    `;

    if (team !== "TBD") {
        line.onclick = (e) => {
            if (e.target.classList.contains('lock-icon')) {
                toggleLock(region, round, team);
            } else {
                // Find opponent for modal
                let opponent = "TBD";
                const currentRound = appState.currentData?.regions[region]?.[round-1];
                if (currentRound) {
                    const matchup = currentRound.matchups.find(m => m.team_a === team || m.team_b === team);
                    if (matchup) {
                        opponent = matchup.team_a === team ? matchup.team_b : matchup.team_a;
                    }
                }
                openMatchupModal(team, opponent);
            }
        };
    }
    return line;
}

// --- Navigation & UX ---

window.zoomToRound = function(round) {
    const container = document.getElementById('bracket-container');
    if (!container) return;

    let scale = 1.0;
    let translateX = 0;
    let translateY = 0;

    // Remove active class from all round buttons
    document.querySelectorAll('.round-btn').forEach(btn => btn.classList.remove('active'));
    
    // Find the clicked button and add active class
    const buttons = document.querySelectorAll('.round-btn');
    buttons.forEach(btn => {
        if (round === 'all' && btn.textContent.includes('Overview')) btn.classList.add('active');
        if (round === 64 && btn.textContent.includes('64')) btn.classList.add('active');
        if (round === 32 && btn.textContent.includes('32')) btn.classList.add('active');
        if (round === 16 && btn.textContent.includes('16')) btn.classList.add('active');
        if (round === 8) btn.classList.add('active');
        if (round === 4) btn.classList.add('active');
        if (round === 2 && btn.textContent.includes('Champ')) btn.classList.add('active');
    });

    if (round === 'all') {
        scale = 0.25;
        translateX = 0;
        translateY = 0;
    } else {
        scale = 1.0;
        // Each round column is 240px + 40px gap = 280px
        if (round === 64) translateX = 0;
        if (round === 32) translateX = -280;
        if (round === 16) translateX = -560;
        if (round === 8) translateX = -840;
        if (round === 4) translateX = -1100; // Final Four focus
        if (round === 2) translateX = -1250; // Championship focus
        
        translateY = 0; // Default to top of stack
    }

    container.style.transform = `scale(${scale}) translate(${translateX}px, ${translateY}px)`;
    
    // Auto-scroll the viewport to the top of the container
    const viewport = document.querySelector('.full-viewport');
    if (viewport) {
        viewport.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function openMatchupModal(teamA, teamB) {
    const modal = document.getElementById('matchup-modal');
    if (modal) modal.classList.add('active');
}

function closeMatchupModal() {
    const modal = document.getElementById('matchup-modal');
    if (modal) modal.classList.remove('active');
}

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    const yearSelect = document.getElementById('year-select');
    if (yearSelect) {
        appState.year = yearSelect.value;
        yearSelect.addEventListener('change', (e) => {
            appState.year = e.target.value;
            fetchTeams(appState.year);
            runSimulation();
        });
    }

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            appState.mode = btn.getAttribute('data-mode');
            
            if (appState.mode === 'custom') {
                const panel = document.getElementById('settings-panel');
                if (panel) panel.classList.add('active');
            } else {
                // Close any open settings modals when switching to non-custom modes
                document.querySelectorAll('.settings-modal').forEach(panel => {
                    panel.classList.remove('active');
                });
            }
            
            if (appState.mode === 'average') resetToOptimal();
            else if (appState.mode === 'perfect') applyWeights(appState.perfectWeights);
            else runSimulation();
        });
    });

    document.querySelectorAll('.region-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const region = btn.getAttribute('data-region');
            document.querySelectorAll('.region-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            appState.filter.region = region;
            // zoomToRegion is deprecated, we focus on rounds now.
            // If the user wants to see a region, we'll just snap to Round 64.
            window.zoomToRound(64); 
        });
    });

    const volSlider = document.getElementById('weight-volatility');
    const volVal = document.getElementById('val-volatility');
    if (volSlider) {
        volSlider.addEventListener('input', (e) => {
            appState.volatility = parseInt(e.target.value);
            if (volVal) volVal.textContent = e.target.value;
            switchToCustom();
            debounceSim();
        });
    }

    const bracketContainer = document.getElementById('bracket-container');
    if (bracketContainer) {
        bracketContainer.addEventListener('click', (e) => {
            const card = e.target.closest('.matchup-card');
            if (card && !card.classList.contains('ff-matchup') && !card.classList.contains('champ-matchup')) {
                // For now, just a placeholder for matchup intelligence
                document.getElementById('matchup-modal').classList.add('active');
            }
        });
    }

    const closeModal = document.getElementById('close-modal');
    if (closeModal) {
        closeModal.addEventListener('click', () => {
            document.getElementById('matchup-modal').classList.remove('active');
        });
    }

    document.querySelectorAll('input[type="range"][id^="weight-"]').forEach(slider => {
        const id = slider.id.replace('weight-', '');
        const numInput = document.getElementById(`num-${id}`);
        slider.addEventListener('input', (e) => {
            if (numInput) numInput.value = e.target.value;
            const label = document.getElementById(`val-${id}`);
            if (label) label.textContent = e.target.value;
            switchToCustom();
            debounceSim();
        });
    });

    const runBtn = document.getElementById('run-sim-btn');
    if (runBtn) runBtn.onclick = runSimulation;

    const resetBtn = document.getElementById('reset-optimal');
    if (resetBtn) resetBtn.onclick = resetToOptimal;

    // Toggle Panels
    const panels = {
        'settings-toggle-btn': 'settings-panel',
        'field-stats-toggle-btn': 'field-stats-panel',
        'research-lab-toggle-btn': 'research-lab-panel'
    };

    Object.entries(panels).forEach(([btnId, panelId]) => {
        const btn = document.getElementById(btnId);
        const panel = document.getElementById(panelId);
        if (btn && panel) {
            btn.onclick = () => panel.classList.toggle('active');
        }
    });

    // Deep Dive Collapsible
    document.querySelectorAll('.group-header').forEach(header => {
        header.onclick = () => {
            header.closest('.collapsible').classList.toggle('expanded');
        };
    });

    document.querySelectorAll('.close-settings, .close-field, .close-research').forEach(btn => {
        btn.onclick = (e) => e.target.closest('.settings-modal').classList.remove('active');
    });

    initWeights();
    fetchTeams(appState.year);
});

// Expose for browser agent
window.appState = appState;
