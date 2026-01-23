import React, { useEffect, useMemo, useState, useRef, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, GeoJSON, Polyline, Circle, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { createMilSymbolIcon } from '../lib/milsymbol-wrapper';
import L from 'leaflet';
import type { LatLngExpression } from 'leaflet';
import type { MissionBase, ThreatEventBase, COASummary, FriendlyUnit, AxisItem } from '../types/schema';
import {
    createThreatInfluenceArea,
    determineThreatSIDC,
    determineFriendlySIDC,
    decodeSIDC,
    getCOAColor,
    SELECTED_COA_COLOR,
    parseCoordinates,
    resolveLocation,
    getAxisLineStyle,
    getPathStyle,
    calculateBearing,
} from '../lib/cop-visualization-utils';
import { MapLegend, type LayerToggleState } from './MapLegend';
import { parseThreatLevel } from '../lib/threat-level-parser';

// Fix Leaflet's default icon path issues
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

const fixLeafletIcons = () => {
    // @ts-ignore
    if (L.Icon.Default && L.Icon.Default.prototype) {
        // @ts-ignore
        delete L.Icon.Default.prototype._getIconUrl;
        L.Icon.Default.mergeOptions({
            iconUrl: markerIcon,
            iconRetinaUrl: markerIcon2x,
            shadowUrl: markerShadow,
        });
    }
};
fixLeafletIcons();

interface UnitMarker {
    id: string;
    name: string;
    sidc: string;
    position: LatLngExpression;
    type: 'FRIENDLY' | 'HOSTILE';
    description?: string;
    selected?: boolean;
    coa_id?: string; // 아군 부대의 경우 소속 방책
    coa_rank?: number; // 방책 Rank
    threat_level?: number; // 위협의 경우 위협 수준
    threat_type_code?: string; // 위협 유형 코드
}

interface AxisInfo {
    axis_id: string;
    axis_name?: string;
    axis_type?: 'PRIMARY' | 'SECONDARY' | 'SUPPORT';
    coordinates?: LatLngExpression[]; // 축선 좌표 경로
}

interface TacticalMapProps {
    missions?: MissionBase[];
    threats?: ThreatEventBase[];
    selectedThreat?: ThreatEventBase | null;
    coaRecommendations?: COASummary[];
    selectedCOA?: COASummary | null;
    onCOAClick?: (coa: COASummary) => void;
    enemyUnits?: Array<{
        id: string;
        name: string;
        position: LatLngExpression;
        type?: string;
        sidc?: string;
    }>;
    // New Props for Initial Visualization
    friendlyUnits?: FriendlyUnit[];
    staticAxes?: AxisItem[];

    situationSummary?: string;
    situationSummarySource?: string; // "llm", "template", "cache" - 정황보고 생성 방식
    situationAssessment?: string; // LLM 기반 상황판단 (모든 방책에 동일)
    axisStates?: any[]; // COA 응답의 axis_states
    situationInfo?: any; // 상황 정보 (위협 정보 포함)
}

const DEFAULT_CENTER: LatLngExpression = [37.5665, 126.9780]; // Seoul center
const DEFAULT_ZOOM = 9; // 줌 레벨 증가로 더 많은 마커 가시성 확보

// Component to handle map view updates
function MapUpdater({ center, zoom }: { center?: LatLngExpression, zoom?: number }) {
    const map = useMap();
    useEffect(() => {
        if (center) map.setView(center, zoom || map.getZoom());
    }, [center, zoom, map]);
    return null;
}

// Component to add zoom control at bottom right
function ZoomControlPositioner() {
    const map = useMap();
    useEffect(() => {
        // Remove any existing zoom controls first
        const timer = setTimeout(() => {
            // Find and remove existing zoom controls
            const mapContainer = map.getContainer();
            const existingZoomControls = mapContainer.querySelectorAll('.leaflet-control-zoom');
            existingZoomControls.forEach(control => {
                const parent = control.parentElement;
                if (parent) {
                    parent.remove();
                }
            });

            // Add new zoom control at bottom right
            const zoomControl = L.control.zoom({
                position: 'bottomright'
            });
            zoomControl.addTo(map);
        }, 100);

        return () => {
            clearTimeout(timer);
        };
    }, [map]);
    return null;
}

export const TacticalMap: React.FC<TacticalMapProps> = ({
    missions = [],
    threats = [],
    selectedThreat,
    coaRecommendations = [],
    selectedCOA,
    onCOAClick,
    enemyUnits = [],
    friendlyUnits = [], // Default empty
    staticAxes = [],    // Default empty
    situationSummary,
    situationSummarySource,
    situationAssessment,
    axisStates = [],
    situationInfo
}) => {
    // 레이어 토글 상태
    const [layerToggle, setLayerToggle] = useState<LayerToggleState>({
        threats: true,
        threatInfluence: true,
        friendlyUnits: true,
        coaPaths: true,
        coaAreas: true,
        axes: true,
        terrain: true,
        reasoningTrace: true,
    });

    const handleLayerToggle = (layer: keyof LayerToggleState) => {
        setLayerToggle(prev => {
            const newState = {
                ...prev,
                [layer]: !prev[layer],
            };
            console.log(`[TacticalMap] Layer ${layer} toggled to:`, newState[layer]);
            return newState;
        });
    };

    // selectedCOA 변경 시 디버깅 정보 출력
    useEffect(() => {
        if (selectedCOA) {
            console.log('[TacticalMap] selectedCOA 변경됨:', {
                coa_id: selectedCOA.coa_id,
                coa_name: selectedCOA.coa_name,
                total_coas: coaRecommendations.length,
                has_unit_positions: !!(selectedCOA as any).unit_positions,
                has_operational_path: !!(selectedCOA as any).operational_path || !!(selectedCOA as any).visualization_data?.operational_path,
                has_operational_area: !!(selectedCOA as any).operational_area || !!(selectedCOA as any).visualization_data?.operational_area,
            });
        } else {
            console.log('[TacticalMap] selectedCOA가 null로 변경됨');
        }
    }, [selectedCOA, coaRecommendations.length]);


    /**
     * 상황 정보로부터 마커 좌표를 결정하는 통합 함수
     */
    const resolveMarkerPosition = useCallback((
        situationInfo: any,
        threatData?: ThreatEventBase
    ): LatLngExpression => {
        // 유효성 검사 함수: undefined, null, 0(한국 지역에서는 유효하지 않음) 체크
        const isValid = (v: any) => v !== undefined && v !== null && v !== 0;

        // 1. 위도/경도 직접 제공 (최우선) - 항상 새 배열 생성
        if (isValid(situationInfo?.latitude) && isValid(situationInfo?.longitude)) {
            return [situationInfo.latitude as number, situationInfo.longitude as number];
        }

        // 2. threatData에서 좌표 추출 (실제 데이터 선택 시)
        if (threatData) {
            if (isValid(threatData.latitude) && isValid(threatData.longitude)) {
                return [threatData.latitude as number, threatData.longitude as number];
            }
            if (threatData.position && Array.isArray(threatData.position)) {
                return [threatData.position[0] as number, threatData.position[1] as number];
            }
        }

        // 3. 좌표정보 문자열 파싱
        const coordStr = situationInfo?.좌표정보 || (threatData as any)?.좌표정보;
        if (coordStr) {
            const parsed = parseCoordinates(coordStr);
            if (parsed) {
                return [parsed[0] as number, parsed[1] as number];
            }
        }

        // 4. location_cell_id 기반 조회
        const cellId = situationInfo?.location_cell_id || situationInfo?.배치지형셀ID || threatData?.location_cell_id;
        if (cellId && typeof cellId === 'string') {
            // cellId 자체를 location으로 취급하여 resolveLocation 시도
            const resolved = resolveLocation(cellId);
            if (resolved) {
                return Array.isArray(resolved)
                    ? [resolved[0] as number, resolved[1] as number]
                    : resolved;
            }
        }

        // 5. 위치 이름 변환 (데모 시나리오, 수동 입력, SITREP)
        const location = situationInfo?.location || situationInfo?.발생장소;
        if (location) {
            const resolved = resolveLocation(location);
            if (resolved) {
                // resolveLocation이 이미 새 배열을 반환하지만, 명시적으로 보장
                return Array.isArray(resolved)
                    ? [resolved[0] as number, resolved[1] as number]
                    : resolved;
            }
        }

        // 6. 기본 위치 (DMZ 중앙)
        return [38.0, 127.0];
    }, []);

    // Convert data to markers
    const markers = useMemo(() => {
        const newMarkers: UnitMarker[] = [];

        // missions 배열의 마커는 제거 (방책의 부대만 표시 -> 이제 friendlyUnits 사용)

        // 0. 초기 아군 부대 표시 (Initial Friendly Units)
        // [FIX] 방책이 선택되어도 모든 부대가 사라지는 현상을 방지하기 위해 상시 표시 결정
        // 다만 selectedCOA가 있고 participating_units가 있으면 필터링 여부만 결정
        const shouldShowInitialUnits = true;

        console.log('[TacticalMap] Friendly Units Rendering Policy:', {
            selectedCOA: selectedCOA?.coa_id || 'none',
            has_unit_positions: (selectedCOA as any)?.has_unit_positions,
            friendlyUnitsCount: friendlyUnits?.length || 0,
        });

        if (shouldShowInitialUnits && friendlyUnits && friendlyUnits.length > 0) {
            // COA가 선택되었으면 participating_units에 포함된 부대만 필터링
            const participatingUnitNames = selectedCOA?.participating_units || [];

            // [FIX] 방책 선택 시 참여 부대만 표시 (사용자 요청 반영: 관여하지 않는 부대는 혼란스러움)
            const unitsToShow = selectedCOA && participatingUnitNames.length > 0
                ? friendlyUnits.filter(unit =>
                    participatingUnitNames.some(name =>
                        name === unit.unit_name || name === unit.unit_id
                    )
                )
                : friendlyUnits;

            // [FIX] 중복 렌더링 방지: 선택된 방책이 직접 부대 마커(unit_positions)를 가지고 있다면 
            // 초기 부대 목록(markers 배열)에서는 생략하고 COA 전용 마커 블록에서 렌더링하도록 함.
            const hasCOAUnitMarkers = selectedCOA &&
                (selectedCOA as any).unit_positions?.features?.length > 0;

            if (!hasCOAUnitMarkers) {
                console.log('[TacticalMap] Rendering', unitsToShow.length, 'friendly units (Markers array).');
                unitsToShow.forEach(unit => {
                    if (unit.latitude && unit.longitude) {
                        const sidc = unit.symbol_id || determineFriendlySIDC(unit.unit_type || 'INFANTRY', unit.echelon || 'BATTALION');

                        newMarkers.push({
                            id: `friendly-${unit.unit_id}`,
                            name: unit.unit_name,
                            sidc: sidc,
                            position: [unit.latitude, unit.longitude],
                            type: 'FRIENDLY',
                            description: `${unit.echelon || ''} ${unit.unit_type || ''} (${unit.status || '가용'})`,
                            selected: false
                        });
                    }
                });
            } else {
                console.log('[TacticalMap] Skipping initial friendly markers array because COA provides unit_positions.');
            }
        }

        // 데모 시나리오/수동 입력/SITREP 처리: situationInfo가 있고 threats 배열에 없는 경우
        // (is_demo, is_manual, is_sitrep 플래그 확인)
        // selectedThreat가 없고, situationInfo가 데모/수동/SITREP인 경우
        if (situationInfo && !selectedThreat &&
            (situationInfo.is_demo || situationInfo.is_manual || situationInfo.is_sitrep)) {
            // 통합 좌표 해결 함수 사용 (항상 새 배열 반환)
            const markerPosition = resolveMarkerPosition(situationInfo);

            const threatType = situationInfo.threat_type || situationInfo.위협유형 || '정찰';
            const sidc = determineThreatSIDC(threatType);

            const parsed = parseThreatLevel(situationInfo.threat_level || situationInfo.위협수준);
            const threatLevel = parsed?.normalized || 0.5;

            // 🔥 FIX: 임무 중심 모드인 경우 마커 이름과 설명을 임무 정보로 표시
            const isMissionCentered = situationInfo.approach_mode === 'mission_centered';
            const missionName = situationInfo.mission_name || situationInfo.임무명;
            const missionId = situationInfo.mission_id || situationInfo.임무ID;
            const missionObjective = situationInfo.mission_objective || situationInfo.임무목표;
            
            let markerName = situationInfo.situation_id || '상황 정보';
            let markerDescription = situationInfo.description || situationInfo.enemy_info || situationInfo.raw_report_text || '상황 정보 위협';
            
            if (isMissionCentered && missionName) {
                markerName = `🎯 ${missionName} (${missionId || 'N/A'})`;
                markerDescription = missionObjective 
                    ? `임무 목표: ${missionObjective}\n` + (threatType !== '정찰' ? `예상 위협: ${threatType}` : '')
                    : `임무 지역. ${threatType !== '정찰' ? `예상 위협: ${threatType}` : ''}`;
            }

            newMarkers.push({
                id: `situation-${situationInfo.situation_id}`,
                name: markerName,
                sidc: sidc,
                position: markerPosition,  // 통합 함수에서 반환된 새 배열 사용
                type: 'HOSTILE',
                description: markerDescription,
                selected: true,
                threat_level: threatLevel,
                threat_type_code: threatType,
            });

            // 데모/수동/SITREP일 때는 실제 위협 목록을 표시하지 않음
            return newMarkers;
        }

        // Add hostile units from threats
        // selectedThreat가 있으면 선택된 위협만 강조 표시, 나머지는 숨김
        threats.forEach((t, idx) => {
            const isSelected = selectedThreat?.threat_id === t.threat_id;

            // selectedThreat가 있고 현재 위협이 선택되지 않았으면 표시하지 않음
            if (selectedThreat && !isSelected) {
                return; // 선택된 위협만 표시
            }

            // 위치 해결: 통합 함수 사용 (모든 입력 방식에서 일관된 처리)
            // 통합 함수가 항상 새 배열을 반환하므로 참조 독립성 보장
            // situationInfo에 해당 위협의 정보가 있으면 우선 사용
            const relevantSituationInfo = situationInfo && (
                situationInfo.threat_id === t.threat_id ||
                situationInfo.selected_threat_id === t.threat_id ||
                situationInfo.위협ID === t.threat_id ||
                situationInfo.situation_id === t.threat_id
            ) ? situationInfo : undefined;

            const position = resolveMarkerPosition(relevantSituationInfo, t) ||
                [37.8 + idx * 0.1, 127.2 + idx * 0.1]; // 폴백: Mock position

            // MIL-STD-2525D 심볼 결정
            const sidc = determineThreatSIDC(t.threat_type_code);

            // 위협 수준 파싱 (문자열 "HIGH", "MEDIUM", "LOW" 지원)
            // situationInfo의 threat_level을 우선 사용, 없으면 원본 데이터 사용
            let threatLevel = 0.5;

            // situationInfo에 해당 위협의 정보가 있는지 확인
            // selectedThreat가 있으면 항상 선택된 위협으로 간주
            const isSelectedThreat = isSelected ||
                (situationInfo && (
                    situationInfo.threat_id === t.threat_id ||
                    situationInfo.selected_threat_id === t.threat_id ||
                    situationInfo.위협ID === t.threat_id ||
                    situationInfo.situation_id === t.threat_id
                ));

            if (isSelectedThreat && situationInfo) {
                // situationInfo에 해당 위협의 정보가 있으면 우선 사용
                // threat_level (숫자) 또는 위협수준 (문자열) 모두 확인
                let situationThreatLevel = situationInfo.threat_level;
                if ((situationThreatLevel === undefined || situationThreatLevel === null || situationThreatLevel === '') && situationInfo.위협수준) {
                    situationThreatLevel = situationInfo.위협수준;
                }

                // 통합 위협수준 파서 사용
                const parsed = parseThreatLevel(situationThreatLevel);
                if (parsed) {
                    threatLevel = parsed.normalized;
                }
            } else {
                // situationInfo에 없으면 원본 데이터 사용 (통합 파서 사용)
                const parsed = parseThreatLevel(t.threat_level);
                if (parsed) {
                    threatLevel = parsed.normalized;
                }
            }

            newMarkers.push({
                id: `threat-${t.threat_id}`,
                name: t.threat_id || t.threat_id,
                sidc: sidc,
                position: position,
                type: 'HOSTILE',
                description: t.raw_report_text || t.threat_type_original || t.threat_type_code,
                selected: isSelected,
                threat_level: threatLevel,
                threat_type_code: t.threat_type_code,
            });
        });

        // 배경 적군 부대 추가
        // selectedThreat가 있을 때는 배경 적군은 표시하지 않음 (선택된 위협에 집중)
        if (!selectedThreat) {
            enemyUnits.forEach((enemy) => {
                newMarkers.push({
                    id: `enemy-${enemy.id}`,
                    name: enemy.name,
                    sidc: enemy.sidc || 'SHGPUCA----K---',
                    position: enemy.position,
                    type: 'HOSTILE',
                    description: `적군 부대: ${enemy.type || '미지정'}`,
                    selected: false
                });
            });
        }

        // COA 응답에서 적군 정보 추출 (background_enemies, enemy_units 등)
        // selectedThreat가 있을 때는 선택된 위협과 관련된 COA의 적군만 표시
        coaRecommendations.forEach((coa) => {

            // selectedCOA가 있을 때 다른 COA 정보는 무시되어야 함.
            // 위 맵퍼 로직에서 missions 제거하고 friendlyUnits 추가했으므로,
            // 방책 추천 부대는 selectedCOA가 있을 때만 추가해야 함.

            // selectedThreat가 있으면 배경 적군은 표시하지 않음 (선택된 위협에 집중)
            if (selectedThreat) {
                return;
            }

            // 선택된 COA가 아니면 스킵 (여러 COA 겹침 방지)
            if (selectedCOA && coa.coa_id !== selectedCOA.coa_id) {
                return;
            }

            const backgroundEnemies = (coa as any).background_enemies || (coa as any).enemy_units;
            if (backgroundEnemies && Array.isArray(backgroundEnemies)) {
                backgroundEnemies.forEach((enemy: any, idx: number) => {
                    if (enemy.position || enemy.coordinates) {
                        const position = enemy.position ||
                            (enemy.coordinates ? [enemy.coordinates[1], enemy.coordinates[0]] : null);
                        if (position) {
                            newMarkers.push({
                                id: `coa-${coa.coa_id}-enemy-${idx}`,
                                name: enemy.name || enemy.unit_name || `적군 ${idx + 1}`,
                                sidc: enemy.sidc || 'SHGPUCA----K---',
                                position: position,
                                type: 'HOSTILE',
                                description: `배경 적군: ${enemy.type || '미지정'}`,
                                selected: false
                            });
                        }
                    }
                });
            }
        });

        // COA 아군 부대 위치 추가 (selectedCOA가 있을 때)
        // 기존 missions 처리 로직보다 우선됨
        if (selectedCOA) {
            // selectedCOA는 coaRecommendations에 포함되어 있으므로 위 루프에서 처리할 수도 있지만
            // 별도로 명확히 처리하는 것이 좋음.
            // ... 하지만 coaRecommendations.forEach에서 처리하면 중복 가능성?

            // coaGeoJSON이나 unit_positions를 통해 아군 부대 표시
            // CoaDetailModal에서는 unit_positions를 사용함.
            // 여기서는 GeoJSON overlay가 이미 있음 (coaGeoJSON).
            // 하지만 마커(심볼)로 표시하려면 unit_positions가 필요함.

            const selectedCOAData = coaRecommendations.find(c => c.coa_id === selectedCOA.coa_id);
            if (selectedCOAData && (selectedCOAData as any).unit_positions) {
                const unitFeatures = (selectedCOAData as any).unit_positions.features || [];
                unitFeatures.forEach((feature: any, idx: number) => {
                    if (!feature.geometry || !feature.geometry.coordinates) return;
                    const [lng, lat] = feature.geometry.coordinates;
                    const props = feature.properties || {};

                    newMarkers.push({
                        id: `coa-unit-${idx}`,
                        name: props.unit_name || `Unit ${idx}`,
                        sidc: props.sidc || 'SFGPU------K---',
                        position: [lat, lng],
                        type: 'FRIENDLY',
                        description: props.description || `COA ${selectedCOA.coa_id} Unit`,
                        selected: false,
                        coa_id: selectedCOA.coa_id,
                        coa_rank: selectedCOA.rank
                    });
                });
            }
        }


        return newMarkers;
    }, [missions, threats, selectedThreat, coaRecommendations, enemyUnits, situationInfo, resolveMarkerPosition, friendlyUnits, selectedCOA]);


    // 축선 정보 추출 및 처리
    const axisLines = useMemo(() => {
        const axes: AxisInfo[] = [];

        // 0. 정적 축선 (Initial Static Axes) - 항상 표시하거나 조건부 표시
        if (staticAxes && staticAxes.length > 0) {
            staticAxes.forEach(sa => {
                // LatLngExpression[]로 변환
                let coordinates: LatLngExpression[] | undefined;

                // 스키마: coordinates?: number[][] // [[lat, lon], ...]
                if (sa.coordinates && sa.coordinates.length >= 2) {
                    coordinates = sa.coordinates.map(c => [c[0], c[1]] as LatLngExpression);

                    axes.push({
                        axis_id: sa.axis_id,
                        axis_name: sa.axis_name,
                        axis_type: (sa.axis_type as any) || 'SECONDARY',
                        coordinates: coordinates
                    });
                }
            });
        }

        // 1. axis_states에서 축선 정보 추출 (동적 축선 - COA 생성 후)
        if (axisStates && Array.isArray(axisStates)) {
            axisStates.forEach((axisState: any) => {
                if (axisState && axisState.axis_id) {
                    // 축선 좌표가 있는지 확인
                    let coordinates: LatLngExpression[] | undefined;

                    // visualization_data 또는 coordinates 필드 확인
                    if (axisState.coordinates && Array.isArray(axisState.coordinates)) {
                        coordinates = axisState.coordinates;
                    } else if (axisState.visualization_data?.coordinates) {
                        coordinates = axisState.visualization_data.coordinates;
                    } else if (axisState.geojson) {
                        // GeoJSON에서 좌표 추출
                        const geojson = axisState.geojson;
                        if (geojson.type === 'LineString' && geojson.coordinates) {
                            coordinates = geojson.coordinates.map(([lng, lat]: [number, number]) => [lat, lng] as LatLngExpression);
                        }
                    }

                    // 축선 타입 결정
                    let axisType: 'PRIMARY' | 'SECONDARY' | 'SUPPORT' = 'SECONDARY';
                    if (axisState.axis_type) {
                        const type = String(axisState.axis_type).toUpperCase();
                        if (type === 'PRIMARY' || type === 'SECONDARY' || type === 'SUPPORT') {
                            axisType = type;
                        }
                    } else if (axisState.importance === 1 || axisState.defense_priority === 1) {
                        axisType = 'PRIMARY';
                    }

                    if (coordinates && coordinates.length >= 2) {
                        axes.push({
                            axis_id: axisState.axis_id,
                            axis_name: axisState.axis_name,
                            axis_type: axisType,
                            coordinates: coordinates,
                        });
                    }
                }
            });
        }

        // 2. 위협/임무의 related_axis_id에서 축선 추출 (좌표가 없는 경우는 나중에 백엔드에서 제공)
        const axisIds = new Set<string>();
        threats.forEach(t => {
            if (t.related_axis_id) axisIds.add(t.related_axis_id);
        });
        missions.forEach(m => {
            if (m.primary_axis_id) axisIds.add(m.primary_axis_id);
        });

        axisIds.forEach(axisId => {
            // 이미 추가된 축선이 아니면 추가 (좌표는 나중에 백엔드에서 제공)
            if (!axes.find(a => a.axis_id === axisId)) {
                axes.push({
                    axis_id: axisId,
                    axis_type: 'SECONDARY',
                });
            }
        });

        return axes;
    }, [axisStates, threats, missions]);

    // Calculate center based on selected threat, selectedCOA, or situationInfo
    // useMemo로 메모이제이션하여 markers 변경 시 자동 업데이트
    const mapCenter = useMemo(() => {
        const selectedMarker = markers.find(m => m.selected);
        if (selectedMarker) {
            // 선택된 마커의 position을 새 배열로 복사하여 반환 (참조 독립성 보장)
            const pos = selectedMarker.position;
            return Array.isArray(pos)
                ? [pos[0] as number, pos[1] as number]
                : pos;
        }

        // selectedCOA가 있으면 선택된 방책의 부대 위치 중심으로 이동
        if (selectedCOA) {
            const selectedCOAUnits = coaRecommendations
                .filter(coa => coa.coa_id === selectedCOA.coa_id)
                .flatMap(coa => {
                    const unitPositions = (coa as any).unit_positions;
                    if (!unitPositions || !unitPositions.features || unitPositions.features.length === 0) {
                        return [];
                    }
                    return unitPositions.features
                        .map((feature: any) => {
                            if (!feature.geometry || !feature.geometry.coordinates) {
                                return null;
                            }
                            const [lng, lat] = feature.geometry.coordinates;
                            return [lat, lng] as LatLngExpression;
                        })
                        .filter(Boolean);
                });

            if (selectedCOAUnits.length > 0) {
                // 부대 위치들의 중심점 계산
                const avgLat = selectedCOAUnits.reduce((sum, pos) => sum + pos[0], 0) / selectedCOAUnits.length;
                const avgLng = selectedCOAUnits.reduce((sum, pos) => sum + pos[1], 0) / selectedCOAUnits.length;
                return [avgLat, avgLng];
            }
        }

        // situationInfo에 좌표가 있으면 지도 중심을 해당 위치로 이동
        if (situationInfo && !selectedCOA) {
            const resolvedPos = resolveMarkerPosition(situationInfo);
            if (resolvedPos) {
                return resolvedPos;
            }
        }

        return DEFAULT_CENTER;
    }, [markers, selectedCOA, coaRecommendations, situationInfo, resolveMarkerPosition]);

    return (
        <div className="h-full w-full rounded-lg overflow-hidden relative z-0">
            {/* 개선된 범례 */}
            <MapLegend
                layers={layerToggle}
                onToggle={handleLayerToggle}
                stats={{
                    threatCount: threats.length,
                    friendlyUnitCount: friendlyUnits.length,
                    coaCount: coaRecommendations.length,
                    hasFriendlyUnits: friendlyUnits.length > 0,
                    hasCOA: coaRecommendations.length > 0,
                }}
            />

            {/* 정황보고 및 상황판단 - 지도 내부 상단에 표시 */}
            {(situationSummary || situationAssessment) && (
                <div className="absolute top-2 left-2 right-2 z-[1000] bg-white/95 dark:bg-zinc-900/95 backdrop-blur-sm rounded-lg border border-blue-300 dark:border-blue-700 shadow-lg px-3 py-2 situation-summary-box max-h-[40vh] overflow-y-auto">
                    {situationSummary && (
                        <div className="flex items-start gap-2 mb-1.5">
                            <div className="flex-shrink-0 pt-0.5 flex items-center gap-1.5">
                                <span className="text-xs font-bold text-blue-600 dark:text-blue-400">📋 정황보고:</span>
                                {situationSummarySource && (
                                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${situationSummarySource === 'llm'
                                        ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                                        : situationSummarySource === 'cache'
                                            ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                                            : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
                                        }`}>
                                        {situationSummarySource === 'llm' ? '🤖 LLM' : situationSummarySource === 'cache' ? '💾 캐시' : '📝 템플릿'}
                                    </span>
                                )}
                            </div>
                            <p className="text-xs text-gray-700 dark:text-gray-300 flex-1 break-words whitespace-pre-wrap">
                                {situationSummary}
                            </p>
                        </div>
                    )}
                    {situationAssessment && (
                        <div className="flex items-start gap-2 pt-1.5 border-t border-blue-200 dark:border-blue-800">
                            <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 flex-shrink-0 pt-0.5">🎯 상황판단:</span>
                            <p className="text-xs text-gray-700 dark:text-gray-300 flex-1 break-words whitespace-pre-wrap">
                                {situationAssessment}
                            </p>
                        </div>
                    )}
                </div>
            )}
            <MapContainer
                center={DEFAULT_CENTER}
                zoom={DEFAULT_ZOOM}
                style={{ height: '100%', width: '100%' }}
                zoomControl={false}
                scrollWheelZoom={true}
                doubleClickZoom={true}
                dragging={true}
            >
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <MapUpdater center={mapCenter} zoom={markers.find(m => m.selected) ? 10 : DEFAULT_ZOOM} />
                <ZoomControlPositioner />

                {/* 축선 라인 표시 */}
                {layerToggle.axes && axisLines
                    .filter(axis => axis.coordinates && axis.coordinates.length >= 2)
                    .map((axis) => {
                        const style = getAxisLineStyle(axis.axis_type || 'SECONDARY');
                        return (
                            <Polyline
                                key={`axis-${axis.axis_id}`}
                                positions={axis.coordinates!}
                                pathOptions={{
                                    color: style.color,
                                    weight: style.weight,
                                    opacity: style.opacity,
                                    dashArray: style.dashArray,
                                }}
                                zIndexOffset={1000}
                            >
                                <Popup>
                                    <div className="p-2 min-w-[200px]">
                                        <h4 className="font-bold text-sm mb-1">
                                            {axis.axis_name || axis.axis_id}
                                        </h4>
                                        <p className="text-xs text-gray-600 dark:text-gray-400">
                                            축선 ID: {axis.axis_id}
                                        </p>
                                        <p className="text-xs text-gray-600 dark:text-gray-400">
                                            타입: {axis.axis_type || 'SECONDARY'}
                                        </p>
                                    </div>
                                </Popup>
                            </Polyline>
                        );
                    })}

                {/* 위협 방향 벡터 (위협이 선택되었을 때만 표시) */}
                {selectedThreat && layerToggle.threats && (() => {
                    const threatMarker = markers.find(m => m.type === 'HOSTILE' && m.selected);
                    if (!threatMarker) return null;

                    // 위협의 관련 축선 찾기
                    const relatedAxis = axisLines.find(axis =>
                        axis.axis_id === selectedThreat.related_axis_id
                    );

                    if (!relatedAxis || !relatedAxis.coordinates || relatedAxis.coordinates.length < 2) {
                        return null;
                    }

                    // 위협 위치에서 축선 방향으로 벡터 그리기
                    const threatPos = threatMarker.position;
                    const axisStart = relatedAxis.coordinates[0];
                    const axisEnd = relatedAxis.coordinates[relatedAxis.coordinates.length - 1];

                    // 위협이 축선을 따라 진행한다고 가정하여 벡터 생성 (약 10km)
                    const bearing = calculateBearing(axisStart, axisEnd);
                    const threatLat = Array.isArray(threatPos) ? threatPos[0] : (threatPos as any).lat;
                    const threatLng = Array.isArray(threatPos) ? threatPos[1] : (threatPos as any).lng;

                    // 간단한 벡터 (약 0.1도 = ~10km)
                    const vectorLength = 0.15;
                    const bearingRad = bearing * Math.PI / 180;
                    const endLat = threatLat + vectorLength * Math.cos(bearingRad);
                    const endLng = threatLng + vectorLength * Math.sin(bearingRad);

                    return (
                        <Polyline
                            key="threat-direction-vector"
                            positions={[
                                [threatLat, threatLng],
                                [endLat, endLng]
                            ]}
                            pathOptions={{
                                color: '#ef4444',
                                weight: 4,
                                opacity: 0.8,
                                dashArray: '10, 5',
                            }}
                            zIndexOffset={3000}
                        >
                            <Popup>
                                <div className="p-2">
                                    <h4 className="font-bold text-sm mb-1">위협 진행 방향</h4>
                                    <p className="text-xs text-gray-600">예상 진행 축선: {relatedAxis.axis_name || relatedAxis.axis_id}</p>
                                </div>
                            </Popup>
                        </Polyline>
                    );
                })()}

                {/* 방책-위협 연결선 (선택된 방책이 있을 때만) */}
                {selectedCOA && selectedThreat && layerToggle.coaPaths && (() => {
                    const threatMarker = markers.find(m => m.type === 'HOSTILE' && m.selected);
                    if (!threatMarker) return null;

                    // 선택된 방책의 부대 위치들 가져오기
                    const coaUnits = markers.filter(m =>
                        m.type === 'FRIENDLY' && m.coa_id === selectedCOA.coa_id
                    );

                    if (coaUnits.length === 0) return null;

                    // 부대들의 중심점 계산
                    const totalLat = coaUnits.reduce((sum, unit) => {
                        const lat = Array.isArray(unit.position) ? unit.position[0] : (unit.position as any).lat;
                        return sum + lat;
                    }, 0);
                    const totalLng = coaUnits.reduce((sum, unit) => {
                        const lng = Array.isArray(unit.position) ? unit.position[1] : (unit.position as any).lng;
                        return sum + lng;
                    }, 0);
                    const centerLat = totalLat / coaUnits.length;
                    const centerLng = totalLng / coaUnits.length;

                    const threatLat = Array.isArray(threatMarker.position) ? threatMarker.position[0] : (threatMarker.position as any).lat;
                    const threatLng = Array.isArray(threatMarker.position) ? threatMarker.position[1] : (threatMarker.position as any).lng;

                    return (
                        <Polyline
                            key="coa-threat-connection"
                            positions={[
                                [centerLat, centerLng],
                                [threatLat, threatLng]
                            ]}
                            pathOptions={{
                                color: '#3b82f6',
                                weight: 2,
                                opacity: 0.5,
                                dashArray: '5, 10',
                            }}
                            zIndexOffset={2500}
                        >
                            <Popup>
                                <div className="p-2">
                                    <h4 className="font-bold text-sm mb-1">방책-위협 대응 관계</h4>
                                    <p className="text-xs text-gray-600">{selectedCOA.coa_name}</p>
                                    <p className="text-xs text-gray-500 mt-1">→ {selectedThreat.threat_id}</p>
                                </div>
                            </Popup>
                        </Polyline>
                    );
                })()}

                {/* 축선 라인 렌더링 (Polyline) */}
                {layerToggle.axes && axisLines
                    .filter(axis => axis.coordinates && axis.coordinates.length >= 2)
                    .map((axis) => {
                        const style = getAxisLineStyle(axis.axis_type || 'SECONDARY');
                        return (
                            <Polyline
                                key={`axis-line-${axis.axis_id}`}
                                positions={axis.coordinates!}
                                pathOptions={{
                                    color: style.color,
                                    weight: style.weight,
                                    opacity: style.opacity,
                                    dashArray: style.dashArray,
                                }}
                                zIndexOffset={1001}
                            >
                                <Popup>
                                    <div className="p-2">
                                        <h4 className="font-bold text-sm mb-1">축선 정보</h4>
                                        <p className="text-xs text-gray-700 dark:text-gray-300">ID: {axis.axis_id}</p>
                                        <p className="text-xs text-gray-700 dark:text-gray-300">명칭: {axis.axis_name}</p>
                                        <p className="text-xs text-gray-700 dark:text-gray-300">유형: {axis.axis_type}</p>
                                    </div>
                                </Popup>
                            </Polyline>
                        );
                    })}

                {/* 지형 분석 요소 렌더링 (임무 관련 지역이나 분석 정보가 있을 때) */}
                {layerToggle.terrain && missions.map((mission, idx) => {
                    if (!mission.location_cell_id) return null;
                    const pos = resolveLocation(mission.location_cell_id);
                    if (!pos) return null;

                    return (
                        <Circle
                            key={`terrain-mission-area-${idx}`}
                            center={pos}
                            radius={2000} // 2km 임무 반경 시각화
                            pathOptions={{
                                color: '#16a34a',
                                fillColor: '#16a34a',
                                fillOpacity: 0.1,
                                weight: 1,
                                dashArray: '5, 5'
                            }}
                        >
                            <Popup>
                                <div className="p-2">
                                    <h4 className="font-bold text-sm mb-1">임무 지역 (지형 분석)</h4>
                                    <p className="text-xs">{mission.mission_name}</p>
                                    <p className="text-[10px] text-gray-500 mt-1">{mission.location_cell_id}</p>
                                </div>
                            </Popup>
                        </Circle>
                    );
                })}

                {/* 축선 화살표 (끝지점) */}
                {layerToggle.axes && axisLines
                    .filter(axis => axis.coordinates && axis.coordinates.length >= 2)
                    .map((axis) => {
                        const coordinates = axis.coordinates!;
                        const endPoint = coordinates[coordinates.length - 1];
                        const startPoint = coordinates[coordinates.length - 2];
                        const style = getAxisLineStyle(axis.axis_type || 'SECONDARY');
                        const bearing = calculateBearing(startPoint, endPoint);

                        return (
                            <Marker
                                key={`axis-arrow-${axis.axis_id}`}
                                position={endPoint}
                                icon={L.divIcon({
                                    className: 'axis-arrow-marker',
                                    html: `<div style="
                                        transform: rotate(${bearing}deg);
                                        color: ${style.color};
                                        font-size: 24px;
                                        font-weight: bold;
                                        line-height: 1;
                                        text-shadow: 0 0 2px white;
                                        margin-top: -12px;
                                        margin-left: -12px;
                                    ">➤</div>`,
                                    iconSize: [24, 24],
                                    iconAnchor: [12, 12],
                                })}
                                zIndexOffset={1002}
                            />
                        );
                    })}

                {/* 축선 라벨 (중간 지점에 표시) - 화살표에 가려지지 않도록 위치 조정 */}
                {layerToggle.axes && axisLines
                    .filter(axis => axis.coordinates && axis.coordinates.length >= 2)
                    .map((axis) => {
                        const midIndex = Math.floor(axis.coordinates!.length / 2);
                        const midPoint = axis.coordinates![midIndex];
                        const style = getAxisLineStyle(axis.axis_type || 'SECONDARY');

                        return (
                            <Marker
                                key={`axis-label-${axis.axis_id}`}
                                position={midPoint}
                                icon={L.divIcon({
                                    className: 'axis-label-marker',
                                    html: `<div style="
                                        background: rgba(255, 255, 255, 0.9);
                                        padding: 2px 6px;
                                        font-size: 12px;
                                        font-weight: bold;
                                        color: ${style.color};
                                        white-space: nowrap;
                                        border-radius: 4px;
                                        border: 1px solid ${style.color};
                                        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                                        text-shadow: none;
                                        transform: translate(-50%, -150%);
                                    ">${axis.axis_name || axis.axis_id}</div>`,
                                    iconSize: [1, 1],
                                    iconAnchor: [0, 0],
                                })}
                                zIndexOffset={1003}
                            />
                        );
                    })}

                {/* 위협 영향 범위 (Circle) - 마커보다 먼저 렌더링 (하위 레이어) */}
                {/* selectedThreat가 있으면 선택된 위협의 영향 범위만 표시 */}
                {layerToggle.threatInfluence && markers
                    .filter(m => {
                        if (m.type !== 'HOSTILE' || m.threat_level === undefined) return false;
                        // selectedThreat가 있으면 선택된 위협만 표시
                        if (selectedThreat) {
                            return m.selected === true;
                        }
                        return true; // selectedThreat가 없으면 모든 위협 표시
                    })
                    .map((marker) => {
                        const influenceArea = createThreatInfluenceArea(
                            marker.id,
                            marker.position,
                            marker.threat_level || 0.5,
                            marker.threat_type_code
                        );

                        // km를 미터로 변환 (Leaflet Circle은 미터 단위)
                        const radiusMeters = influenceArea.radius * 1000;

                        // 마커의 position을 직접 사용하여 중심 정확히 일치시키기
                        // Circle의 center와 Marker의 position이 정확히 동일한 좌표를 사용하도록 보장
                        // 배열인 경우 새 배열로 복사하여 참조 문제 방지
                        // ⚠️ 중요: marker.position은 이미 통합 함수(resolveMarkerPosition)에서 새 배열로 생성되었으므로
                        // 여기서도 새 배열로 복사하여 Circle과 Marker가 완전히 독립적인 참조를 사용하도록 보장
                        const circleCenter: LatLngExpression = Array.isArray(marker.position)
                            ? [marker.position[0] as number, marker.position[1] as number]
                            : marker.position;

                        // 디버깅: position과 circleCenter가 동일한지 확인
                        // console.log(`[DEBUG] Marker ${marker.id}: position=${JSON.stringify(marker.position)}, circleCenter=${JSON.stringify(circleCenter)}`);

                        return (
                            <Circle
                                key={`influence-${marker.id}`}
                                center={circleCenter}
                                radius={radiusMeters}
                                pathOptions={{
                                    color: influenceArea.visualization.strokeColor,
                                    fillColor: influenceArea.visualization.color,
                                    fillOpacity: marker.selected ? influenceArea.visualization.opacity : influenceArea.visualization.opacity * 0.3,
                                    weight: marker.selected ? influenceArea.visualization.strokeWidth : 1,
                                    opacity: marker.selected ? influenceArea.visualization.opacity + 0.2 : (influenceArea.visualization.opacity + 0.2) * 0.3,
                                }}
                                zIndexOffset={marker.selected ? 2000 : 1000}
                            >
                                <Popup>
                                    <div className="p-2 min-w-[200px]">
                                        <h4 className="font-bold text-sm mb-1">위협 영향 범위</h4>
                                        <p className="text-xs text-gray-600 dark:text-gray-400">
                                            위협: {marker.name}
                                        </p>
                                        <p className="text-xs text-gray-600 dark:text-gray-400">
                                            위협 수준: {(marker.threat_level || 0) * 100}%
                                        </p>
                                        <p className="text-xs text-gray-600 dark:text-gray-400">
                                            반경: {influenceArea.radius.toFixed(1)} km
                                        </p>
                                        {marker.selected && (
                                            <p className="text-xs text-red-600 dark:text-red-400 font-bold mt-1">
                                                선택된 위협
                                            </p>
                                        )}
                                    </div>
                                </Popup>
                            </Circle>
                        );
                    })}

                {/* 마커 표시 */}
                {markers
                    .filter(m => {
                        if (m.type === 'HOSTILE') {
                            if (!layerToggle.threats) return false;
                            // selectedThreat가 있으면 선택된 위협만 표시
                            if (selectedThreat) {
                                return m.selected === true;
                            }
                            return true; // selectedThreat가 없으면 모든 위협 표시
                        }
                        if (m.type === 'FRIENDLY') return layerToggle.friendlyUnits;
                        return true;
                    })
                    .map((marker) => {
                        // 아군 부대의 경우 방책별 색상 적용
                        let markerColor: string | undefined;
                        if (marker.type === 'FRIENDLY' && marker.coa_id) {
                            const isSelected = selectedCOA?.coa_id === marker.coa_id;
                            markerColor = isSelected ? SELECTED_COA_COLOR : (marker.coa_rank ? getCOAColor(marker.coa_rank) : undefined);
                        }

                        // 선택된 위협 마커는 더 크고 강조
                        const markerSize = marker.selected ? 50 : (marker.type === 'FRIENDLY' && selectedCOA?.coa_id === marker.coa_id ? 35 : 30);

                        return (
                            <Marker
                                key={marker.id}
                                position={marker.position}
                                icon={createMilSymbolIcon({
                                    sidc: marker.sidc,
                                    size: marker.selected ? 45 : markerSize,
                                    uniqueDesignation: marker.name,
                                    additionalInformation: marker.selected ? 'SELECTED' : undefined,
                                    selected: marker.selected,
                                    pulse: marker.selected && marker.type === 'HOSTILE'
                                })}
                                zIndexOffset={marker.selected ? 10000 : (marker.type === 'FRIENDLY' && selectedCOA?.coa_id === marker.coa_id ? 5000 : 0)}
                            >
                                <Popup>
                                    <div className="p-1 min-w-[150px]">
                                        <div className={`text-[10px] font-bold uppercase mb-1 ${marker.type === 'FRIENDLY' ? 'text-blue-600' : 'text-red-600'} ${marker.selected ? 'animate-pulse' : ''}`}>
                                            {marker.type} {marker.selected && '(선택됨)'}
                                        </div>
                                        <h3 className="font-bold text-sm mb-1">{marker.name}</h3>
                                        <p className="text-xs text-gray-600 dark:text-gray-400 max-w-[200px]">{marker.description}</p>
                                        {marker.coa_id && (
                                            <p className="text-[10px] text-blue-600 dark:text-blue-400 mt-1">
                                                방책: {marker.coa_id} (Rank {marker.coa_rank || 'N/A'})
                                            </p>
                                        )}
                                        {marker.threat_level !== undefined && (
                                            <p className="text-[10px] text-red-600 dark:text-red-400 mt-1">
                                                위협 수준: {(marker.threat_level * 100).toFixed(1)}%
                                            </p>
                                        )}
                                        {marker.selected && marker.type === 'HOSTILE' && (
                                            <p className="text-[10px] text-red-600 dark:text-red-400 font-bold mt-1 border-t pt-1">
                                                ⭐ 선택된 위협
                                            </p>
                                        )}
                                        <div className="text-[10px] mt-2 border-t pt-1 space-y-1">
                                            <p className="text-gray-500 dark:text-gray-400">
                                                심볼 유형: <span className="font-medium text-gray-700 dark:text-gray-300">{decodeSIDC(marker.sidc)}</span>
                                            </p>
                                            <p className="font-mono text-gray-400 text-[9px]">
                                                SIDC: {marker.sidc}
                                            </p>
                                        </div>
                                    </div>
                                </Popup>
                            </Marker>
                        );
                    })}

                {/* COA GeoJSON 레이어 - 방책별 색상 구분 */}
                {(layerToggle.coaPaths || layerToggle.coaAreas) && coaRecommendations.map((coa) => {
                    const isSelected = selectedCOA?.coa_id === coa.coa_id;
                    const coaGeoJSON = (coa as any).coa_geojson;

                    if (!coaGeoJSON || !coaGeoJSON.features || coaGeoJSON.features.length === 0) {
                        return null;
                    }

                    // 방책별 색상 결정
                    const coaColor = isSelected ? SELECTED_COA_COLOR : getCOAColor(coa.rank);

                    return (
                        <GeoJSON
                            key={`coa-${coa.coa_id}`}
                            data={coaGeoJSON}
                            style={{
                                color: coaColor,
                                weight: isSelected ? 4 : 1,
                                opacity: isSelected ? 0.9 : 0.2, // Ghosting
                                fillOpacity: isSelected ? 0.2 : 0.05
                            }}
                            zIndexOffset={isSelected ? 5000 : (coa.rank === 1 ? 2000 : 1000)}
                            onEachFeature={(feature, layer) => {
                                layer.on('click', () => {
                                    if (onCOAClick) {
                                        onCOAClick(coa);
                                    }
                                });

                                // Popup 추가
                                if (feature.properties) {
                                    const popupContent = `
                                        <div class="p-2 min-w-[200px]">
                                            <h4 class="font-bold text-sm mb-1">${coa.coa_name}</h4>
                                            <p class="text-xs text-gray-600">Rank ${coa.rank}</p>
                                            <p class="text-xs text-gray-500 mt-1">점수: ${coa.total_score !== undefined ? (coa.total_score * 100).toFixed(1) : 'N/A'}%</p>
                                            ${isSelected ? '<p class="text-xs text-red-600 mt-1 font-bold">선택된 방책</p>' : ''}
                                        </div>
                                    `;
                                    layer.bindPopup(popupContent);
                                }
                            }}
                        />
                    );
                })}

                {/* 부대 배치 마커 - 방책별 색상 구분 */}
                {/* selectedCOA가 있으면 선택된 방책의 부대만 표시, 없으면 모든 방책의 부대 표시 */}
                {layerToggle.friendlyUnits && coaRecommendations
                    .filter((coa) => {
                        // selectedCOA가 있으면 선택된 방책만 표시
                        if (selectedCOA) {
                            return coa.coa_id === selectedCOA.coa_id;
                        }
                        // selectedCOA가 없으면 모든 방책 표시
                        return true;
                    })
                    .flatMap((coa) => {
                        const unitPositions = (coa as any).unit_positions;
                        if (!unitPositions || !unitPositions.features || unitPositions.features.length === 0) {
                            // 디버깅: unit_positions가 없는 경우 로그
                            if (selectedCOA && coa.coa_id === selectedCOA.coa_id) {
                                console.warn(`[TacticalMap] unit_positions가 없습니다. COA: ${coa.coa_id}`, {
                                    coa_id: coa.coa_id,
                                    coa_name: coa.coa_name,
                                    has_unit_positions: !!unitPositions,
                                    unit_positions_type: typeof unitPositions,
                                    unit_positions_keys: unitPositions ? Object.keys(unitPositions) : []
                                });
                            }
                            return [];
                        }

                        const isSelected = selectedCOA?.coa_id === coa.coa_id;
                        const coaColor = isSelected ? SELECTED_COA_COLOR : getCOAColor(coa.rank);

                        return unitPositions.features.map((feature: any, idx: number) => {
                            if (!feature.geometry || !feature.geometry.coordinates) {
                                return null;
                            }

                            const [lng, lat] = feature.geometry.coordinates;
                            const unitName = feature.properties?.unit_name || feature.properties?.name || feature.properties?.부대명 || `Unit ${idx + 1}`;

                            // SIDC 결정: 직접 제공된 값 또는 부대 유형 기반
                            let sidc = feature.properties?.sidc;
                            if (!sidc) {
                                const 제대 = feature.properties?.제대 || feature.properties?.unit_type || feature.properties?.unit_level;
                                const 병종 = feature.properties?.병종 || feature.properties?.unit_class || feature.properties?.unit_type;
                                sidc = determineFriendlySIDC(제대, 병종);
                            }

                            return (
                                <Marker
                                    key={`${coa.coa_id}-unit-${idx}`}
                                    position={[lat, lng]}
                                    icon={createMilSymbolIcon({
                                        sidc: sidc,
                                        size: isSelected ? 40 : (coa.rank === 1 ? 30 : 25),
                                        uniqueDesignation: unitName,
                                        selected: isSelected,
                                    })}
                                    zIndexOffset={isSelected ? 5000 : (coa.rank === 1 ? 2000 : 1000)}
                                >
                                    <Popup>
                                        <div className="p-2 min-w-[200px]">
                                            <h4 className="font-bold text-sm mb-1">{coa.coa_name || coa.coa_id}</h4>
                                            <p className="text-xs text-gray-600 dark:text-gray-400 font-semibold">{unitName}</p>
                                            {feature.properties?.제대 && (
                                                <p className="text-[10px] text-gray-500 mt-1">제대: {feature.properties.제대}</p>
                                            )}
                                            {feature.properties?.병종 && (
                                                <p className="text-[10px] text-gray-500">병종: {feature.properties.병종}</p>
                                            )}
                                            {feature.properties?.전투력지수 && (
                                                <p className="text-[10px] text-blue-600 dark:text-blue-400 mt-1">
                                                    전투력: {feature.properties.전투력지수}
                                                </p>
                                            )}
                                            <p className="text-[10px] text-gray-500 mt-1">Rank {coa.rank}</p>
                                            {isSelected && (
                                                <p className="text-[10px] text-red-600 dark:text-red-400 mt-1 font-bold border-t pt-1">
                                                    ⭐ 선택된 방책
                                                </p>
                                            )}
                                        </div>
                                    </Popup>
                                </Marker>
                            );
                        }).filter(Boolean);
                    })}

                {/* 방책 작전 경로 (operational_path) */}
                {/* selectedCOA가 있으면 선택된 방책의 경로만 표시 */}
                {layerToggle.coaPaths && coaRecommendations
                    .filter(coa => {
                        // selectedCOA가 있으면 선택된 방책만 표시
                        if (selectedCOA) {
                            if (coa.coa_id !== selectedCOA.coa_id) {
                                return false;
                            }
                        }
                        const operationalPath = (coa as any).visualization_data?.operational_path || (coa as any).operational_path;
                        const hasPath = operationalPath && operationalPath.waypoints && Array.isArray(operationalPath.waypoints) && operationalPath.waypoints.length >= 2;

                        // 디버깅: 경로가 없는 경우 로그
                        if (selectedCOA && coa.coa_id === selectedCOA.coa_id && !hasPath) {
                            console.warn(`[TacticalMap] operational_path가 없습니다. COA: ${coa.coa_id}`, {
                                coa_id: coa.coa_id,
                                has_visualization_data: !!(coa as any).visualization_data,
                                has_operational_path: !!operationalPath,
                                operational_path: operationalPath
                            });
                        }

                        return hasPath;
                    })
                    .map((coa) => {
                        const isSelected = selectedCOA?.coa_id === coa.coa_id;
                        const operationalPath = (coa as any).visualization_data?.operational_path || (coa as any).operational_path;
                        // waypoints가 [lng, lat] 형식이면 [lat, lng]로 변환
                        const waypoints = operationalPath.waypoints.map((wp: any) => {
                            // 이미 [lat, lng] 형식인지 확인
                            if (Array.isArray(wp) && wp.length === 2) {
                                // 첫 번째 값이 위도 범위(33~43)인지 확인
                                if (wp[0] >= 33 && wp[0] <= 43) {
                                    return wp as LatLngExpression; // 이미 [lat, lng]
                                } else {
                                    return [wp[1], wp[0]] as LatLngExpression; // [lng, lat] -> [lat, lng]
                                }
                            }
                            return wp as LatLngExpression;
                        });

                        const pathType = operationalPath.path_type || 'MOVEMENT';
                        const style = getPathStyle(pathType, isSelected);

                        return (
                            <Polyline
                                key={`coa-path-${coa.coa_id}`}
                                positions={waypoints}
                                pathOptions={{
                                    color: style.color,
                                    weight: isSelected ? 6 : 2,
                                    opacity: isSelected ? 1.0 : 0.2, // Ghosting
                                    dashArray: style.dashArray,
                                }}
                                zIndexOffset={isSelected ? 5000 : (coa.rank === 1 ? 2000 : 1000)}
                            >
                                <Popup>
                                    <div className="p-2 min-w-[200px]">
                                        <h4 className="font-bold text-sm mb-1">{coa.coa_name}</h4>
                                        <p className="text-xs text-gray-600 dark:text-gray-400">
                                            작전 경로 ({pathType})
                                        </p>
                                        <p className="text-xs text-gray-500 mt-1">Rank {coa.rank}</p>
                                    </div>
                                </Popup>
                            </Polyline>
                        );
                    })}

                {/* 방책 작전 영역 (operational_area) */}
                {/* selectedCOA가 있으면 선택된 방책의 영역만 표시 */}
                {layerToggle.coaAreas && coaRecommendations
                    .filter(coa => {
                        // selectedCOA가 있으면 선택된 방책만 표시
                        if (selectedCOA) {
                            if (coa.coa_id !== selectedCOA.coa_id) {
                                return false;
                            }
                        }
                        const operationalArea = (coa as any).visualization_data?.operational_area || (coa as any).operational_area;
                        const hasArea = operationalArea && (
                            (operationalArea.deployment_area?.polygon) ||
                            (operationalArea.engagement_area?.polygon) ||
                            (operationalArea.polygon)
                        );

                        // 디버깅: 영역이 없는 경우 로그
                        if (selectedCOA && coa.coa_id === selectedCOA.coa_id && !hasArea) {
                            console.warn(`[TacticalMap] operational_area가 없습니다. COA: ${coa.coa_id}`, {
                                coa_id: coa.coa_id,
                                has_visualization_data: !!(coa as any).visualization_data,
                                has_operational_area: !!operationalArea,
                                operational_area: operationalArea
                            });
                        }

                        return hasArea;
                    })
                    .map((coa) => {
                        const isSelected = selectedCOA?.coa_id === coa.coa_id;
                        const operationalArea = (coa as any).visualization_data?.operational_area || (coa as any).operational_area;
                        const coaColor = isSelected ? SELECTED_COA_COLOR : getCOAColor(coa.rank);

                        // 배치 영역, 교전 영역, 또는 일반 영역
                        const polygons: Array<{ polygon: LatLngExpression[], type: string }> = [];
                        if (operationalArea.deployment_area?.polygon) {
                            polygons.push({ polygon: operationalArea.deployment_area.polygon, type: '배치 영역' });
                        }
                        if (operationalArea.engagement_area?.polygon) {
                            polygons.push({ polygon: operationalArea.engagement_area.polygon, type: '교전 영역' });
                        }
                        if (operationalArea.polygon) {
                            polygons.push({ polygon: operationalArea.polygon, type: '작전 영역' });
                        }

                        return polygons.map((area, idx) => {
                            // polygon 좌표 변환: [lng, lat] -> [lng, lat] (GeoJSON 형식)
                            const polygonCoords = area.polygon.map((p: any) => {
                                if (Array.isArray(p) && p.length === 2) {
                                    // 이미 [lng, lat] 형식인지 확인
                                    if (p[0] >= 124 && p[0] <= 132) {
                                        return [p[0], p[1]]; // 이미 [lng, lat]
                                    } else {
                                        return [p[1], p[0]]; // [lat, lng] -> [lng, lat]
                                    }
                                }
                                return p;
                            });

                            return (
                                <GeoJSON
                                    key={`coa-area-${coa.coa_id}-${idx}`}
                                    data={{
                                        type: 'Feature',
                                        geometry: {
                                            type: 'Polygon',
                                            coordinates: [polygonCoords],
                                        },
                                        properties: {
                                            coa_id: coa.coa_id,
                                            coa_name: coa.coa_name,
                                            area_type: area.type,
                                        },
                                    }}
                                    style={{
                                        color: coaColor,
                                        weight: isSelected ? 3 : 1,
                                        opacity: isSelected ? 0.8 : 0.2, // Ghosting
                                        fillColor: coaColor,
                                        fillOpacity: isSelected ? 0.25 : 0.05,
                                        dashArray: isSelected ? undefined : '5, 5',
                                    }}
                                    zIndexOffset={isSelected ? 4000 : (coa.rank === 1 ? 1500 : 800)}
                                >
                                    <Popup>
                                        <div className="p-2 min-w-[200px]">
                                            <h4 className="font-bold text-sm mb-1">{coa.coa_name}</h4>
                                            <p className="text-xs text-gray-600 dark:text-gray-400">{area.type}</p>
                                            <p className="text-xs text-gray-500 mt-1">Rank {coa.rank}</p>
                                        </div>
                                    </Popup>
                                </GeoJSON>
                            );
                        });
                    })
                    .flat()}

                {/* 추론 경로 시각화 (reasoning_trace) */}
                {layerToggle.reasoningTrace && selectedCOA && (selectedCOA as any).reasoning_trace && Array.isArray((selectedCOA as any).reasoning_trace) && (
                    <>
                        {(selectedCOA as any).reasoning_trace
                            .filter((step: any) => step && (step.location || step.coordinates || step.position))
                            .map((step: any, idx: number) => {
                                let position: LatLngExpression | null = null;

                                // 위치 정보 추출
                                if (step.coordinates && Array.isArray(step.coordinates)) {
                                    position = [step.coordinates[1], step.coordinates[0]]; // [lat, lng]
                                } else if (step.position && Array.isArray(step.position)) {
                                    position = [step.position[0], step.position[1]];
                                } else if (step.location && step.location.lat && step.location.lng) {
                                    position = [step.location.lat, step.location.lng];
                                }

                                if (!position) return null;

                                return (
                                    <Marker
                                        key={`reasoning-${idx}`}
                                        position={position}
                                        icon={L.divIcon({
                                            className: 'reasoning-trace-marker',
                                            html: `<div style="
                                                width: 20px;
                                                height: 20px;
                                                border-radius: 50%;
                                                background: rgba(139, 92, 246, 0.8);
                                                border: 2px solid white;
                                                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                                                display: flex;
                                                align-items: center;
                                                justify-content: center;
                                                color: white;
                                                font-weight: bold;
                                                font-size: 10px;
                                            ">${idx + 1}</div>`,
                                            iconSize: [20, 20],
                                            iconAnchor: [10, 10]
                                        })}
                                        zIndexOffset={300}
                                    >
                                        <Popup>
                                            <div className="p-2 min-w-[200px]">
                                                <h4 className="font-bold text-sm mb-1">추론 단계 {idx + 1}</h4>
                                                <p className="text-xs text-gray-600 dark:text-gray-400">
                                                    {step.description || step.reasoning || step.step || '추론 단계'}
                                                </p>
                                                {step.concept && (
                                                    <p className="text-[10px] text-purple-600 dark:text-purple-400 mt-1">
                                                        개념: {step.concept}
                                                    </p>
                                                )}
                                            </div>
                                        </Popup>
                                    </Marker>
                                );
                            })
                            .filter(Boolean)}

                        {/* 추론 경로 연결선 (Polyline) */}
                        {(() => {
                            const positions = (selectedCOA as any).reasoning_trace
                                .map((step: any) => {
                                    if (step.coordinates && Array.isArray(step.coordinates)) {
                                        return [step.coordinates[1], step.coordinates[0]] as LatLngExpression;
                                    } else if (step.position && Array.isArray(step.position)) {
                                        return [step.position[0], step.position[1]] as LatLngExpression;
                                    } else if (step.location && step.location.lat && step.location.lng) {
                                        return [step.location.lat, step.location.lng] as LatLngExpression;
                                    }
                                    return null;
                                })
                                .filter((pos: LatLngExpression | null) => pos !== null) as LatLngExpression[];

                            if (positions.length < 2) return null;

                            return (
                                <Polyline
                                    positions={positions}
                                    pathOptions={{
                                        color: '#8b5cf6',
                                        weight: 3,
                                        opacity: 0.6,
                                        dashArray: '10, 5'
                                    }}
                                />
                            );
                        })()}
                    </>
                )}
            </MapContainer>
        </div>
    );
};
