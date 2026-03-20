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
    simTimer: null,
    zoom: {
        scale: 0.45,
        x: 0,
        y: 0,
        isPanning: false,
        startX: 0,
        startY: 0
    }
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
        // Fetch both preset profiles in parallel
        const [avgRes, champRes] = await Promise.all([
            fetch('/api/weights/preset?mode=avg'),
            fetch('/api/weights/preset?mode=champion')
        ]);
        const avgData = await avgRes.json();
        const champData = await champRes.json();

        // Store the full weight dicts for each mode
        appState.optimalWeights = avgData.weights || {};
        appState.perfectWeights = champData.weights || {};

        // Also populate the old flat-key format for backward compat with resetToOptimal sliders
        const w = appState.optimalWeights;
        appState._optimalFlat = {
            trb: w.trb_weight,
            to: w.to_weight,
            sos: w.sos_weight,
            momentum: w.momentum_weight,
            efficiency: w.efficiency_weight,
            ft: w.ft_weight,
            def_premium: w.defense_premium,
            orb_density: w.orb_density_weight,
            luck_regression: w.luck_regression_weight,
            coach_moxie: w.coach_tournament_weight,
            tempo_upset: w.tempo_upset_weight,
            fatigue: w.fatigue_sensitivity,
            bench: w.bench_rest_bonus
        };

        console.log('[Weights] Loaded MAX_AVG preset:', avgData.meta);
        console.log('[Weights] Loaded MAX_PERFECT preset:', champData.meta);
    } catch (err) {
        console.error("Failed to fetch preset weights", err);
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
                locks: appState.locks,
                use_live_results: appState.useLiveResults || false
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
    
    const quadGrid = document.createElement('div');
    quadGrid.className = 'quad-grid';
    container.appendChild(quadGrid);

    // Regions Placement Mapping
    const regionConfigs = {
        'East': { col: 1, row: 1, mirrored: false },
        'South': { col: 1, row: 2, mirrored: false },
        'Midwest': { col: 3, row: 1, mirrored: true },
        'West': { col: 3, row: 2, mirrored: true }
    };

    const regionsOrder = ['East', 'South', 'Midwest', 'West'];
    
    // Create Center Stage
    const centerStage = document.createElement('div');
    centerStage.className = 'center-stage';
    quadGrid.appendChild(centerStage);

    // Populate Regional Rounds (1-4)
    regionsOrder.forEach((regionName) => {
        const config = regionConfigs[regionName];
        const rounds = data.regions[regionName];
        if (!rounds) return;

        const regContainer = document.createElement('div');
        regContainer.className = `region-container ${config.mirrored ? 'mirrored' : ''}`;
        regContainer.style.gridColumn = config.col;
        regContainer.style.gridRow = config.row;
        quadGrid.appendChild(regContainer);

        // Region Label
        const label = document.createElement('div');
        label.className = 'region-label-v2';
        label.style.top = '10px';
        if (config.mirrored) label.style.right = '2rem'; else label.style.left = '2rem';
        label.textContent = regionName;
        regContainer.appendChild(label);

        // Create 4 columns for this region
        const columns = [];
        for (let i = 1; i <= 4; i++) {
            const col = document.createElement('div');
            col.className = `round-column round-${i}`;
            columns.push(col);
            regContainer.appendChild(col);
        }

        rounds.forEach((r) => {
            const col = columns[r.round - 1];
            const span = Math.pow(2, r.round);
            
            r.matchups.forEach((m, mIdx) => {
                const mCard = document.createElement('div');
                mCard.className = 'matchup-card';
                
                // Add top/bottom class for connectors
                const isTop = (mIdx % 2 === 0);
                mCard.classList.add(isTop ? 'm-top' : 'm-bottom');
                
                const span = Math.pow(2, r.round);
                const start = (mIdx * span) + 1;
                mCard.style.gridRow = `${start} / span ${span}`;
                mCard.style.setProperty('--span-height', `${span * 60}px`);
                
                const vol = appState.volatility / 100;
                let probA = m.probability || 0.5;
                let blendedA = ((1.0 - vol) * probA) + (vol * 0.5);
                
                mCard.appendChild(createTeamLine(regionName, r.round, m.team_a, m.seed_a, m.winner === m.team_a, (blendedA * 100).toFixed(0)));
                mCard.appendChild(createTeamLine(regionName, r.round, m.team_b, m.seed_b, m.winner === m.team_b, ((1-blendedA) * 100).toFixed(0)));
                
                col.appendChild(mCard);
            });
        });
    });

    // Populate Final Four (Round 5)
    if (data.final_four) {
        const leftF4 = document.createElement('div');
        leftF4.className = 'ff-games-stack ff-left';
        const rightF4 = document.createElement('div');
        rightF4.className = 'ff-games-stack ff-right';
        
        centerStage.appendChild(leftF4);
        centerStage.appendChild(rightF4);

        data.final_four.forEach((m, idx) => {
            const mCard = document.createElement('div');
            mCard.className = `matchup-card ff-matchup`;
            mCard.style.width = '300px';
            
            mCard.appendChild(createTeamLine('final_four', 1, m.team_a, m.seed_a, m.winner === m.team_a, ''));
            mCard.appendChild(createTeamLine('final_four', 1, m.team_b, m.seed_b, m.winner === m.team_b, ''));
            
            if (idx === 0) leftF4.appendChild(mCard); else rightF4.appendChild(mCard);
        });
    }

    // Populate Championship (Round 6)
    if (data.championship) {
        const m = data.championship;
        const champContainer = document.createElement('div');
        champContainer.className = 'hero-champ';
        centerStage.appendChild(champContainer);

        const mCard = document.createElement('div');
        mCard.className = 'matchup-card championship-box';
        mCard.style.width = '420px';
        
        mCard.appendChild(createTeamLine('championship', 1, m.team_a, m.seed_a, m.winner === m.team_a, ''));
        mCard.appendChild(createTeamLine('championship', 1, m.team_b, m.seed_b, m.winner === m.team_b, ''));
        
        if (m.winner) {
            const trophy = document.createElement('div');
            trophy.className = 'champ-winner-glow trophy-outside';
            trophy.innerHTML = `🏆 ${m.winner} 🏆`;
            champContainer.appendChild(trophy);
        }
        champContainer.appendChild(mCard);
    }
    
    if (appState.filter.region !== 'all') {
        zoomToRound('all');
    }
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
        line.style.cursor = 'pointer';
        line.addEventListener('click', (e) => {
            if (e.target.classList.contains('lock-icon')) {
                toggleLock(region, round, team);
            } else {
                const currentRound = appState.currentData?.regions[region]?.[round-1];
                if (currentRound) {
                    const matchup = currentRound.matchups.find(m => m.team_a === team || m.team_b === team);
                    if (matchup) {
                        openMatchupModal(matchup);
                    }
                }
            }
        });
    }
    return line;
}

// --- Navigation & UX ---

window.zoomToRound = function(round) {
    const container = document.getElementById('bracket-container');
    if (!container) return;

    const overviewBtn = document.getElementById('overview-btn');
    if (overviewBtn) {
        if (round === 'all') overviewBtn.classList.add('active');
        else overviewBtn.classList.remove('active');
    }

    if (round === 'all') {
        const vH = window.innerHeight;
        const vW = window.innerWidth;
        const scaleH = (vH - 180) / 1920;
        const scaleW = (vW - 100) / 2840;
        appState.zoom.scale = Math.min(scaleH, scaleW, 0.45); 
        appState.zoom.x = (vW - (2840 * appState.zoom.scale)) / 2;
        appState.zoom.y = 0;
    } else {
        appState.zoom.scale = 0.8; 
        appState.zoom.x = (window.innerWidth - (2840 * appState.zoom.scale)) / 2;
        appState.zoom.y = 0;
    }

    applyZoom();
    
    const viewport = document.querySelector('.full-viewport');
    if (viewport) {
        viewport.scrollTo({ 
            top: 0, 
            left: 0, 
            behavior: 'smooth' 
        });
    }
}

// --- Simulation Control ---

window.resetSimulation = function() {
    appState.locks = {
        regions: {},
        final_four: {},
        championship: {}
    };
    
    // Also reset any active button states
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector('.tab-btn[data-mode="custom"]')?.classList.add('active');
    appState.mode = 'custom';
    
    runSimulation();
}

function applyZoom() {
    const container = document.getElementById('bracket-container');
    const proxy = document.getElementById('zoom-container');
    if (!container || !proxy) return;
    
    // Scale the visual
    container.style.transform = `scale(${appState.zoom.scale})`;
    
    // Precise bounds for Quad Grid (2840px x 1920px)
    proxy.style.width = (2840 * appState.zoom.scale + 100) + "px";
    proxy.style.height = (1920 * appState.zoom.scale + 200) + "px";
}

function initInteractiveZoom() {
    const viewport = document.querySelector('.full-viewport');
    if (!viewport) return;

    viewport.addEventListener('wheel', (e) => {
        if (!e.ctrlKey && !e.metaKey) return; 

        e.preventDefault();
        const delta = e.deltaY;
        const zoomSpeed = 0.001;
        
        // Capture mouse position for potentially centering zoom later
        appState.zoom.scale = Math.min(Math.max(0.1, appState.zoom.scale - delta * zoomSpeed), 3.0);
        applyZoom();
    }, { passive: false });

    // Panning is now primarily native via overflow:auto
    // Removing mousedown/mousemove logic to prevent conflicts
}

function openMatchupModal(matchup) {
    const modal = document.getElementById('matchup-modal');
    if (!modal) return;
    
    const teamA = appState.teams[matchup.team_a] || { name: matchup.team_a, seed: matchup.seed_a };
    const teamB = appState.teams[matchup.team_b] || { name: matchup.team_b, seed: matchup.seed_b };

    // Set probability from the matchup itself
    const vol = appState.volatility / 100;
    const probA = matchup.probability || 0.5;
    const blendedA = ((1.0 - vol) * probA) + (vol * 0.5);
    
    const probBadge = document.getElementById('modal-prob');
    if (probBadge) probBadge.textContent = `${(blendedA * 100).toFixed(0)}% Win Prob`;

    // Populate Modal Content
    const title = modal.querySelector('h2') || modal.querySelector('.modal-title');
    if (title) title.innerHTML = `<span style="color:var(--accent-gold)">${teamA.name}</span> vs <span style="color:var(--accent-gold)">${teamB.name}</span>`;
    
    // Why Analysis (Dynamic summary)
    const whyContent = document.getElementById('modal-why-content');
    if (whyContent) {
        const favorite = blendedA > 0.5 ? teamA : teamB;
        const underdog = blendedA > 0.5 ? teamB : teamA;
        const confText = favorite.is_power_conf ? "power conference powerhouse" : "disciplined contender";
        
        whyContent.innerHTML = `
            <p><strong>Scenario Intelligence:</strong> ${favorite.name} enters as the statistical favorite with a ${confText} profile. 
            The simulation indicates a ${ (Math.abs(blendedA - 0.5) * 200).toFixed(0) }% efficiency advantage in our multi-era regression model.</p>
            <p style="margin-top:0.5rem"><strong>Key Factor:</strong> Verticality and tempo control. ${teamA.name}'s efficiency at ${teamA.off_efficiency?.toFixed(1) || 'N/A'} vs ${teamB.name}'s ${teamB.off_efficiency?.toFixed(1) || 'N/A'} is the primary driver of this projection.</p>
        `;
    }

    // Metric Comparison Table
    const metricsTable = document.getElementById('modal-metrics-table');
    if (metricsTable) {
        const metrics = [
            { name: "Seed", a: teamA.seed || '?', b: teamB.seed || '?' },
            { name: "Offensive Eff", a: teamA.off_efficiency?.toFixed(1) || 'N/A', b: teamB.off_efficiency?.toFixed(1) || 'N/A' },
            { name: "Defensive Eff", a: teamA.def_efficiency?.toFixed(1) || 'N/A', b: teamB.def_efficiency?.toFixed(1) || 'N/A' },
            { name: "Adj Tempo", a: teamA.pace?.toFixed(1) || 'N/A', b: teamB.pace?.toFixed(1) || 'N/A' },
            { name: "Season Luck", a: (teamA.luck > 0 ? '+' : '') + (teamA.luck?.toFixed(3) || '0.000'), b: (teamB.luck > 0 ? '+' : '') + (teamB.luck?.toFixed(3) || '0.000') }
        ];
        
        metricsTable.innerHTML = metrics.map(m => `
            <div class="metric-row">
                <span class="metric-name">${m.name}</span>
                <span class="metric-val" style="color:${parseFloat(m.a) > parseFloat(m.b) ? 'var(--accent-gold)' : 'inherit'}">${m.a}</span>
                <span class="metric-val" style="color:${parseFloat(m.b) > parseFloat(m.a) ? 'var(--accent-gold)' : 'inherit'}">${m.b}</span>
            </div>
        `).join('');
    }
    
    modal.classList.add('active');
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

    initInteractiveZoom();

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

    // Matchup intelligence is now handled via event delegation inside createTeamLine or on cards
    // Removing redundant global listener that might block clicks

    const closeModal = document.getElementById('close-modal');
    if (closeModal) {
        closeModal.addEventListener('click', () => {
            document.getElementById('matchup-modal').classList.remove('active');
        });
    }

    document.querySelectorAll('input[type="range"][id^="weight-"], input[type="number"][id^="num-"]').forEach(input => {
        input.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            const id = e.target.id.replace('weight-', '').replace('num-', '');
            
            const slider = document.getElementById(`weight-${id}`);
            const numInput = document.getElementById(`num-${id}`);
            const label = document.getElementById(`val-${id}`);
            
            if (slider) slider.value = val;
            if (numInput) numInput.value = val;
            if (label) label.textContent = val;
            
            switchToCustom();
            debounceSim();
        });
    });

    const scratchBtn = document.getElementById('run-sim-scratch-btn');
    if (scratchBtn) scratchBtn.onclick = () => {
        appState.useLiveResults = false;
        runSimulation();
    };

    const liveBtn = document.getElementById('run-sim-live-btn');
    if (liveBtn) liveBtn.onclick = () => {
        appState.useLiveResults = true;
        runSimulation();
    };

    const syncBtn = document.getElementById('sync-live-btn');
    if (syncBtn) syncBtn.onclick = async () => {
        syncBtn.disabled = true;
        syncBtn.textContent = '🔄 Syncing...';
        try {
            const res = await fetch('/api/sync/live', { method: 'POST' });
            const data = await res.json();
            alert(data.message || 'Sync complete!');
            fetchTeams(appState.year);
            runSimulation();
        } catch (err) {
            console.error('Sync failed', err);
        } finally {
            syncBtn.disabled = false;
            syncBtn.textContent = '🔄 Sync';
        }
    };

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
