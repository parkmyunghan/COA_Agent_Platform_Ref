# ui/components/ontology_aware_cop_leaflet.py
# -*- coding: utf-8 -*-
"""
Ontology-aware COP Component (Leaflet 기반)
온톨로지 기반 방책 추천 결과를 공간적으로 검증하는 지휘 인터페이스

핵심 원칙:
- COP는 "상황 표시 지도"가 아니라 "온톨로지 추론 결과를 공간적으로 검증하는 지휘 인터페이스"
- 지도는 배경이며, 핵심은 COA 판단과 설명
- 모든 전술 객체는 온톨로지 URI를 포함해야 함
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
    height: int = 700,
    offline_mode: bool = True
):
    """
    온톨로지 인식 COP 렌더링 (Leaflet 기반)
    
    Args:
        coa_recommendations: COA 추천 결과 리스트 (점수, 추론 근거 포함)
        threat_geojson: 위협 GeoJSON (온톨로지 URI 포함)
        coa_geojson: COA GeoJSON (온톨로지 URI 포함)
        ontology_manager: 온톨로지 매니저 (추론 경로 조회용)
        height: 컴포넌트 높이
        offline_mode: 오프라인 모드
    """
    
    # 프로젝트 루트 경로
    BASE_DIR = Path(__file__).parent.parent.parent
    
    # 데이터 준비
    cop_data = {
        "coaRecommendations": coa_recommendations or [],
        "threatData": threat_geojson or {"type": "FeatureCollection", "features": []},
        "coaData": coa_geojson or {"type": "FeatureCollection", "features": []},
        "ontologyAvailable": ontology_manager is not None
    }
    
    json_props = json.dumps(cop_data, ensure_ascii=False)
    
    # 리소스 경로
    base_url = "http://localhost:8080" if offline_mode else ""
    resources = {
        "leaflet_css": f"{base_url}/static/lib/leaflet.css" if offline_mode else "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
        "leaflet_js": f"{base_url}/static/lib/leaflet.js" if offline_mode else "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
        "milsymbol": f"{base_url}/static/lib/milsymbol.js" if offline_mode else "https://unpkg.com/milsymbol@2.0.0/dist/milsymbol.js",
        "react": f"{base_url}/static/lib/react.production.min.js" if offline_mode else "https://unpkg.com/react@18/umd/react.production.min.js",
        "react_dom": f"{base_url}/static/lib/react-dom.production.min.js" if offline_mode else "https://unpkg.com/react-dom@18/umd/react-dom.production.min.js",
        "babel": f"{base_url}/static/lib/babel.min.js" if offline_mode else "https://unpkg.com/babel-standalone@6/babel.min.js"
    }
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        
        <!-- Leaflet CSS -->
        <link rel="stylesheet" href="{resources['leaflet_css']}" />
        
        <style>
            body {{ margin: 0; padding: 0; background-color: #0d1117; font-family: 'Segoe UI', sans-serif; overflow: hidden; }}
            #root {{ width: 100vw; height: {height}px; position: relative; }}
            
            /* COP Layout */
            .cop-container {{ width: 100%; height: 100%; position: relative; }}
            
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
                font-family: 'Consolas', monospace;
                color: #c9d1d9;
                line-height: 1.6;
            }}
            
            .ontology-uri {{
                font-size: 10px;
                color: #58a6ff;
                word-break: break-all;
                margin-top: 4px;
            }}
            
            /* 하단 패널: COA 비교 */
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
            
            .coa-type {{
                font-size: 11px;
                color: #8b949e;
                margin-top: 4px;
            }}
            
            /* 지도 컨테이너 */
            .map-container {{
                width: 100%;
                height: 100%;
            }}
            
            /* Leaflet Customization */
            .leaflet-container {{
                background: #0d1117;
            }}
            
            .unit-popup {{
                background: #161b22;
                color: #c9d1d9;
                padding: 12px;
                border-radius: 4px;
                font-size: 12px;
                max-width: 300px;
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
        </style>
        
        <!-- React & DOM -->
        <script crossorigin src="{resources['react']}"></script>
        <script crossorigin src="{resources['react_dom']}"></script>
        <script src="{resources['babel']}"></script>
        
        <!-- Leaflet & Libraries -->
        <script src="{resources['leaflet_js']}"></script>
        <script src="{resources['milsymbol']}"></script>
    </head>
    <body>
        <div id="root"></div>

        <script type="text/babel">
            const {{ useState, useEffect, useRef }} = React;

            // Initial Data
            const copData = {json_props};
            
            const OntologyAwareCOP = () => {{
                const mapRef = useRef(null);
                const mapInstanceRef = useRef(null);
                const layerRefs = useRef({{}});
                const [selectedCOA, setSelectedCOA] = useState(null);
                const [selectedUnit, setSelectedUnit] = useState(null);
                const [showReasoning, setShowReasoning] = useState(false);
                const [timeStep, setTimeStep] = useState(0); // 시간 단계 (0: 초기, 1: 실행, 2: 완료)
                const [timeSteps] = useState(["초기 상황", "작전 실행", "작전 완료"]); // 시간 단계 라벨
                
                // Initialize Map
                useEffect(() => {{
                    if (!mapRef.current || mapInstanceRef.current) return;
                    
                    // Leaflet 지도 초기화
                    const map = L.map(mapRef.current, {{
                        center: [36.5, 127.5], // 한반도 중심
                        zoom: 7,
                        zoomControl: true,
                        attributionControl: true,
                        minZoom: 5,
                        maxZoom: 14
                    }});
                    
                    // 배경 레이어 (기본 배경)
                    L.rectangle(
                        [[33, 124], [39, 132]],
                        {{
                            color: '#d0e8f0',
                            fillColor: '#e8f4f8',
                            fillOpacity: 1.0,
                            weight: 0
                        }}
                    ).addTo(map);
                    
                    // 전술 레이어 렌더링
                    renderTacticalLayers(map);
                    
                    mapInstanceRef.current = map;
                }}, []);
                
                // 추론 경로 그래프 렌더링 함수
                const renderReasoningPathGraph = (reasoningPath) => {{
                    if (!reasoningPath || !Array.isArray(reasoningPath)) {{
                        return '<div style="color: #8b949e; font-size: 11px;">추론 경로 데이터가 없습니다.</div>';
                    }}
                    
                    // 간단한 트리 구조로 표시
                    let html = '<div style="font-family: Consolas, monospace; font-size: 10px; line-height: 1.8;">';
                    
                    reasoningPath.forEach((path, index) => {{
                        const threat = path.threat || path.threat_uri || 'Unknown';
                        const relation = path.relation || path.relation_uri || 'relatedTo';
                        const coa = path.coa || path.coa_uri || 'Current COA';
                        
                        // URI에서 로컬 이름 추출
                        const getLocalName = (uri) => {{
                            if (!uri) return 'Unknown';
                            const parts = uri.split('#');
                            return parts.length > 1 ? parts[parts.length - 1] : uri.split('/').pop();
                        }};
                        
                        const threatName = getLocalName(threat);
                        const relationName = getLocalName(relation);
                        const coaName = getLocalName(coa);
                        
                        // 트리 구조 시각화
                        html += `
                            <div style="margin-bottom: 8px; padding: 8px; background: rgba(0,0,0,0.2); border-radius: 3px; border-left: 3px solid #58a6ff;">
                                <div style="color: #58a6ff; font-weight: 600; margin-bottom: 4px;">
                                    ${index + 1}. 경로
                                </div>
                                <div style="color: #c9d1d9; margin-left: 12px;">
                                    <div style="margin-bottom: 2px;">
                                        <span style="color: #ff6b6b;">위협:</span> 
                                        <span style="color: #79c0ff;">${threatName}</span>
                                    </div>
                                    <div style="margin-bottom: 2px; margin-left: 8px;">
                                        <span style="color: #8b949e;">${relationName}</span>
                                    </div>
                                    <div>
                                        <span style="color: #3fb950;">COA:</span> 
                                        <span style="color: #79c0ff;">${coaName}</span>
                                    </div>
                                </div>
                            </div>
                        `;
                    }});
                    
                    html += '</div>';
                    return html;
                }};
                
                // COA 선택 시 위협 강조 함수 (먼저 정의)
                const highlightThreatsForCOA = (coa) => {{
                    if (!mapInstanceRef.current || !coa) return;
                    
                    const coaId = coa.coa_id || coa.coa_name;
                    const exposedThreats = coa.exposed_threats || [];
                    
                    // 위협 레이어의 모든 마커 확인
                    if (layerRefs.current.threats) {{
                        layerRefs.current.threats.eachLayer((layer) => {{
                            if (layer instanceof L.Marker && layer._threatData) {{
                                const threatData = layer._threatData;
                                const affectedCOAs = threatData.affected_coa || [];
                                
                                // 선택된 COA와 관련된 위협인지 확인
                                const isRelated = 
                                    affectedCOAs.includes(coaId) || 
                                    affectedCOAs.includes(coa.coa_name) ||
                                    exposedThreats.some(t => 
                                        t === threatData.threat_type || 
                                        t === layer.options.title
                                    );
                                
                                if (isRelated) {{
                                    // 관련 위협 강조
                                    threatData.isHighlighted = true;
                                    
                                    // 아이콘 크기 증가 및 색상 변경
                                    const currentIcon = layer.options.icon;
                                    if (currentIcon) {{
                                        const sidc = layer.options.icon.options.html ? 
                                            layer.options.icon.options.html.match(/sidc="([^"]+)"/)?.[1] || "SHGPE-----H----" :
                                            "SHGPE-----H----";
                                        
                                        const sym = new ms.Symbol(sidc, {{ 
                                            size: 40, 
                                            icon: true,
                                            colorMode: 'Light',
                                            fill: true,
                                            fillColor: '#ff1744'
                                        }});
                                        
                                        const highlightedIcon = L.divIcon({{
                                            className: 'threat-highlighted',
                                            html: sym.asSVG(),
                                            iconSize: [40, 40],
                                            iconAnchor: [20, 20]
                                        }});
                                        
                                        layer.setIcon(highlightedIcon);
                                        
                                        // 펄스 애니메이션 효과
                                        layer.setZIndexOffset(1000);
                                    }}
                                    
                                    layer.setOpacity(1.0);
                                }} else {{
                                    // 관련 없는 위협은 반투명 처리
                                    threatData.isHighlighted = false;
                                    layer.setOpacity(0.3);
                                    layer.setZIndexOffset(0);
                                }}
                            }}
                        }});
                    }}
                }};
                
                // 전술 레이어 렌더링
                const renderTacticalLayers = (map) => {{
                    layerRefs.current = {{}};
                    
                    // 위협 레이어
                    layerRefs.current.threats = L.layerGroup().addTo(map);
                    layerRefs.current.threatZones = L.layerGroup().addTo(map);
                    
                    // 아군 레이어
                    layerRefs.current.blueUnits = L.layerGroup().addTo(map);
                    layerRefs.current.coaPaths = L.layerGroup().addTo(map);
                    
                    // 위협 표시
                    if (copData.threatData && copData.threatData.features) {{
                        copData.threatData.features.forEach((feature, index) => {{
                            const props = feature.properties;
                            const coords = feature.geometry.coordinates;
                            
                            if (feature.geometry.type === "Point") {{
                                const latlng = [coords[1], coords[0]];
                                const sidc = props.sidc || "SHGPE-----H----";
                                
                                // Milsymbol 아이콘 생성
                                const sym = new ms.Symbol(sidc, {{ size: 30, icon: true }});
                                const icon = L.divIcon({{
                                    className: '',
                                    html: sym.asSVG(),
                                    iconSize: [30, 30],
                                    iconAnchor: [15, 15]
                                }});
                                
                                // 위협 마커
                                const marker = L.marker(latlng, {{ icon }}).addTo(layerRefs.current.threats);
                                
                                // 팝업 내용 (3계층 정보)
                                let popupContent = `
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
                                `;
                                
                                marker.bindPopup(popupContent);
                                
                                // 위협 개념적 표현 (반경 시각화 금지)
                                // 위협 유형에 따라 다른 시각적 표현
                                const threatType = (props.threat_type || "unknown").toLowerCase();
                                const confidence = props.confidence || 0.5;
                                
                                // 위협 유형별 개념적 표현
                                if (threatType.includes("missile") || threatType.includes("미사일")) {{
                                    // 미사일: 위협 방향을 나타내는 화살표 (가장 가까운 아군/목표 방향)
                                    // 위협 영향 범위를 화살표 길이로 표현
                                    const threatRadius = props.threat_radius || 50000; // 기본 50km
                                    const arrowLength = Math.min(threatRadius / 10, 20000); // 최대 20km
                                    
                                    // 가장 가까운 아군 부대 찾기 (COA 데이터에서)
                                    let targetDirection = [0, 1]; // 기본 남쪽
                                    if (copData.coaData && copData.coaData.features) {{
                                        const blueUnits = copData.coaData.features.filter(f => 
                                            f.geometry.type === "Point" && f.properties.type === "BLUE"
                                        );
                                        if (blueUnits.length > 0) {{
                                            const nearestUnit = blueUnits.reduce((nearest, unit) => {{
                                                const unitLat = unit.geometry.coordinates[1];
                                                const unitLng = unit.geometry.coordinates[0];
                                                const dist = Math.sqrt(
                                                    Math.pow(unitLat - latlng[0], 2) + 
                                                    Math.pow(unitLng - latlng[1], 2)
                                                );
                                                const nearestDist = Math.sqrt(
                                                    Math.pow(nearest.geometry.coordinates[1] - latlng[0], 2) + 
                                                    Math.pow(nearest.geometry.coordinates[0] - latlng[1], 2)
                                                );
                                                return dist < nearestDist ? unit : nearest;
                                            }});
                                            
                                            const unitLat = nearestUnit.geometry.coordinates[1];
                                            const unitLng = nearestUnit.geometry.coordinates[0];
                                            const dx = unitLng - latlng[1];
                                            const dy = unitLat - latlng[0];
                                            const dist = Math.sqrt(dx * dx + dy * dy);
                                            targetDirection = [dy / dist, dx / dist];
                                        }}
                                    }}
                                    
                                    // 화살표 끝점 계산
                                    const arrowEnd = [
                                        latlng[0] + targetDirection[0] * (arrowLength / 111000), // 위도
                                        latlng[1] + targetDirection[1] * (arrowLength / (111000 * Math.cos(latlng[0] * Math.PI / 180))) // 경도
                                    ];
                                    
                                    // 화살표 폴리라인
                                    const arrow = L.polyline([latlng, arrowEnd], {{
                                        color: '#ff1744',
                                        weight: 3,
                                        opacity: 0.8,
                                        dashArray: '10, 5'
                                    }}).addTo(layerRefs.current.threatZones);
                                    
                                    // 화살표 머리 (삼각형)
                                    const arrowHead = L.polygon([
                                        arrowEnd,
                                        [
                                            arrowEnd[0] - targetDirection[0] * 0.001 + targetDirection[1] * 0.0005,
                                            arrowEnd[1] - targetDirection[1] * 0.001 - targetDirection[0] * 0.0005
                                        ],
                                        [
                                            arrowEnd[0] - targetDirection[0] * 0.001 - targetDirection[1] * 0.0005,
                                            arrowEnd[1] - targetDirection[1] * 0.001 + targetDirection[0] * 0.0005
                                        ]
                                    ], {{
                                        color: '#ff1744',
                                        fillColor: '#ff1744',
                                        fillOpacity: 0.6,
                                        weight: 2
                                    }}).addTo(layerRefs.current.threatZones);
                                    
                                }} else if (threatType.includes("artillery") || threatType.includes("포병")) {{
                                    // 포병: 사격 범위를 나타내는 부채꼴 (일반적으로 북쪽 방향)
                                    const threatRadius = props.threat_radius || 30000; // 기본 30km
                                    const sectorAngle = 45; // 45도 부채꼴
                                    const bearing = 180; // 남쪽 방향 (DMZ 방향)
                                    
                                    // 부채꼴 생성 (다각형)
                                    const sectorPoints = [latlng];
                                    const numPoints = 20;
                                    for (let i = 0; i <= numPoints; i++) {{
                                        const angle = (bearing - sectorAngle / 2) + (sectorAngle * i / numPoints);
                                        const rad = angle * Math.PI / 180;
                                        const lat = latlng[0] + (threatRadius / 111000) * Math.cos(rad);
                                        const lng = latlng[1] + (threatRadius / (111000 * Math.cos(latlng[0] * Math.PI / 180))) * Math.sin(rad);
                                        sectorPoints.push([lat, lng]);
                                    }}
                                    
                                    L.polygon(sectorPoints, {{
                                        color: '#ff6b6b',
                                        fillColor: '#ff6b6b',
                                        fillOpacity: 0.2,
                                        weight: 2,
                                        dashArray: '5, 5'
                                    }}).addTo(layerRefs.current.threatZones);
                                    
                                }} else {{
                                    // 기타 위협: 신뢰도에 따라 아이콘 크기와 색상으로 표현
                                    const iconSize = 30 + (confidence * 20); // 30-50px
                                    const iconColor = confidence > 0.7 ? '#ff1744' : confidence > 0.4 ? '#ff6b6b' : '#ff9999';
                                    
                                    // 아이콘 업데이트 (더 큰 크기로)
                                    const sym = new ms.Symbol(sidc, {{ 
                                        size: iconSize, 
                                        icon: true,
                                        colorMode: 'Light',
                                        fill: true,
                                        fillColor: iconColor
                                    }});
                                    const enhancedIcon = L.divIcon({{
                                        className: '',
                                        html: sym.asSVG(),
                                        iconSize: [iconSize, iconSize],
                                        iconAnchor: [iconSize / 2, iconSize / 2]
                                    }});
                                    
                                    marker.setIcon(enhancedIcon);
                                }}
                                
                                // 위협 강조 표시 (COA 선택 시 사용)
                                marker._threatData = {{
                                    threat_type: threatType,
                                    confidence: confidence,
                                    affected_coa: props.affected_coa || [],
                                    isHighlighted: false
                                }};
                            }}
                        }});
                    }}
                    
                    // COA 경로 표시
                    if (copData.coaData && copData.coaData.features) {{
                        copData.coaData.features.forEach((feature) => {{
                            const props = feature.properties;
                            
                            if (feature.geometry.type === "LineString") {{
                                const latlngs = feature.geometry.coordinates.map(c => [c[1], c[0]]);
                                
                                // COA 경로 스타일 (선택된 COA에 따라 강조)
                                const isSelected = selectedCOA && props.coa_id === selectedCOA.coa_id;
                                const color = isSelected ? '#58a6ff' : '#8b949e';
                                const weight = isSelected ? 5 : 3;
                                
                                L.polyline(latlngs, {{
                                    color: color,
                                    weight: weight,
                                    dashArray: '10, 10',
                                    opacity: 0.8
                                }}).addTo(layerRefs.current.coaPaths);
                            }} else if (feature.geometry.type === "Point") {{
                                const latlng = [feature.geometry.coordinates[1], feature.geometry.coordinates[0]];
                                const sidc = props.sidc || "SFAPM-----H----";
                                
                                // Milsymbol 아이콘
                                const sym = new ms.Symbol(sidc, {{ size: 30, icon: true }});
                                const icon = L.divIcon({{
                                    className: '',
                                    html: sym.asSVG(),
                                    iconSize: [30, 30],
                                    iconAnchor: [15, 15]
                                }});
                                
                                // 부대 마커
                                const marker = L.marker(latlng, {{ icon }}).addTo(layerRefs.current.blueUnits);
                                
                                // 팝업 내용 (3계층 정보)
                                let popupContent = `
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
                                `;
                                
                                marker.bindPopup(popupContent);
                            }}
                        }});
                    }}
                }};
                
                // COA 선택 핸들러
                const handleCOASelect = (coa) => {{
                    setSelectedCOA(coa);
                    setShowReasoning(true);
                    
                    // 레이어 다시 렌더링하여 선택된 COA 강조
                    if (mapInstanceRef.current) {{
                        mapInstanceRef.current.eachLayer((layer) => {{
                            if (layer instanceof L.LayerGroup) {{
                                mapInstanceRef.current.removeLayer(layer);
                            }}
                        }});
                        renderTacticalLayers(mapInstanceRef.current);
                        
                        // 선택된 COA와 관련된 위협 강조
                        setTimeout(() => {{
                            highlightThreatsForCOA(coa);
                        }}, 100);
                    }}
                }};
                
                // 레이어 업데이트 (selectedCOA 변경 시)
                useEffect(() => {{
                    if (mapInstanceRef.current) {{
                        renderTacticalLayers(mapInstanceRef.current);
                        // COA 선택 시 위협 강조
                        if (selectedCOA) {{
                            highlightThreatsForCOA(selectedCOA);
                        }} else {{
                            // COA 선택 해제 시 모든 위협 정상 표시
                            if (layerRefs.current.threats) {{
                                layerRefs.current.threats.eachLayer((layer) => {{
                                    if (layer instanceof L.Marker) {{
                                        layer.setOpacity(1.0);
                                        layer.setZIndexOffset(0);
                                    }}
                                }});
                            }}
                        }}
                    }}
                }}, [selectedCOA]);
                
                // 시간 단계 변경 시 레이어 업데이트
                useEffect(() => {{
                    if (mapInstanceRef.current) {{
                        // 시간 단계에 따른 시각적 변화 (예: COA 경로 애니메이션, 부대 이동 등)
                        // 현재는 기본 렌더링만 유지, 향후 확장 가능
                        renderTacticalLayers(mapInstanceRef.current);
                        if (selectedCOA) {{
                            highlightThreatsForCOA(selectedCOA);
                        }}
                    }}
                }}, [timeStep]);
                
                return (
                    <div className="cop-container">
                        <div className="map-container" ref={{mapRef}} />
                        
                        {{/* 좌측 패널: 상황 요약 */}}
                        <div className="left-panel">
                            <h3>📊 상황 요약</h3>
                            <div className="situation-summary">
                                <div className="summary-item">
                                    <strong>위협:</strong> ${{(copData.threatData?.features || []).filter(f => f.properties?.is_identified_threat === true).length || 0}}개
                                </div>
                                <div className="summary-item">
                                    <strong>부대:</strong> ${{copData.coaData.features?.filter(f => f.geometry.type === "Point").length || 0}}개
                                </div>
                                <div className="summary-item">
                                    <strong>COA 후보:</strong> ${{copData.coaRecommendations?.length || 0}}개
                                </div>
                                ${{selectedCOA ? `
                                <div className="summary-item" style="margin-top: 16px; border-top: 1px solid #30363d; padding-top: 12px;">
                                    <strong>선택된 COA:</strong><br/>
                                    ${{selectedCOA.coa_name || "Unknown"}}<br/>
                                    <span style="color: #3fb950; font-size: 18px; font-weight: 600;">
                                        ${{((selectedCOA.score || selectedCOA.total_score || 0) * 100).toFixed(1)}}%
                                    </span>
                                </div>
                                ` : ""}}
                            </div>
                        </div>
                        
                        {{/* 우측 패널: 추론 근거 */}}
                        <div className={{`right-panel ${{showReasoning ? 'active' : ''}}`}}>
                            <h3>🧠 추론 근거</h3>
                            ${{selectedCOA ? `
                                <div>
                                    <h4 style="margin: 0 0 8px 0; color: #58a6ff;">${{selectedCOA.coa_name || "Unknown"}}</h4>
                                    <div className="coa-score" style="font-size: 20px; margin: 8px 0;">
                                        ${{((selectedCOA.score || selectedCOA.total_score || 0) * 100).toFixed(1)}}%
                                    </div>
                                    
                                    ${{selectedCOA.reason || selectedCOA.reasoning ? `
                                    <div className="reasoning-section">
                                        <div className="reasoning-section-title">추천 근거</div>
                                        <div className="reasoning-path">
                                            ${{selectedCOA.reason || (Array.isArray(selectedCOA.reasoning) ? selectedCOA.reasoning.map(r => r.reason || r).join("\\n") : selectedCOA.reasoning)}}
                                        </div>
                                    </div>
                                    ` : ""}}
                                    
                                    ${{selectedCOA.breakdown ? `
                                    <div className="reasoning-section">
                                        <div className="reasoning-section-title">점수 세부</div>
                                        <div className="reasoning-path">
                                            ${{Object.entries(selectedCOA.breakdown).map(([key, value]) => `${{key}}: ${{(value * 100).toFixed(1)}}%`).join("\\n")}}
                                        </div>
                                    </div>
                                    ` : ""}}
                                    
                                    ${{selectedCOA.coa_uri ? `
                                    <div className="reasoning-section">
                                        <div className="reasoning-section-title">온톨로지 URI</div>
                                        <div className="ontology-uri">${{selectedCOA.coa_uri}}</div>
                                    </div>
                                    ` : ""}}
                                    
                                    ${{selectedCOA.ontology_reasoning_path ? `
                                    <div className="reasoning-section">
                                        <div className="reasoning-section-title">추론 경로</div>
                                        <div className="reasoning-path-graph" id="reasoning-path-graph-${{selectedCOA.coa_id}}">
                                            ${{renderReasoningPathGraph(selectedCOA.ontology_reasoning_path)}}
                                        </div>
                                    </div>
                                    ` : ""}}
                                </div>
                            ` : "COA를 선택하면 추론 근거가 표시됩니다."}}
                        </div>
                        
                        {{/* 하단 패널: 시간 흐름 및 COA 비교 */}}
                        <div className="bottom-panel">
                            {{/* 시간 흐름 슬라이더 */}}
                            <div className="timeline-control" style="margin-bottom: 12px; padding: 8px; background: rgba(0,0,0,0.2); border-radius: 4px;">
                                <div style="display: flex; align-items: center; gap: 12px;">
                                    <label style="color: #8b949e; font-size: 11px; min-width: 80px;">시간 단계:</label>
                                    <input 
                                        type="range" 
                                        min="0" 
                                        max="${{timeSteps.length - 1}}" 
                                        value="${{timeStep}}" 
                                        onChange={{e => setTimeStep(parseInt(e.target.value))}}
                                        style="flex: 1; height: 4px; background: #30363d; outline: none; border-radius: 2px;"
                                    />
                                    <span style="color: #58a6ff; font-size: 12px; font-weight: 600; min-width: 100px;">
                                        ${{timeSteps[timeStep]}}
                                    </span>
                                    <div style="display: flex; gap: 4px;">
                                        <button 
                                            onClick={{() => setTimeStep(Math.max(0, timeStep - 1))}}
                                            disabled={{timeStep === 0}}
                                            style="padding: 4px 8px; background: #21262d; border: 1px solid #30363d; color: #c9d1d9; border-radius: 3px; cursor: pointer; font-size: 11px;"
                                        >
                                            ◀ 이전
                                        </button>
                                        <button 
                                            onClick={{() => setTimeStep(Math.min(timeSteps.length - 1, timeStep + 1))}}
                                            disabled={{timeStep === timeSteps.length - 1}}
                                            style="padding: 4px 8px; background: #21262d; border: 1px solid #30363d; color: #c9d1d9; border-radius: 3px; cursor: pointer; font-size: 11px;"
                                        >
                                            다음 ▶
                                        </button>
                                    </div>
                                </div>
                            </div>
                            
                            {{/* COA 비교 */}}
                            <div className="coa-comparison">
                                ${{copData.coaRecommendations?.map((coa, index) => {{
                                    const score = (coa.score || coa.total_score || 0) * 100;
                                    const isSelected = selectedCOA && coa.coa_id === selectedCOA.coa_id;
                                    
                                    // 시간 단계에 따른 COA 상태 표시
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
                                    
                                    return `
                                    <div 
                                        className={{`coa-card ${{isSelected ? 'selected' : ''}}`}}
                                        onClick={{() => handleCOASelect(coa)}}
                                        style="position: relative;"
                                    >
                                        <div style="position: absolute; top: 8px; right: 8px; font-size: 9px; color: ${{timeStatusColor}}; background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 3px;">
                                            ${{timeStatus}}
                                        </div>
                                        <h4>${{coa.coa_name || `COA ${{index + 1}}`}}</h4>
                                        <div className="coa-score">${{score.toFixed(1)}}%</div>
                                        <div className="coa-type">${{coa.coa_type || "알 수 없음"}}</div>
                                    </div>
                                    `;
                                }}).join("") || "COA 데이터가 없습니다."}}
                            </div>
                        </div>
                    </div>
                );
            }};
            
            ReactDOM.createRoot(document.getElementById('root')).render(<OntologyAwareCOP />);
        </script>
    </body>
    </html>
    """
    
    components.html(html_code, height=height)



