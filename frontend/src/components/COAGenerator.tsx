import React, { useState, useEffect } from 'react';
import api from '../lib/api';
import type { COAGenerationRequest, COAResponse, COASummary, MissionBase, ThreatEventBase } from '../types/schema';
import { COADetailModal } from './COADetailModal';
import { COAComparisonPanel } from './COAComparisonPanel';
import { ProgressStatus } from './common/ProgressStatus';
import { useExecutionContext } from '../contexts/ExecutionContext';
import { BarChart3 } from 'lucide-react';
import { SkeletonCOACard } from './common/SkeletonCOACard';

interface COAGeneratorProps {
    selectedMission: MissionBase | null;
    selectedThreat: ThreatEventBase | null;
    situationInfo?: any; // SituationInputPanel에서 입력한 상황 정보
    onResponse?: (res: COAResponse) => void;
    onCOASelect?: (coa: COASummary | null) => void; // 선택된 방책 전달
    selectedCOA?: COASummary | null; // 외부에서 선택된 방책 (플로팅 카드 등에서)
    modalAnchorElement?: HTMLElement | null; // 모달 위치 계산용 앵커 요소 (플로팅 카드)
    onRequestModalOpen?: (coa: COASummary) => void; // 모달 열기 요청 (드롭다운에서 "상세 분석" 버튼 클릭 시)
    usePalantirMode?: boolean;
    coaTypeFilter?: string[];
}

export const COAGenerator: React.FC<COAGeneratorProps> = ({
    selectedMission,
    selectedThreat,
    situationInfo,
    onResponse,
    onCOASelect, // 선택된 방책 전달 콜백
    selectedCOA: externalSelectedCOA, // 외부에서 선택된 방책
    modalAnchorElement, // 모달 위치 계산용 앵커 요소
    onRequestModalOpen, // 모달 열기 요청 (드롭다운에서 "상세 분석" 버튼 클릭 시)
    usePalantirMode = true,
    coaTypeFilter = []
}) => {
    const [loading, setLoading] = useState(false);
    const [response, setResponse] = useState<COAResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [internalSelectedCOA, setInternalSelectedCOA] = useState<COASummary | null>(null);
    const [showComparison, setShowComparison] = useState(false);

    // 외부에서 선택된 방책이 있으면 그것을 우선 사용, 없으면 내부 상태 사용
    const selectedCOA = externalSelectedCOA !== undefined ? externalSelectedCOA : internalSelectedCOA;

    // ExecutionContext 사용 (옵션 - 없으면 로컬 상태만 사용)
    let executionContext: ReturnType<typeof useExecutionContext> | null = null;

    // 외부에서 선택된 방책이 변경되면 내부 상태도 동기화 (드롭다운 표시용)
    useEffect(() => {
        if (externalSelectedCOA !== undefined) {
            setInternalSelectedCOA(externalSelectedCOA);
        }
    }, [externalSelectedCOA]);

    // 1단계: 버튼 상태 수정 - response 설정 시 loading 해제
    useEffect(() => {
        if (response) {
            setLoading(false);
        }
    }, [response]);
    try {
        executionContext = useExecutionContext();
    } catch (e) {
        // ExecutionProvider가 없으면 로컬 상태만 사용
        console.log('ExecutionContext not available, using local state only');
    }

    // SituationInputPanel에서 입력한 정보를 기반으로 위협 데이터 생성
    const buildThreatFromSituation = (situation: any): ThreatEventBase | null => {
        if (!situation || situation.approach_mode === 'mission_centered') {
            return null;
        }

        // 위협 중심 모드일 때만 위협 데이터 생성
        // 백엔드 ThreatEventBase 형식에 맞춰 필드명 매핑

        // 1. 위협 수준 파싱 및 정규화 (0.5 또는 50% 형태 모두 지원)
        let rawThreatLevel = situation.threat_level !== undefined ? situation.threat_level : (situation.위협수준 || 0.7);
        let threatLevelValue: number = 0.7;

        if (typeof rawThreatLevel === 'string') {
            const cleaned = rawThreatLevel.replace('%', '').trim();
            const parsed = parseFloat(cleaned);
            if (!isNaN(parsed)) {
                // 1보다 크면 100으로 나누어 정규화 (예: 75 -> 0.75)
                threatLevelValue = parsed > 1 ? parsed / 100 : parsed;
            }
        } else if (typeof rawThreatLevel === 'number') {
            threatLevelValue = rawThreatLevel > 1 ? rawThreatLevel / 100 : rawThreatLevel;
        }

        const threatType = situation.threat_type || situation.위협유형 || '기타';
        const location = situation.location || situation.발생장소;
        const axisId = situation.axis_id || situation.관련축선ID;
        const timestamp = situation.timestamp || new Date().toISOString();

        // 백엔드 ThreatEventBase 스키마에 맞게 필드명 변환 (빈 문자열은 undefined로 처리)
        // [FIX] threat_level은 백엔드에서 0-1 사이의 값을 기대하므로 정규화된 값 전달
        const threatData: ThreatEventBase = {
            threat_id: situation.situation_id || `THREAT_${Date.now()}`,
            threat_type_code: threatType,
            threat_level: String(threatLevelValue), // 백엔드 기대치에 맞게 0-1 범위로 전달
            ...(location && { location_cell_id: location }),
            ...(axisId && { related_axis_id: axisId }),
            occurrence_time: timestamp, // ISO string 형식 (Pydantic이 자동 파싱)
            raw_report_text: `위협 수준: ${Math.round(threatLevelValue * 100)}%, 유형: ${threatType}`,
            threat_type_original: threatType,
            confidence: Math.round(threatLevelValue * 100), // 백엔드는 int를 기대
            status: 1 // 기본값: 활성 상태
        };

        return threatData;
    };

    // 입력 검증 로직
    const validateInput = (): { isValid: boolean; errors: string[] } => {
        const errors: string[] = [];
        const approachMode = situationInfo?.approach_mode || 'threat_centered';
        const threatToUse = situationInfo
            ? buildThreatFromSituation(situationInfo)
            : selectedThreat;

        // 위협 중심 모드 검증
        if (approachMode === 'threat_centered') {
            if (!threatToUse && !selectedThreat) {
                errors.push('위협 정보가 필요합니다.');
            } else if (threatToUse) {
                if (!threatToUse.threat_type_code && !threatToUse.threat_type_original && !situationInfo?.위협유형) {
                    errors.push('위협 유형을 입력해주세요.');
                }
                if (threatToUse.threat_level !== undefined) {
                    const level = parseFloat(String(threatToUse.threat_level));
                    if (isNaN(level) || level < 0 || level > 100) {
                        errors.push('위협 수준은 0-100 사이의 값이어야 합니다.');
                    }
                }


                if (!threatToUse.location && !threatToUse.location_cell_id && !situationInfo?.발생장소) {
                    errors.push('발생 장소를 입력해주세요.');
                }
            }
        }

        // 임무 중심 모드 검증
        if (approachMode === 'mission_centered') {
            if (!selectedMission?.mission_id && !situationInfo?.mission_id) {
                errors.push('임무 정보가 필요합니다.');
            }
        }

        return {
            isValid: errors.length === 0,
            errors
        };
    };

    // 버튼 활성화 조건 개선 - 더 관대한 조건
    const isButtonDisabled = (): boolean => {
        if (loading) return true;

        // situationInfo가 있으면 항상 활성화 (사용자가 입력했다고 가정)
        if (situationInfo) {
            // 최소한의 정보가 있으면 활성화
            const hasMinimalInfo =
                situationInfo.threat_level !== undefined ||
                situationInfo.threat_type ||
                situationInfo.위협유형 ||
                situationInfo.location ||
                situationInfo.발생장소 ||
                situationInfo.mission_id ||
                situationInfo.임무ID;

            if (hasMinimalInfo) return false;
        }

        const approachMode = situationInfo?.approach_mode || 'threat_centered';

        // 위협 중심 모드: 위협 정보 또는 situationInfo가 있으면 활성화
        if (approachMode === 'threat_centered') {
            const threatToUse = situationInfo
                ? buildThreatFromSituation(situationInfo)
                : selectedThreat;
            // situationInfo가 있으면 활성화 (사용자가 입력 중일 수 있음)
            if (situationInfo) return false;
            return !threatToUse && !selectedThreat;
        }

        // 임무 중심 모드: 임무 정보 또는 situationInfo가 있으면 활성화
        if (approachMode === 'mission_centered') {
            // situationInfo가 있으면 활성화
            if (situationInfo) return false;
            return !selectedMission && !situationInfo?.mission_id;
        }

        // 기본적으로 selectedThreat나 selectedMission이 있으면 활성화
        return !selectedThreat && !selectedMission;
    };

    // 에러 처리 개선
    const handleError = (err: any) => {
        if (err.response) {
            // HTTP 에러
            const status = err.response.status;
            let detail = err.response.data?.detail || '알 수 없는 오류';

            // detail이 객체인 경우 JSON 문자열로 변환
            if (typeof detail === 'object') {
                try {
                    detail = JSON.stringify(detail, null, 2);
                } catch {
                    detail = String(detail);
                }
            }

            // 422 오류의 경우 더 자세한 정보 표시
            if (status === 422) {
                const validationErrors = err.response.data?.detail;
                if (Array.isArray(validationErrors)) {
                    const errorMessages = validationErrors.map((e: any) => {
                        if (typeof e === 'object' && e.msg) {
                            return `${e.loc?.join('.')}: ${e.msg}`;
                        }
                        return String(e);
                    }).join(', ');
                    setError(`입력 검증 오류: ${errorMessages}`);
                } else {
                    setError(`입력 검증 오류 (422): ${detail}`);
                }
                return;
            }

            switch (status) {
                case 400:
                    setError(`입력 오류: ${detail}`);
                    break;
                case 404:
                    setError(`리소스를 찾을 수 없습니다: ${detail}`);
                    break;
                case 500:
                    setError(`서버 오류: ${detail}`);
                    break;
                default:
                    setError(`오류 발생 (${status}): ${detail}`);
            }
        } else if (err.request) {
            // 네트워크 에러
            setError('서버에 연결할 수 없습니다. 네트워크를 확인해주세요.');
        } else {
            // 기타 에러
            setError(`오류 발생: ${err.message}`);
        }
    };

    const handleGenerate = async () => {
        // 입력 검증
        const validation = validateInput();
        if (!validation.isValid) {
            setError(validation.errors.join(', '));
            return;
        }

        // SituationInputPanel에서 입력한 정보가 있으면 우선 사용
        const threatToUse = situationInfo
            ? buildThreatFromSituation(situationInfo)
            : selectedThreat;

        setLoading(true);
        setError(null);
        setResponse(null);

        // ExecutionContext 시작
        if (executionContext) {
            executionContext.startExecution();
            executionContext.addLog('방책 생성 요청 전송...');
        }

        try {
            const approachMode = situationInfo?.approach_mode || 'threat_centered';

            // threat_data가 없거나 유효하지 않으면 threat_id만 사용
            let threatDataToSend: ThreatEventBase | undefined = undefined;
            let threatIdToSend: string | undefined = undefined;

            if (threatToUse) {
                // threat_data가 유효한 ThreatEventBase 형식인지 확인
                if (threatToUse.threat_id) {
                    // 백엔드 스키마에 맞게 필드명 변환 및 undefined 필드 제거
                    const cleanedThreatData: any = {
                        threat_id: threatToUse.threat_id
                    };

                    // 필수/유용한 필드만 포함
                    if (threatToUse.threat_type_code || threatToUse.threat_type) {
                        cleanedThreatData.threat_type_code = threatToUse.threat_type_code || threatToUse.threat_type;
                    }
                    if (threatToUse.threat_level !== undefined) {
                        cleanedThreatData.threat_level = typeof threatToUse.threat_level === 'string'
                            ? threatToUse.threat_level
                            : String(threatToUse.threat_level);
                    }
                    if (threatToUse.location_cell_id || threatToUse.location) {
                        cleanedThreatData.location_cell_id = threatToUse.location_cell_id || threatToUse.location;
                    }
                    if (threatToUse.related_axis_id || threatToUse.axis_id) {
                        cleanedThreatData.related_axis_id = threatToUse.related_axis_id || threatToUse.axis_id;
                    }
                    if (threatToUse.occurrence_time || threatToUse.timestamp) {
                        cleanedThreatData.occurrence_time = threatToUse.occurrence_time || threatToUse.timestamp;
                    }
                    if (threatToUse.raw_report_text || threatToUse.description) {
                        cleanedThreatData.raw_report_text = threatToUse.raw_report_text || threatToUse.description;
                    }
                    if (threatToUse.threat_type_original || threatToUse.threat_type) {
                        cleanedThreatData.threat_type_original = threatToUse.threat_type_original || threatToUse.threat_type;
                    }
                    if (threatToUse.confidence !== undefined) {
                        cleanedThreatData.confidence = threatToUse.confidence;
                    }
                    if (threatToUse.status !== undefined) {
                        cleanedThreatData.status = threatToUse.status;
                    }

                    threatDataToSend = cleanedThreatData as ThreatEventBase;
                    threatIdToSend = threatToUse.threat_id;
                }
            } else if (selectedThreat) {
                threatIdToSend = selectedThreat.threat_id;
                // selectedThreat는 이미 백엔드 형식이므로 그대로 사용
                threatDataToSend = selectedThreat;
            }

            // 🔥 FIX: 임무 ID 추출 (mission_id 또는 임무ID 필드 확인)
            const missionIdToSend = selectedMission?.mission_id 
                || situationInfo?.mission_id 
                || situationInfo?.임무ID;
            
            const payload: COAGenerationRequest = {
                ...(threatIdToSend && { threat_id: threatIdToSend }),
                ...(threatDataToSend && { threat_data: threatDataToSend }),
                ...(missionIdToSend && { mission_id: missionIdToSend }),
                user_params: {
                    max_coas: 3,
                    approach_mode: approachMode,
                    use_palantir_mode: usePalantirMode,
                    ...(coaTypeFilter.length > 0 && { coa_type_filter: coaTypeFilter }),
                    // SituationInputPanel에서 입력한 추가 정보 전달
                    ...(situationInfo && {
                        situation_info: {
                            situation_id: situationInfo.situation_id,
                            ...(situationInfo.environment && { environment: situationInfo.environment }),
                            ...(situationInfo.defense_assets && { defense_assets: situationInfo.defense_assets }),
                            ...(situationInfo.resource_availability && { resource_availability: situationInfo.resource_availability })
                        }
                    })
                }
            };

            // 디버깅을 위한 로깅
            console.log('COA Generation Request:', JSON.stringify(payload, null, 2));

            if (executionContext) {
                executionContext.updateProgress(5, '방책 분석 시작...');
                executionContext.addLog('방책 추천 요청 전송 중...');
            }

            // 진행 상황 시뮬레이션 (백엔드 응답을 기다리는 동안)
            const progressSimulation = [
                { progress: 5, message: '온톨로지 데이터 로드 중...' },
                { progress: 10, message: '전술 상황 분석 중...' },
                { progress: 20, message: '방책 후보 검색 중...' },
                { progress: 30, message: '방책 유형 분석 중...' },
                { progress: 45, message: '방책 점수 계산 중...' },
                { progress: 60, message: '종합 점수 계산 중...' },
                { progress: 75, message: 'LLM 기반 구체화 중...' },
                { progress: 85, message: '선정사유 생성 중...' },
            ];

            let simulationIndex = 0;
            let simulationInterval: NodeJS.Timeout | null = null;

            if (executionContext) {
                simulationInterval = setInterval(() => {
                    if (simulationIndex < progressSimulation.length && executionContext) {
                        const step = progressSimulation[simulationIndex];
                        executionContext.updateProgress(step.progress, step.message);
                        executionContext.addLog(`[${step.progress}%] ${step.message}`);
                        simulationIndex++;
                    } else if (simulationInterval) {
                        clearInterval(simulationInterval);
                        simulationInterval = null;
                    }
                }, 800); // 0.8초마다 업데이트
            }

            // Agent 기반 방책 추천 사용 (Streamlit과 동일한 로직)
            // Agent API를 사용하여 온톨로지 + RAG + LLM 통합 파이프라인 활용
            const agentPayload = {
                agent_class_path: "agents.defense_coa_agent.logic_defense_enhanced.EnhancedDefenseCOAAgent",
                situation_id: threatIdToSend || situationInfo?.situation_id,
                situation_info: situationInfo ? {
                    ...situationInfo,
                    approach_mode: approachMode,
                    // ThreatEventBase 형식으로 변환된 데이터도 포함
                    ...(threatDataToSend && {
                        threat_id: threatDataToSend.threat_id,
                        threat_type_code: threatDataToSend.threat_type_code,
                        threat_level: threatDataToSend.threat_level,
                        location_cell_id: threatDataToSend.location_cell_id,
                        related_axis_id: threatDataToSend.related_axis_id,
                        occurrence_time: threatDataToSend.occurrence_time,
                        raw_report_text: threatDataToSend.raw_report_text
                    })
                } : undefined,
                use_palantir_mode: usePalantirMode,
                enable_rag_search: true,
                coa_type_filter: coaTypeFilter.length > 0 ? coaTypeFilter : undefined,
                user_params: {
                    max_coas: 3,
                    approach_mode: approachMode,
                    ...(situationInfo && {
                        situation_info: {
                            situation_id: situationInfo.situation_id,
                            ...(situationInfo.environment && { environment: situationInfo.environment }),
                            ...(situationInfo.defense_assets && { defense_assets: situationInfo.defense_assets }),
                            ...(situationInfo.resource_availability && { resource_availability: situationInfo.resource_availability })
                        }
                    })
                }
            };

            // Agent API 호출
            const res = await api.post<COAResponse>('/agent/execute', agentPayload);

            // 시뮬레이션 중지
            if (simulationInterval) {
                clearInterval(simulationInterval);
                simulationInterval = null;
            }

            // 백엔드에서 수집한 실제 진행 상황 로그가 있으면 재생
            if (res.data.progress_logs && res.data.progress_logs.length > 0 && executionContext) {
                // 실제 진행 상황 로그를 시간 순서대로 재생 (빠르게)
                // 마지막 진행률로 먼저 업데이트 (실제 진행 상황 반영)
                const lastLog = res.data.progress_logs[res.data.progress_logs.length - 1];
                if (lastLog.progress !== null) {
                    executionContext.updateProgress(lastLog.progress, lastLog.message);
                }

                // 모든 로그를 빠르게 재생하여 사용자가 전체 과정을 볼 수 있도록
                res.data.progress_logs.forEach((log, idx) => {
                    setTimeout(() => {
                        if (executionContext && log.progress !== null) {
                            executionContext.updateProgress(log.progress, log.message);
                            executionContext.addLog(`[${log.progress}%] ${log.message}`);
                        }
                    }, idx * 50); // 0.05초 간격으로 빠르게 재생
                });

                // 마지막 로그 재생 완료 대기
                await new Promise(resolve => setTimeout(resolve, res.data.progress_logs.length * 50 + 100));
            }

            if (executionContext) {
                executionContext.updateProgress(95, '결과 처리 중...');
                executionContext.addLog('방책 추천 완료');
            }

            // 응답 데이터 검증
            if (!res.data || !res.data.coas) {
                throw new Error('응답 데이터 형식이 올바르지 않습니다.');
            }

            // Agent API 응답은 이미 상위 3개만 포함하므로 그대로 사용
            // situation_summary와 situation_summary_source가 있으면 추가
            const limitedResponse = {
                ...res.data,
                coas: Array.isArray(res.data.coas) ? res.data.coas.slice(0, 3) : [],
                // Agent API에서 반환한 situation_summary 및 source 포함
                situation_summary: (res.data as any).situation_summary,
                situation_summary_source: (res.data as any).situation_summary_source
            };

            setResponse(limitedResponse);
            if (onResponse) onResponse(limitedResponse);

            if (executionContext) {
                executionContext.updateProgress(100, '방책 추천 완료');
                executionContext.addLog(`상위 ${limitedResponse.coas.length}개 방책 추천 완료`);
                // 완료 후 약간의 지연을 두고 숨김 (사용자가 완료 메시지를 볼 수 있도록)
                setTimeout(() => {
                    executionContext?.completeExecution();
                }, 2000); // 2초 후 사라짐
            }

            // 4단계: 성공 토스트 알림 (컴포넌트 내부에서 처리)
            // Toast는 CommandControlPage에서 관리
        } catch (err: any) {
            console.error('COA 생성 오류:', err);
            console.error('Error details:', {
                message: err.message,
                response: err.response?.data,
                stack: err.stack
            });

            // 에러 처리
            handleError(err);

            if (executionContext) {
                const errorMessage = err.response?.data?.detail
                    ? (typeof err.response.data.detail === 'string'
                        ? err.response.data.detail
                        : JSON.stringify(err.response.data.detail))
                    : err.message || '알 수 없는 오류';
                executionContext.errorExecution(errorMessage);
            }

            // 에러 발생 시에도 로딩 상태 해제
            setLoading(false);
        }
    };

    const handleCOAClick = (coa: COASummary, fromDropdown: boolean = false) => {
        setInternalSelectedCOA(coa);
        if (onCOASelect) {
            onCOASelect(coa);
            // 드롭다운에서 선택한 경우, 부모 컴포넌트에 중앙 배치를 알려야 함
            // 하지만 modalAnchorElement는 부모에서 관리하므로 여기서는 onCOASelect만 호출
        }
    };

    const handleModalClose = () => {
        console.log('handleModalClose 호출됨');
        // 외부 상태를 먼저 클리어 (onCOASelect를 통해 CommandControlPage의 selectedCOA를 null로 설정)
        if (onCOASelect) {
            console.log('onCOASelect(null) 호출');
            onCOASelect(null);
        }
        // 내부 상태도 클리어
        console.log('setInternalSelectedCOA(null) 호출');
        setInternalSelectedCOA(null);
    };

    // 모달 표시 조건: selectedCOA가 null이 아닐 때만 표시
    // 🔥 FIX: modalAnchorElement가 있을 때만 모달 표시 (플로팅 카드의 "상세 분석" 버튼 클릭 시)
    // 카드 클릭만으로는 모달이 열리지 않도록 수정
    // document.body는 드롭다운에서 "상세 분석" 버튼 클릭 시 사용 (중앙 배치)
    const shouldShowModal = selectedCOA !== null && selectedCOA !== undefined &&
        modalAnchorElement !== null && modalAnchorElement !== undefined;

    return (
        <>
            <div className="bg-white dark:bg-zinc-800 p-4 rounded-lg shadow-sm border border-gray-200 dark:border-zinc-700 h-full flex flex-col">
                <h3 className="font-semibold text-lg mb-4 dark:text-white">방책 추천 (COA Recommendation)</h3>

                <div className="mb-4 space-y-2 text-sm">
                    <div className="flex justify-between items-center p-2 bg-gray-50 dark:bg-zinc-700 rounded">
                        <span className="text-gray-500 dark:text-gray-400">대상 임무:</span>
                        <span className="font-medium dark:text-white">
                            {selectedMission?.mission_id || situationInfo?.mission_id || '선택 안됨'}
                        </span>
                    </div>
                    <div className="flex justify-between items-center p-2 bg-gray-50 dark:bg-zinc-700 rounded">
                        <span className="text-gray-500 dark:text-gray-400">대상 위협:</span>
                        <span className="font-medium text-red-600 dark:text-red-400">
                            {situationInfo?.selected_threat_id || situationInfo?.위협ID || situationInfo?.situation_id || selectedThreat?.threat_id || '선택 안됨'}
                        </span>
                    </div>
                    {situationInfo && (
                        <div className="flex justify-between items-center p-2 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
                            <span className="text-gray-500 dark:text-gray-400">접근 방식:</span>
                            <span className="font-medium text-blue-600 dark:text-blue-400">
                                {situationInfo.approach_mode === 'threat_centered' ? '위협 중심' : '임무 중심'}
                            </span>
                        </div>
                    )}
                </div>

                <button
                    onClick={handleGenerate}
                    disabled={isButtonDisabled()}
                    className={`w-full py-3 px-4 rounded text-white font-bold text-lg mb-6 shadow-md transition-all transform hover:scale-[1.02] ${isButtonDisabled()
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700'
                        }`}
                >
                    {loading ? (
                        <span className="flex items-center justify-center gap-2">
                            <span className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></span>
                            방책 생성 및 워게임 진행 중...
                        </span>
                    ) : (
                        '방책 추천 실행'
                    )}
                </button>

                {error && (
                    <div className="p-3 mb-4 bg-red-50 text-red-700 text-sm rounded border border-red-200">
                        {error}
                    </div>
                )}

                <div className="flex-1 overflow-auto">
                    {loading ? (
                        <div className="space-y-4">
                            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg animate-pulse">
                                <div className="h-4 w-48 bg-blue-200 dark:bg-blue-800 rounded mb-2"></div>
                                <div className="h-3 w-32 bg-blue-100 dark:bg-blue-900 rounded"></div>
                            </div>
                            {/* 3개의 스켈레톤 카드 표시 */}
                            <SkeletonCOACard />
                            <SkeletonCOACard />
                            <SkeletonCOACard />
                        </div>
                    ) : response ? (
                        <div className="space-y-4">
                            <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="text-green-600 dark:text-green-400 text-lg">✓</span>
                                    <h4 className="font-bold text-sm text-gray-800 dark:text-gray-200">
                                        {response.coas.length}개의 방책이 추천되었습니다
                                    </h4>
                                </div>
                                <p className="text-xs text-gray-600 dark:text-gray-400">
                                    상단 결과 패널에서 방책을 확인하고 선택할 수 있습니다. 상세 분석은 방책을 클릭하세요.
                                </p>
                            </div>

                            {/* 방책 선택 드롭다운 (간소화 - 하이브리드 방안: 유지하되 간소화) */}
                            {response.coas.length > 0 && (
                                <div className="mb-4">
                                    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">
                                        🔍 상세 분석할 방책 선택 (선택사항)
                                    </label>
                                    <div className="flex gap-2">
                                        <select
                                            value={selectedCOA?.coa_id || ''}
                                            onChange={(e) => {
                                                const coa = response.coas.find(c => c.coa_id === e.target.value);
                                                if (coa) {
                                                    handleCOAClick(coa);
                                                    // 드롭다운에서 선택 시 onCOASelect 호출 (지도에 표시만, 모달은 열지 않음)
                                                    if (onCOASelect) {
                                                        onCOASelect(coa);
                                                    }
                                                } else {
                                                    // 선택 해제
                                                    if (onCOASelect) {
                                                        onCOASelect(null);
                                                    }
                                                }
                                            }}
                                            className="flex-1 h-9 rounded-md border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        >
                                            <option value="">방책 선택...</option>
                                            {response.coas.map((coa, idx) => (
                                                <option key={coa.coa_id} value={coa.coa_id}>
                                                    {idx + 1}. {coa.coa_name} ({coa.total_score !== undefined ? (coa.total_score * 100).toFixed(1) : 'N/A'}%)
                                                </option>
                                            ))}
                                        </select>
                                        {selectedCOA && (
                                            <button
                                                onClick={() => {
                                                    // 🔥 FIX: 드롭다운에서 "상세 분석" 버튼 클릭 시 모달 열기
                                                    // 부모 컴포넌트에 모달 열기 요청
                                                    if (onRequestModalOpen) {
                                                        onRequestModalOpen(selectedCOA);
                                                    }
                                                }}
                                                className="px-3 h-9 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold transition-colors whitespace-nowrap"
                                            >
                                                상세 분석
                                            </button>
                                        )}
                                    </div>
                                    <p className="mt-1 text-[10px] text-gray-500 dark:text-gray-500 italic">
                                        💡 방책 선택 시 지도에 표시됩니다. 상세 분석은 버튼을 클릭하세요
                                    </p>
                                </div>
                            )}
                        </div>
                    ) : null}
                </div>
            </div>

            {shouldShowModal && (
                <COADetailModal
                    coa={selectedCOA}
                    onClose={handleModalClose}
                    anchorElement={modalAnchorElement || undefined}
                    situationInfo={situationInfo}
                />
            )}

            {/* COA 비교 패널 */}
            {showComparison && response && (
                <COAComparisonPanel
                    coas={response.coas}
                    onClose={() => setShowComparison(false)}
                />
            )}

            {/* 진행 상황 표시 */}
            {executionContext && (executionContext.isRunning || executionContext.progress > 0) && (
                <ProgressStatus
                    label={executionContext.message}
                    progress={executionContext.progress}
                    logs={executionContext.logs}
                    state={
                        executionContext.progress === 100 && !executionContext.isRunning
                            ? 'complete'
                            : executionContext.message.includes('오류') || executionContext.message.includes('ERROR')
                                ? 'error'
                                : 'running'
                    }
                    onCancel={executionContext.isRunning ? executionContext.cancelExecution : undefined}
                />
            )}
        </>
    );
};

// 방책 유형 한글 변환
const coaTypeMap: Record<string, string> = {
    "Defense": "방어",
    "Offensive": "공세",
    "Counter_Attack": "반격",
    "Preemptive": "선제",
    "Deterrence": "억제",
    "Maneuver": "기동",
    "Information_Ops": "정보작전"
};

// 선정 카테고리 한글 변환
const categoryMap: Record<string, string> = {
    "Operational Optimum": "작전 최적",
    "Maneuver & Speed": "기동/속도",
    "Firepower Focus": "화력 집중",
    "Sustainable Defense": "지속 방어"
};

const COACard: React.FC<{ coa: COASummary; onClick: () => void; isSelected?: boolean }> = ({
    coa,
    onClick,
    isSelected = false
}) => {
    // 참여 부대 정보 추출
    const participatingUnits = (coa as any).participating_units;
    const unitsText = Array.isArray(participatingUnits)
        ? participatingUnits.join(', ')
        : participatingUnits || '';

    // 방책 유형 및 선정 카테고리
    const coaType = (coa as any).coa_type || (coa as any).type;
    const selectionCategory = (coa as any).selection_category;
    const coaTypeKo = coaType ? (coaTypeMap[coaType] || coaType) : '';
    const categoryKo = selectionCategory ? (categoryMap[selectionCategory] || selectionCategory) : '';

    // 시스템 탐색 과정
    const systemSearchPath = (coa as any).reasoning?.system_search_path ||
        (coa as any).reasoning?.search_path;

    return (
        <div
            onClick={onClick}
            className={`p-4 bg-white dark:bg-zinc-900 border rounded-lg hover:shadow-md transition-all cursor-pointer group ${isSelected
                ? 'border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20'
                : 'border-gray-200 dark:border-zinc-700 hover:border-blue-500 dark:hover:border-blue-400'
                }`}
        >
            <div className="flex justify-between items-start mb-3">
                <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-black bg-blue-600 text-white uppercase italic">
                            Rank {coa.rank}
                        </span>
                        <h5 className="text-md font-bold text-gray-900 dark:text-white group-hover:text-blue-600 transition-colors">
                            {coa.coa_name}
                        </h5>
                        {coaTypeKo && (
                            <span className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 border border-indigo-300 dark:border-indigo-700">
                                {coaTypeKo}
                            </span>
                        )}
                        {categoryKo && (
                            <span className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 border border-orange-300 dark:border-orange-700">
                                {categoryKo}
                            </span>
                        )}
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 mb-2">
                        {coa.description || '작전 방안 세부 설명 없음'}
                    </p>

                    {/* 참여 부대 */}
                    {unitsText && (
                        <div className="text-xs text-gray-600 dark:text-gray-400 mb-2 flex items-center gap-1">
                            <span>⚓</span>
                            <span>{unitsText}</span>
                        </div>
                    )}

                    {/* 시스템 탐색 과정 */}
                    {systemSearchPath && (
                        <div className="text-xs text-gray-500 dark:text-gray-500 italic mb-2 bg-gray-50 dark:bg-zinc-800 p-2 rounded">
                            🔍 {systemSearchPath}
                        </div>
                    )}
                </div>
                <div className="text-right ml-4">
                    <div className="text-2xl font-black text-indigo-600 dark:text-indigo-400 leading-none">
                        {coa.total_score !== undefined ? (coa.total_score * 10).toFixed(1) : 'N/A'}
                    </div>
                    <span className="text-[9px] text-gray-400 font-bold uppercase tracking-widest block mt-1">Total Score</span>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-x-4 gap-y-2 pt-3 border-t border-gray-100 dark:border-zinc-800">
                <ScoreProgressBar label="전투력" score={coa.combat_power_score} color="bg-blue-500" />
                <ScoreProgressBar label="기동성" score={coa.mobility_score} color="bg-green-500" />
                <ScoreProgressBar label="제약조건" score={coa.constraint_score} color="bg-yellow-500" />
                <ScoreProgressBar label="위협대응" score={coa.threat_response_score} color="bg-red-500" />
            </div>

            <div className="flex justify-end mt-3">
                <span className="text-[11px] text-indigo-500 font-bold group-hover:underline flex items-center gap-1">
                    상세 인텔리전스 확인 &rarr;
                </span>
            </div>
        </div>
    );
};

const ScoreProgressBar: React.FC<{ label: string; score: number | undefined; color: string }> = ({ label, score = 0, color }) => {
    const safeScore = score !== undefined && score !== null ? score : 0;
    return (
        <div className="space-y-1">
            <div className="flex justify-between text-[10px]">
                <span className="text-gray-500 font-medium">{label}</span>
                <span className="font-bold text-gray-700 dark:text-zinc-300">{(safeScore * 100).toFixed(0)}%</span>
            </div>
            <div className="w-full h-1 bg-gray-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                <div
                    className={`h-full ${color} transition-all duration-1000`}
                    style={{ width: `${Math.min(safeScore * 100, 100)}%` }}
                />
            </div>
        </div>
    );
};
