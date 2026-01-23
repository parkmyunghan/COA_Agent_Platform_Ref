// frontend/src/pages/HomePage.tsx
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Layout } from '../components/Layout';
import { TacticalMap } from '../components/TacticalMap';
import { COAGenerator } from '../components/COAGenerator';
import ChatInterface from '../components/ChatInterface';
import { SettingsPanel } from '../components/SettingsPanel';
import { AgentSelector } from '../components/AgentSelector';
import { SituationInputPanel } from '../components/SituationInputPanel';
import { SituationSummaryPanel } from '../components/SituationSummaryPanel';
import { SituationBanner } from '../components/SituationBanner';
import { useSystemData } from '../hooks/useSystemData';
import { useCodeLabels } from '../hooks/useCodeLabels';
import type { MissionBase, ThreatEventBase, COASummary } from '../types/schema';
import { parseThreatLevel } from '../lib/threat-level-parser';

import { AxisSummaryPanel } from '../components/AxisSummaryPanel';
import { COAFloatingCards, type COAFloatingCardsRef } from '../components/COAFloatingCards';
import { COAComparisonPanel } from '../components/COAComparisonPanel';
import { ToastContainer } from '../components/common/Toast';
import { Info } from 'lucide-react';

const DEFAULT_COA_TYPES = ['Defense', 'Offensive', 'Counter_Attack', 'Preemptive', 'Deterrence', 'Maneuver', 'Information_Ops'];

export default function CommandControlPage() {
    // System Data Context
    const { missions, threats, health, loading, error, refetch, friendlyUnits, axes } = useSystemData();
    const { getThreatTypeLabel, getAxisLabel, getThreatIdLabel, formatWithCode, isLoading: isCodeLabelsLoading } = useCodeLabels();

    // Local State
    const [stats, setStats] = useState<any>(null);
    const [selectedMission, setSelectedMission] = useState<MissionBase | null>(null);
    const [selectedThreat, setSelectedThreat] = useState<ThreatEventBase | null>(null);
    const [lastResponse, setLastResponse] = useState<any>(null);
    const [usePalantirMode, setUsePalantirMode] = useState<boolean>(true);
    const [selectedCOATypes, setSelectedCOATypes] = useState<string[]>(DEFAULT_COA_TYPES);
    const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
    const [situationInfo, setSituationInfo] = useState<any>(null);
    const [coaResponse, setCOAResponse] = useState<any>(null);
    const [selectedCOA, setSelectedCOA] = useState<any>(null);
    const [showComparison, setShowComparison] = useState(false);
    const [toasts, setToasts] = useState<Array<{ id: string; message: string; type: 'success' | 'error' | 'info' }>>([]);
    const floatingCardsRef = useRef<COAFloatingCardsRef>(null);
    const [modalAnchorElement, setModalAnchorElement] = useState<HTMLElement | null>(null);
    const [isGeneratingSummary, setIsGeneratingSummary] = useState<boolean>(false); // 정황보고 생성 중 상태
    const [isChatOpen, setIsChatOpen] = useState<boolean>(false); // 채팅 인터페이스 열림/닫힘 상태

    // Fetch real-time KPI stats
    useEffect(() => {
        const fetchKPI = async () => {
            try {
                const res = await fetch(`http://${window.location.hostname}:8000/api/v1/system/stats/kpi`);
                const data = await res.json();
                setStats(data);
            } catch (err) {
                console.error('Failed to fetch KPI', err);
            }
        };
        fetchKPI();
    }, []);

    // Auto-select first mission if available
    // DISABLED: 사용자가 명시적으로 선택할 때까지 초기 상태를 깨끗하게 유지
    // useEffect(() => {
    //     if (missions.length > 0 && !selectedMission) {
    //         setSelectedMission(missions[0]);
    //     }
    // }, [missions.length, selectedMission?.mission_id]);

    // situationInfo가 변경되면 selectedThreat 자동 설정
    // situationInfo 객체 전체 대신 특정 필드만 의존성으로 사용
    const threatIdFromSituation = situationInfo?.selected_threat_id || situationInfo?.threat_id;
    useEffect(() => {
        if (threatIdFromSituation) {
            const threat = threats.find(t => t.threat_id === threatIdFromSituation);
            if (threat && (!selectedThreat || selectedThreat.threat_id !== threatIdFromSituation)) {
                setSelectedThreat(threat);
            }
        } else if (!threatIdFromSituation && selectedThreat) {
            // situationInfo에 위협 정보가 없으면 selectedThreat 초기화
            setSelectedThreat(null);
        }
    }, [threatIdFromSituation, threats.length, selectedThreat?.threat_id]); // 객체 참조 대신 특정 값만 사용

    // situationInfo의 mission_id 또는 related_mission_id가 변경되면 해당 임무 자동 선택
    // [FIX] mission_id가 없으면 기존 선택이 어떻게 될지 결정해야 하는데,
    // 데모 시나리오 등에서 명시적으로 mission_id를 초기화하고 싶을 수 있음.
    const missionIdFromSituation = situationInfo?.mission_id || situationInfo?.임무ID || situationInfo?.related_mission_id;
    useEffect(() => {
        if (missionIdFromSituation) {
            // 미션 ID가 있으면 해당 미션 찾아서 선택
            if (missions.length > 0) {
                const mission = missions.find(m => m.mission_id === missionIdFromSituation);
                if (mission && (!selectedMission || selectedMission.mission_id !== missionIdFromSituation)) {
                    setSelectedMission(mission);
                    console.log('[CommandControlPage] Active Mission 업데이트:', mission.mission_id);
                }
            }
        } else if (situationInfo && !missionIdFromSituation && selectedMission) {
            // [FIX] 상황 정보는 있는데 미션 ID가 명시적으로 없는 경우 (예: 초기화된 경우)
            // 기존에 데모 시나리오 등에 의해 설정된 미션이면 해제하는 것이 맞을 수 있음.
            // 하지만 사용자가 수동으로 선택한 것을 덮어쓰면 안 됨.
            // 일단 데모 모드일 때는 강제로 해제하도록 로직 추가
            if (situationInfo.is_demo) {
                setSelectedMission(null);
                console.log('[CommandControlPage] 데모 시나리오 미션 정보 없음 -> Active Mission 해제');
            }
        }
    }, [missionIdFromSituation, missions.length, selectedMission?.mission_id, situationInfo?.is_demo]);

    // 위협 선택 시 정황보고 즉시 생성 (COA 생성 전)
    useEffect(() => {
        let isCancelled = false;

        const fetchSituationSummary = async (threatId: string, threatData: any) => {
            console.log('[정황보고] API 호출 시작:', threatId);
            setIsGeneratingSummary(true); // 로딩 시작

            try {
                const response = await fetch(`http://${window.location.hostname}:8000/api/v1/coa/generate-situation-summary`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        threat_id: threatId,
                        threat_data: threatData,
                        user_params: situationInfo // 전체 상황 정보도 user_params로 전달
                    })
                });

                if (response.ok) {
                    const data = await response.json();

                    // [Race Condition Fix] 요청이 취소되지 않았을 때만 상태 업데이트
                    if (!isCancelled) {
                        // lastResponse에 정황보고 및 ID 설정 (위협ID 또는 상황ID)
                        setLastResponse({
                            threat_id: data.threat_id || threatId, // 검증을 위한 ID
                            situation_id: data.situation_id || situationInfo?.situation_id, // 🔥 FIX: 데모 시나리오 ID
                            situation_summary: data.situation_summary,
                            situation_summary_source: data.situation_summary_source
                        });
                        console.log('[정황보고] 생성 완료:', data.situation_summary_source, 'threatId:', threatId, 'situationId:', data.situation_id);
                    } else {
                        console.log('[정황보고] 이전 요청 응답 무시 (Race Condition 방지):', threatId);
                    }
                } else {
                    console.error('[정황보고] 생성 실패:', response.status);
                }
            } catch (error) {
                console.error('[정황보고] API 호출 에러:', error);
            } finally {
                if (!isCancelled) {
                    setIsGeneratingSummary(false); // 로딩 종료
                }
            }
        };

        // 🔥 FIX: SITREP/데모/수동 모드인 경우 실제 위협 기반 API 호출을 스킵
        const isDemoOrSitrepOrManual = situationInfo?.is_demo || situationInfo?.is_sitrep || situationInfo?.is_manual;
        
        // 1. 실제 위협이 선택된 경우 (SITREP/데모 모드가 아닌 경우에만)
        if (selectedThreat && !coaResponse && !isDemoOrSitrepOrManual) {
            // 이미 마지막 응답이 있고, 그것이 현재 선택된 위협에 대한 것이라면 스킵
            const responseThreatId = lastResponse?.threat_id || lastResponse?.original_request?.threat_id;
            const isSameThreat = responseThreatId === selectedThreat.threat_id;

            if (!isSameThreat || !lastResponse?.situation_summary) {
                fetchSituationSummary(selectedThreat.threat_id, selectedThreat);
            }
        }
        // 2. 데모 시나리오 또는 SITREP 모드인 경우
        else if (situationInfo && !coaResponse && isDemoOrSitrepOrManual) {
            // 🔥 FIX: selectedThreat 상태와 관계없이 SITREP/데모 데이터 사용
            const isDemoOrSitrep = situationInfo.is_demo || situationInfo.is_sitrep || situationInfo.is_manual;

            console.log('[정황보고] 조건 체크:', {
                hasSituationInfo: !!situationInfo,
                hasSelectedThreat: !!selectedThreat,
                hasCOAResponse: !!coaResponse,
                isDemoOrSitrep,
                is_manual: situationInfo.is_manual,
                is_demo: situationInfo.is_demo,
                is_sitrep: situationInfo.is_sitrep
            });

            if (isDemoOrSitrep) {
                // situationInfo에서 threat_data 구성
                const threatId = situationInfo.threat_id || situationInfo.위협ID || situationInfo.situation_id || 'UNKNOWN';
                const threatData = {
                    threat_id: threatId,
                    threat_type_code: situationInfo.threat_type || situationInfo.위협유형,
                    location_cell_id: situationInfo.location || situationInfo.발생장소,
                    related_axis_id: situationInfo.axis_id || situationInfo.관련축선ID,
                    threat_level: situationInfo.threat_level || situationInfo.위협수준,
                    occurrence_time: situationInfo.occurrence_time || situationInfo.탐지시각,
                    raw_report_text: situationInfo.raw_report_text || situationInfo.description || situationInfo.상황설명,
                    // 🔥 FIX: 임무 관련 정보 추가
                    related_mission_id: situationInfo.mission_id || situationInfo.임무ID,
                    mission_type: situationInfo.mission_type || situationInfo.임무유형,
                    mission_name: situationInfo.mission_name || situationInfo.임무명,
                    mission_objective: situationInfo.mission_objective || situationInfo.임무목표,
                    // 🔥 FIX: approach_mode 추가 (임무 중심/위협 중심)
                    approach_mode: situationInfo.approach_mode || 'threat_centered',
                    // 데모 시나리오 식별을 위한 플래그
                    is_demo: situationInfo.is_demo,
                    is_manual: situationInfo.is_manual
                };

                console.log('[정황보고] 수동/데모/SITREP 모드 API 호출:', { threatId, approachMode: threatData.approach_mode, isDemoOrSitrep });
                fetchSituationSummary(threatId, threatData);
            }
        }

        // 클린업 함수: 새로운 위협 선택 시 이전 비동기 작업 취소
        return () => {
            isCancelled = true;
        };
    }, [
        selectedThreat?.threat_id,
        situationInfo?.threat_id,
        situationInfo?.situation_id,
        situationInfo?.is_manual,
        situationInfo?.is_demo,
        situationInfo?.is_sitrep,
        // 🔥 FIX: 수동 입력 시 모든 주요 필드 변경 감지
        situationInfo?.threat_type,
        situationInfo?.위협유형,
        situationInfo?.location,
        situationInfo?.발생장소,
        situationInfo?.axis_id,
        situationInfo?.관련축선ID,
        situationInfo?.threat_level,
        situationInfo?.위협수준,
        situationInfo?.description,
        situationInfo?.raw_report_text,
        // mission 관련 필드
        situationInfo?.mission_id,
        situationInfo?.임무ID,
        situationInfo?.mission_type,
        situationInfo?.임무유형,
        situationInfo?.mission_name,
        situationInfo?.임무명,
        situationInfo?.mission_objective,
        situationInfo?.임무목표,
        // 🔥 FIX: approach_mode 변경 감지 (위협 중심 ↔ 임무 중심)
        situationInfo?.approach_mode,
        coaResponse
    ]);

    const handleCOAResponse = (res: any) => {

        setLastResponse(res);
        setCOAResponse(res);
        // 방책 추천 완료 후 자동으로 모달이 열리지 않도록 선택하지 않음
        // 사용자가 플로팅 카드나 드롭다운에서 명시적으로 선택했을 때만 모달이 열림
        setModalAnchorElement(null); // 초기화
    };

    // COASelect 핸들러: 플로팅 카드에서 카드 클릭 시 또는 드롭다운에서 선택 시
    // 모달을 열지 않고 지도에 방책 정보만 표시
    const handleCOASelect = async (coa: COASummary | null) => {
        if (!coa) {
            setSelectedCOA(null);
            setModalAnchorElement(null);
            return;
        }

        console.log('[CommandControlPage] 방책 선택 (상세):', JSON.stringify({
            coa_id: coa?.coa_id,
            coa_name: coa?.coa_name,
            has_unit_positions: !!(coa as any)?.unit_positions,
            has_operational_path: !!(coa as any)?.operational_path || !!(coa as any)?.visualization_data?.operational_path,
            has_operational_area: !!(coa as any)?.operational_area || !!(coa as any)?.visualization_data?.operational_area,
            unit_positions_features: (coa as any)?.unit_positions?.features?.length || 0,
            participating_units: (coa as any)?.participating_units,
            participating_units_count: (coa as any)?.participating_units?.length || 0,
        }, null, 2));

        // 전체 COA 객체도 출력 (참조용, 펼쳐볼 수 있음)
        console.log('[CommandControlPage] 전체 COA 객체:', coa);

        // 🔥 FIX: unit_positions가 없는 경우 별도 API 호출하여 시각화 데이터 생성
        const unit_positions = (coa as any)?.unit_positions;
        const hasVisualization = unit_positions &&
            typeof unit_positions === 'object' &&
            unit_positions.features &&
            unit_positions.features.length > 0;

        if (!hasVisualization && (coa as any)?.participating_units) {
            console.log('[CommandControlPage] 시각화 데이터 없음, API 호출하여 생성 시도...');
            try {
                const response = await fetch(`http://${window.location.hostname}:8000/api/v1/coa/generate-visualization`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        coa_id: coa.coa_id,
                        participating_units: (coa as any).participating_units,
                        threat_position: selectedThreat ? {
                            latitude: (selectedThreat as any).latitude || 38.5,
                            longitude: (selectedThreat as any).longitude || 127.0
                        } : null
                    })
                });

                if (response.ok) {
                    const vizData = await response.json();
                    console.log('[CommandControlPage] 시각화 데이터 생성 성공:', {
                        has_unit_positions: !!vizData.unit_positions,
                        unit_positions_features: vizData.unit_positions?.features?.length || 0,
                        has_operational_path: !!vizData.operational_path,
                        has_operational_area: !!vizData.operational_area
                    });

                    // COA 객체에 시각화 데이터 추가
                    const updatedCOA = {
                        ...coa,
                        unit_positions: vizData.unit_positions,
                        visualization_data: {
                            ...(coa as any).visualization_data,
                            operational_path: vizData.operational_path,
                            operational_area: vizData.operational_area
                        }
                    } as COASummary;

                    setSelectedCOA(updatedCOA);
                } else {
                    console.error('[CommandControlPage] 시각화 데이터 생성 실패:', response.status);
                    setSelectedCOA(coa); // 원본 COA 사용
                }
            } catch (error) {
                console.error('[CommandControlPage] 시각화 API 호출 에러:', error);
                setSelectedCOA(coa); // 원본 COA 사용
            }
        } else {
            setSelectedCOA(coa);
        }

        // 🔥 FIX: 카드 클릭 시 모달을 열지 않도록 modalAnchorElement를 null로 유지
        // 지도에 방책 정보만 표시됨
        setModalAnchorElement(null);
    };

    // 정황보고 생성 함수 - useCallback으로 메모이제이션
    // 상황 정보의 모든 필드를 활용하여 상세하고 자연스러운 정황보고 생성
    const generateSituationSummary = useCallback((situation: any, selectedThreatData?: any): string | undefined => {
        if (!situation) return undefined;

        const approachMode = situation.approach_mode || 'threat_centered';
        const isMissionCentered = approachMode === 'mission_centered';

        // 시간 정보 (ISO 8601 형식을 사용자 친화적 형식으로 변환)
        let timeStr = situation.time_str || situation.occurrence_time || situation.timestamp || '';

        // ISO 8601 형식 변환 (예: "2025-01-01T23:10:00" -> "23:10")
        if (timeStr) {
            try {
                // ISO 8601 형식 파싱 시도
                if (timeStr.includes('T')) {
                    // ISO 8601 형식: "2025-01-01T23:10:00" 또는 "2025-01-01T23:10:00.000Z"
                    const date = new Date(timeStr);
                    if (!isNaN(date.getTime())) {
                        // 시간만 추출 (예: "23:10")
                        const hours = String(date.getHours()).padStart(2, '0');
                        const minutes = String(date.getMinutes()).padStart(2, '0');
                        timeStr = `${hours}:${minutes}`;
                    }
                }
                // 이미 시간 형식인 경우 (예: "23:10")는 그대로 사용
            } catch (e) {
                // 파싱 실패 시 원본 사용
            }
        }

        const timePrefix = timeStr ? `${timeStr} 현재, ` : '';

        // 위치 정보 (우선순위: 발생지역+발생지형명 > 발생지형명 > 발생장소 > location)
        const locationRegion = situation.발생지역 || situation.location_region || '';
        const locationName = situation.발생지형명 || situation.location_name || '';
        const locationCell = situation.발생장소 || situation.location || '';
        let locationDisplay = '';
        if (locationRegion && locationName) {
            locationDisplay = `${locationRegion} ${locationName}`;
        } else if (locationName) {
            locationDisplay = locationName;
        } else if (locationCell) {
            locationDisplay = locationCell;
        } else {
            locationDisplay = '작전 지역';
        }

        // 축선 정보 (코드-한글 매핑 적용)
        const axisId = situation.관련축선ID || situation.axis_id || '';
        const axisName = situation.관련축선명 || situation.axis_name || '';
        let axisDisplay = '';
        if (axisId) {
            // 코드를 한글로 변환
            const axisLabel = getAxisLabel(axisId);
            if (axisLabel && axisLabel !== axisId) {
                axisDisplay = formatWithCode(axisLabel, axisId);
            } else if (axisName && axisName !== 'N/A') {
                axisDisplay = `${axisName} (${axisId})`;
            } else {
                axisDisplay = axisId;
            }
        }

        // 위협 수준/임무 성공 가능성
        // situationInfo의 threat_level 또는 위협수준을 우선 사용, 없으면 selectedThreatData의 threat_level 사용
        // 위협수준이 문자열("HIGH", "MEDIUM", "LOW")로 저장되어 있을 수 있으므로 통합 파서 사용
        let threatLevelRaw = situation.threat_level;
        if ((threatLevelRaw === undefined || threatLevelRaw === null || threatLevelRaw === '') && situation.위협수준) {
            threatLevelRaw = situation.위협수준;
        }
        if ((threatLevelRaw === undefined || threatLevelRaw === null || threatLevelRaw === '') && selectedThreatData) {
            threatLevelRaw = selectedThreatData.threat_level;
        }

        let levelText = '미상';
        let levelPercent = '';

        // 통합 위협수준 파서 사용 (문자열 "HIGH", "MEDIUM", "LOW" 지원)
        const parsed = parseThreatLevel(threatLevelRaw);
        if (parsed) {
            levelPercent = `${parsed.percent}%`;

            // 위협 수준 텍스트 결정
            if (isMissionCentered) {
                if (parsed.normalized >= 0.8) levelText = '낮음';
                else if (parsed.normalized >= 0.5) levelText = '보통';
                else levelText = '높음';
            } else {
                if (parsed.normalized >= 0.8) levelText = '높음';
                else if (parsed.normalized >= 0.5) levelText = '중간';
                else levelText = '낮음';
            }
        }

        // 상황 설명 (상세 정보)
        const description = situation.상황설명 || situation.description || situation.raw_report_text || '';

        if (isMissionCentered) {
            // 임무 중심 모드
            const missionName = situation.임무명 || situation.mission_name || '기본 임무';
            const missionId = situation.임무ID || situation.mission_id || 'N/A';
            const missionType = situation.임무유형 || situation.mission_type || '';
            const missionObjective = situation.임무목표 || situation.mission_objective || '';

            let summary = `${timePrefix}${locationDisplay} 일대에서 **${missionName}**(${missionId}) 임무가 하달되었습니다.`;

            if (missionType) {
                summary += ` 임무 유형은 **${missionType}**이며,`;
            }

            if (axisDisplay) {
                summary += ` 주요 작전 축선은 **${axisDisplay}** 방향입니다.`;
            } else {
                summary += ' 주요 작전 축선은 미지정입니다.';
            }

            if (missionObjective) {
                summary += ` 임무 목표는 ${missionObjective}입니다.`;
            }

            if (levelPercent) {
                summary += ` 현재 분석된 임무 성공 가능성은 **${levelText}** 수준(${levelPercent})으로 평가됩니다.`;
            }

            if (description) {
                summary += ` ${description}`;
            }

            return summary;
        } else {
            // 위협 중심 모드
            const threatTypeRaw = situation.위협유형 || situation.threat_type || situation.threat_type_code || '미상';

            // 위협유형 코드를 한글로 변환
            let threatType = '미상';
            if (threatTypeRaw && threatTypeRaw !== '미상') {
                const threatTypeLabel = getThreatTypeLabel(threatTypeRaw);
                // 코드와 라벨이 다른 경우 병행 표기
                if (threatTypeLabel && threatTypeLabel !== threatTypeRaw) {
                    threatType = formatWithCode(threatTypeLabel, threatTypeRaw);
                } else {
                    threatType = threatTypeRaw;
                }
            } else {
                threatType = threatTypeRaw || '미상';
            }

            const enemyUnit = situation.enemy_units || situation.적부대 || '';
            const threatId = situation.selected_threat_id || situation.threat_id || situation.situation_id || 'N/A';

            let summary = `${timePrefix}${locationDisplay} 일대에서`;

            if (enemyUnit && enemyUnit !== '****' && enemyUnit !== 'N/A') {
                summary += ` **${enemyUnit}**에 의한`;
            } else {
                summary += ' 미상의 위협원에 의한';
            }

            summary += ` **${threatType}** 위협이 식별되었습니다.`;

            if (threatId && threatId !== 'N/A') {
                // 위협 ID에 위협 유형 정보 추가 (선택적)
                const threatIdLabel = getThreatIdLabel(threatId);
                if (threatIdLabel) {
                    summary += ` 위협 식별 번호는 **${threatId} (${threatIdLabel})**입니다.`;
                } else {
                    summary += ` 위협 식별 번호는 **${threatId}**입니다.`;
                }
            }

            if (axisDisplay) {
                summary += ` **${axisDisplay}** 방향 위협 수준은 **${levelText}** 상태`;
            } else {
                summary += ` 위협 수준은 **${levelText}** 상태`;
            }

            if (levelPercent) {
                summary += `(${levelPercent})로 분석됩니다.`;
            } else {
                summary += '입니다.';
            }

            if (description) {
                summary += ` ${description}`;
            }

            return summary;
        }
    }, []); // 의존성 배열이 비어있어서 한 번만 생성됨

    // situationSummary를 useMemo로 메모이제이션
    // 상황 정보의 더 많은 필드 변경을 감지하여 정황보고 재생성
    const situationSummary = useMemo(() => {
        // 0. 정황보고 생성 중일 때는 로딩 메시지 표시 (기존 값 유지하지 않음)
        if (isGeneratingSummary) {
            return "현재 상황을 분석하고 있습니다... (AI 정황보고 생성 중)";
        }

        // 1. 백엔드에서 생성된 정황보고를 최우선으로 사용
        if (lastResponse?.situation_summary) {
            // [정합성 검증] 현재 상황 ID와 응답 ID가 일치하는지 확인
            // 🔥 FIX: SITREP/데모 모드에서는 situationInfo의 ID를 우선 사용
            const isDemoOrSitrep = situationInfo?.is_demo || situationInfo?.is_sitrep || situationInfo?.is_manual;
            
            // SITREP/데모 모드에서는 situationInfo를 우선, 그 외에는 selectedThreat 우선
            const currentId = isDemoOrSitrep
                ? (situationInfo?.threat_id || situationInfo?.위협ID || situationInfo?.situation_id || selectedThreat?.threat_id)
                : (selectedThreat?.threat_id || situationInfo?.threat_id || situationInfo?.위협ID || situationInfo?.situation_id);
            
            const responseId = lastResponse.threat_id 
                || lastResponse.situation_id  // 데모 시나리오용
                || lastResponse.original_request?.threat_id;

            // ID가 있는데 불일치하는 경우 (Race Condition의 잔재 또는 데모→실제 전환)
            if (currentId && responseId && currentId !== responseId) {
                console.warn('[정황보고] ID 불일치 감지:', currentId, 'vs', responseId, '(isDemoOrSitrep:', isDemoOrSitrep, ')');
                // 🔥 FIX: 불일치하더라도 일단 응답을 표시 (사용자 경험 우선)
                // 다음 API 호출에서 올바른 데이터로 업데이트될 것임
                console.log('[정황보고] 불일치하지만 현재 응답 표시:', lastResponse.situation_summary?.substring(0, 50));
            }

            return lastResponse.situation_summary;
        }

        // 2. 백엔드 응답이 없으면 대기 메시지 반환
        if (situationInfo || selectedThreat) {
            return "상황 분석 대기 중...";
        }

        return undefined;
    }, [
        isGeneratingSummary,
        lastResponse?.situation_summary,
        lastResponse?.threat_id,
        lastResponse?.situation_id,  // 🔥 FIX: 데모 시나리오용 추가
        lastResponse?.original_request?.threat_id,
        situationInfo?.threat_id,
        situationInfo?.위협ID,
        situationInfo?.situation_id,  // 🔥 FIX: 데모 시나리오용 추가
        selectedThreat?.threat_id
    ]);

    // 축선 필터링: 관련된 축선만 표시 (위협 필터링과 동일한 로직)
    const visibleAxes = useMemo(() => {
        const relevantAxisIds = new Set<string>();

        // 1. 선택된 임무의 주 축선
        if (selectedMission?.primary_axis_id) {
            relevantAxisIds.add(selectedMission.primary_axis_id);
        }

        // 2. 선택된 위협의 관련 축선
        if (selectedThreat?.related_axis_id) {
            relevantAxisIds.add(selectedThreat.related_axis_id);
        }

        // 3. 상황 정보의 축선
        const situationAxisId = situationInfo?.관련축선ID || situationInfo?.axis_id;
        if (situationAxisId) {
            relevantAxisIds.add(situationAxisId);
        }

        // 관련 축선 ID가 없으면 빈 배열 반환 (초기 상태 깨끗함)
        if (relevantAxisIds.size === 0) {
            return [];
        }

        // 관련 축선만 필터링하여 반환
        return axes.filter(axis => relevantAxisIds.has(axis.axis_id));
    }, [
        selectedMission?.primary_axis_id,
        selectedThreat?.related_axis_id,
        situationInfo?.관련축선ID,
        situationInfo?.axis_id,
        axes
    ]);

    // onSituationChange를 useCallback으로 메모이제이션 (JSX 밖에서 정의)
    const handleSituationChange = useCallback((newSituation: any) => {
        // 실제로 변경된 경우에만 업데이트
        // situation_id가 변경되면 무조건 업데이트 (데모 시나리오, 실제 데이터 선택 등)
        const situationIdChanged = !situationInfo ||
            situationInfo.situation_id !== newSituation.situation_id;

        // 다른 주요 필드 변경 확인 (모든 수동 입력 필드 포함)
        const otherFieldsChanged = !situationInfo ||
            situationInfo.selected_threat_id !== newSituation.selected_threat_id ||
            situationInfo.위협ID !== newSituation.위협ID ||
            situationInfo.threat_id !== newSituation.threat_id ||
            situationInfo.mission_id !== newSituation.mission_id ||
            situationInfo.임무ID !== newSituation.임무ID ||
            situationInfo.threat_level !== newSituation.threat_level ||
            situationInfo.위협수준 !== newSituation.위협수준 ||
            situationInfo.location !== newSituation.location ||
            situationInfo.발생장소 !== newSituation.발생장소 ||
            situationInfo.axis_id !== newSituation.axis_id ||
            situationInfo.관련축선ID !== newSituation.관련축선ID ||
            // 🔥 FIX: 위협유형, 임무유형 필드 추가
            situationInfo.threat_type !== newSituation.threat_type ||
            situationInfo.위협유형 !== newSituation.위협유형 ||
            situationInfo.mission_type !== newSituation.mission_type ||
            situationInfo.임무유형 !== newSituation.임무유형 ||
            situationInfo.description !== newSituation.description ||
            situationInfo.raw_report_text !== newSituation.raw_report_text ||
            situationInfo.is_demo !== newSituation.is_demo ||
            situationInfo.is_sitrep !== newSituation.is_sitrep ||
            situationInfo.is_manual !== newSituation.is_manual ||
            // 🔥 FIX: approach_mode 변경 감지
            situationInfo.approach_mode !== newSituation.approach_mode ||
            situationInfo.mission_name !== newSituation.mission_name ||
            situationInfo.임무명 !== newSituation.임무명 ||
            situationInfo.mission_objective !== newSituation.mission_objective ||
            situationInfo.임무목표 !== newSituation.임무목표;

        if (situationIdChanged || otherFieldsChanged) {
            // 상황 정보 변경 시 관련된 모든 상태 초기화
            setSituationInfo(newSituation);

            // 🔥 FIX: 수동/데모/SITREP 모드에서는 lastResponse를 즉시 초기화하지 않음
            // useEffect가 새 데이터로 API를 호출하고 응답을 업데이트할 것임
            const isDemoOrSitrepOrManual = newSituation.is_demo || newSituation.is_sitrep || newSituation.is_manual;
            
            // situation_id가 완전히 바뀐 경우에만 초기화 (모드 전환 등)
            if (situationIdChanged && !isDemoOrSitrepOrManual) {
                setLastResponse(null);
                setIsGeneratingSummary(false);
            }
            // 수동/데모/SITREP 모드에서는 로딩 상태만 true로 설정 (기존 응답 유지하면서 업데이트 대기)
            else if (isDemoOrSitrepOrManual) {
                // lastResponse는 유지 - useEffect가 업데이트할 것임
                // setIsGeneratingSummary(true)는 fetchSituationSummary에서 설정됨
            }

            // 방책 추천 초기화 (새 상황이므로 방책 재생성 필요)
            setCOAResponse(null);
            // 선택된 방책 초기화
            setSelectedCOA(null);
            // 모달 앵커 초기화
            setModalAnchorElement(null);
            // 🔥 FIX: 데모/SITREP/수동 모드에서는 selectedThreat 초기화
            // (이 모드들은 situationInfo를 통해 처리됨)
            if (newSituation.is_demo || newSituation.is_sitrep || newSituation.is_manual || !newSituation.selected_threat_id) {
                setSelectedThreat(null);
            }
        }
    }, [situationInfo]);

    // onThreatIdentified를 useCallback으로 메모이제이션
    const handleThreatIdentified = useCallback((t: ThreatEventBase) => {
        setSelectedThreat(t);
    }, []);

    const removeToast = (id: string) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    };

    // 비교 패널에서 상세 보기 클릭 시 처리
    const handleViewCOADetail = (coa: COASummary) => {
        setSelectedCOA(coa);
        // 🔥 FIX: 드롭다운에서 선택한 경우에도 모달을 열 수 있도록
        // 하지만 modalAnchorElement가 null이면 모달이 열리지 않으므로, 
        // 드롭다운 선택 시에는 모달을 열지 않고 지도에만 표시
        // (사용자가 명시적으로 "상세 분석" 버튼을 클릭해야 모달이 열림)
        setModalAnchorElement(null); // 중앙 배치 (하지만 shouldShowModal 조건 때문에 모달이 열리지 않음)
    };

    // 드롭다운에서 "상세 분석" 버튼 클릭 시 처리
    const handleRequestModalOpen = (coa: COASummary) => {
        setSelectedCOA(coa);
        // 드롭다운에서 요청한 경우 중앙 배치를 위해 임시 요소 생성
        // 또는 null로 설정하고 shouldShowModal 조건을 수정
        // 임시 해결책: document.body를 anchor로 사용하여 중앙 배치
        setModalAnchorElement(document.body);
    };

    // 플로팅 카드에서 상세 분석 버튼 클릭 시 처리
    const handleFloatingCardViewDetail = (coa: COASummary) => {
        setSelectedCOA(coa);
        // 플로팅 카드 컨테이너 요소를 찾아서 모달 위치 계산에 사용
        const containerElement = floatingCardsRef.current?.getContainerElement();
        setModalAnchorElement(containerElement || null);
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 text-blue-600"></div>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="flex flex-col h-full">
                {/* Main Workspace - 지도가 화면 전체 높이 차지 */}
                <section className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1 min-h-0">

                    {/* Left: Analysis & COA (3 cols) - 좌측 패널 축소 및 컴팩트 */}
                    <div className="lg:col-span-3 flex flex-col gap-3 pr-1 overflow-y-auto custom-scrollbar">
                        {/* 축선별 전장분석 요약 - 좌측 패널 상단으로 이동 */}
                        {lastResponse?.axis_states && (
                            <div className="bg-white dark:bg-zinc-800 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-700 p-3 flex-shrink-0">
                                <div className="flex items-center gap-2 mb-2">
                                    <h3 className="font-black text-[10px] text-gray-500 dark:text-zinc-400 uppercase tracking-widest">축선별 전장분석 요약</h3>
                                    <div className="h-px flex-1 bg-gray-100 dark:bg-zinc-800" />
                                </div>
                                <AxisSummaryPanel axisStates={lastResponse.axis_states} />
                            </div>
                        )}

                        {/* Agent 선택 */}
                        <AgentSelector
                            onAgentChange={setSelectedAgent}
                            selectedAgent={selectedAgent}
                        />

                        {/* 시스템 설정 패널 - 컴팩트 */}
                        <div className="bg-white dark:bg-zinc-800 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-700 p-3">
                            <h3 className="font-semibold text-xs mb-2 text-gray-700 dark:text-gray-300 uppercase tracking-wider">시스템 설정</h3>
                            <SettingsPanel
                                usePalantirMode={usePalantirMode}
                                onPalantirModeChange={setUsePalantirMode}
                                selectedCOATypes={selectedCOATypes}
                                onCOATypesChange={setSelectedCOATypes}
                            />
                        </div>

                        {/* 상황 정보 입력 - 항상 표시 */}
                        <SituationInputPanel
                            onSituationChange={handleSituationChange}
                            initialSituation={situationInfo}
                            onThreatIdentified={handleThreatIdentified}
                        />

                        {/* 상황 요약 */}
                        {situationInfo && (
                            <SituationSummaryPanel situation={situationInfo} />
                        )}

                        <div className="bg-gradient-to-br from-white to-gray-50 dark:from-zinc-800 dark:to-zinc-900 p-3 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-700">
                            <div className="flex items-center gap-2 mb-1.5">
                                <span className="text-blue-500 text-[10px] font-black uppercase tracking-widest">Active Mission</span>
                                <div className="h-px flex-1 bg-blue-100 dark:bg-blue-900/30" />
                            </div>
                            {selectedMission ? (
                                <div>
                                    <div className="font-black text-base text-gray-900 dark:text-white mb-0.5">{selectedMission.mission_id}</div>
                                    <div className="text-gray-500 dark:text-zinc-400 text-xs italic line-clamp-2 leading-snug">
                                        "{selectedMission.commander_intent || '지휘관 의도 정보가 없습니다.'}"
                                    </div>
                                </div>
                            ) : (
                                <div className="text-gray-400 text-xs italic bg-gray-100 dark:bg-zinc-700/50 p-2 rounded-lg text-center">선택된 임무 없음</div>
                            )}
                        </div>
                        <COAGenerator
                            selectedMission={selectedMission}
                            selectedThreat={selectedThreat}
                            situationInfo={situationInfo}
                            onResponse={handleCOAResponse}
                            onCOASelect={handleCOASelect}
                            selectedCOA={selectedCOA}
                            modalAnchorElement={modalAnchorElement}
                            onRequestModalOpen={handleRequestModalOpen}
                            usePalantirMode={usePalantirMode}
                            coaTypeFilter={selectedCOATypes}
                        />
                    </div>

                    {/* Right: Map (9 cols) - 화면 전체 높이 */}
                    <div className="lg:col-span-9 flex flex-col bg-white dark:bg-zinc-800 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-700 overflow-hidden transition-all hover:border-blue-500/30 h-full">
                        <div className="p-2 border-b border-gray-200 dark:border-zinc-700 flex justify-between items-center bg-gray-50/50 dark:bg-zinc-900/50 flex-shrink-0">
                            <h3 className="font-black text-xs uppercase tracking-wider dark:text-zinc-300">실시간 작전 상황도 (Live COP)</h3>
                            <div className="flex gap-1.5 items-center">
                                <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                                <span className="text-[9px] font-bold text-gray-400 uppercase">Live</span>
                            </div>
                        </div>
                        <div className="flex-1 relative w-full min-h-0">
                            <TacticalMap
                                missions={missions}
                                threats={selectedThreat ? [selectedThreat] : []}
                                selectedThreat={selectedThreat}
                                coaRecommendations={coaResponse?.coas || []}
                                selectedCOA={selectedCOA}
                                onCOAClick={setSelectedCOA}
                                situationSummary={situationSummary}
                                situationSummarySource={lastResponse?.situation_summary_source}
                                situationAssessment={coaResponse?.coas?.[0]?.reasoning?.situation_assessment}
                                axisStates={coaResponse?.axis_states || lastResponse?.axis_states || []}
                                situationInfo={situationInfo}
                                friendlyUnits={friendlyUnits}
                                staticAxes={visibleAxes}
                            />

                            {/* 옵션 D: 플로팅 카드 - 지도 위에 표시 */}
                            {coaResponse?.coas && coaResponse.coas.length > 0 && (
                                <COAFloatingCards
                                    ref={floatingCardsRef}
                                    coas={coaResponse.coas}
                                    selectedCOA={selectedCOA}
                                    onCOASelect={handleCOASelect}
                                    onViewDetail={handleFloatingCardViewDetail}
                                    onCompare={() => setShowComparison(true)}
                                />
                            )}
                        </div>

                        {/* 지도 하단: 채팅 버튼 (항상 표시) 및 선택된 방책 정보 (방책 선택 시) */}
                        <div className="border-t border-gray-200 dark:border-zinc-700 bg-gray-50 dark:bg-zinc-900/50 flex-shrink-0 p-3">
                            {selectedCOA ? (
                                // 방책이 선택된 경우: 방책 정보 + 채팅 버튼
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3 flex-1 min-w-0">
                                        <span className="inline-block px-2 py-0.5 rounded text-xs font-bold bg-indigo-600 text-white flex-shrink-0">
                                            Rank {selectedCOA.rank}
                                        </span>
                                        <div className="flex-1 min-w-0">
                                            <h4 className="text-sm font-bold text-gray-900 dark:text-white line-clamp-2">{selectedCOA.coa_name}</h4>
                                            <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-3">
                                                {selectedCOA.description || '설명 없음'}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3 flex-shrink-0">
                                        <div className="text-right">
                                            <div className="text-lg font-bold text-indigo-600 dark:text-indigo-400">
                                                {selectedCOA.total_score !== undefined ? (selectedCOA.total_score * 100).toFixed(1) : 'N/A'}%
                                            </div>
                                            <div className="text-[10px] text-gray-500 dark:text-gray-400">총점</div>
                                        </div>
                                        <button
                                            onClick={() => setIsChatOpen(true)}
                                            className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg transition-colors"
                                        >
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                                            </svg>
                                            <span>작전 지휘관 채팅 (AI)</span>
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                // 방책이 선택되지 않은 경우: 채팅 버튼만
                                <div className="flex items-center justify-end">
                                    <button
                                        onClick={() => setIsChatOpen(true)}
                                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors shadow-md"
                                    >
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                                        </svg>
                                        <span>작전 지휘관 채팅 (AI)</span>
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </section>
            </div>
            <ChatInterface
                coaRecommendations={coaResponse?.coas || []}
                selectedCOA={selectedCOA}
                situationInfo={situationInfo}
                isOpen={isChatOpen}
                onOpenChange={setIsChatOpen}
            />

            {/* COA 비교 패널 */}
            {showComparison && coaResponse?.coas && (
                <COAComparisonPanel
                    coas={coaResponse.coas}
                    onClose={() => setShowComparison(false)}
                    onViewDetail={handleViewCOADetail}
                />
            )}

            {/* 4단계: 토스트 알림 */}
            {toasts.length > 0 && (
                <ToastContainer toasts={toasts} onRemove={removeToast} />
            )}

        </Layout>
    );
}
