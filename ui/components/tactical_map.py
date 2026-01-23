# ui/components/tactical_map.py
# -*- coding: utf-8 -*-
"""
Tactical Map Component (Leaflet + Milsymbol)
Common Operational Picture (COP)를 시각화하는 커스텀 Streamlit 컴포넌트
"""
import streamlit as st
import streamlit.components.v1 as components
import json
import os
from pathlib import Path

def render_tactical_map(coa_recommendations, threat_geojson, coa_geojson, reasoning_geojson=None, height=600, situation_summary=None):
    """
    Tactical Situation Map을 렌더링함.
    """
    # 리소스 경로 설정 (milsymbol.js 등)
    static_dir = Path(__file__).parent.parent / "static"
    milsymbol_path = static_dir / "milsymbol.js"
    
    use_local_milsymbol = False
    milsymbol_js_content = ""
    
    if milsymbol_path.exists():
        try:
            with open(milsymbol_path, "r", encoding="utf-8") as f:
                milsymbol_js_content = f.read()
            use_local_milsymbol = True
        except Exception:
            pass

    # Milsymbol 로딩 전략
    if use_local_milsymbol:
        milsymbol_script_tag = f"<script>{milsymbol_js_content}</script>"
    else:
        milsymbol_script_tag = '<script src="https://unpkg.com/milsymbol@2.0.0/dist/milsymbol.js"></script>'

    # 데이터 직렬화
    data_props = {
        "coaRecommendations": coa_recommendations,
        "threatData": threat_geojson,
        "coaData": coa_geojson,
        "reasoningData": reasoning_geojson,
        "situationSummary": situation_summary
    }
    json_props = json.dumps(data_props, ensure_ascii=False)

    # 타일 및 라이브러리 리소스
    resources = {
        "leaflet_css": "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
        "leaflet_js": "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
        "tile_sat": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "tile_dark": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
    }

    # Use a non-f-string template to avoid brace issues
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <link rel="stylesheet" href="__LEAFLET_CSS__" />
        <script src="__LEAFLET_JS__"></script>
        __MILSYMBOL_SCRIPT__
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
        <style>
            body { margin: 0; padding: 0; background-color: #1e1e1e; font-family: 'Inter', sans-serif; overflow: hidden; }
            #map-container { width: 100%; height: __HEIGHT__px; position: relative; border-radius: 8px; overflow: hidden; }
            #map { width: 100%; height: 100%; z-index: 1; }

            /* UI Panels */
            .overlay-panel {
                position: absolute;
                z-index: 2000; /* Increased z-index to stay above everything */
                background: rgba(13, 17, 23, 0.85);
                backdrop-filter: blur(8px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: #e6edf3;
                box-shadow: 0 4px 15px rgba(0,0,0,0.5);
                transition: all 0.3s ease;
            }

            .top-left-panel { top: 20px; left: 20px; width: 300px; max-height: 80%; overflow-y: auto; }
            .top-right-panel { top: 20px; right: 20px; width: 320px; max-height: 80%; overflow-y: auto; }
            .bottom-panel { bottom: 20px; left: 50%; transform: translateX(-50%); width: 60%; padding: 10px; }
            
            .collapsed { width: 40px !important; height: 40px !important; overflow: hidden !important; padding: 0 !important; }
            .collapsed * { display: none !important; }
            
            /* ... (skip middle items) ... */

            /* STATUS OVERLAY REMOVED PER USER REQUEST */
            
            /* Legend */
            .legend-panel { 
                position: absolute; bottom: 80px; left: 20px; 
                background: rgba(13,17,23,0.95); 
                padding: 12px; 
                border-radius: 6px; 
                font-size: 12px; 
                z-index: 1500;
                color: #e6edf3;
                border: 1px solid rgba(255,255,255,0.2);
            }
            .legend-item { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; color: #e6edf3; }
            .legend-icon { width: 16px; height: 16px; border-radius: 50%; border: 2px solid; }
            .legend-line { width: 26px; height: 0; border-top-width: 3px; border-top-style: solid; }
            
            .collapsed { width: 40px !important; height: 40px !important; overflow: hidden !important; padding: 0 !important; }
            .collapsed * { display: none !important; }
            
            .panel-header {
                padding: 12px 15px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                display: flex;
                align-items: center;
                gap: 10px;
                cursor: default;
            }

            .panel-header h3 { margin: 0; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; flex-grow: 1; }
            .sidebar-toggle { background: none; border: none; color: #888; cursor: pointer; padding: 5px; }
            .sidebar-toggle:hover { color: #fff; }

            .panel-content { padding: 15px; }

            /* Stats and Lists */
            .summary-section { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }
            .stat-box { background: rgba(255,255,255,0.05); padding: 10px; border-radius: 4px; border-left: 3px solid #58a6ff; }
            .stat-box .label { display: block; font-size: 11px; color: #8b949e; margin-bottom: 4px; }
            .stat-box .value { display: block; font-size: 18px; font-weight: 600; }
            .stat-box.red { border-left-color: #f85149; }
            
            .list-section h4 { font-size: 12px; color: #8b949e; margin: 0 0 10px 0; }
            .coa-list { display: flex; flex-direction: column; gap: 8px; }
            .coa-item {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 6px;
                padding: 10px;
                display: flex;
                align-items: center;
                gap: 12px;
                cursor: pointer;
                transition: all 0.2s;
            }
            .coa-item:hover { background: rgba(56, 139, 253, 0.1); border-color: #388bfd; }
            .coa-item.active { background: rgba(56, 139, 253, 0.2); border-color: #388bfd; box-shadow: 0 0 10px rgba(56, 139, 253, 0.3); }
            
            .coa-score { width: 45px; height: 45px; border-radius: 50%; border: 2px solid #388bfd; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; }
            .coa-info { flex-grow: 1; }
            .coa-name { display: block; font-size: 13px; font-weight: 600; margin-bottom: 2px; }
            .coa-type { font-size: 11px; color: #8b949e; }

            /* Reasoning Panel */
            .reasoning-item { margin-bottom: 15px; }
            .reasoning-item h5 { font-size: 12px; color: #388bfd; margin: 0 0 5px 0; }
            .reasoning-item p { font-size: 12px; line-height: 1.5; color: #d0d7de; margin: 0; }

            /* Legend */
            .legend-panel { position: absolute; bottom: 80px; left: 20px; background: rgba(13,17,23,0.8); padding: 10px; border-radius: 6px; font-size: 11px; }
            .legend-item { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }
            .legend-color { width: 12px; height: 12px; border-radius: 2px; }



            /* Animation Controls */
            .timeline-container { display: flex; align-items: center; gap: 15px; }
            .play-btn { background: #388bfd; border: none; color: white; border-radius: 4px; padding: 5px 15px; cursor: pointer; }
            #time-slider { flex-grow: 1; accent-color: #388bfd; }
            .time-display { font-family: monospace; font-size: 12px; width: 40px; }

            /* Reopen buttons */
            .reopen-btn {
                position: absolute; z-index: 2001; /* Above panels (2000) */
                background: #388bfd; color: white; width: 30px; height: 30px;
                border: none; border-radius: 4px; cursor: pointer;
                display: none; align-items: center; justify-content: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.5);
            }
            .reopen-left { top: 20px; left: 20px; }
            .reopen-right { top: 20px; right: 20px; }
            .reopen-btn.visible { display: flex !important; }

            /* Marker labels */
            .marker-label {
                background: none !important; border: none !important; box-shadow: none !important;
                color: white; font-weight: 600; font-size: 11px; text-shadow: 0 0 3px black;
                white-space: nowrap;
            }
            .red-label { color: #ff4d4d; }
            .blue-label { color: #58a6ff; }

            /* Map styles override */
            .leaflet-container { background: #1e1e1e !important; }
            
            /* High threat animation */
            @keyframes pulse-red {
                0% { transform: scale(1); filter: drop-shadow(0 0 2px #ff4d4d); }
                50% { transform: scale(1.1); filter: drop-shadow(0 0 10px #ff4d4d); }
                100% { transform: scale(1); filter: drop-shadow(0 0 2px #ff4d4d); }
            }
            .high-threat-icon { animation: pulse-red 2s infinite; }
            
            /* Floating controls */
            .map-controls { position: absolute; top: 20px; left: 50%; transform: translateX(-50%); z-index: 1000; display: flex; gap: 10px; }
            .control-btn { 
                background: rgba(13,17,23,0.8); border: 1px solid rgba(255,255,255,0.1); 
                color: #e6edf3; padding: 6px 12px; border-radius: 20px; font-size: 12px;
                cursor: pointer; backdrop-filter: blur(4px);
            }
            .control-btn:hover { background: rgba(56,139,253,0.2); border-color: #388bfd; }
            .control-btn.active { background: #388bfd; color: white; }
        </style>
    </head>
    <body>
        <div id="map-container">
            <div id="map"></div>
            
            <!-- Map Controls -->
            <div class="map-controls">
                <button id="btn-ghost-mode" class="control-btn">👻 Ghost Mode</button>
                <button id="btn-satellite" class="control-btn">🛰️ Satellite</button>
            </div>

            <!-- Left Sidebar: Analysis Summary -->
            <button id="reopen-left" class="reopen-btn reopen-left" onclick="toggleSidebar('left')" title="패널 열기">📊</button>
            <div id="left-sidebar" class="overlay-panel top-left-panel">
                <div class="panel-header">
                    <span class="icon">📊</span>
                    <h3>분석 요약</h3>
                    <button class="sidebar-toggle" onclick="toggleSidebar('left')" title="패널 닫기">✕</button>
                </div>
                <div id="summary-content"></div>
            </div>

            <!-- Right Sidebar: Reasoning Details -->
            <button id="reopen-right" class="reopen-btn reopen-right" onclick="toggleSidebar('right')" title="패널 열기">🧠</button>
            <div id="right-sidebar" class="overlay-panel top-right-panel">
                <div class="panel-header">
                    <span class="icon">🧠</span>
                    <h3>추론 근거</h3>
                    <button class="sidebar-toggle" onclick="toggleSidebar('right')" title="패널 닫기">✕</button>
                </div>
                <div id="reasoning-content"></div>
            </div>

            <!-- Legend -->
            <div class="legend-panel">
                <div class="legend-item">
                    <div class="legend-icon" style="background:#ff4d4d; border-color:#ff0000;"></div>
                    <span>적 위협 (Enemy)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-icon" style="background:#388bfd; border-color:#0056b3;"></div>
                    <span>아군 (Friendly)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-line" style="border-color:#ff4d4d; border-top-style:dashed; opacity:0.3;"></div>
                    <span>위협 영향권</span>
                </div>
                <div class="legend-item">
                    <div class="legend-line" style="border-color:#388bfd; border-top-width:4px;"></div>
                    <span>주 축선 (Main Axis)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-line" style="border-color:#999; border-top-style:dashed;"></div>
                    <span>보조 축선 (Alt Axis)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-line" style="border-color:#f39c12; border-top-style:dashed; border-top-width:2px;"></div>
                    <span>AI 추론경로</span>
                </div>
            </div>



            <!-- Timeline/Bottom Panel -->
            <div class="overlay-panel bottom-panel">
                <div class="timeline-container">
                    <div class="time-display" id="time-display">00:00</div>
                    <input type="range" id="time-slider" min="0" max="100" value="0">
                    <button class="play-btn" id="play-btn">▶ PLAY</button>
                </div>
            </div>
            
        </div>

        <script>
            // --- App State & Data ---
            const initialProps = __JSON_PROPS__;
            const tileSatUrl = "__TILE_SAT__";
            const tileDarkUrl = "__TILE_DARK__";

            const state = {
                selectedCOA: initialProps.coaRecommendations && initialProps.coaRecommendations.length > 0 ? initialProps.coaRecommendations[0] : null,
                ghostMode: false, // [FIX] Default to False to focus on selected COA
                time: 0,
                isPlaying: false,
                map: null,
                satelliteLayer: null,
                darkLayer: null,
                layerRefs: {
                    threats: null,
                    threatCircles: null,
                    blueUnits: null,
                    arrows: null,
                    reasoning: null,
                    risk: null,
                    tacticalGraphics: null
                }
            };

            // --- Sidebar Toggle Logic ---
            function toggleSidebar(side) {
                try {
                    const sidebar = document.getElementById(side + '-sidebar');
                    const reopenTab = document.getElementById('reopen-' + side);
                    if (!sidebar || !reopenTab) return;
                    
                    sidebar.classList.toggle('collapsed');
                    const isCollapsed = sidebar.classList.contains('collapsed');
                    
                    try {
                        localStorage.setItem('cop_sidebar_' + side + '_v2', isCollapsed ? 'collapsed' : 'open');
                    } catch(e) {}
                    
                    if (isCollapsed) {
                        reopenTab.classList.add('visible');
                    } else {
                        reopenTab.classList.remove('visible');
                    }
                } catch(e) { console.error("toggleSidebar failed", e); }
            }
            
            function restoreSidebarStates() {
                try {
                    // Force Open to resolve visibility issues
                    let leftState = 'open';
                    let rightState = 'open';
                    
                    const leftSidebar = document.getElementById('left-sidebar');
                    const rightSidebar = document.getElementById('right-sidebar');
                    const reopenLeft = document.getElementById('reopen-left');
                    const reopenRight = document.getElementById('reopen-right');
                    
                    // Reset classes
                    leftSidebar.classList.remove('collapsed');
                    rightSidebar.classList.remove('collapsed');
                    reopenLeft.classList.remove('visible');
                    reopenRight.classList.remove('visible');
                    
                } catch(e) { console.error("restoreSidebarStates failed", e); }
            }

            // --- Initialization ---
            document.addEventListener('DOMContentLoaded', () => {
                console.log("[COP] DOMContentLoaded");
                restoreSidebarStates();
                initMap();
                initUI();
                updateUI();
            });

            function initMap() {
                if (typeof L === 'undefined') {
                    console.error("[COP] Leaflet not found");
                    return;
                }
                try {
                    const map = L.map('map', {
                        center: [36.5, 127.5],
                        zoom: 7,
                        zoomControl: false,
                        attributionControl: false,
                        minZoom: 5
                    });

                    L.control.zoom({ position: 'bottomright' }).addTo(map);

                    // Create both layers but only add dark by default
                    const darkLayer = L.tileLayer(tileDarkUrl);
                    const satelliteLayer = L.tileLayer(tileSatUrl);
                    
                    darkLayer.addTo(map);
                    
                    state.map = map;
                    state.darkLayer = darkLayer;
                    state.satelliteLayer = satelliteLayer;

                    state.layerRefs.threats = L.layerGroup().addTo(map);
                    state.layerRefs.threatCircles = L.layerGroup().addTo(map);
                    state.layerRefs.blueUnits = L.layerGroup().addTo(map);
                    state.layerRefs.arrows = L.layerGroup().addTo(map);
                    state.layerRefs.reasoning = L.layerGroup().addTo(map);
                    state.layerRefs.risk = L.layerGroup().addTo(map);
                    state.layerRefs.tacticalGraphics = L.layerGroup().addTo(map);

                    setTimeout(() => map.invalidateSize(), 500);
                } catch(e) { console.error("initMap failed", e); }
            }

            function initUI() {
                const slider = document.getElementById('time-slider');
                const playBtn = document.getElementById('play-btn');
                const timeDisplay = document.getElementById('time-display');

                if (slider && timeDisplay) {
                    slider.addEventListener('input', (e) => {
                        state.time = e.target.value;
                        timeDisplay.innerText = `00:${String(state.time).padStart(2,'0')}`;
                        renderMapLayers();
                    });
                }

                if (playBtn) {
                    playBtn.addEventListener('click', () => {
                        state.isPlaying = !state.isPlaying;
                        playBtn.innerText = state.isPlaying ? '■ STOP' : '▶ PLAY';
                    });
                }
                
                const ghostBtn = document.getElementById('btn-ghost-mode');
                if (ghostBtn) {
                    ghostBtn.addEventListener('click', function() {
                        state.ghostMode = !state.ghostMode;
                        this.classList.toggle('active', state.ghostMode);
                        renderMapLayers();
                    });
                }
                
                // Satellite button toggle
                const satBtn = document.getElementById('btn-satellite');
                if (satBtn) {
                    satBtn.addEventListener('click', function() {
                        if (!state.map || !state.satelliteLayer || !state.darkLayer) return;
                        
                        const isSatellite = state.map.hasLayer(state.satelliteLayer);
                        if (isSatellite) {
                            state.map.removeLayer(state.satelliteLayer);
                            state.map.addLayer(state.darkLayer);
                            this.classList.remove('active');
                        } else {
                            state.map.removeLayer(state.darkLayer);
                            state.map.addLayer(state.satelliteLayer);
                            this.classList.add('active');
                        }
                    });
                }
            }

            function updateUI() {
                try {
                    // Status Overlay removed per request
                    renderSituationSidebar();
                    renderReasoningSidebar();
                    renderMapLayers();
                } catch(e) { console.error("updateUI failed", e); }
            }

            function renderSituationSidebar() {
                const container = document.getElementById('summary-content');
                if (!container) return;
                
                const recs = initialProps.coaRecommendations || [];
                // [FIX] 위협식별 숫자는 실제 식별된 위협상황만 카운트 (배경 적군 제외)
                const allThreats = (initialProps.threatData && initialProps.threatData.features) ? initialProps.threatData.features : [];
                const threatsCount = allThreats.filter(f => f.properties && f.properties.is_identified_threat === true).length;
                const coasCount = recs.length;

                let html = `
                    <div class="panel-content">
                        <div class="summary-section">
                            <div class="stat-box">
                                <span class="label">식별 위협</span>
                                <span class="value red">${threatsCount}</span>
                            </div>
                            <div class="stat-box blue">
                                <span class="label">가용 방책</span>
                                <span class="value blue">${coasCount}</span>
                            </div>
                        </div>
                        <div class="list-section">
                            <h4>추천 방책 (COA)</h4>
                            <div class="coa-list">
                `;

                recs.forEach((coa, idx) => {
                    // [FIX] ID 매칭 로직 개선
                    const selectedId = state.selectedCOA ? 
                        (state.selectedCOA.coa_id || state.selectedCOA.COA_ID || state.selectedCOA.id || "").toString().trim() : null;
                    const coaId = (coa.coa_id || coa.COA_ID || coa.id || "").toString().trim();
                    const activeClass = selectedId && coaId && 
                        (selectedId.toLowerCase() === coaId.toLowerCase() || selectedId === coaId) ? 'active' : '';
                    html += `
                        <div class="coa-item ${activeClass}" onclick="selectCOA(${idx})">
                            <div class="coa-score">${(coa.score * 100).toFixed(1)}%</div>
                            <div class="coa-info">
                                <div class="coa-name">${coa.coa_name || "Unknown"}</div>
                                <div class="coa-type">${coa.coa_type || "N/A"}</div>
                            </div>
                        </div>
                    `;
                });

                if (coasCount === 0) {
                    html += '<p style="font-size:12px; color:#888; text-align:center;">표시할 방책이 없습니다.</p>';
                }

                html += `</div></div></div>`;
                container.innerHTML = html;
            }

            function renderReasoningSidebar() {
                const container = document.getElementById('reasoning-content');
                if (!container) return;
                
                if (!state.selectedCOA) {
                    container.innerHTML = '<div class="panel-content"><p style="font-size:12px; color:#888;">방책을 선택하면 추론 근거가 표시됩니다.</p></div>';
                    return;
                }

                const coa = state.selectedCOA;
                const r = coa.reasoning || {};

                container.innerHTML = `
                    <div class="panel-content">
                        <div class="reasoning-item">
                            <h5>상황 판단</h5>
                            <p>${r.situation_assessment || coa.description || "정보 없음"}</p>
                        </div>
                        <div class="reasoning-item">
                            <h5>선정 사유</h5>
                            <p>${r.justification || coa.reason || "정보 없음"}</p>
                        </div>
                        <div class="reasoning-item">
                            <h5>기대 효과</h5>
                            <p>${coa.expected_effects || "정보 없음"}</p>
                        </div>
                    </div>
                `;
            }

            function selectCOA(idx) {
                state.selectedCOA = initialProps.coaRecommendations[idx];
                updateUI();
            }

            // --- Rendering Map Layers ---
            function renderMapLayers() {
                if (!state.map) return;
                const refs = state.layerRefs;
                const currentCOA = state.selectedCOA;

                Object.values(refs).forEach(layer => layer && layer.clearLayers());

                // 1. Threats
                const threats = initialProps.threatData;
                if (threats && threats.features) {
                    threats.features.forEach(f => {
                        const latlng = [f.geometry.coordinates[1], f.geometry.coordinates[0]];
                        const props = f.properties;
                        
                        // [MOD] Highlight selected threat
                        const isSelected = props.selected === true;
                        // [FIX] 적부대 시각화 개선 - 모든 적부대가 명확히 보이도록 투명도 조정
                        const opacity = isSelected ? 1.0 : 0.7; // 배경 적부대도 더 잘 보이도록 (0.4 -> 0.7)
                        const extraClass = isSelected ? "high-threat-icon" : "";
                        
                        const icon = createMilsymbolIcon(props.sidc || "SHGPE-----H----", props, 34, extraClass);
                        
                        // [FIX] 적부대 마커에 더 많은 정보 표시
                        const threatName = props.name || props.위협명 || props.label || "적 부대";
                        const threatType = props.threat_type || props.위협유형 || "Unknown";
                        const threatLevel = props.threat_level || props.위협수준 || "N/A";
                        
                        L.marker(latlng, { icon: icon, opacity: opacity, zIndexOffset: isSelected ? 1000 : 0 })
                            .bindTooltip(`${threatName} (${threatType})`, { 
                                permanent: isSelected, // Always show label for selected
                                direction: "top", 
                                className: isSelected ? "marker-label red-label" : "marker-label",
                                opacity: opacity
                            })
                            .bindPopup(createPopupContent(props, 'RED'))
                            .addTo(refs.threats);
                            
                        // [MOD] Auto-center on selected threat if not already moved by user
                        if (isSelected && state.map) {
                            // Only center initially or if needed. 
                            // Using a flag to prevent constant re-centering if user drags map could be added,
                            // but for now, ensuring visibility is key.
                            console.log("[COP] Centering on selected threat:", props.name, latlng);
                            state.map.setView(latlng, 10, { animate: true });
                        }
                            
                        if (props.threat_radius) {
                            L.circle(latlng, { 
                                radius: props.threat_radius, 
                                color: '#ff4d4d', 
                                fillOpacity: isSelected ? 0.1 : 0.05, 
                                weight: isSelected ? 1 : 0.5, 
                                dashArray: '5, 5' 
                            })
                            .bindTooltip(`위협 영향권: ${(props.threat_radius/1000).toFixed(1)}km`, { 
                                permanent: false, 
                                className: "marker-label red-label" 
                            })
                            .addTo(refs.threatCircles);
                        }
                    });
                }

                // 2. COA Data
                const coaData = initialProps.coaData;
                console.log("[COP] Rendering COA Data:", coaData);
                console.log("[COP] Current Selected COA:", currentCOA);

                if (coaData && coaData.features) {
                    console.log(`[COP] Found ${coaData.features.length} features in COA Data`);
                    coaData.features.forEach(f => {
                        const props = f.properties;
                        // [FIX] 모든 가능한 ID 필드 확인 및 정규화
                        const featureCOAId = (props.coa_id || props.COA_ID || props.id || "").toString().trim();
                        const selectedCOAId = currentCOA ? 
                            (currentCOA.coa_id || currentCOA.COA_ID || currentCOA.id || "").toString().trim() : null;
                        // [FIX] 문자열 비교 개선 - 대소문자 무시 및 공백 제거
                        const isCurrent = selectedCOAId && featureCOAId && 
                            (featureCOAId.toLowerCase() === selectedCOAId.toLowerCase() || 
                             featureCOAId === selectedCOAId);
                        
                        console.log(`[COP] Feature ${props.name} (COA: ${featureCOAId}) - Selected: ${selectedCOAId} - IsCurrent: ${isCurrent} - GhostMode: ${state.ghostMode}`);

                        // [FIX] Point 타입만 Ghost Mode 조건 적용, LineString(축선)은 항상 표시
                        if (f.geometry.type === "Point" && !isCurrent && !state.ghostMode) return;
                        const opacity = isCurrent ? 0.9 : 0.2;

                        if (f.geometry.type === "Point") {
                            const latlng = [f.geometry.coordinates[1], f.geometry.coordinates[0]];
                            L.marker(latlng, { icon: createMilsymbolIcon(props.sidc || "SFGPE-----H----", props, 34), opacity: opacity })
                                .bindTooltip(props.name, { className: "marker-label blue-label", opacity: opacity })
                                .bindPopup(createPopupContent(props, 'BLUE'))
                                .addTo(refs.blueUnits);
                        } else if (f.geometry.type === "LineString") {
                            const latlngs = f.geometry.coordinates.map(c => [c[1], c[0]]);
                            
                            // Determine axis type from properties
                            let axisType = "기동축선";
                            const axisInfo = props.axis_type || props.type || "";
                            
                            if (axisInfo.toLowerCase().includes("main") || axisInfo.includes("주축")) {
                                axisType = "주축선";
                            } else if (axisInfo.toLowerCase().includes("secondary") || axisInfo.includes("보조")) {
                                axisType = "보조축선";
                            } else if (axisInfo.toLowerCase().includes("reserve") || axisInfo.includes("예비")) {
                                axisType = "예비축선";
                            }
                            
                            // [FIX] ID 매칭 로직 재사용 (위와 동일)
                            const featureCOAIdForAxis = (props.coa_id || props.COA_ID || props.id || "").toString().trim();
                            const selectedCOAIdForAxis = currentCOA ? 
                                (currentCOA.coa_id || currentCOA.COA_ID || currentCOA.id || "").toString().trim() : null;
                            const isCurrent = selectedCOAIdForAxis && featureCOAIdForAxis && 
                                (featureCOAIdForAxis.toLowerCase() === selectedCOAIdForAxis.toLowerCase() || 
                                 featureCOAIdForAxis === selectedCOAIdForAxis);
                            const axisLabel = isCurrent ? `주 ${axisType}` : `보조 ${axisType}`;
                            const coaName = props.coa_name || (currentCOA ? currentCOA.coa_name : null) || "방책";
                            
                            L.polyline(latlngs, { 
                                color: isCurrent ? '#388bfd' : '#999', 
                                weight: isCurrent ? 6 : 3, 
                                dashArray: isCurrent ? null : '10,10', 
                                opacity: opacity 
                            })
                            .bindTooltip(`${axisLabel} (${coaName})`, {
                                permanent: false,
                                className: "marker-label blue-label"
                            })
                            .addTo(refs.arrows);
                        }
                    });
                }

                // 3. Reasoning Data
                if (initialProps.reasoningData && initialProps.reasoningData.features) {
                    console.log(`[COP] Found ${initialProps.reasoningData.features.length} features in Reasoning Data`);
                    initialProps.reasoningData.features.forEach(f => {
                        const props = f.properties;
                        // [FIX] ID 매칭 로직 개선
                        const featureCOAId = (props.coa_id || props.COA_ID || props.id || "").toString().trim();
                        const selectedCOAId = currentCOA ? 
                            (currentCOA.coa_id || currentCOA.COA_ID || currentCOA.id || "").toString().trim() : null;
                        
                        console.log(`[COP] Reasoning Feature - COA: ${featureCOAId}, Selected: ${selectedCOAId}, Type: ${f.geometry.type}`);
                        
                        // [FIX] ID가 없거나 선택된 COA가 없으면 모든 추론경로 표시, ID가 있으면 매칭된 것만 표시
                        const shouldShow = !featureCOAId || !selectedCOAId || 
                            featureCOAId.toLowerCase() === selectedCOAId.toLowerCase() || 
                            featureCOAId === selectedCOAId;
                        
                        if (!shouldShow) {
                            console.log(`[COP] Reasoning path skipped - ID mismatch: ${featureCOAId} !== ${selectedCOAId}`);
                            return;
                        }

                        if (f.geometry.type === "LineString") {
                            const latlngs = f.geometry.coordinates.map(c => [c[1], c[0]]);
                            console.log(`[COP] Rendering reasoning path with ${latlngs.length} points`);
                            L.polyline(latlngs, { 
                                color: '#f39c12', 
                                weight: 2, 
                                dashArray: '5,5', 
                                opacity: 0.8 
                            })
                            .bindTooltip(`AI 추론경로: ${props.description || 'Reasoning Trace'}`, {
                                permanent: false,
                                className: "marker-label",
                                style: "color: #f39c12;"
                            })
                            .addTo(refs.reasoning);
                        }
                    });
                } else {
                    console.log(`[COP] No reasoning data found - reasoningData:`, initialProps.reasoningData);
                }
            }

            // --- Helpers ---
            function createMilsymbolIcon(sidc, props, size=34, extraClass="") {
                if (typeof ms === 'undefined') {
                    return L.divIcon({ className: 'marker-label', html: '<div style="background:gray; width:20px; height:20px;"></div>' });
                }
                try {
                    const sym = new ms.Symbol(sidc, { size: size, icon: true, frame: true, fill: true });
                    return L.divIcon({
                        className: extraClass,
                        html: sym.asSVG(),
                        iconSize: [sym.getSize().width, sym.getSize().height],
                        iconAnchor: [sym.getAnchor().x, sym.getAnchor().y]
                    });
                } catch(e) { return L.divIcon({ className:'red-label', html:'!' }); }
            }

            function createPopupContent(props, side) {
                // [FIX] 범례 정보 모두 표시 - 적군/아군 공통 정보
                const name = props.name || props.위협명 || props.label || 'Unknown';
                const description = props.description || props.상황설명 || props.비고 || '';
                const organization = props.organization || props.소속부대 || 'Unknown';
                const mission = props.mission || props.임무 || 'Unknown';
                
                // MIL-STD-2525D Modifiers
                const uniqueDesignation = props.uniqueDesignation || props.고유명칭 || name;
                const higherFormation = props.higherFormation || props.상급부대 || organization;
                
                // [FIX] 0 값 처리를 위해 삼항연산자 대신 명시적 체크
                // props.speed가 0일 수 있으므로 undefined/null 체크 필요
                let speed = 0;
                if (props.raw_speed !== undefined && props.raw_speed !== null) speed = props.raw_speed;
                else if (props.speed !== undefined && props.speed !== null) speed = props.speed;
                else if (props.이동속도 !== undefined && props.이동속도 !== null) speed = props.이동속도;
                
                let direction = 0;
                if (props.raw_direction !== undefined && props.raw_direction !== null) direction = props.raw_direction;
                else if (props.direction !== undefined && props.direction !== null) direction = props.direction;
                else if (props.이동방향 !== undefined && props.이동방향 !== null) direction = props.이동방향;
                
                const status = props.status || props.상태 || 'Operational';
                let combatEffectiveness = props.combatEffectiveness || props.전투력 || 1.0;
                
                // [FIX] 전투력 값 범위 정규화 (0-100 범위를 0-1 범위로 변환)
                if (combatEffectiveness > 1.0) {
                    // 0-100 범위로 저장된 경우 0-1 범위로 정규화
                    combatEffectiveness = combatEffectiveness / 100.0;
                }
                // 0-1 범위로 보장
                combatEffectiveness = Math.max(0.0, Math.min(1.0, combatEffectiveness));
                
                // [FIX] 방향 및 속도 표시 개선
                let directionText = 'N/A';
                if (speed === 0) {
                    directionText = '- (정지)';
                } else {
                    directionText = `→ ${typeof direction === 'number' ? direction.toFixed(0) : direction}°`;
                }
                const directionStyle = `display:inline-block; transform:rotate(${direction}deg); font-size:16px; margin-left:5px;`;
                
                // 속도 텍스트 (0도 표시)
                const speedText = (typeof speed === 'number') ? `${speed.toFixed(1)} km/h` : 'N/A';
                
                // 상태에 따른 색상
                const statusColor = status === 'Operational' ? '#28a745' : 
                                    status === 'Damaged' ? '#ffc107' : 
                                    status === 'Destroyed' ? '#dc3545' : '#6c757d';
                
                // 전투력에 따른 색상 (0-1 범위로 정규화된 값)
                const effectivenessPercent = (combatEffectiveness * 100).toFixed(0);
                const effectivenessColor = combatEffectiveness >= 0.8 ? '#28a745' : 
                                          combatEffectiveness >= 0.5 ? '#ffc107' : 
                                          combatEffectiveness >= 0.3 ? '#fd7e14' : '#dc3545';
                
                let html = `<div style="color:black; min-width:250px; font-size:13px;">
                    <b style="font-size:15px;">${name}</b><br>
                    <hr style="margin:5px 0;">`;
                
                // 적군/아군 공통 정보
                if (side === 'RED') {
                    const threatType = props.threat_type || props.위협유형 || 'Unknown';
                    const threatLevel = props.threat_level || props.위협수준 || 'N/A';
                    const threatRadius = props.threat_radius || 0;
                    // [FIX] 적군부대도 제대/병종 정보 표시
                    const unitType = props.제대 || props.unit_type || 'Unknown';
                    const unitClass = props.병종 || props.unit_class || '';
                    const deploymentLocation = props.deployment_location || props.배치위치 || '정보 없음'; // 적군은 발생장소/위치
                    
                    html += `
                    <div style="margin-bottom:8px;">
                        <strong>유형:</strong> ${threatType}<br>
                        ${unitType !== 'Unknown' ? `<strong>제대:</strong> ${unitType}${unitClass ? ` (${unitClass})` : ''}<br>` : ''}
                        ${deploymentLocation !== '정보 없음' ? `<strong>위치:</strong> ${deploymentLocation}<br>` : ''}
                        <strong>위협수준:</strong> ${typeof threatLevel === 'number' ? (threatLevel * 100).toFixed(0) + '%' : threatLevel}<br>
                        ${threatRadius > 0 ? `<strong>위협반경:</strong> ${(threatRadius/1000).toFixed(1)}km<br>` : ''}
                    </div>`;
                } else {
                    // [FIX] 아군 부대 정보 상세화
                    const unitType = props.unit_type || props.제대 || 'unknown';
                    const unitClass = props.unit_class || props.병종 || '';
                    const deploymentLocation = props.deployment_location || props.배치위치 || '정보 없음';
                    const deploymentCellId = props.deployment_cell_id || props.배치지형셀ID || props.배치축선ID || '';
                    
                    html += `
                    <div style="margin-bottom:8px;">
                        <strong>제대:</strong> ${unitType}${unitClass ? ` (${unitClass})` : ''}<br>
                        ${deploymentLocation !== '정보 없음' && deploymentLocation !== '배치지 정보 없음' ? 
                            `<strong>배치위치:</strong> ${deploymentLocation}${deploymentCellId ? ` [${deploymentCellId}]` : ''}<br>` : 
                            ''}
                    </div>`;
                }
                
                // MIL-STD-2525D 공통 정보
                html += `
                    <div style="margin-bottom:8px;">
                        <strong>소속:</strong> ${organization}<br>
                        <strong>상급부대:</strong> ${higherFormation}<br>
                        <strong>고유명칭:</strong> ${uniqueDesignation}<br>
                        <strong>임무:</strong> ${mission}<br>
                    </div>
                    <hr style="margin:5px 0;">
                    <div style="margin-bottom:8px;">
                        <strong>전투력:</strong> 
                        <span style="color:${effectivenessColor}; font-weight:bold;">${effectivenessPercent}%</span>
                        <div style="width:100%; height:8px; background:#e0e0e0; border-radius:4px; margin-top:3px;">
                            <div style="width:${effectivenessPercent}%; height:100%; background:${effectivenessColor}; border-radius:4px;"></div>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <strong>이동속도:</strong> ${speedText}<br>
                        <strong>이동방향:</strong> ${directionText}<br>
                        <strong>상태:</strong> 
                        <span style="color:${statusColor}; font-weight:bold;">${status}</span>
                        <span style="display:inline-block; width:10px; height:10px; background:${statusColor}; border-radius:50%; margin-left:5px; vertical-align:middle;"></span>
                    </div>`;
                
                if (description) {
                    html += `<hr style="margin:5px 0;"><div style="font-style:italic; color:#666; font-size:12px;">${description}</div>`;
                }
                
                html += `</div>`;
                return html;
            }
        </script>
    </body>
    </html>
    """
    
    # Manual replacement for robustness
    html_code = html_template
    html_code = html_code.replace("__LEAFLET_CSS__", resources['leaflet_css'])
    html_code = html_code.replace("__LEAFLET_JS__", resources['leaflet_js'])
    html_code = html_code.replace("__MILSYMBOL_SCRIPT__", milsymbol_script_tag)
    html_code = html_code.replace("__JSON_PROPS__", json_props)
    html_code = html_code.replace("__TILE_SAT__", resources['tile_sat'])
    html_code = html_code.replace("__TILE_DARK__", resources['tile_dark'])
    html_code = html_code.replace("__HEIGHT__", str(height))
    
    components.html(html_code, height=height)
