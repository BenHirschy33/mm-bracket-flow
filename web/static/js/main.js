console.log("[MM-Bracket-Flow] main.js loaded v1.2");

const appState = {
    mode: 'standard', // standard, average, perfect
    showSettings: false,
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
        efficiency_weight: 0.25,
        momentum_weight: 0.15,
        sos_weight: 0.4,
        intuition_factor_weight: 0.8,
        upset_delta_weight: 0.9,
        composure_index_weight: 0.7,
        three_point_dominance: 0.14,
        orb_weight: 0.38,
        ts_weight: 0.85,
        defense_premium: 8.9,
        rim_protection_weight: 0.12,
        defensive_grit_bias: 0.39,
        experience_weight: 10.5,
        cinderella_factor: 4.3,
        luck_regression_weight: 0.06
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

// Expose for browser agent and HTML onclick handlers early
window.appState = appState;

// Define global handlers early so they are available for HTML onclick
const zoomToRound = (round) => {
    const vH = window.innerHeight;
    const vW = window.innerWidth;
    if (round === 'all') {
        const scaleH = (vH - 250) / 1920;
        const scaleW = (vW - 100) / 3560;
        appState.zoom.scale = Math.min(scaleH, scaleW, 0.45);
        appState.zoom.x = (vW - (3560 * appState.zoom.scale)) / 2;
        appState.zoom.y = 10;
        appState.filter.region = 'all';
    } else {
        appState.zoom.scale = 0.8;
        appState.zoom.x = 20;
        appState.zoom.y = 20;
    }
    applyZoom();
};
window.zoomToRound = zoomToRound;

window.globalZoomOverview = function(round) {
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
        // The Quad Grid is 2840px wide x 1920px high
        // Calculate scale to fit within viewport
        const scaleH = (vH - 250) / 1920;
        const scaleW = (vW - 100) / 2840;
        // Centering calculation for 5-column layout (approx 3500px total)
        appState.zoom.scale = Math.min(scaleH, scaleW, 0.48); /* Slightly tighter fit */
        appState.zoom.x = (vW - (3560 * appState.zoom.scale)) / 2; 
        appState.zoom.y = 10; 
    } else {
        appState.zoom.scale = 0.8; 
        appState.zoom.x = 0;
        appState.zoom.y = 0;
    }

    applyZoom();
    
    const viewport = document.querySelector('.full-viewport');
    if (viewport) {
        viewport.scrollTo({ top: 0, left: 0, behavior: 'smooth' });
    }
}

window.globalResetUI = function() {
    console.trace('[Reset] Trace:');
    appState.locks = {
        regions: {},
        final_four: {},
        championship: {}
    };
    appState.currentData = null;
    
    // Clear the visual bracket
    renderMMBracket(); 

    // Also reset any active button states
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector('.tab-btn[data-mode="custom"]')?.classList.add('active');
    appState.mode = 'custom';
    
    const liveIndicator = document.getElementById('live-indicator');
    if (liveIndicator) liveIndicator.style.display = 'none';

    console.log('[Reset] Simulation state and locks cleared.');
}

window.globalResetOptimal = function() {
    const weights = appState.optimalWeights || {};
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
        const finalVal = val !== undefined ? val : 0;
        const slider = document.getElementById(id);
        const statName = id.replace('weight-', '');
        const numInput = document.getElementById('num-' + statName);
        const valLabel = document.getElementById('val-' + statName);

        if (slider) slider.value = finalVal;
        if (numInput) numInput.value = finalVal;
        if (valLabel) valLabel.textContent = finalVal;
    }
    
    appState.volatility = 0;
    const volSlider = document.getElementById('weight-volatility');
    if (volSlider) volSlider.value = 0;
    const volVal = document.getElementById('val-volatility');
    if (volVal) volVal.textContent = '0';

    runSimulation();
}

// --- Core Logic ---

function debounceSim() {
    if (appState.isApplyingPreset) return;
    clearTimeout(appState.simTimer);
    appState.simTimer = setTimeout(runSimulation, 400);
}

// Logic moved to window.resetToOptimal

function applyWeights(weights) {
    if (!weights) return;
    appState.isApplyingPreset = true; // Guard against slider event loops
    const mapping = {
        'weight-eff': weights.efficiency || weights.efficiency_weight,
        'weight-sos': weights.sos || weights.sos_weight,
        'weight-trb': weights.trb || weights.trb_weight,
        'weight-momentum': weights.momentum || weights.momentum_weight,
        'weight-def-premium': weights.defense_premium || weights.def_premium || weights.late_round_def_premium,
        'weight-three-point-dominance': weights.three_point_dominance,
        'weight-orb': weights.orb_weight || weights.orb,
        'weight-ts': weights.ts_weight || weights.ts,
        'weight-rim-protection': weights.rim_protection_weight || weights.rim_protection,
        'weight-defensive-grit-bias': weights.defensive_grit_bias,
        'weight-experience': weights.experience_weight || weights.experience,
        'weight-cinderella-factor': weights.cinderella_factor,
        'weight-luck-regression': weights.luck_regression_weight || weights.luck_regression
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
    setTimeout(() => { appState.isApplyingPreset = false; }, 300);
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
        if (!appState.locks[region]) appState.locks[region] = {};
        if (appState.locks[region][teamName]) {
            delete appState.locks[region][teamName];
        } else {
            appState.locks[region] = { [teamName]: true };
        }
    } else {
        if (!appState.locks.regions) appState.locks.regions = {};
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

function isLocked(region, round, team) {
    if (region === 'final_four') return !!appState.locks.final_four[team];
    if (region === 'championship') return !!appState.locks.championship[team];
    return !!appState.locks.regions[region]?.[round]?.[team];
}

async function renderMMBracket() {
    console.log("[MM-Bracket-Flow] Executing renderMMBracket");
    try {
        const response = await fetch(`/api/bracket/${appState.year}`);
        const data = await response.json();
        
        if (data.error) {
            console.error("Bracket load error:", data.error);
            return;
        }

        // Transform into a TBD-filled structure for initial view
        const initialData = {
            regions: {},
            final_four: null,
            championship: null
        };
        
        for (const [reg, matchups] of Object.entries(data.regions)) {
            initialData.regions[reg] = [
                { round: 1, matchups: matchups.map(m => ({ ...m, winner: null })) }
            ];
            // Add placeholder rounds for Round 2, 3, 4
            for (let r = 2; r <= 4; r++) {
                initialData.regions[reg].push({ 
                    round: r, 
                    matchups: Array(16 / Math.pow(2, r)).fill(null).map(() => ({ 
                        team_a: null, team_b: null, winner: null 
                    })) 
                });
            }
        }
        
        renderBracketWaterfall(initialData);
        // Default to Standard Overview zoom - use small delay to ensure rendering is complete
        setTimeout(() => {
            if (typeof zoomToRound === 'function') {
                zoomToRound('all');
            }
        }, 100);
    } catch (err) {
        console.error("Initial bracket load failed", err);
    }
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

        console.log('[Weights] Loaded MAX_AVG preset:', avgData.meta);
        console.log('[Weights] Loaded MAX_PERFECT preset:', champData.meta);
        
        // Populate sliders for initial mode (custom/avg)
        if (appState.mode === 'average') {
            applyWeights(appState.optimalWeights);
        }
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
        const useLive = (appState.mode === 'current');
        const response = await fetch(`/api/simulation/full`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                year: parseInt(appState.year),
                mode: appState.mode,
                volatility: appState.volatility / 100,
                weights: weights,
                locks: appState.locks,
                use_live_results: useLive
            })
        });
        const data = await response.json();
        appState.currentData = data;
        
        // Update Live Indicator
        const liveIndicator = document.getElementById('live-indicator');
        if (liveIndicator) {
            liveIndicator.style.display = useLive ? 'flex' : 'none';
        }
        
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
        let rounds = data.regions[regionName];
        if (!rounds) return;

        // Ensure rounds have the .round property attached for UI rendering
        if (Array.isArray(rounds)) {
            rounds = rounds.map((r, i) => r.round ? r : { round: i + 1, matchups: r.matchups || r });
        }

        const regContainer = document.createElement('div');
        regContainer.className = `region-container ${config.mirrored ? 'mirrored' : ''}`;
        regContainer.style.gridColumn = config.col;
        regContainer.style.gridRow = config.row;
        quadGrid.appendChild(regContainer);

        // Region Label
        const label = document.createElement('div');
        label.className = 'region-label-v2';
        label.style.pointerEvents = 'none';
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
            if (!col) return;
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
                
                const isA = (m.team_a === m.winner);
                const isActualA = isA && m.is_actual;
                const isActualB = !isA && m.is_actual;
                
                mCard.appendChild(createTeamLine(regionName, r.round, m.team_a, m.seed_a, isA, isA ? m.probability : null, isActualA));
                mCard.appendChild(createTeamLine(regionName, r.round, m.team_b, m.seed_b, !isA, !isA ? m.probability : null, isActualB));
            
            col.appendChild(mCard);
        });
    });
});

// Populate Center Stage (Final Four & Championship)
if (data.final_four) {
    const leftF4 = document.createElement('div');
    leftF4.className = 'ff-games-stack ff-left';
    const rightF4 = document.createElement('div');
    rightF4.className = 'ff-games-stack ff-right';
    
    // Create Championship centerpiece
    const champContainer = document.createElement('div');
    champContainer.className = 'hero-champ-container';

    // Order: Left FF -> Champ -> Right FF
    centerStage.appendChild(leftF4);
    centerStage.appendChild(champContainer);
    centerStage.appendChild(rightF4);

    data.final_four.forEach((m, idx) => {
        const mCard = document.createElement('div');
        mCard.className = `matchup-card ff-matchup`;
        mCard.style.width = '280px';
        
        const isA = (m.team_a === m.winner);
        const isActualA = isA && m.is_actual;
        const isActualB = !isA && m.is_actual;
        
        mCard.appendChild(createTeamLine('final_four', 5, m.team_a, m.seed_a, isA, isA ? m.probability : null, isActualA));
        mCard.appendChild(createTeamLine('final_four', 5, m.team_b, m.seed_b, !isA, !isA ? m.probability : null, isActualB));
        

        if (idx === 0) leftF4.appendChild(mCard); else rightF4.appendChild(mCard);
    });

    if (data.championship) {
        const m = data.championship;
        const mCard = document.createElement('div');
        mCard.className = 'matchup-card championship-box';
        mCard.style.width = '320px';
        
        const isA = (m.team_a === m.winner);
        const isActualA = isA && m.is_actual;
        const isActualB = !isA && m.is_actual;
        
        mCard.appendChild(createTeamLine('championship', 6, m.team_a, m.seed_a, isA, isA ? m.probability : null, isActualA));
        mCard.appendChild(createTeamLine('championship', 6, m.team_b, m.seed_b, !isA, !isA ? m.probability : null, isActualB));
        
        
        champContainer.appendChild(mCard);
    }
}
    
    if (appState.filter.region !== 'all') {
        zoomToRound('all');
    }
}

function createTeamLine(region, round, teamName, seed, isWinner, prob, isActual = false) {
    const line = document.createElement('div');
    const team = teamName || "TBD";
    const userLocked = isLocked(region, round, team);
    const lockedClass = (userLocked || isActual) ? 'locked' : '';
    line.className = `team-line ${isWinner ? 'winner' : ''} ${lockedClass} ${team === "TBD" ? 'tbd' : ''}`;
    
    const cleanName = team.replace(/^\d+\s+/, '');
    line.innerHTML = `
        <span class="team-content">
            <span class="seed">${seed || '?'}</span>
            <span class="name">${cleanName}</span>
            ${team !== "TBD" ? `<span class="lock-icon ${lockedClass ? 'active' : ''} ${isActual ? 'is-actual' : ''}" title="${isActual ? 'Actual Tournament Result' : 'Lock team to advance'}">${isActual ? '🔒' : '🔒'}</span>` : ''}
        </span>
        ${isWinner && prob ? `<span class="prob-tag">${(parseFloat(prob) * 100).toFixed(0)}%</span>` : ''}
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

// Navigation & UX logic moved to top for global availability

// --- Simulation Control ---

// Reset logic moved to top for global availability

function applyZoom() {
    const container = document.getElementById('bracket-container');
    const proxy = document.getElementById('zoom-container');
    const viewport = document.querySelector('.full-viewport');
    if (!container || !proxy || !viewport) return;
    
    // Clamp movement 
    const vW = window.innerWidth;
    const vH = window.innerHeight;
    const gridW = 3560 * appState.zoom.scale; /* Updated for gaps */
    const gridH = 1920 * appState.zoom.scale;
    
    // Minimal bleed for tight focus
    const margin = 50; 
    const minX = vW - gridW - margin;
    const maxX = margin;
    const minY = vH - gridH - margin;
    const maxY = margin;
    
    appState.zoom.x = Math.min(Math.max(appState.zoom.x, minX), maxX);
    appState.zoom.y = Math.min(Math.max(appState.zoom.y, minY), maxY);

    // Scale the visual
    container.style.transform = `translate(${appState.zoom.x}px, ${appState.zoom.y}px) scale(${appState.zoom.scale})`;
    
    // Precise bounds 
    proxy.style.width = (3560 * appState.zoom.scale + 100) + "px";
    proxy.style.height = (1920 * appState.zoom.scale + 100) + "px";
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
    if (probBadge) probBadge.textContent = `${(blendedA * 100).toFixed(2)}% Win Prob`;

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
            The simulation indicates a ${ (Math.abs(blendedA - 0.5) * 200).toFixed(2) }% efficiency advantage in our multi-era regression model.</p>
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
            renderMMBracket(); 
        });
    }

    renderMMBracket(); 

    initInteractiveZoom();
    
    document.getElementById('run-simulation-btn')?.addEventListener('click', () => {
        const btn = document.getElementById('run-simulation-btn');
        const originalHtml = btn.innerHTML;
        btn.innerHTML = `<span style="display:inline-block; animation: spin 1s linear infinite; margin-right:8px;">↻</span>SIMULATING...`;
        btn.style.pointerEvents = 'none';
        
        runSimulation().finally(() => {
            btn.innerHTML = originalHtml;
            btn.style.pointerEvents = 'auto';
        });
    });

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.mode;
            if (!mode) return;
            
            // Update app state and UI
            appState.mode = mode;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            if (mode === 'settings') {
                const panel = document.getElementById('settings-panel');
                if (panel) panel.classList.add('active');
                return;
            }
            
            // For other modes, ensure settings panel is closed
            document.getElementById('settings-panel')?.classList.remove('active');

            if (appState.mode === 'standard') {
                document.body.classList.remove('mode-sandbox');
            } else {
                 // Average/Perfect modes can also show sandbox if they aren't "Live"
                 document.body.classList.remove('mode-sandbox');
            }
            
            if (appState.mode === 'average') applyWeights(appState.optimalWeights);
            else if (appState.mode === 'perfect') applyWeights(appState.perfectWeights);
            
            renderMMBracket();
        });
    });

    // Consolidated Sync Button
    const btnSyncLive = document.getElementById('btn-sync-current');
    if (btnSyncLive) btnSyncLive.addEventListener('click', () => syncStartRound('live'));

    const btnCloseSettings = document.getElementById('close-settings-btn');
    const panelSettings = document.getElementById('settings-panel');

    if (btnCloseSettings) {
        btnCloseSettings.addEventListener('click', () => {
            panelSettings.style.display = 'none';
        });
    }

    // Toggle Panels
    const panels = {
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

    // Initial data load
    initWeights();
    fetchTeams(appState.year);
});

async function syncStartRound(round) {
    let btnId = 'btn-sync-current';
    if (round !== 'live') btnId = `btn-lock-${round}`;
    const btn = document.getElementById(btnId);
    const originalText = btn ? btn.innerHTML : '';
    
    if (btn) {
        btn.innerHTML = `<span style="display:inline-block; animation: spin 1s linear infinite; margin-right: 8px;">↻</span>${btn.innerText}`;
        btn.style.pointerEvents = 'none';
        btn.style.opacity = '0.7';
    }
    
    // Artificial delay to ensure spinner renders on localhost
    await new Promise(r => setTimeout(r, 500));
    
    if (round === 'live') {
        try {
            const response = await fetch(`/api/sync/live?year=${appState.year}`, { method: 'POST' });
            const data = await response.json();
            alert(data.message || data.error);
            appState.mode = 'standard';
            await fetchTeams(appState.year);
            renderMMBracket(); 
        } catch (err) {
            console.error(err);
            alert("Failed to sync live bracket.");
        } finally {
            if (btn) {
                btn.innerHTML = originalText;
                btn.style.pointerEvents = 'auto';
                btn.style.opacity = '1';
            }
        }
        return;
    }

    try {
        const response = await fetch(`/api/sync/start_round?round=${round}&year=${appState.year}`, { 
            method: 'POST' 
        });
        const result = await response.json();
        if (response.ok) {
            alert(`Success: ${result.message}`);
            await fetchTeams(appState.year);
            renderMMBracket();
        } else {
            alert(`Error: ${result.error}`);
        }
    } catch (err) {
        console.error("Sync error:", err);
        alert("Failed to start round synchronization");
    } finally {
        if (btn) {
            btn.innerHTML = originalText;
            btn.style.pointerEvents = 'auto';
            btn.style.opacity = '1';
        }
    }
}

async function syncLiveBracket() {
    const btn = document.getElementById('sync-live-btn');
    if (btn) btn.classList.add('spinning');
    
    try {
        const response = await fetch(`/api/sync/live?year=${appState.year}`, { method: 'POST' });
        if (response.ok) {
            appState.mode = 'standard';
            await renderMMBracket();
            alert("Bracket synced with live data.");
        }
    } catch (err) {
        console.error("Sync failed:", err);
    } finally {
        if (btn) btn.classList.remove('spinning');
    }
}

// Expose for browser agent and HTML onclick handlers
window.appState = appState;
window.globalResetSimulation = () => {
    appState.locks = { regions: {}, final_four: {}, championship: {} };
    renderMMBracket();
};

// Backdrop dismissal for modals
document.addEventListener('click', (e) => {
    const overlay = document.querySelector('.modal-overlay');
    const settings = document.getElementById('settings-panel');
    if (e.target === overlay) {
        overlay.style.display = 'none';
        overlay.classList.remove('active');
    }
    if (e.target === settings) {
        settings.style.display = 'none';
        settings.classList.remove('active');
    }
});
