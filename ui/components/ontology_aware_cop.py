# ui/components/ontology_aware_cop.py
# -*- coding: utf-8 -*-
"""
Ontology-aware COP Component (MapLibre GL JS 기반)
온톨로지 기반 방책 추천 결과를 공간적으로 검증하는 지휘 인터페이스

핵심 원칙:
- COP는 "상황 표시 지도"가 아니라 "온톨로지 추론 결과를 공간적으로 검증하는 지휘 인터페이스"
- 지도는 배경이며, 핵심은 COA 판단과 설명
- 모든 전술 객체는 온톨로지 URI를 포함해야 함
- Base Map: 로컬 MBTiles (MapLibre GL JS 사용)
"""
import streamlit as st
import streamlit.components.v1 as components
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

def render_ontology_aware_cop(
    coa_recommendations: List[Dict],
    threat_geojson: Optional[Dict] = None,
    coa_geojson: Optional[Dict] = None,
    ontology_manager=None,
    axes_geojson: Optional[Dict] = None,
    terrain_cells_geojson: Optional[Dict] = None,
    height: int = 700,
    height: int = 700,
    situation_summary: Optional[str] = None
):
    """
    온톨로지 인식 COP 렌더링 (MapLibre GL JS 기반)
    
    Args:
        coa_recommendations: COA 추천 결과 리스트 (점수, 추론 근거 포함)
        threat_geojson: 위협 GeoJSON (온톨로지 URI 포함)
        coa_geojson: COA GeoJSON (온톨로지 URI 포함)
        ontology_manager: 온톨로지 매니저 (추론 경로 조회용)
        axes_geojson: 축선 GeoJSON (LineString)
        terrain_cells_geojson: 지형셀 GeoJSON (Polygon)
        height: 컴포넌트 높이
        height: 컴포넌트 높이
        situation_summary: 상황 요약 텍스트
    """
    
    # 프로젝트 루트 경로
    BASE_DIR = Path(__file__).parent.parent.parent
    
    # 데이터 준비
    cop_data = {
        "coaRecommendations": coa_recommendations or [],
        "threatData": threat_geojson or {"type": "FeatureCollection", "features": []},
        "coaData": coa_geojson or {"type": "FeatureCollection", "features": []},
        "axesData": axes_geojson or {"type": "FeatureCollection", "features": []},
        "terrainCellsData": terrain_cells_geojson or {"type": "FeatureCollection", "features": []},
        "ontologyAvailable": ontology_manager is not None,
        "situationSummary": situation_summary
    }
    
    # 데이터 해시 생성 (지도 재초기화 최소화를 위해)
    import hashlib
    data_string = json.dumps(cop_data, sort_keys=True, ensure_ascii=False)
    data_hash = hashlib.md5(data_string.encode('utf-8')).hexdigest()[:8]
    
    # 이전 해시와 비교하여 데이터 변경 여부 확인
    prev_hash_key = "cop_map_data_hash"
    prev_hash = st.session_state.get(prev_hash_key, None)
    data_changed = (prev_hash != data_hash)
    
    # 현재 해시 저장
    st.session_state[prev_hash_key] = data_hash
    
    json_props = json.dumps(cop_data, ensure_ascii=False)
    
    # 리소스 경로 (오프라인 모드 실패 시 온라인 리소스로 fallback)
    # 리소스 경로 (모두 온라인 CDN 사용)
    online_maplibre_css = "https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css"
    online_maplibre_js = "https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"
    online_milsymbol = "https://unpkg.com/milsymbol@2.0.0/dist/milsymbol.js"
    
    resources = {
        "maplibre_css": online_maplibre_css,
        "maplibre_js": online_maplibre_js,
        "milsymbol": online_milsymbol,
        "fallback_maplibre_css": online_maplibre_css,
        "fallback_maplibre_js": online_maplibre_js,
        "fallback_milsymbol": online_milsymbol
    }
    
    # MBTiles 타일 URL (벡터 타일) - 온라인 모드에서는 사용 안함
    tile_url = ""
    
    # JavaScript에서 사용할 base_url (문자열로 전달)
    base_url_js = ""
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        
        <!-- MapLibre GL CSS (로드 실패 시 fallback) -->
        <link rel="stylesheet" href="{resources['maplibre_css']}" 
              onerror="this.onerror=null; this.href='{resources['fallback_maplibre_css']}'" />
        
        <style>
            body {{ margin: 0; padding: 0; background-color: #0d1117; font-family: 'Segoe UI', sans-serif; overflow: hidden; }}
            html, body {{ height: 100%; width: 100%; }}
            #root {{ width: 100%; height: {height}px; min-height: {height}px; position: relative; display: block; }}
            
            /* COP Layout */
            .cop-container {{ width: 100%; height: {height}px; min-height: {height}px; position: relative; display: block; }}
            
            /* 좌측 패널: 상황 요약 */
            .left-panel {{
                position: absolute;
                top: 20px;
                left: 20px;
                width: 300px;
                max-height: calc(100% - 40px);
                background: rgba(16, 22, 26, 0.95);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-left: 3px solid #58a6ff;
                border-radius: 4px;
                padding: 16px;
                color: #c9d1d9;
                z-index: 1000;
                overflow-y: auto;
            }}
            
            .left-panel h3 {{
                margin: 0 0 12px 0;
                color: #58a6ff;
                font-size: 14px;
                font-weight: 600;
            }}
            
            .situation-summary {{
                font-size: 12px;
                line-height: 1.6;
            }}
            
            .summary-item {{
                margin-bottom: 8px;
                padding: 8px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 3px;
            }}
            
            /* 위협상황 브리핑 스타일 */
            .threat-briefing-item {{
                margin-bottom: 12px;
                padding: 10px;
                background: rgba(255, 107, 107, 0.1);
                border-left: 3px solid #ff6b6b;
                border-radius: 3px;
            }}
            
            .threat-briefing-item h5 {{
                margin: 0 0 6px 0;
                color: #ff6b6b;
                font-size: 12px;
                font-weight: 600;
            }}
            
            .threat-briefing-item .briefing-detail {{
                margin: 4px 0;
                font-size: 11px;
                color: #c9d1d9;
            }}
            
            .threat-briefing-item .briefing-label {{
                color: #8b949e;
                font-weight: 500;
                margin-right: 6px;
            }}
            
            .threat-briefing-item .briefing-value {{
                color: #e6edf3;
            }}
            
            .summary-item strong {{
                color: #79c0ff;
            }}
            
            /* 우측 패널: 추론 근거 */
            .right-panel {{
                position: absolute;
                top: 20px;
                right: 20px;
                width: 380px;
                max-height: calc(100% - 40px);
                background: rgba(16, 22, 26, 0.95);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-left: 3px solid #3fb950;
                border-radius: 4px;
                padding: 16px;
                color: #c9d1d9;
                z-index: 1000;
                overflow-y: auto;
                display: none;
            }}
            
            .right-panel.active {{
                display: block;
            }}
            
            .right-panel h3 {{
                margin: 0 0 12px 0;
                color: #3fb950;
                font-size: 14px;
                font-weight: 600;
            }}
            
            .reasoning-section {{
                margin-bottom: 16px;
                padding: 12px;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 3px;
            }}
            
            .reasoning-section-title {{
                font-size: 11px;
                color: #8b949e;
                margin-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .reasoning-path {{
                font-size: 11px;
                color: #c9d1d9;
                line-height: 1.6;
            }}
            
            .reasoning-path-graph {{
                font-size: 10px;
                font-family: 'Consolas', monospace;
                color: #c9d1d9;
                line-height: 1.8;
            }}
            
            .ontology-uri {{
                font-size: 10px;
                color: #58a6ff;
                word-break: break-all;
                margin-top: 4px;
            }}
            
            /* 하단 패널: 시간 흐름 및 COA 비교 */
            .bottom-panel {{
                position: absolute;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                width: 85%;
                max-width: 1400px;
                background: rgba(16, 22, 26, 0.95);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                padding: 12px;
                z-index: 1000;
            }}
            
            .timeline-control {{
                margin-bottom: 12px;
                padding: 8px;
                background: rgba(0,0,0,0.2);
                border-radius: 4px;
            }}
            
            .coa-comparison {{
                display: flex;
                gap: 12px;
                overflow-x: auto;
                padding: 4px;
            }}
            
            .coa-card {{
                min-width: 220px;
                padding: 12px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 3px;
                border: 2px solid transparent;
                cursor: pointer;
                transition: all 0.2s;
                position: relative;
            }}
            
            .coa-card:hover {{
                background: rgba(255, 255, 255, 0.1);
                transform: translateY(-2px);
            }}
            
            .coa-card.selected {{
                border-color: #58a6ff;
                background: rgba(88, 166, 255, 0.15);
                box-shadow: 0 0 12px rgba(88, 166, 255, 0.3);
            }}
            
            .coa-card h4 {{
                margin: 0 0 8px 0;
                color: #58a6ff;
                font-size: 13px;
                font-weight: 600;
            }}
            
            .coa-score {{
                font-size: 24px;
                font-weight: 700;
                color: #3fb950;
                margin: 8px 0;
                font-family: 'Consolas', monospace;
            }}
            
            .coa-type {
                font-size: 11px;
                color: #8b949e;
                margin-top: 4px;
            }
            
            /* 지도 컨테이너 */
            .map-container {{
                width: 100% !important;
                height: {height}px !important;
                min-height: {height}px !important;
                position: absolute !important;
                top: 0 !important;
                left: 0 !important;
                background-color: #0d1117 !important;
                z-index: 1 !important;
            }}
            
            /* MapLibre Customization */
            .maplibregl-popup {{
                max-width: 300px;
            }}
            
            .maplibregl-popup-content {{
                background: #161b22;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 12px;
                font-size: 12px;
            }}
            
            /* MapLibre 컨트롤 위치 조정 - 추론근거 패널과 겹치지 않도록 아래로 이동 */
            .maplibregl-ctrl-top-right {{
                top: auto !important;
                bottom: 20px !important;
                right: 20px !important;
            }}
            
            /* 컨트롤 그룹이 추론근거 패널 아래에 오도록 z-index 조정 */
            .maplibregl-ctrl-group {{
                z-index: 999 !important;
            }}
            
            .unit-popup h4 {{
                margin: 0 0 8px 0;
                color: #58a6ff;
                font-size: 13px;
            }}
            
            .info-section {{
                margin-bottom: 12px;
                padding-bottom: 8px;
                border-bottom: 1px solid #30363d;
            }}
            
            .info-section:last-child {{
                border-bottom: none;
            }}
            
            .info-section-title {{
                font-size: 10px;
                color: #8b949e;
                margin-bottom: 4px;
                text-transform: uppercase;
            }}
            
            .info-section-content {{
                font-size: 12px;
                color: #c9d1d9;
            }}
            
            /* 위협 강조 스타일 */
            .threat-highlighted {{
                filter: drop-shadow(0 0 8px rgba(255, 23, 68, 0.8));
                animation: threatPulse 2s ease-in-out infinite;
            }}
            
            @keyframes threatPulse {{
                0%, 100% {{
                    opacity: 1;
                    transform: scale(1);
                }}
                50% {{
                    opacity: 0.8;
                    transform: scale(1.1);
                }}
            }}
            
            /* 영구 레이블 스타일 */
            .marker-label {{
                background: rgba(13, 17, 23, 0.85);
                color: #fff;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                white-space: nowrap;
                border: 1px solid rgba(255, 255, 255, 0.2);
                box-shadow: 0 2px 4px rgba(0,0,0,0.5);
                pointer-events: none;
                z-index: 2000;
                margin-top: 5px;
            }}
            
            /* 위협 레이블 특화 */
            .threat-label {{
                border-left: 3px solid #ff1744;
            }}
            
            /* 아군 레이블 특화 */
            .blue-label {{
                border-left: 3px solid #58a6ff;
            }}
        </style>
        
        <!-- MapLibre GL JS & Libraries (로드 실패 시 fallback) -->
        <script src="{resources['maplibre_js']}" 
                onerror="this.onerror=null; this.src='{resources['fallback_maplibre_js']}'"></script>
        <script src="{resources['milsymbol']}" 
                onerror="this.onerror=null; this.src='{resources['fallback_milsymbol']}'"></script>
        
        <!-- 리소스 로드 확인 스크립트 -->
        <script>
            // MapLibre GL JS 로드 확인
            window.addEventListener('load', function() {{
                if (typeof maplibregl === 'undefined') {{
                    console.error('❌ MapLibre GL JS 로드 실패 - fallback 시도');
                    const script = document.createElement('script');
                    script.src = '{resources['fallback_maplibre_js']}';
                    script.onload = function() {{
                        console.log('✅ MapLibre GL JS fallback 로드 성공');
                    }};
                    document.head.appendChild(script);
                }} else {{
                    console.log('✅ MapLibre GL JS 로드 성공');
                }}
                
                if (typeof ms === 'undefined') {{
                    console.error('❌ Milsymbol 로드 실패 - fallback 시도');
                    const script = document.createElement('script');
                    script.src = '{resources['fallback_milsymbol']}';
                    script.onload = function() {{
                        console.log('✅ Milsymbol fallback 로드 성공');
                    }};
                    document.head.appendChild(script);
                }} else {{
                    console.log('✅ Milsymbol 로드 성공');
                }}
            }});
        </script>
    </head>
    <body>
        <div id="root">
            <div class="cop-container">
                <div class="map-container" id="map-container"></div>
                
                <!-- 좌측 패널: 상황 요약 -->
                <div class="left-panel" id="left-panel">
                    <h3>📊 상황 요약</h3>
                    <div class="situation-summary" id="situation-summary">
                        <div class="summary-item">
                            <strong>위협:</strong> <span id="threat-count">0</span>개
                        </div>
                        <div class="summary-item">
                            <strong>부대:</strong> <span id="unit-count">0</span>개
                        </div>
                        <div class="summary-item">
                            <strong>COA 후보:</strong> <span id="coa-count">0</span>개
                        </div>
                        <div class="summary-item" id="selected-coa-summary" style="display: none;">
                            <strong>선택된 COA:</strong>
                            <br />
                            <span id="selected-coa-name"></span>
                            <br />
                            <span id="selected-coa-score" style="color: #3fb950; font-size: 18px; font-weight: 600;"></span>
                        </div>
                    </div>
                </div>
                
                <!-- 우측 패널: 추론 근거 -->
                <div class="right-panel" id="right-panel">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h3 style="margin: 0;">🧠 추론 근거</h3>
                        <button 
                            id="close-reasoning-btn"
                            style="background: transparent; border: none; color: #8b949e; cursor: pointer; font-size: 18px; padding: 4px 8px; line-height: 1; transition: color 0.2s;"
                            onmouseover="this.style.color='#c9d1d9'"
                            onmouseout="this.style.color='#8b949e'"
                            title="닫기"
                        >✕</button>
                    </div>
                    <div id="reasoning-content">
                        <div>COA를 선택하면 추론 근거가 표시됩니다.</div>
                    </div>
                </div>
                
                <!-- 하단 패널: 시간 흐름 및 COA 비교 -->
                <div class="bottom-panel">
                    <!-- 시간 흐름 슬라이더 -->
                    <div class="timeline-control">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <label style="color: #8b949e; font-size: 11px; min-width: 80px;">시간 단계:</label>
                            <input 
                                type="range" 
                                id="time-slider"
                                min="0" 
                                max="2" 
                                value="0"
                                style="flex: 1; height: 4px; background: #30363d; outline: none; border-radius: 2px;"
                            />
                            <span id="time-step-label" style="color: #58a6ff; font-size: 12px; font-weight: 600; min-width: 100px;">초기 상황</span>
                            <div style="display: flex; gap: 4px;">
                                <button 
                                    id="time-prev-btn"
                                    style="padding: 4px 8px; background: #21262d; border: 1px solid #30363d; color: #c9d1d9; border-radius: 3px; cursor: pointer; font-size: 11px;"
                                >
                                    ◀ 이전
                                </button>
                                <button 
                                    id="time-next-btn"
                                    style="padding: 4px 8px; background: #21262d; border: 1px solid #30363d; color: #c9d1d9; border-radius: 3px; cursor: pointer; font-size: 11px;"
                                >
                                    다음 ▶
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <!-- COA 비교 -->
                    <div class="coa-comparison" id="coa-comparison">
                        <div>COA 데이터가 없습니다.</div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // 즉시 실행되는 디버깅 코드
            console.log("🚀 COP 스크립트 시작!");
            console.log("📦 document.readyState:", document.readyState);
            console.log("📦 map-container 존재 여부:", !!document.getElementById('map-container'));
            
            // Initial Data
            const copData = {json_props};
            
            // 디버깅: 데이터 확인
            console.log("🔍 COP 데이터:", copData);
            console.log("🔍 위협 데이터:", copData.threatData);
            const threatFeaturesCount = (copData.threatData && copData.threatData.features && Array.isArray(copData.threatData.features)) ? copData.threatData.features.length : 0;
            console.log("🔍 위협 features 개수:", threatFeaturesCount);
            
            // 상태 관리 (순수 JavaScript)
            let mapInstance = null;
            let markersRef = {{}};
            let selectedCOA = null;
            let showReasoning = false;
            
            // 데이터 해시 관리 (지도 재초기화 최소화)
            const currentDataHash = "{data_hash}";
            const prevDataHashKey = "cop_map_prev_hash";
            const prevDataHash = localStorage.getItem(prevDataHashKey);
            const dataChanged = (prevDataHash !== currentDataHash);
            
            console.log("📊 데이터 해시 비교:", {{
                current: currentDataHash,
                previous: prevDataHash,
                changed: dataChanged
            }});
            
            // 현재 해시 저장
            if (dataChanged) {{
                localStorage.setItem(prevDataHashKey, currentDataHash);
                console.log("✅ 새로운 데이터 해시 저장됨");
            }} else {{
                console.log("ℹ️ 데이터 변경 없음 - 지도 재초기화 스킵 가능");
            }}
            let timeStep = 0;
            const timeSteps = ["초기 상황", "작전 실행", "작전 완료"];
            
            // 추론 경로 그래프 렌더링 함수
            const renderReasoningPathGraph = (reasoningPath) => {{
                if (!reasoningPath || !Array.isArray(reasoningPath)) {{
                    return '<div style="color: #8b949e; font-size: 11px;">추론 경로 데이터가 없습니다.</div>';
                }}
                
                let html = '<div style="font-family: Consolas, monospace; font-size: 10px; line-height: 1.8;">';
                
                reasoningPath.forEach((path, index) => {{
                    const threat = path.threat || path.threat_uri || 'Unknown';
                    const relation = path.relation || path.relation_uri || 'relatedTo';
                    const coa = path.coa || path.coa_uri || 'Current COA';
                    
                    const getLocalName = (uri) => {{
                        if (!uri) return 'Unknown';
                        const parts = uri.split('#');
                        return parts.length > 1 ? parts[parts.length - 1] : uri.split('/').pop();
                    }};
                    
                    const threatName = getLocalName(threat);
                    const relationName = getLocalName(relation);
                    const coaName = getLocalName(coa);
                    
                    html += `
                        <div style="margin-bottom: 8px; padding: 8px; background: rgba(0,0,0,0.2); border-radius: 3px; border-left: 3px solid #58a6ff;">
                            <div style="color: #58a6ff; font-weight: 600; margin-bottom: 4px;">
                                ${{index + 1}}. 경로
                            </div>
                            <div style="color: #c9d1d9; margin-left: 12px;">
                                <div style="margin-bottom: 2px;">
                                    <span style="color: #ff6b6b;">위협:</span> 
                                    <span style="color: #79c0ff;">${{threatName}}</span>
                                </div>
                                <div style="margin-bottom: 2px; margin-left: 8px;">
                                    <span style="color: #8b949e;">${{relationName}}</span>
                                </div>
                                <div>
                                    <span style="color: #3fb950;">COA:</span> 
                                    <span style="color: #79c0ff;">${{coaName}}</span>
                                </div>
                            </div>
                        </div>
                    `;
                }});
                
                html += '</div>';
                return html;
            }};
                
            // COA 선택 시 위협 강조 함수
            const highlightThreatsForCOA = (coa) => {{
                if (!mapInstance || !coa) return;
                
                const coaId = coa.coa_id || coa.coa_name;
                const exposedThreats = coa.exposed_threats || [];
                
                // 모든 위협 마커 확인
                Object.values(markersRef).forEach(markerData => {{
                    if (markerData.type === 'threat') {{
                        const threatData = markerData.threatData;
                        const affectedCOAs = threatData.affected_coa || [];
                        
                        const isRelated = 
                            affectedCOAs.includes(coaId) || 
                            affectedCOAs.includes(coa.coa_name) ||
                            exposedThreats.some(t => 
                                t === threatData.threat_type || 
                                t === markerData.name
                            );
                        
                        if (isRelated) {{
                            // 관련 위협 강조
                            threatData.isHighlighted = true;
                            const marker = markerData.marker;
                            
                            // 아이콘 크기 증가 및 색상 변경
                            const sidc = markerData.sidc || "SHGPE-----H----";
                            const iconEl = document.createElement('div');
                            
                            if (typeof ms !== 'undefined' && ms && ms.Symbol) {{
                                try {{
                                    const sym = new ms.Symbol(sidc, {{ 
                                        size: 40, 
                                        icon: true,
                                        colorMode: 'Light',
                                        fill: true,
                                        fillColor: '#ff1744'
                                    }});
                                    iconEl.innerHTML = sym.asSVG();
                                }} catch (e) {{
                                    iconEl.innerHTML = '🔴';
                                    iconEl.style.fontSize = '32px';
                                }}
                            }} else {{
                                iconEl.innerHTML = '🔴';
                                iconEl.style.fontSize = '32px';
                            }}
                            
                            iconEl.style.width = '40px';
                            iconEl.style.height = '40px';
                            iconEl.style.textAlign = 'center';
                            
                            // [MOD] 레이블을 보존하며 아이콘만 업데이트
                            if (marker && marker._element) {{
                                const existingIcon = marker._element.querySelector('div') || marker._element.firstChild;
                                if (existingIcon) {{
                                    existingIcon.innerHTML = iconEl.innerHTML;
                                    existingIcon.style.width = '40px';
                                    existingIcon.style.height = '40px';
                                    existingIcon.className = 'threat-highlighted';
                                }}
                                marker._element.style.filter = 'drop-shadow(0 0 8px rgba(255, 23, 68, 0.8))';
                                marker._element.style.opacity = '1.0';
                            }}
                            
                        }} else {{
                            // 관련 없는 위협은 반투명 처리
                            threatData.isHighlighted = false;
                            const marker = markerData.marker;
                            if (marker && marker._element) {{
                                marker._element.style.opacity = '0.3';
                                marker._element.style.filter = 'none';
                                const existingIcon = marker._element.querySelector('div') || marker._element.firstChild;
                                if (existingIcon) existingIcon.className = '';
                            }}
                        }}
                    }}
                }});
            }};
            
            // UI 업데이트 함수들
            const updateSummary = () => {{
                // [FIX] 위협식별 숫자는 실제 식별된 위협상황만 카운트 (배경 적군 제외)
                const allThreats = (copData.threatData && copData.threatData.features && Array.isArray(copData.threatData.features)) ? copData.threatData.features : [];
                const threatCount = allThreats.filter(f => f.properties && f.properties.is_identified_threat === true).length;
                const unitCount = (copData.coaData && copData.coaData.features && Array.isArray(copData.coaData.features)) ? copData.coaData.features.filter(f => f.geometry.type === "Point").length : 0;
                const coaCount = (copData.coaRecommendations && Array.isArray(copData.coaRecommendations)) ? copData.coaRecommendations.length : 0;
                
                document.getElementById('threat-count').textContent = threatCount;
                document.getElementById('unit-count').textContent = unitCount;
                document.getElementById('coa-count').textContent = coaCount;
                
                if (selectedCOA) {{
                    document.getElementById('selected-coa-summary').style.display = 'block';
                    document.getElementById('selected-coa-name').textContent = selectedCOA.coa_name || "Unknown";
                    document.getElementById('selected-coa-score').textContent = ((selectedCOA.score || selectedCOA.total_score || 0) * 100).toFixed(1) + '%';
                }} else {{
                    document.getElementById('selected-coa-summary').style.display = 'none';
                }}
                
                // 위협상황 브리핑 업데이트
                updateThreatBriefing();
            }};
            
            // 위협상황 브리핑 생성 함수
            const updateThreatBriefing = () => {{
                const briefingContent = document.getElementById('threat-briefing-content');
                if (!briefingContent) return;
                
                const threats = (copData.threatData && copData.threatData.features && Array.isArray(copData.threatData.features)) 
                    ? copData.threatData.features 
                    : [];
                
                if (threats.length === 0) {{
                    briefingContent.innerHTML = '<div style="color: #8b949e; font-style: italic;">현재 탐지된 위협이 없습니다.</div>';
                    return;
                }}
                
                // 축선 정보 가져오기
                const axes = (copData.axesData && copData.axesData.features && Array.isArray(copData.axesData.features))
                    ? copData.axesData.features
                    : [];
                
                // 축선 ID -> 이름 매핑 생성
                const axisMap = {{}};
                axes.forEach(axis => {{
                    const props = axis.properties || {{}};
                    const axisId = props.id || props.axis_id || props.축선ID || '';
                    const axisName = props.name || props.axis_name || props.축선명 || axisId;
                    if (axisId) {{
                        axisMap[axisId] = axisName;
                    }}
                }});
                
                // 각 위협에 대한 브리핑 생성
                let briefingHTML = '';
                threats.forEach((threat, index) => {{
                    const props = threat.properties || {{}};
                    const coords = threat.geometry && threat.geometry.coordinates ? threat.geometry.coordinates : null;
                    
                    // 위협 정보 추출
                    const threatName = props.name || props.위협명 || props.label || `위협 ${index + 1}`;
                    const threatType = props.threat_type || props.위협유형 || props.type || '알 수 없음';
                    const threatLevel = props.threat_level || props.위협수준 || 0;
                    const threatLevelPercent = typeof threatLevel === 'number' ? (threatLevel * 100).toFixed(0) : threatLevel;
                    
                    // 발생장소 추출
                    const location = props.location || props.발생장소 || props.occurrence_location || 
                                    (coords ? `위도 ${coords[1].toFixed(4)}, 경도 ${coords[0].toFixed(4)}` : '미상');
                    
                    // 관련 축선 추출
                    const axisId = props.axis_id || props.관련축선ID || props.related_axis_id || props.axisLabel || '';
                    const axisName = axisMap[axisId] || axisId || '미지정';
                    
                    // 온톨로지 정보 추출
                    const threatUri = props.uri || props.threat_uri || '';
                    const hasOntology = threatUri && threatUri.trim() !== '';
                    
                    // 위협 수준에 따른 색상 결정
                    const threatLevelNum = typeof threatLevel === 'number' ? threatLevel : parseFloat(threatLevel) || 0;
                    let levelColor = '#8b949e'; // 기본 (낮음)
                    let levelText = '낮음';
                    if (threatLevelNum >= 0.7) {{
                        levelColor = '#ff6b6b'; // 높음
                        levelText = '높음';
                    }} else if (threatLevelNum >= 0.4) {{
                        levelColor = '#f1c40f'; // 중간
                        levelText = '중간';
                    }}
                    
                    briefingHTML += `
                        <div class="threat-briefing-item">
                            <h5>${{{{threatName}}}}</h5>
                            <div class="briefing-detail">
                                <span class="briefing-label">유형:</span>
                                <span class="briefing-value">${{{{threatType}}}}</span>
                            </div>
                            <div class="briefing-detail">
                                <span class="briefing-label">발생장소:</span>
                                <span class="briefing-value">${{{{location}}}}</span>
                            </div>
                            <div class="briefing-detail">
                                <span class="briefing-label">관련 축선:</span>
                                <span class="briefing-value">${{{{axisName}}}}</span>
                            </div>
                            <div class="briefing-detail">
                                <span class="briefing-label">위협 수준:</span>
                                <span class="briefing-value" style="color: ${{{{levelColor}}}}; font-weight: 600;">
                                    ${{{{levelText}}}} (${{{{threatLevelPercent}}}}%)
                                </span>
                            </div>
                            ${{{{hasOntology ? `
                            <div class="briefing-detail">
                                <span class="briefing-label">온톨로지:</span>
                                <span class="briefing-value" style="color: #58a6ff; font-size: 10px;">✓ 연결됨</span>
                            </div>
                            ` : ''}}}}
                        </div>
                    `;
                }});
                
                briefingContent.innerHTML = briefingHTML;
            }};
            
            const updateReasoning = () => {{
                const reasoningContent = document.getElementById('reasoning-content');
                if (!selectedCOA) {{
                    reasoningContent.innerHTML = '<div>COA를 선택하면 추론 근거가 표시됩니다.</div>';
                    document.getElementById('right-panel').classList.remove('active');
                    return;
                }}
                
                document.getElementById('right-panel').classList.add('active');
                
                // [RESILIENCE] 데이터 매핑 로직 정교화 (중복 표시 원천 차단)
                const r = selectedCOA.reasoning || {{}};
                
                // 상황 판단: reasoning 데이터 우선, 없으면 description 폴백
                let assessment = r.situation_assessment || selectedCOA.description;
                if (!assessment || assessment.includes("데이터 대기중")) {{
                    assessment = "현재 전술 상황 및 위협 분석 데이터가 집계되지 않았습니다.";
                }}
                
                // 선정 사유
                let justification = r.justification || selectedCOA.reason || selectedCOA.llm_reason;
                if (!justification) {{
                    justification = "현재 방책에 대한 세부 선정 사유를 분석 중입니다.";
                }}

                // 기대효과: r.pros가 리스트면 사용, 아니면 strengths 폴백, 그외 기본값
                const pros = (Array.isArray(r.pros) && r.pros.length > 0) ? r.pros : 
                             ((Array.isArray(selectedCOA.strengths) && selectedCOA.strengths.length > 0) ? selectedCOA.strengths : 
                             ["전술적 목표 달성", "자원 활용 효율화", "작전 위험도 감소"]);
                
                let html = `
                    <h4 style="margin: 0 0 12px 0; color: #58a6ff; border-bottom: 1px solid rgba(88, 166, 255, 0.2); padding-bottom: 8px;">${selectedCOA.coa_name || "Unknown"}</h4>
                    <div class="coa-score" style="font-size: 24px; margin: 12px 0; color: #3fb950; font-weight: bold;">${((selectedCOA.score || selectedCOA.total_score || 0) * 100).toFixed(1)}%</div>
                `;
                
                // 상황 판단
                html += `
                    <div class="reasoning-section">
                        <div class="reasoning-section-title">⚖️ 상황 판단</div>
                        <div class="reasoning-path" style="font-family: inherit; font-size: 12px;">${assessment}</div>
                    </div>
                `;
                
                // 선정 사유
                html += `
                    <div class="reasoning-section">
                        <div class="reasoning-section-title">💡 선정 사유</div>
                        <div class="reasoning-path" style="font-family: inherit; font-size: 12px;">${justification}</div>
                    </div>
                `;
                
                // 기대 효과
                let prosHtml = '<ul style="margin:0; padding-left:20px; font-size:12px; color:#c9d1d9;">';
                if (Array.isArray(pros)) {{
                    pros.forEach(p => {{ prosHtml += `<li>${p}</li>`; }});
                }} else {{
                    prosHtml += `<li>${pros}</li>`;
                }}
                prosHtml += '</ul>';
                
                html += `
                    <div class="reasoning-section">
                        <div class="reasoning-section-title">🎯 기대 효과</div>
                        ${prosHtml}
                    </div>
                `;
                
                if (selectedCOA.coa_uri) {{
                    html += `
                        <div class="reasoning-section">
                            <div class="reasoning-section-title">🔗 온톨로지 URI</div>
                            <div class="ontology-uri" style="font-size: 10px; opacity: 0.7;">${selectedCOA.coa_uri}</div>
                        </div>
                    `;
                }}
                
                if (selectedCOA.ontology_reasoning_path) {{
                    html += `
                        <div class="reasoning-section">
                            <div class="reasoning-section-title">🛤️ 추론 경로</div>
                            <div class="reasoning-path-graph">${renderReasoningPathGraph(selectedCOA.ontology_reasoning_path)}</div>
                        </div>
                    `;
                }}
                
                reasoningContent.innerHTML = html;
                
                // 닫기 버튼 이벤트 리스너 재등록 (내용 업데이트 후에도 작동하도록)
                attachCloseButtonHandler();
            }};
            
            const updateCOAComparison = () => {{
                const comparisonContainer = document.getElementById('coa-comparison');
                
                if (!copData.coaRecommendations || !Array.isArray(copData.coaRecommendations) || copData.coaRecommendations.length === 0) {{
                    comparisonContainer.innerHTML = '<div>COA 데이터가 없습니다.</div>';
                    return;
                }}
                
                comparisonContainer.innerHTML = '';
                
                copData.coaRecommendations.forEach((coa, index) => {{
                    const score = (coa.score || coa.total_score || 0) * 100;
                    const isSelected = selectedCOA && (coa.coa_id === selectedCOA.coa_id || coa.coa_name === selectedCOA.coa_name);
                    
                    let timeStatus = "";
                    let timeStatusColor = "#8b949e";
                    if (timeStep === 0) {{
                        timeStatus = "계획";
                        timeStatusColor = "#58a6ff";
                    }} else if (timeStep === 1) {{
                        timeStatus = "실행 중";
                        timeStatusColor = "#3fb950";
                    }} else {{
                        timeStatus = "완료";
                        timeStatusColor = "#8b949e";
                    }}
                    
                    const classNameValue = isSelected ? 'coa-card selected' : 'coa-card';
                    const coaNameValue = coa.coa_name || ('COA ' + (index + 1));
                    const coaTypeValue = coa.coa_type || "알 수 없음";
                    
                    const cardDiv = document.createElement('div');
                    cardDiv.className = classNameValue;
                    cardDiv.style.position = 'relative';
                    cardDiv.onclick = () => handleCOASelect(coa);
                    
                    cardDiv.innerHTML = `
                        <div style="position: absolute; top: 8px; right: 8px; font-size: 9px; color: ${{timeStatusColor}}; background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 3px;">${{timeStatus}}</div>
                        <h4>${{coaNameValue}}</h4>
                        <div class="coa-score">${{score.toFixed(1)}}%</div>
                        <div class="coa-type">${{coaTypeValue}}</div>
                    `;
                    
                    comparisonContainer.appendChild(cardDiv);
                }});
            }};
            
            // COA 선택 핸들러
            const handleCOASelect = (coa) => {{
                selectedCOA = coa;
                showReasoning = true;
                
                // UI 업데이트
                updateSummary();
                updateReasoning();
                updateCOAComparison();
                
                // 지도에서 해당 COA 강조
                if (mapInstance) {{
                    // COA 경로 강조
                    copData.coaRecommendations.forEach((c, index) => {{
                        const layerId = `coa-path-line-${{index}}`;
                        if (mapInstance.getLayer(layerId)) {{
                            const isSelected = c.coa_id === coa.coa_id;
                            mapInstance.setPaintProperty(layerId, 'line-color', isSelected ? '#58a6ff' : '#8b949e');
                            mapInstance.setPaintProperty(layerId, 'line-width', isSelected ? 5 : 3);
                        }}
                    }});
                    
                    // 위협 강조
                    setTimeout(() => {{
                        highlightThreatsForCOA(coa);
                    }}, 100);
                }}
            }};
            
            // Initialize Map - 최적화된 초기화
            const initMap = () => {{
                // 이미 초기화되었고 데이터가 변경되지 않았으면 마커만 업데이트
                if (mapInstance && !dataChanged) {{
                    console.log("ℹ️ 지도가 이미 초기화되었고 데이터 변경 없음. 마커만 업데이트합니다.");
                    // 지도는 이미 있으므로 마커만 업데이트
                    if (mapInstance.loaded()) {{
                        renderTacticalLayers(mapInstance);
                        updateSummary();
                        updateCOAComparison();
                    }}
                    return;
                }}
                
                // 데이터가 변경되었거나 지도가 없으면 재초기화
                if (mapInstance && dataChanged) {{
                    console.log("🔄 데이터 변경 감지 - 지도 재초기화");
                    // 기존 마커 제거
                    Object.values(markersRef).forEach(marker => {{
                        if (marker && marker.remove) marker.remove();
                    }});
                    markersRef = {{}};
                    // 지도 제거
                    if (mapInstance.remove) mapInstance.remove();
                    mapInstance = null;
                }}
                
                console.log("🔍 지도 초기화 시작...");
                const mapContainer = document.getElementById('map-container');
                if (!mapContainer) {{
                    console.warn("⚠️ map-container를 찾을 수 없습니다. 재시도...");
                    setTimeout(initMap, 100);
                    return;
                }}
                console.log("✅ map-container 찾음:", mapContainer);
                
                // 컨테이너가 보이지 않으면 강제로 표시
                if (mapContainer.offsetWidth === 0 || mapContainer.offsetHeight === 0) {{
                    console.warn("⚠️ 컨테이너 크기가 0입니다. 강제로 설정...");
                    mapContainer.style.display = 'block';
                    mapContainer.style.visibility = 'visible';
                    mapContainer.style.width = '100%';
                    mapContainer.style.height = '{height}px';
                    mapContainer.style.minHeight = '{height}px';
                }}
                
                // MapLibre GL JS 확인
                if (typeof maplibregl === 'undefined') {{
                    console.error("❌ MapLibre GL JS가 로드되지 않았습니다!");
                    mapContainer.innerHTML = '<div style="padding: 20px; color: white;">MapLibre GL JS를 로드할 수 없습니다.</div>';
                    return;
                }}
                console.log("✅ MapLibre GL JS 확인됨");
                
                // 기본 지도 스타일
                const mapStyle = {{
                    version: 8,
                    sources: {{}},
                    layers: [{{
                        id: "background",
                        type: "background",
                        paint: {{ "background-color": "#0d1117" }}
                    }}]
                }};
                
                // 타일 URL 확인
                const tileUrl = "{tile_url}";
                if (tileUrl && tileUrl.trim() !== "") {{
                    mapStyle.sources["vector-tiles"] = {{
                        type: "vector",
                        tiles: [tileUrl],
                        minzoom: 0,
                        maxzoom: 14
                    }};
                }}
                
                // 지도 생성
                const map = new maplibregl.Map({{
                    container: mapContainer,
                    style: mapStyle,
                    center: [127.5, 36.5],
                    zoom: 7
                }});
                
                map.on('load', () => {{
                    console.log("✅ 지도 로드 완료");
                    
                    // 타일이 있으면 레이어 추가
                    if (tileUrl && map.getSource('vector-tiles')) {{
                        const waterPaint = {{ 'fill-color': '#2563eb', 'fill-opacity': 0.8 }};
                        const landPaint = {{ 'fill-color': '#16a34a', 'fill-opacity': 0.6 }};
                        const roadPaint = {{ 'line-color': '#ffffff', 'line-width': 2 }};
                        
                        try {{
                            map.addLayer({{
                                id: 'water',
                                type: 'fill',
                                source: 'vector-tiles',
                                'source-layer': 'water',
                                paint: waterPaint
                            }}, 'background');
                        }} catch(e) {{ console.warn('water 레이어 추가 실패:', e); }}
                        
                        try {{
                            map.addLayer({{
                                id: 'landcover',
                                type: 'fill',
                                source: 'vector-tiles',
                                'source-layer': 'landcover',
                                paint: landPaint
                            }}, 'background');
                        }} catch(e) {{ console.warn('landcover 레이어 추가 실패:', e); }}
                        
                        try {{
                            map.addLayer({{
                                id: 'roads',
                                type: 'line',
                                source: 'vector-tiles',
                                'source-layer': 'transportation',
                                paint: roadPaint
                            }}, 'background');
                        }} catch(e) {{ console.warn('roads 레이어 추가 실패:', e); }}
                    }}
                    
                    renderTacticalLayers(map);
                    updateSummary();
                    updateCOAComparison();
                }});
                
                mapInstance = map;
                console.log("✅ 지도 인스턴스 저장 완료");
            }};
            
            // DOMContentLoaded 이벤트와 함께 즉시 실행도 시도 (이미 로드된 경우)
            console.log("🔍 DOM 상태:", document.readyState);
            if (document.readyState === 'loading') {{
                console.log("⏳ DOM 로딩 중... DOMContentLoaded 대기");
                document.addEventListener('DOMContentLoaded', () => {{
                    console.log("✅ DOMContentLoaded 이벤트 발생");
                    setTimeout(initMap, 100);
                }});
            }} else {{
                console.log("✅ DOM이 이미 로드됨. 즉시 실행");
                // DOM이 이미 로드된 경우 즉시 실행
                setTimeout(initMap, 100);
            }}
            
            // 추가 안전장치: 1초 후에도 실행되지 않으면 재시도
            setTimeout(() => {{
                if (!mapInstance) {{
                    console.warn("⚠️ 1초 후에도 지도가 초기화되지 않았습니다. 재시도...");
                    initMap();
                }}
            }}, 1000);
            
            // 전술 레이어 렌더링
            const renderTacticalLayers = (map) => {{
                markersRef = {{}};
                
                // 위협 레이어
                if (copData.threatData && copData.threatData.features) {{
                    copData.threatData.features.forEach((feature, index) => {{
                        const props = feature.properties;
                        const coords = feature.geometry.coordinates;
                        
                        if (feature.geometry.type === "Point") {{
                            const [lng, lat] = coords;
                            const sidc = props.sidc || "SHGPE-----H----";
                            
                            // Milsymbol 아이콘 생성 (milsymbol이 없으면 기본 마커 사용)
                            let el = document.createElement('div');
                            if (typeof ms !== 'undefined' && ms && ms.Symbol) {{
                                try {{
                                    const sym = new ms.Symbol(sidc, {{ size: 30, icon: true }});
                                    el.innerHTML = sym.asSVG();
                                    el.style.width = '30px';
                                    el.style.height = '30px';
                                }} catch (e) {{
                                    console.warn('Milsymbol 생성 실패, 기본 마커 사용:', e);
                                    // 기본 마커 사용
                                    el.innerHTML = '🔴';
                                    el.style.width = '30px';
                                    el.style.height = '30px';
                                    el.style.textAlign = 'center';
                                    el.style.fontSize = '24px';
                                }}
                            }} else {{
                                // milsymbol이 없으면 기본 마커 사용
                                console.warn('Milsymbol 라이브러리가 로드되지 않았습니다. 기본 마커를 사용합니다.');
                                el.innerHTML = '🔴';
                                el.style.width = '30px';
                                el.style.height = '30px';
                                el.style.textAlign = 'center';
                                el.style.fontSize = '24px';
                            }}
                            
                            // MapLibre Marker 생성을 위한 컨테이너 구성
                            const container = document.createElement('div');
                            container.className = 'marker-container';
                            container.style.display = 'flex';
                            container.style.flexDirection = 'column';
                            container.style.alignItems = 'center';
                            
                            // 아이콘 추가
                            container.appendChild(el);
                            
                            // [NEW] 영구 레이블 추가
                            const labelEl = document.createElement('div');
                            labelEl.className = 'marker-label threat-label';
                            labelEl.innerText = props.label || props.name || "위협";
                            container.appendChild(labelEl);
                            
                            // MapLibre Marker 생성
                            const marker = new maplibregl.Marker(container)
                                .setLngLat([lng, lat])
                                .setPopup(new maplibregl.Popup().setHTML(`
                                    <div class="unit-popup">
                                        <h4>${{props.name || "위협"}}</h4>
                                        <div class="info-section">
                                            <div class="info-section-content">
                                                ${{props.description ? `<div style="margin-bottom:8px; font-style:italic; color:#8b949e;">${{props.description}}</div>` : ''}}
                                                <div><strong>유형:</strong> ${{props.threat_type || "알 수 없음"}}</div>
                                                <div><strong>위협수준:</strong> ${{props.threat_level ? (props.threat_level * 100).toFixed(0) + '%' : "N/A"}}</div>
                                                <div><strong>소속:</strong> ${{props.organization || "적군"}}</div>
                                                <div><strong>임무:</strong> ${{props.mission || "알 수 없음"}}</div>
                                                <div><strong>ID:</strong> ${{props.id || "N/A"}}</div>
                                            </div>
                                        </div>
                                    </div>
                                `))
                                .addTo(map);
                            
                            markersRef[`threat-${{index}}`] = marker;
                        }}
                    }});
                }}
                
                // COA 레이어
                if (copData.coaData && copData.coaData.features) {{
                    copData.coaData.features.forEach((feature, index) => {{
                        const props = feature.properties;
                        const coords = feature.geometry.coordinates;
                        
                        if (feature.geometry.type === "Point") {{
                            const [lng, lat] = coords;
                            const sidc = props.sidc || "SFGPE-----H----";
                            
                            // Milsymbol 아이콘 생성
                            let el = document.createElement('div');
                            if (typeof ms !== 'undefined' && ms && ms.Symbol) {{
                                try {{
                                    const sym = new ms.Symbol(sidc, {{ size: 25, icon: true }});
                                    el.innerHTML = sym.asSVG();
                                    el.style.width = '25px';
                                    el.style.height = '25px';
                                }} catch (e) {{
                                    el.innerHTML = '🔵';
                                    el.style.width = '25px';
                                    el.style.height = '25px';
                                    el.style.textAlign = 'center';
                                    el.style.fontSize = '20px';
                                }}
                            }} else {{
                                el.innerHTML = '🔵';
                                el.style.width = '25px';
                                el.style.height = '25px';
                                el.style.textAlign = 'center';
                                el.style.fontSize = '20px';
                            }}
                            
                            const marker = new maplibregl.Marker(el)
                                .setLngLat([lng, lat])
                                .setPopup(new maplibregl.Popup().setHTML(`
                                    <div class="unit-popup">
                                        <h4>${{props.name || "아군 부대"}}</h4>
                                        <div class="info-section">
                                            <div class="info-section-content">
                                                <div><strong>소속:</strong> ${{props.organization || "아군"}}</div>
                                                <div><strong>임무:</strong> ${{props.mission || "대기"}}</div>
                                                <div><strong>ID:</strong> ${{props.id || "N/A"}}</div>
                                            </div>
                                        </div>
                                    </div>
                                `))
                                .addTo(map);
                            
                            markersRef[`coa-${{index}}`] = marker;
                        }}
                    }});
                }}
            }};
            
            // 이전 코드 제거 (복잡한 로직)
            // const oldComplexLogic = () => {{
                            if (e.sourceId === 'vector-tiles') {{
                                const source = map.getSource('vector-tiles');
                                
                                // 타일 요청 상태 추적
                                if (source && source._tiles) {{
                                    const allTiles = Object.values(source._tiles);
                                    const loadedTiles = allTiles.filter(t => t && t.state === 'loaded').length;
                                    const loadingTiles = allTiles.filter(t => t && (t.state === 'loading' || t.state === 'reloading')).length;
                                    const erroredTiles = allTiles.filter(t => t && t.state === 'errored').length;
                                    
                                    // 첫 번째 로드 성공 시
                                    if (loadedTiles > 0 && !firstTileLoaded) {{
                                        firstTileLoaded = true;
                                        tilesLoadedCount = loadedTiles;
                                        console.log(`✅ 벡터 타일 소스 로드됨 (로드된 타일: ${{loadedTiles}}개)`);
                                        
                                        // 첫 번째 타일이 로드되면 레이어 추가 시도
                                        setTimeout(() => {{
                                            if (!layersAdded) {{
                                                addLayersFromTiles();
                                            }}
                                        }}, 500);
                                    }}
                                    
                                    // 타일 상태 로깅 (디버깅용)
                                    if (allTiles.length > 0 && (loadingTiles > 0 || erroredTiles > 0)) {{
                                        console.log(`🔍 타일 상태: 로드됨=${{loadedTiles}}, 로딩 중=${{loadingTiles}}, 에러=${{erroredTiles}}, 전체=${{allTiles.length}}`);
                                        
                                        // 에러가 있는 타일의 URL 확인
                                        if (erroredTiles > 0) {{
                                            const erroredTile = allTiles.find(t => t && t.state === 'errored');
                                            if (erroredTile && erroredTile.url) {{
                                                console.warn(`⚠️ 에러 타일 URL: ${{erroredTile.url}}`);
                                            }}
                                        }}
                                    }}
                                }}
                                
                                // 소스 로드 완료 확인
                                if (e.isSourceLoaded) {{
                                    console.log("✅ 타일 소스 로드 완료");
                                }} else if (e.dataType === 'source') {{
                                    console.log("ℹ️ 타일 소스 데이터 이벤트:", e.dataType);
                                }}
                            }}
                        }});
                        
                        // 타일 로드 에러 감지 (더 상세한 정보)
                        map.on('error', (e) => {{
                            if (e.tile) {{
                                tilesErroredCount++;
                                const tileUrl = e.tile.url || 'unknown';
                                console.warn(`⚠️ 타일 로드 에러 (총 ${{tilesErroredCount}}개):`, e.error?.message || e.error);
                                console.warn(`   타일 URL: ${{tileUrl}}`);
                                console.warn(`   타일 상태: ${{e.tile.state || 'unknown'}}`);
                                
                                // 첫 번째 에러 시 타일 서버 상태 확인
                                if (tilesErroredCount === 1) {{
                                    console.warn("💡 타일 서버 상태 확인 중...");
                                    fetch("http://localhost:8080/")
                                        .then(response => {{
                                            if (response.ok) {{
                                                return response.json();
                                            }}
                                            throw new Error(`HTTP ${{response.status}}`);
                                        }})
                                        .then(data => {{
                                            console.log("✅ 타일 서버 응답:", data);
                                            if (data.mbtiles_available) {{
                                                console.warn("💡 MBTiles 파일은 있지만 타일 요청이 실패했습니다.");
                                                console.warn("💡 타일 좌표나 줌 레벨을 확인하세요.");
                                                
                                                // 샘플 타일 요청 테스트
                                                const testTileUrl = "http://localhost:8080/tiles/7/110/50";
                                                console.log(`🔍 샘플 타일 테스트: ${{testTileUrl}}`);
                                                fetch(testTileUrl)
                                                    .then(tileResponse => {{
                                                        if (tileResponse.ok) {{
                                                            console.log("✅ 샘플 타일 요청 성공");
                                                        }} else {{
                                                            console.error(`❌ 샘플 타일 요청 실패: HTTP ${{tileResponse.status}}`);
                                                        }}
                                                    }})
                                                    .catch(tileError => {{
                                                        console.error("❌ 샘플 타일 요청 에러:", tileError);
                                                    }});
                                            }} else {{
                                                console.warn("⚠️ MBTiles 파일이 없습니다:", data.mbtiles_path || "없음");
                                            }}
                                        }})
                                        .catch(error => {{
                                            console.error("❌ 타일 서버 연결 실패:", error.message);
                                        }});
                                }}
                            }}
                        }});
                        
                        // 타일 소스 데이터 로드 실패 감지
                        map.on('sourcedata', (e) => {{
                            if (e.sourceId === 'vector-tiles' && e.dataType === 'source' && e.isSourceLoaded === false) {{
                                console.warn("⚠️ 타일 소스 로드 실패 감지");
                                console.warn("   소스 ID:", e.sourceId);
                                console.warn("   데이터 타입:", e.dataType);
                            }}
                        }});
                        
                        // 함수는 이미 map.on('load') 전에 정의되어 있음 (중복 제거 완료)
                        
                        // 타일 로드 대기 후 레이어 추가 함수 (레거시, 타일이 이미 로드된 경우 사용)
                        const addLayersFromTiles = (retryCount = 0) => {{
                            try {{
                                const source = map.getSource('vector-tiles');
                                if (!source) {{
                                    console.warn("⚠️ 타일 소스가 없습니다.");
                                    return;
                                }}
                                
                                // 타일이 로드되었는지 확인
                                const tilesLoaded = source._tiles ? Object.values(source._tiles).filter(t => t && t.state === 'loaded').length : 0;
                                
                                if (tilesLoaded === 0 && retryCount < 5) {{
                                    console.log(`⏳ 타일 로드 대기 중... (시도 ${{retryCount + 1}}/5, 로드된 타일: ${{tilesLoaded}}개)`);
                                    setTimeout(() => addLayersFromTiles(retryCount + 1), 1000);
                                    return;
                                }}
                                
                                // 타일이 로드되었거나 재시도 횟수 초과 시 레이어 추가
                                if (tilesLoaded > 0 || retryCount >= 5) {{
                                    console.log(`💡 타일 상태: 로드됨=${{tilesLoaded}}개, 레이어 추가 시도`);
                                    addLayersNow();
                                }}
                                
                            }} catch (e) {{
                                console.error("❌ 레이어 추가 실패:", e);
                            }}
                        }};
                        
                        // 타일 소스 로드 이벤트
                        map.on('sourcedata', (e) => {{
                            if (e.sourceId === 'vector-tiles') {{
                                if (e.isSourceLoaded) {{
                                    tilesLoaded++;
                                    console.log(`✅ 타일 소스 로드됨 (총 ${{tilesLoaded}}개 타일)`);
                                    
                                    // 첫 번째 타일이 로드되면 실제 레이어 목록 확인 및 출력
                                    if (tilesLoaded === 1) {{
                                        // 타일이 완전히 로드될 때까지 대기
                                        const checkTileLayers = (attempt = 0) => {{
                                            if (attempt > 5) {{
                                                console.warn("⚠️ 타일 레이어 정보를 가져올 수 없습니다 (5회 시도 후)");
                                                if (!layersAdded) {{
                                                    addLayersFromTiles();
                                                }}
                                                return;
                                            }}
                                            
                                            const source = map.getSource('vector-tiles');
                                            if (!source || !source._tiles || Object.keys(source._tiles).length === 0) {{
                                                setTimeout(() => checkTileLayers(attempt + 1), 500);
                                                return;
                                            }}
                                            
                                            // 모든 타일에서 레이어 정보 수집
                                            const allLayers = new Set();
                                            let tilesWithLayers = 0;
                                            
                                            Object.values(source._tiles).forEach((tile, index) => {{
                                                if (tile) {{
                                                    // 다양한 방법으로 레이어 정보 확인
                                                    if (tile.vectorLayers && Array.isArray(tile.vectorLayers)) {{
                                                        tile.vectorLayers.forEach(layer => {{
                                                            const layerName = layer.id || layer.name || layer;
                                                            if (layerName) {{
                                                                allLayers.add(layerName);
                                                                tilesWithLayers++;
                                                            }}
                                                        }});
                                                    }}
                                                    
                                                    // 타일이 완전히 로드되었는지 확인
                                                    if (tile.state === 'loaded' && tile.tile) {{
                                                        try {{
                                                            // 타일 데이터에서 직접 레이어 정보 추출 시도
                                                            const tileData = tile.tile;
                                                            if (tileData.layers) {{
                                                                Object.keys(tileData.layers).forEach(layerName => {{
                                                                    allLayers.add(layerName);
                                                                }});
                                                            }}
                                                        }} catch (e) {{
                                                            // 타일 데이터 접근 실패는 무시
                                                        }}
                                                    }}
                                                }}
                                            }});
                                            
                                            if (allLayers.size > 0) {{
                                                const actualLayers = Array.from(allLayers).sort();
                                                console.log("🔍 실제 타일의 레이어 목록:", actualLayers);
                                                console.log(`🔍 레이어 정보를 가진 타일: ${{tilesWithLayers}}개`);
                                                
                                                // 실제 레이어 목록과 현재 추가된 레이어 비교
                                                const currentLayers = ['water', 'landcover', 'roads', 'boundaries'];
                                                currentLayers.forEach(layerId => {{
                                                    const layer = map.getLayer(layerId);
                                                    if (layer) {{
                                                        const sourceLayer = layer.sourceLayer;
                                                        const exists = actualLayers.includes(sourceLayer);
                                                        console.log(`🔍 레이어 ${{layerId}} (source-layer: ${{sourceLayer}}): ${{exists ? '✅ 존재' : '❌ 없음'}}`);
                                                        
                                                        if (!exists) {{
                                                            // 유사한 레이어 이름 찾기
                                                            const similar = actualLayers.filter(l => 
                                                                l.toLowerCase().includes(sourceLayer.toLowerCase()) ||
                                                                sourceLayer.toLowerCase().includes(l.toLowerCase())
                                                            );
                                                            if (similar.length > 0) {{
                                                                console.log(`💡 유사한 레이어 발견: ${{similar.join(', ')}}`);
                                                            }}
                                                        }}
                                                    }}
                                                }});
                                                
                                                // 레이어 추가 시도
                                                if (!layersAdded) {{
                                                    addLayersFromTiles();
                                                }}
                                            }} else {{
                                                console.log(`⏳ 타일 레이어 정보 대기 중... (시도 ${{attempt + 1}}/5)`);
                                                setTimeout(() => checkTileLayers(attempt + 1), 500);
                                            }}
                                        }};
                                        
                                        setTimeout(() => checkTileLayers(), 500);
                                    }}
                                }} else if (e.error) {{
                                    tilesErrored++;
                                    console.warn(`⚠️ 타일 로드 오류 (총 ${{tilesErrored}}개):`, e.error);
                                }}
                            }}
                        }});
                        
                        // 초기 레이어 추가 시도 (지도 로드 직후)
                        setTimeout(() => addLayersFromTiles(), 1000);
                        
                        // 추가 안전장치: 5초 후에도 레이어가 없으면 다시 시도
                        setTimeout(() => {{
                            const hasAnyLayer = ['water', 'landcover', 'roads', 'boundaries'].some(id => map.getLayer(id));
                            if (!hasAnyLayer && !layersAdded) {{
                                console.warn("⚠️ 레이어가 추가되지 않았습니다. 재시도...");
                                addLayersFromTiles();
                            }}
                        }}, 5000);
                    }} else {{
                        console.warn("⚠️ 타일 소스가 없습니다. 기본 배경만 표시됩니다.");
                    }}
                    
                    renderTacticalLayers(map);
                    updateSummary();
                    updateCOAComparison();
                    
                    // 추가 안전장치: 레이어가 추가되었는지 확인
                    setTimeout(() => {{
                        const addedLayers = ['water', 'landcover', 'roads', 'boundaries'].filter(id => map.getLayer(id));
                        console.log(`🔍 추가된 레이어 확인: ${{addedLayers.length}}개 (${{addedLayers.join(', ')}})`);
                        
                        if (addedLayers.length === 0) {{
                            console.warn("⚠️ 레이어가 하나도 추가되지 않았습니다. 재시도...");
                            addLayersFromTilesImmediate();
                        }} else {{
                            // 레이어가 추가되었으므로 타일 로드 상태 확인
                            const source = map.getSource('vector-tiles');
                            if (source && source._tiles) {{
                                const allTiles = Object.values(source._tiles);
                                const loadedTiles = allTiles.filter(t => t && t.state === 'loaded').length;
                                const loadingTiles = allTiles.filter(t => t && (t.state === 'loading' || t.state === 'reloading')).length;
                                const erroredTiles = allTiles.filter(t => t && t.state === 'errored').length;
                                
                                console.log(`🔍 타일 상태 (3초 후): 로드됨=${{loadedTiles}}, 로딩 중=${{loadingTiles}}, 에러=${{erroredTiles}}, 전체=${{allTiles.length}}`);
                                
                                if (erroredTiles > 0 && loadedTiles === 0) {{
                                    console.error("❌ 모든 타일 요청이 실패했습니다. 타일 서버를 확인하세요.");
                                    console.error("   타일 URL: http://localhost:8080/tiles/{{z}}/{{x}}/{{y}}");
                                }}
                            }}
                        }}
                    }}, 3000);
                }});
                
                // 타일 로드 오류 처리
                map.on('error', (e) => {{
                    console.warn("⚠️ 지도 오류:", e);
                    if (e.error && e.error.message && e.error.message.includes('tile')) {{
                        tileLoadFailed = true;
                        console.warn("⚠️ 타일 로드 오류 감지");
                        
                        // 타일 로드 실패 시 GeoJSON fallback 시도
                        if (geojsonUrl && !geojsonFallbackAdded) {{
                            console.log("💡 타일 로드 실패로 인해 GeoJSON fallback으로 전환...");
                            setTimeout(() => addGeoJSONFallback(map), 1000);
                        }}
                    }}
                }});
                
                // GeoJSON fallback 추가 함수
                const addGeoJSONFallback = (map) => {{
                    if (geojsonFallbackAdded) {{
                        console.log("⚠️ GeoJSON fallback이 이미 추가되었습니다.");
                        return;
                    }}
                    
                    const fallbackUrl = baseUrl ? `${{baseUrl}}/maps/korea_osm.geojson` : "";
                    if (!fallbackUrl || fallbackUrl.trim() === "") {{
                        console.warn("⚠️ GeoJSON fallback URL이 없습니다.");
                        return;
                    }}
                    
                    console.log("🗺️ GeoJSON fallback 로드 시도:", fallbackUrl);
                    
                    fetch(fallbackUrl)
                        .then(response => {{
                            if (!response.ok) {{
                                throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                            }}
                            return response.json();
                        }})
                        .then(geojsonData => {{
                            console.log("✅ GeoJSON fallback 로드 성공, features:", geojsonData.features ? geojsonData.features.length : 0);
                            
                            if (!geojsonData || !geojsonData.features || geojsonData.features.length === 0) {{
                                console.warn("⚠️ GeoJSON 데이터가 비어있습니다.");
                                return;
                            }}
                            
                            // GeoJSON 소스 추가 또는 업데이트
                            if (map.getSource('geojson-fallback')) {{
                                map.getSource('geojson-fallback').setData(geojsonData);
                            }} else {{
                                map.addSource('geojson-fallback', {{
                                    type: 'geojson',
                                    data: geojsonData
                                }});
                            }}
                            
                            // GeoJSON 레이어 추가 (타일이 없을 때만)
                            if (!map.getLayer('geojson-land')) {{
                                // 육지 레이어
                                map.addLayer({{
                                    id: 'geojson-land',
                                    type: 'fill',
                                    source: 'geojson-fallback',
                                    paint: {{
                                        'fill-color': '#2d4a3e',
                                        'fill-opacity': 0.5,
                                        'fill-outline-color': '#4a5568'
                                    }},
                                    filter: ['==', '$type', 'Polygon']
                                }}, 'background'); // background 레이어 위에 추가
                                
                                // 경계선 레이어
                                map.addLayer({{
                                    id: 'geojson-boundaries',
                                    type: 'line',
                                    source: 'geojson-fallback',
                                    paint: {{
                                        'line-color': '#718096',
                                        'line-width': 1.5,
                                        'line-opacity': 0.8
                                    }},
                                    filter: ['==', '$type', 'LineString']
                                }}, 'geojson-land'); // 육지 레이어 위에 추가
                                
                                console.log("✅ GeoJSON 레이어 추가 완료");
                                
                                // 지도 범위 조정
                                try {{
                                    const bounds = new maplibregl.LngLatBounds();
                                    let hasBounds = false;
                                    
                                    geojsonData.features.forEach(feature => {{
                                        if (feature.geometry && feature.geometry.coordinates) {{
                                            if (feature.geometry.type === 'Polygon' && feature.geometry.coordinates[0]) {{
                                                feature.geometry.coordinates[0].forEach(coord => {{
                                                    if (Array.isArray(coord) && coord.length >= 2) {{
                                                        bounds.extend([coord[0], coord[1]]);
                                                        hasBounds = true;
                                                    }}
                                                }});
                                            }} else if (feature.geometry.type === 'LineString') {{
                                                feature.geometry.coordinates.forEach(coord => {{
                                                    if (Array.isArray(coord) && coord.length >= 2) {{
                                                        bounds.extend([coord[0], coord[1]]);
                                                        hasBounds = true;
                                                    }}
                                                }});
                                            }}
                                        }}
                                    }});
                                    
                                    if (hasBounds && !bounds.isEmpty()) {{
                                        map.fitBounds(bounds, {{ padding: 50, maxZoom: 8, duration: 1000 }});
                                        console.log("✅ 지도 범위 조정 완료");
                                    }}
                                }} catch (e) {{
                                    console.warn("⚠️ 지도 범위 조정 실패:", e);
                                }}
                            }}
                            
                            geojsonFallbackAdded = true;
                        }})
                        .catch(error => {{
                            console.error("❌ GeoJSON fallback 로드 실패:", error);
                            console.warn("⚠️ 기본 배경만 표시됩니다. 서버 상태를 확인하세요:", fallbackUrl);
                        }});
                }};
                
                // 소스 오류 처리 (타일 로드 오류는 위에서 이미 처리됨)
                map.on('sourcedata', (e) => {{
                    if (e.isSourceLoaded && e.source && e.source.type === 'vector') {{
                        console.log("✅ 벡터 타일 소스 로드됨");
                    }} else if (e.error && e.sourceId === 'vector-tiles') {{
                        console.warn("⚠️ 벡터 타일 소스 로드 실패:", e.error);
                        tileLoadFailed = true;
                        if (!geojsonFallbackAdded) {{
                            setTimeout(() => addGeoJSONFallback(map), 1000);
                        }}
                    }}
                }});
                
                mapInstance = map;
                }});
            }};
            
            // DOMContentLoaded 이벤트와 함께 즉시 실행도 시도 (이미 로드된 경우)
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', initMap);
            }} else {{
                // DOM이 이미 로드된 경우 즉시 실행
                setTimeout(initMap, 100);
            }}
            
            // 전술 레이어 렌더링
            const renderTacticalLayers = (map) => {{
                markersRef = {{}};
                    
                    // 위협 레이어
                    if (copData.threatData && copData.threatData.features) {{
                        copData.threatData.features.forEach((feature, index) => {{
                            const props = feature.properties;
                            const coords = feature.geometry.coordinates;
                            
                            if (feature.geometry.type === "Point") {{
                                const [lng, lat] = coords;
                                const sidc = props.sidc || "SHGPE-----H----";
                                
                                                // Milsymbol 아이콘 생성 (milsymbol이 없으면 기본 마커 사용)
                                let el = document.createElement('div');
                                if (typeof ms !== 'undefined' && ms && ms.Symbol) {{
                                    try {{
                                        const sym = new ms.Symbol(sidc, {{ size: 30, icon: true }});
                                        el.innerHTML = sym.asSVG();
                                        el.style.width = '30px';
                                        el.style.height = '30px';
                                    }} catch (e) {{
                                        console.warn('Milsymbol 생성 실패, 기본 마커 사용:', e);
                                        // 기본 마커 사용
                                        el.innerHTML = '🔴';
                                        el.style.width = '30px';
                                        el.style.height = '30px';
                                        el.style.textAlign = 'center';
                                        el.style.fontSize = '24px';
                                    }}
                                }} else {{
                                    // milsymbol이 없으면 기본 마커 사용
                                    console.warn('Milsymbol 라이브러리가 로드되지 않았습니다. 기본 마커를 사용합니다.');
                                    el.innerHTML = '🔴';
                                    el.style.width = '30px';
                                    el.style.height = '30px';
                                    el.style.textAlign = 'center';
                                    el.style.fontSize = '24px';
                                }}
                                
                                // MapLibre Marker 생성
                                const marker = new maplibregl.Marker(el)
                                    .setLngLat([lng, lat])
                                    .setPopup(new maplibregl.Popup().setHTML(`
                                        <div class="unit-popup">
                                            <h4>${{props.name || "위협"}}</h4>
                                            <div class="info-section">
                                                <div class="info-section-title">위협 유형</div>
                                                <div class="info-section-content">${{props.threat_type || "알 수 없음"}}</div>
                                            </div>
                                            ${{props.confidence ? `
                                            <div class="info-section">
                                                <div class="info-section-title">신뢰도</div>
                                                <div class="info-section-content">${{(props.confidence * 100).toFixed(0)}}%</div>
                                            </div>
                                            ` : ""}}
                                            ${{props.affected_coa && props.affected_coa.length > 0 ? `
                                            <div class="info-section">
                                                <div class="info-section-title">영향받는 COA</div>
                                                <div class="info-section-content">${{props.affected_coa.join(", ")}}</div>
                                            </div>
                                            ` : ""}}
                                            ${{props.threat_uri ? `
                                            <div class="info-section">
                                                <div class="info-section-title">온톨로지 URI</div>
                                                <div class="info-section-content ontology-uri">${{props.threat_uri}}</div>
                                            </div>
                                            ` : ""}}
                                        </div>
                                    `))
                                    .addTo(map);
                                
                                // 위협 개념적 표현 (반경 시각화 금지)
                                const threatType = (props.threat_type || "unknown").toLowerCase();
                                const confidence = props.confidence || 0.5;
                                
                                // 위협 유형별 개념적 표현
                                if (threatType.includes("missile") || threatType.includes("미사일")) {{
                                    // 미사일: 위협 방향 화살표
                                    const threatRadius = props.threat_radius || 50000;
                                    const arrowLength = Math.min(threatRadius / 10, 20000);
                                    
                                    let targetDirection = [0, 1];
                                    if (copData.coaData && copData.coaData.features) {{
                                        const blueUnits = copData.coaData.features.filter(f => 
                                            f.geometry.type === "Point" && f.properties.type === "BLUE"
                                        );
                                        if (blueUnits.length > 0) {{
                                            const nearestUnit = blueUnits.reduce((nearest, unit) => {{
                                                const unitCoords = unit.geometry.coordinates;
                                                const dist = Math.sqrt(
                                                    Math.pow(unitCoords[1] - lat, 2) + 
                                                    Math.pow(unitCoords[0] - lng, 2)
                                                );
                                                const nearestDist = Math.sqrt(
                                                    Math.pow(nearest.geometry.coordinates[1] - lat, 2) + 
                                                    Math.pow(nearest.geometry.coordinates[0] - lng, 2)
                                                );
                                                return dist < nearestDist ? unit : nearest;
                                            }});
                                            
                                            const unitCoords = nearestUnit.geometry.coordinates;
                                            const dx = unitCoords[0] - lng;
                                            const dy = unitCoords[1] - lat;
                                            const dist = Math.sqrt(dx * dx + dy * dy);
                                            targetDirection = [dy / dist, dx / dist];
                                        }}
                                    }}
                                    
                                    const arrowEnd = [
                                        lng + targetDirection[1] * (arrowLength / (111000 * Math.cos(lat * Math.PI / 180))),
                                        lat + targetDirection[0] * (arrowLength / 111000)
                                    ];
                                    
                                    // 화살표 GeoJSON 소스 추가
                                    const arrowSourceId = `threat-arrow-${{index}}`;
                                    map.addSource(arrowSourceId, {{
                                        type: 'geojson',
                                        data: {{
                                            type: 'Feature',
                                            geometry: {{
                                                type: 'LineString',
                                                coordinates: [[lng, lat], arrowEnd]
                                            }}
                                        }}
                                    }});
                                    
                                    map.addLayer({{
                                        id: `threat-arrow-line-${{index}}`,
                                        type: 'line',
                                        source: arrowSourceId,
                                        paint: {{
                                            'line-color': '#ff1744',
                                            'line-width': 3,
                                            'line-opacity': 0.8,
                                            'line-dasharray': [10, 5]
                                        }}
                                    }});
                                    
                                }} else if (threatType.includes("artillery") || threatType.includes("포병")) {{
                                    // 포병: 부채꼴 범위
                                    const threatRadius = props.threat_radius || 30000;
                                    const sectorAngle = 45;
                                    const bearing = 180;
                                    
                                    const sectorPoints = [[lng, lat]];
                                    const numPoints = 20;
                                    for (let i = 0; i <= numPoints; i++) {{
                                        const angle = (bearing - sectorAngle / 2) + (sectorAngle * i / numPoints);
                                        const rad = angle * Math.PI / 180;
                                        const sectorLng = lng + (threatRadius / (111000 * Math.cos(lat * Math.PI / 180))) * Math.sin(rad);
                                        const sectorLat = lat + (threatRadius / 111000) * Math.cos(rad);
                                        sectorPoints.push([sectorLng, sectorLat]);
                                    }}
                                    
                                    const sectorSourceId = `threat-sector-${{index}}`;
                                    map.addSource(sectorSourceId, {{
                                        type: 'geojson',
                                        data: {{
                                            type: 'Feature',
                                            geometry: {{
                                                type: 'Polygon',
                                                coordinates: [sectorPoints]
                                            }}
                                        }}
                                    }});
                                    
                                    map.addLayer({{
                                        id: `threat-sector-fill-${{index}}`,
                                        type: 'fill',
                                        source: sectorSourceId,
                                        paint: {{
                                            'fill-color': '#ff6b6b',
                                            'fill-opacity': 0.2
                                        }}
                                    }});
                                    
                                    map.addLayer({{
                                        id: `threat-sector-line-${{index}}`,
                                        type: 'line',
                                        source: sectorSourceId,
                                        paint: {{
                                            'line-color': '#ff6b6b',
                                            'line-width': 2,
                                            'line-dasharray': [5, 5]
                                        }}
                                    }});
                                    
                                }} else {{
                                    // 기타 위협: 신뢰도에 따라 아이콘 크기/색상
                                    const iconSize = 30 + (confidence * 20);
                                    const iconColor = confidence > 0.7 ? '#ff1744' : confidence > 0.4 ? '#ff6b6b' : '#ff9999';
                                    
                                    // 기존 el 요소를 업데이트하거나 새로 생성
                                    const iconEl = document.createElement('div');
                                    
                                    if (typeof ms !== 'undefined' && ms && ms.Symbol) {{
                                        try {{
                                            const sym = new ms.Symbol(sidc, {{ 
                                                size: iconSize, 
                                                icon: true,
                                                colorMode: 'Light',
                                                fill: true,
                                                fillColor: iconColor
                                            }});
                                            iconEl.innerHTML = sym.asSVG();
                                        }} catch (e) {{
                                            console.warn('Milsymbol 생성 실패:', e);
                                            iconEl.innerHTML = '🔴';
                                            iconEl.style.fontSize = `${{iconSize * 0.8}}px`;
                                            iconEl.style.textAlign = 'center';
                                        }}
                                    }} else {{
                                        iconEl.innerHTML = '🔴';
                                        iconEl.style.fontSize = `${{iconSize * 0.8}}px`;
                                        iconEl.style.textAlign = 'center';
                                    }}
                                    
                                    iconEl.style.width = `${{iconSize}}px`;
                                    iconEl.style.height = `${{iconSize}}px`;
                                    
                                    // 마커 요소 업데이트
                                    marker.getElement().innerHTML = iconEl.innerHTML;
                                    marker.getElement().style.width = `${{iconSize}}px`;
                                    marker.getElement().style.height = `${{iconSize}}px`;
                                    if (iconEl.style.textAlign) {{
                                        marker.getElement().style.textAlign = iconEl.style.textAlign;
                                    }}
                                    if (iconEl.style.fontSize) {{
                                        marker.getElement().style.fontSize = iconEl.style.fontSize;
                                    }}
                                }}
                                
                                // 위협 데이터 저장
                                markersRef[`threat-${{index}}`] = {{
                                    type: 'threat',
                                    marker: marker,
                                    sidc: sidc,
                                    name: props.name,
                                    threatData: {{
                                        threat_type: threatType,
                                        confidence: confidence,
                                        affected_coa: props.affected_coa || [],
                                        isHighlighted: false
                                    }}
                                }};
                            }}
                        }});
                    }}
                    
                    // COA 경로 및 부대 레이어
                    if (copData.coaData && copData.coaData.features) {{
                        copData.coaData.features.forEach((feature, index) => {{
                            const props = feature.properties;
                            
                            if (feature.geometry.type === "LineString") {{
                                // COA 경로 (LineString)
                                const coords = feature.geometry.coordinates;
                                const isSelected = selectedCOA && (props.coa_id === selectedCOA.coa_id || props.coa_name === selectedCOA.coa_name);
                                
                                const coaSourceId = `coa-path-${{index}}`;
                                map.addSource(coaSourceId, {{
                                    type: 'geojson',
                                    data: {{
                                        type: 'Feature',
                                        geometry: feature.geometry,
                                        properties: props
                                    }}
                                }});
                                
                                map.addLayer({{
                                    id: `coa-path-line-${{index}}`,
                                    type: 'line',
                                    source: coaSourceId,
                                    paint: {{
                                        'line-color': isSelected ? '#58a6ff' : '#8b949e',
                                        'line-width': isSelected ? 5 : 3,
                                        'line-opacity': 0.8,
                                        'line-dasharray': [10, 10]
                                    }}
                                }});
                                
                            }} else if (feature.geometry.type === "Point") {{
                                // 아군 부대 (Point)
                                const [lng, lat] = feature.geometry.coordinates;
                                const sidc = props.sidc || "SFAPM-----H----";
                                
                                const el = document.createElement('div');
                                if (typeof ms !== 'undefined' && ms && ms.Symbol) {{
                                    try {{
                                        const sym = new ms.Symbol(sidc, {{ size: 30, icon: true }});
                                        el.innerHTML = sym.asSVG();
                                    }} catch (e) {{
                                        console.warn('Milsymbol 생성 실패, 기본 마커 사용:', e);
                                        el.innerHTML = '🔵';
                                        el.style.fontSize = '24px';
                                    }}
                                }} else {{
                                    el.innerHTML = '🔵';
                                    el.style.fontSize = '24px';
                                }}
                                el.style.width = '30px';
                                el.style.height = '30px';
                                el.style.textAlign = 'center';
                                
                                const marker = new maplibregl.Marker(el)
                                    .setLngLat([lng, lat])
                                    .setPopup(new maplibregl.Popup().setHTML(`
                                        <div class="unit-popup">
                                            <h4>${{props.name || "아군 부대"}}</h4>
                                            <div class="info-section">
                                                <div class="info-section-title">정적 정보</div>
                                                <div class="info-section-content">
                                                    ${{props.organization ? `편제: ${{props.organization}}<br>` : ""}}
                                                    ${{props.unit_type ? `제대: ${{props.unit_type}}` : ""}}
                                                </div>
                                            </div>
                                            <div class="info-section">
                                                <div class="info-section-title">동적 상태</div>
                                                <div class="info-section-content">
                                                    ${{props.mission ? `임무: ${{props.mission}}<br>` : ""}}
                                                    ${{props.availability ? `가용성: ${{props.availability}}` : ""}}
                                                </div>
                                            </div>
                                            ${{props.coa_inclusion_reason || props.coa_exclusion_reason ? `
                                            <div class="info-section">
                                                <div class="info-section-title">추론 연계</div>
                                                <div class="info-section-content">
                                                    ${{props.coa_inclusion_reason ? `포함 이유: ${{props.coa_inclusion_reason}}<br>` : ""}}
                                                    ${{props.coa_exclusion_reason ? `제외 이유: ${{props.coa_exclusion_reason}}` : ""}}
                                                </div>
                                            </div>
                                            ` : ""}}
                                            ${{props.unit_uri ? `
                                            <div class="info-section">
                                                <div class="info-section-title">온톨로지 URI</div>
                                                <div class="info-section-content ontology-uri">${{props.unit_uri}}</div>
                                            </div>
                                            ` : ""}}
                                        </div>
                                    `))
                                    .addTo(map);
                                
                                markersRef[`unit-${{index}}`] = {{
                                    type: 'unit',
                                    marker: marker,
                                    sidc: sidc,
                                    name: props.name
                                }};
                            }}
                        }});
                    }}
                }};
                
            // 시간 단계 업데이트 함수
            const updateTimeStep = (newStep) => {{
                timeStep = Math.max(0, Math.min(timeSteps.length - 1, newStep));
                document.getElementById('time-slider').value = timeStep;
                document.getElementById('time-step-label').textContent = timeSteps[timeStep];
                
                // 버튼 활성화/비활성화
                document.getElementById('time-prev-btn').disabled = timeStep === 0;
                document.getElementById('time-next-btn').disabled = timeStep === timeSteps.length - 1;
                
                // COA 비교 업데이트 (시간 단계에 따라 상태 변경)
                updateCOAComparison();
                
                // 지도 레이어 업데이트 (필요시)
                if (mapInstance && mapInstance.loaded()) {{
                    if (selectedCOA) {{
                        highlightThreatsForCOA(selectedCOA);
                    }}
                }}
            }};
            
            // 닫기 버튼 이벤트 리스너 등록 함수 (재사용 가능)
            const attachCloseButtonHandler = () => {{
                const closeReasoningBtn = document.getElementById('close-reasoning-btn');
                if (closeReasoningBtn) {{
                    // 기존 이벤트 리스너 제거 (중복 방지)
                    const newBtn = closeReasoningBtn.cloneNode(true);
                    closeReasoningBtn.parentNode.replaceChild(newBtn, closeReasoningBtn);
                    
                    // 새 이벤트 리스너 등록
                    newBtn.addEventListener('click', () => {{
                        const rightPanel = document.getElementById('right-panel');
                        if (rightPanel) {{
                            rightPanel.classList.remove('active');
                            showReasoning = false;
                        }}
                    }});
                }}
            }};
            
            // 이벤트 리스너 설정
            document.addEventListener('DOMContentLoaded', () => {{
                // 시간 슬라이더
                const timeSlider = document.getElementById('time-slider');
                if (timeSlider) {{
                    timeSlider.addEventListener('input', (e) => {{
                        updateTimeStep(parseInt(e.target.value));
                    }});
                }}
                
                // 이전/다음 버튼
                const timePrevBtn = document.getElementById('time-prev-btn');
                const timeNextBtn = document.getElementById('time-next-btn');
                if (timePrevBtn) {{
                    timePrevBtn.addEventListener('click', () => {{
                        updateTimeStep(timeStep - 1);
                    }});
                }}
                if (timeNextBtn) {{
                    timeNextBtn.addEventListener('click', () => {{
                        updateTimeStep(timeStep + 1);
                    }});
                }}
                
                // 추론 근거 패널 닫기 버튼 (초기 등록)
                attachCloseButtonHandler();
                
                // 초기 UI 업데이트
                updateTimeStep(0);
            }});
                
        </script>
    </body>
    </html>
    """
    
    # 렌더링
    # 데이터 해시를 기반으로 컴포넌트 키 생성 (Streamlit이 변경사항을 추적)
    # components.html은 key를 지원하지 않지만, 데이터 해시 기반 최적화로
    # 지도 재초기화를 최소화합니다.
    
    components.html(html_code, height=height)
