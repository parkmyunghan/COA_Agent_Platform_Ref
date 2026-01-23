import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
// RadioGroup은 직접 구현 (간단한 버전)
// Select는 HTML select로 대체
import { Slider } from './ui/slider';
import { Textarea } from './ui/textarea';
import api from '../lib/api';
import type { ThreatEventBase } from '../types/schema';
import { useSystemData } from '../hooks/useSystemData';
import { useCodeLabels } from '../hooks/useCodeLabels';
import { parseThreatLevel } from '../lib/threat-level-parser';

interface SituationInputPanelProps {
    onSituationChange: (situation: any) => void;
    initialSituation?: any;
    onThreatIdentified?: (threat: any) => void;
}

export const SituationInputPanel: React.FC<SituationInputPanelProps> = ({
    onSituationChange,
    initialSituation,
    onThreatIdentified
}) => {
    // 임무 중심 모드 제거 - 위협 중심 모드만 지원
    const approachMode = 'threat_centered' as const;
    const [inputMode, setInputMode] = useState<'manual' | 'real_data' | 'sitrep' | 'scenario'>('real_data');
    const [situation, setSituation] = useState<any>(initialSituation || {
        situation_id: '',
        approach_mode: 'threat_centered',
        timestamp: new Date().toISOString(),
        is_manual: true,
        threat_level: 0,
        location: '',
        threat_type: ''
    });

    // 시스템 데이터에서 정보 가져오기 (위협, 임무, 축선, 지형셀)
    const { threats: availableThreats, missions: availableMissions, axes: availableAxes, terrainCells, loading: loadingThreats } = useSystemData();

    // 코드-한글 매핑 훅
    const { getThreatTypeLabel } = useCodeLabels();

    // filteredAxes 및 filteredTerrainCells 계산을 위한 useMemo 추가
    const filteredAxes = React.useMemo(() => {
        const locationId = situation.발생장소 || situation.location;
        if (!locationId) return availableAxes;

        return availableAxes.filter(axis =>
            axis.start_cell_id === locationId || axis.end_cell_id === locationId
        );
    }, [situation.발생장소, situation.location, availableAxes]);

    const filteredTerrainCells = React.useMemo(() => {
        const axisId = situation.관련축선ID || situation.axis_id;
        if (!axisId) return terrainCells;

        const selectedAxis = availableAxes.find(a => a.axis_id === axisId);
        if (!selectedAxis) return terrainCells;

        return terrainCells.filter(cell =>
            cell.cell_id === selectedAxis.start_cell_id ||
            cell.cell_id === selectedAxis.end_cell_id
        );
    }, [situation.관련축선ID, situation.axis_id, availableAxes, terrainCells]);

    // initialSituation이 변경될 때 내부 상태 동기화 (외부에서 강제 업데이트된 경우)
    // useRef로 이전 값 추적하여 실제 변경 여부 확인
    const prevInitialSituationRef = useRef<any>(null);
    useEffect(() => {
        if (initialSituation) {
            // 실제로 변경된 경우에만 업데이트
            const hasChanged = !prevInitialSituationRef.current ||
                prevInitialSituationRef.current.selected_threat_id !== initialSituation.selected_threat_id ||
                prevInitialSituationRef.current.mission_id !== initialSituation.mission_id ||
                prevInitialSituationRef.current.threat_level !== initialSituation.threat_level ||
                prevInitialSituationRef.current.location !== initialSituation.location;

            if (hasChanged) {
                setSituation(initialSituation);
                prevInitialSituationRef.current = initialSituation;
            }
        }
    }, [initialSituation?.selected_threat_id, initialSituation?.mission_id, initialSituation?.threat_level, initialSituation?.location]);

    // 초기 상황 정보를 부모에게 전달하는 로직 제거 (초기 상태 리셋 유지)
    // useEffect(() => {
    //    if (!initialSituation && situation && Object.keys(situation).length > 0) {
    //        onSituationChange(situation);
    //    }
    // }, []);

    // 시스템 데이터에서 정보 가져오기 로직 상단으로 이동됨

    // onSituationChange를 useRef로 저장하여 최신 참조 유지
    const onSituationChangeRef = useRef(onSituationChange);
    useEffect(() => {
        onSituationChangeRef.current = onSituationChange;
    }, [onSituationChange]);

    // 데이터 정규화 및 텍스트 자동 생성 헬퍼
    const normalizeSituationData = (data: any) => {
        // 1. 키 정규화 (한글 -> 영문 표준)
        const normalized = { ...data };

        if (!normalized.threat_type && normalized.위협유형) normalized.threat_type = normalized.위협유형;
        if (!normalized.threat_level && normalized.위협수준) {
            // 위협수준이 문자열(%)인 경우 처리
            const val = String(normalized.위협수준).replace('%', '').trim();
            const num = parseFloat(val);
            normalized.threat_level = !isNaN(num) && num > 1 ? num / 100 : num;
        }
        if (!normalized.location && normalized.발생장소) normalized.location = normalized.발생장소;
        if (!normalized.axis_id && normalized.관련축선ID) normalized.axis_id = normalized.관련축선ID;
        if (!normalized.mission_id && normalized.임무ID) normalized.mission_id = normalized.임무ID;

        // 🔥 FIX: 중요한 플래그들을 명시적으로 보존 (정황보고 API 호출 조건에 필요)
        // inputMode에 따라 해당 플래그 설정
        if (inputMode === 'manual') {
            normalized.is_manual = true;
            normalized.is_demo = false;
            normalized.is_sitrep = false;
        } else if (inputMode === 'scenario') {
            normalized.is_demo = true;
            normalized.is_manual = false;
            normalized.is_sitrep = false;
        } else if (inputMode === 'sitrep') {
            normalized.is_sitrep = true;
            normalized.is_manual = false;
            normalized.is_demo = false;
        } else {
            // real_data 모드는 플래그 없음
            normalized.is_manual = false;
            normalized.is_demo = false;
            normalized.is_sitrep = false;
        }

        // 2. 누락된 raw_report_text 자동 생성 (수동 모드이거나 텍스트가 없는 경우)
        // 단, SITREP 모드는 사용자가 직접 입력하므로 제외할 수 있으나, 비어있다면 생성
        if (!normalized.raw_report_text && inputMode === 'manual') {
            normalized.raw_report_text = generateAutoReportText(normalized);
        }

        return normalized;
    };

    const generateAutoReportText = (data: any) => {
        const time = new Date().toLocaleString('ko-KR');
        const loc = data.location || data.발생장소 || '미상 지역';
        const type = data.threat_type || data.위협유형 || '미상 위협';
        const level = data.threat_level !== undefined ? Math.round(data.threat_level * 100) : 0;
        const axis = data.axis_id || data.관련축선ID ? `(${data.axis_id || data.관련축선ID} 축선)` : '';
        const env = data.environment ? `기상은 ${data.environment.weather || '보통'}이며 지형은 ${data.environment.terrain || '복합'} 지형임.` : '';

        let levelDesc = '낮음';
        if (level >= 80) levelDesc = '매우 심각';
        else if (level >= 50) levelDesc = '중간';

        return `[자동생성 보고] ${time}경 ${loc} 일대${axis}에서 ${type} 활동이 식별됨. 현재 위협 수준은 ${level}%(${levelDesc})로 평가됨. ${env} 아군 부대의 즉각적인 상황 판단 및 대응이 요구됨.`;
    };

    // updateSituation을 useCallback으로 메모이제이션
    // 실제로 변경된 필드만 확인하여 불필요한 업데이트 방지
    const updateSituation = useCallback((updates: any) => {
        setSituation((prevSituation) => {
            const tempSituation = { ...prevSituation, ...updates };

            // 정규화 적용 (텍스트 생성 포함)
            // 주의: 리렌더링 루프를 방지하기 위해, raw_report_text가 변경될 때마다 다시 updateSituation이 불리지 않도록 주의해야 함.
            // 하지만 여기서는 setSituation 내부이므로 괜찮음.
            // 다만, inputMode 의존성이 generateAutoReportText 내부에 있으므로 useCallback 의존성에 inputMode 추가해야 함. 
            // -> inputMode는 Ref로 관리하거나 의존성 배열에 추가. 
            // 여기서는 간단히 normalize 로직을 분리하지 않고 인라인으로 처리하거나 함수 인자로 받음.

            // *컴포넌트 스코프의 변수(inputMode)를 사용하려면 의존성 필요. 
            // updateSituation이 자주 재생성되지 않도록 하려면 inputMode를 인자로 받거나 ref 사용.
            // 여기서는 기능 단순화를 위해 정규화된 객체를 '부모에게 보낼 때'만 만듦.

            const normalizedForParent = normalizeSituationData(tempSituation);

            // 본인 state에는 updates만 반영 (User Input 유지)
            // 단, raw_report_text가 자동 생성된 경우 State에도 반영해야 UI에 보일 수 있음(필요시).
            // 여기서는 부모에게 보내는 데이터만 풍부하게 만듦.

            // 업데이트된 필드 중 실제로 변경된 것이 있는지 확인 (정규화 전 기준)
            const hasChanged = Object.keys(updates).some(key => {
                const oldValue = prevSituation[key];
                const newValue = tempSituation[key];
                if (oldValue === null || oldValue === undefined) return newValue !== null && newValue !== undefined;
                if (newValue === null || newValue === undefined) return oldValue !== null && oldValue !== undefined;
                return oldValue !== newValue;
            });

            // 실제로 변경된 경우에만 부모에게 알림 (정규화된 데이터 전송)
            if (hasChanged) {
                onSituationChangeRef.current(normalizedForParent);
            }

            return tempSituation;
        });
    }, [inputMode]); // inputMode가 바뀌면 함수 재생성 (generateAutoReportText가 inputMode 참조하므로)

    // 임무 중심 모드 관련 함수 제거됨 - 위협 중심 모드만 지원

    return (
        <Card className="border-gray-200 dark:border-zinc-700">
            <CardHeader>
                <CardTitle className="text-sm font-semibold">📋 상황 정보 설정</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* 입력 방식 선택 */}
                <div className="space-y-4">
                    <div className="space-y-2">
                        <Label className="text-sm font-medium">입력 방식</Label>
                        <select
                            value={inputMode}
                            onChange={(e) => {
                                const newMode = e.target.value as any;
                                setInputMode(newMode);

                                // 모드 변경 시 초기화 로직
                                if (newMode === 'manual') {
                                    const newSituationId = `MANUAL_${Date.now()}`;
                                    updateSituation({
                                        situation_id: newSituationId,
                                        selected_threat_id: newSituationId, // 🔥 FIX: UI 표시용 ID
                                        threat_id: newSituationId, // 🔥 FIX: API 호출용 ID
                                        위협ID: newSituationId,
                                        is_manual: true,
                                        is_demo: false,
                                        is_sitrep: false, // 🔥 FIX: 명시적으로 false 설정
                                        approach_mode: approachMode, // 🔥 FIX: 현재 접근방식 유지
                                        // 기존 데이터 초기화
                                        threat_level: 0.7,
                                        threat_type: '',
                                        위협유형: '',
                                        location: '',
                                        발생장소: '',
                                        axis_id: '',
                                        관련축선ID: '',
                                        latitude: undefined,
                                        longitude: undefined,
                                        mission_id: undefined, // 임무 초기화
                                        임무ID: undefined,
                                        mission_name: undefined,
                                        임무명: undefined,
                                        mission_type: undefined,
                                        임무유형: undefined,
                                        mission_objective: undefined,
                                        임무목표: undefined,
                                        related_mission_id: undefined,
                                        description: '',
                                        raw_report_text: '' // 🔥 FIX: 원시 보고 텍스트 초기화
                                    });
                                }
                            }}
                            className="w-full h-10 rounded-md border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            {/* 위협 중심 입력 옵션 */}
                            <option value="real_data">실제 위협에서 선택</option>
                            <option value="scenario">데모 시나리오</option>
                            <option value="sitrep">SITREP 텍스트 입력</option>
                            <option value="manual">수동 입력</option>
                        </select>
                    </div>
                </div>

                {/* 수동 입력 폼 */}
                {inputMode === 'manual' && (
                    <div className="space-y-4 pt-2 border-t border-gray-200 dark:border-zinc-700">
                        <div className="space-y-2">
                            <Label htmlFor="situation_id" className="text-sm">상황 ID</Label>
                            <Input
                                id="situation_id"
                                value={situation.situation_id || ''}
                                onChange={(e) => updateSituation({ situation_id: e.target.value })}
                                placeholder="SIT_20240101_120000"
                            />
                        </div>

                        {/* 위협 중심 입력 */}
                                <div className="space-y-2">
                                    <Label className="text-sm">위협 수준: {(() => {
                                        // 위협 수준 파싱 (문자열일 수 있음)
                                        const threatLevelRaw = situation.threat_level || situation.위협수준;
                                        if (threatLevelRaw === undefined || threatLevelRaw === null) {
                                            return '70%';
                                        }

                                        let threatLevel: number = 0.7;
                                        if (typeof threatLevelRaw === 'string') {
                                            const cleaned = String(threatLevelRaw).replace('%', '').trim();
                                            const parsed = parseFloat(cleaned);
                                            if (!isNaN(parsed)) {
                                                threatLevel = parsed > 1 ? parsed / 100 : parsed;
                                            }
                                        } else {
                                            threatLevel = typeof threatLevelRaw === 'number' ? threatLevelRaw : 0.7;
                                        }

                                        return `${Math.round(threatLevel * 100)}%`;
                                    })()}</Label>
                                    <Slider
                                        value={[(() => {
                                            // 위협 수준 파싱 (문자열일 수 있음)
                                            const threatLevelRaw = situation.threat_level || situation.위협수준;
                                            if (threatLevelRaw === undefined || threatLevelRaw === null) {
                                                return 70;
                                            }

                                            let threatLevel: number = 0.7;
                                            if (typeof threatLevelRaw === 'string') {
                                                const cleaned = String(threatLevelRaw).replace('%', '').trim();
                                                const parsed = parseFloat(cleaned);
                                                if (!isNaN(parsed)) {
                                                    threatLevel = parsed > 1 ? parsed / 100 : parsed;
                                                }
                                            } else {
                                                threatLevel = typeof threatLevelRaw === 'number' ? threatLevelRaw : 0.7;
                                            }

                                            return Math.round(threatLevel * 100);
                                        })()]}
                                        onValueChange={([value]) => updateSituation({
                                            threat_level: value / 100.0,
                                            위협수준: String(value),
                                            심각도: value
                                        })}
                                        min={0}
                                        max={100}
                                        step={1}
                                        className="w-full"
                                    />
                                    <div className="flex gap-2 text-xs">
                                        {(() => {
                                            // 위협 수준 파싱 (문자열일 수 있음)
                                            const threatLevelRaw = situation.threat_level || situation.위협수준;
                                            if (threatLevelRaw === undefined || threatLevelRaw === null) {
                                                return null;
                                            }

                                            let threatLevel: number = 0.7;
                                            if (typeof threatLevelRaw === 'string') {
                                                const cleaned = String(threatLevelRaw).replace('%', '').trim();
                                                const parsed = parseFloat(cleaned);
                                                if (!isNaN(parsed)) {
                                                    threatLevel = parsed > 1 ? parsed / 100 : parsed;
                                                }
                                            } else {
                                                threatLevel = typeof threatLevelRaw === 'number' ? threatLevelRaw : 0.7;
                                            }

                                            if (threatLevel >= 0.8) {
                                                return <span className="text-red-600 dark:text-red-400">🔴 높은 위협</span>;
                                            } else if (threatLevel >= 0.5) {
                                                return <span className="text-yellow-600 dark:text-yellow-400">🟡 중간 위협</span>;
                                            } else {
                                                return <span className="text-green-600 dark:text-green-400">🟢 낮은 위협</span>;
                                            }
                                        })()}
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label className="text-sm">위협 유형</Label>
                                        <select
                                            value={situation.위협유형 || situation.threat_type || ''}
                                            onChange={(e) => updateSituation({ 위협유형: e.target.value, threat_type: e.target.value })}
                                            className="w-full h-10 rounded-md border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        >
                                            <option value="">위협 유형 선택</option>
                                            <option value="공중위협">공중위협</option>
                                            <option value="포격">포격</option>
                                            <option value="침투">침투</option>
                                            <option value="국지도발">국지도발</option>
                                            <option value="전면전">전면전</option>
                                            <option value="사이버">사이버</option>
                                            <option value="기습공격">기습공격</option>
                                        </select>
                                    </div>
                                    <div className="space-y-2">
                                        <Label className="text-sm">현재 임무 유형 (선택)</Label>
                                        <select
                                            value={situation.임무유형 || situation.mission_type || ''}
                                            onChange={(e) => updateSituation({ 임무유형: e.target.value, mission_type: e.target.value })}
                                            className="w-full h-10 rounded-md border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        >
                                            <option value="">선택 안 함</option>
                                            <option value="방어">방어</option>
                                            <option value="공격">공격</option>
                                            <option value="반격">반격</option>
                                            <option value="정찰">정찰</option>
                                        </select>
                                    </div>
                                </div>



                                {/* 위치 및 축선 정보 */}
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label className="text-sm">발생 장소 (지형셀 선택)</Label>
                                        <select
                                            value={situation.발생장소 || situation.location || ''}
                                            onChange={(e) => {
                                                const cellId = e.target.value;
                                                const updates: any = { 발생장소: cellId, location: cellId };

                                                // 지형셀에 매핑된 좌표 자동 입력
                                                const selectedCell = terrainCells.find(c => c.cell_id === cellId);
                                                if (selectedCell && selectedCell.coordinates && selectedCell.coordinates.length === 2) {
                                                    updates.longitude = selectedCell.coordinates[0];
                                                    updates.lng = selectedCell.coordinates[0];
                                                    updates.latitude = selectedCell.coordinates[1];
                                                    updates.lat = selectedCell.coordinates[1];
                                                }

                                                updateSituation(updates);
                                            }}
                                            className="w-full h-10 rounded-md border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        >
                                            <option value="">지형셀 선택... {(situation.관련축선ID || situation.axis_id) ? '(축선 관련)' : ''}</option>
                                            {filteredTerrainCells.map((cell) => (
                                                <option key={cell.cell_id} value={cell.cell_id}>
                                                    {cell.name || cell.cell_id} ({cell.cell_id})
                                                </option>
                                            ))}
                                            {filteredTerrainCells.length === 0 && (situation.관련축선ID || situation.axis_id) && (
                                                <option value="" disabled>해당 축선의 시작/종점이 아닙니다</option>
                                            )}
                                        </select>
                                    </div>
                                    <div className="space-y-2">
                                        <Label className="text-sm">관련 축선 선택</Label>
                                        <select
                                            value={situation.관련축선ID || situation.axis_id || ''}
                                            onChange={(e) => updateSituation({ 관련축선ID: e.target.value, axis_id: e.target.value })}
                                            className="w-full h-10 rounded-md border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        >
                                            <option value="">축선 선택... {(situation.발생장소 || situation.location) ? '(위치 관련)' : ''}</option>
                                            {filteredAxes.map((axis) => (
                                                <option key={axis.axis_id} value={axis.axis_id}>
                                                    {axis.axis_name} ({axis.axis_id})
                                                </option>
                                            ))}
                                            {filteredAxes.length === 0 && (situation.발생장소 || situation.location) && (
                                                <option value="" disabled>이 위치를 지나는 축선이 없습니다</option>
                                            )}
                                        </select>
                                    </div>
                                </div>

                                {/* 좌표 정보 (선택) */}
                                <div className="grid grid-cols-2 gap-4">
                                    {/* (생략) 좌표는 직접 입력 유지하되, 축선 선택 시 자동 채움 기능 고려 가능. 일단 유지 */}
                                    <div className="space-y-2">
                                        <Label className="text-sm">경도 (Longitude)</Label>
                                        <Input
                                            type="number"
                                            step="0.0001"
                                            value={situation.longitude || situation.lng || ''}
                                            onChange={(e) => updateSituation({
                                                longitude: e.target.value === '' ? undefined : parseFloat(e.target.value),
                                                lng: e.target.value === '' ? undefined : parseFloat(e.target.value)
                                            })}
                                            placeholder="127.xxxx"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label className="text-sm">위도 (Latitude)</Label>
                                        <Input
                                            type="number"
                                            step="0.0001"
                                            value={situation.latitude || situation.lat || ''}
                                            onChange={(e) => updateSituation({
                                                latitude: e.target.value === '' ? undefined : parseFloat(e.target.value),
                                                lat: e.target.value === '' ? undefined : parseFloat(e.target.value)
                                            })}
                                            placeholder="37.xxxx"
                                        />
                                    </div>
                                </div>

                                {/* 임무 연동 (수동 모드에서도 임무 선택 가능) */}
                                <div className="space-y-2">
                                    <Label className="text-sm">관련 임무 (선택)</Label>
                                    <select
                                        value={situation.mission_id || situation.임무ID || ''}
                                        onChange={(e) => {
                                            const mId = e.target.value;
                                            const selectedM = availableMissions.find(m => m.mission_id === mId);
                                            updateSituation({
                                                mission_id: mId,
                                                임무ID: mId,
                                                related_mission_id: mId,
                                                mission_name: selectedM?.mission_name
                                            });
                                        }}
                                        className="w-full h-10 rounded-md border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    >
                                        <option value="">임무 연동 안 함 (자동 추론)</option>
                                        {availableMissions.map((m) => (
                                            <option key={m.mission_id} value={m.mission_id}>
                                                {m.mission_name} ({m.mission_id})
                                            </option>
                                        ))}
                                    </select>
                                    <p className="text-xs text-gray-500">
                                        특정 임무와 연동하려면 선택하세요. 선택하지 않으면 위협/축선 기반으로 자동 추론됩니다.
                                    </p>

                                    {/* 선택된 임무 요약 정보 표시 */}
                                    {(() => {
                                        const selectedMId = situation.mission_id || situation.임무ID;
                                        const selectedMission = availableMissions.find(m => m.mission_id === selectedMId);

                                        if (selectedMission) {
                                            return (
                                                <div className="mt-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md border border-blue-100 dark:border-blue-800 text-xs space-y-1">
                                                    <div className="font-bold text-blue-900 dark:text-blue-100 flex items-center justify-between">
                                                        <span>🎯 {selectedMission.mission_id}</span>
                                                        <span className="px-2 py-0.5 bg-white dark:bg-blue-900 rounded text-blue-800 dark:text-blue-200 border border-blue-200 dark:border-blue-700">
                                                            {selectedMission.mission_type || '임무'}
                                                        </span>
                                                    </div>
                                                    {selectedMission.commander_intent && (
                                                        <div className="pt-1">
                                                            <div className="font-semibold text-blue-800 dark:text-blue-200 mb-0.5">지휘관 의도</div>
                                                            <div className="text-blue-900 dark:text-blue-100 leading-relaxed">
                                                                {selectedMission.commander_intent}
                                                            </div>
                                                        </div>
                                                    )}
                                                    {selectedMission.remarks && (
                                                        <div className="pt-1 mt-1 border-t border-blue-200 dark:border-blue-800">
                                                            <span className="text-blue-800 dark:text-blue-300">비고: {selectedMission.remarks}</span>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        }
                                        return null;
                                    })()}
                                </div>

                        {/* 공통: 작전 환경 및 자원 */}
                        <div className="pt-4 border-t border-gray-200 dark:border-zinc-700 space-y-4">
                            <Label className="text-sm font-semibold">작전 환경 및 자원</Label>

                            <div className="space-y-2">
                                <Label className="text-sm">자원 가용성: {situation.resource_availability ? Math.round(situation.resource_availability * 100) : 70}%</Label>
                                <Slider
                                    value={[situation.resource_availability ? Math.round(situation.resource_availability * 100) : 70]}
                                    onValueChange={([value]) => updateSituation({ resource_availability: value / 100.0 })}
                                    min={0}
                                    max={100}
                                    step={5}
                                />
                            </div>

                            <div className="grid grid-cols-3 gap-4">
                                <div className="space-y-2">
                                    <Label className="text-sm">기상</Label>
                                    <select
                                        value={situation.environment?.weather || '맑음'}
                                        onChange={(e) => updateSituation({
                                            environment: { ...situation.environment, weather: e.target.value }
                                        })}
                                        className="w-full h-10 rounded-md border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    >
                                        <option value="맑음">맑음</option>
                                        <option value="흐림">흐림</option>
                                        <option value="비">비</option>
                                        <option value="눈">눈</option>
                                        <option value="안개">안개</option>
                                    </select>
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-sm">지형</Label>
                                    <select
                                        value={situation.environment?.terrain || '평지'}
                                        onChange={(e) => updateSituation({
                                            environment: { ...situation.environment, terrain: e.target.value }
                                        })}
                                        className="w-full h-10 rounded-md border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    >
                                        <option value="평지">평지</option>
                                        <option value="산악">산악</option>
                                        <option value="시가지">시가지</option>
                                        <option value="하천">하천</option>
                                        <option value="혼합">혼합</option>
                                    </select>
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-sm">시간</Label>
                                    <select
                                        value={situation.environment?.time_of_day || '주간'}
                                        onChange={(e) => updateSituation({
                                            environment: { ...situation.environment, time_of_day: e.target.value }
                                        })}
                                        className="w-full h-10 rounded-md border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    >
                                        <option value="주간">주간</option>
                                        <option value="야간">야간</option>
                                        <option value="새벽">새벽</option>
                                        <option value="황혼">황혼</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        {/* 방어 자산 정보 */}
                        <div className="pt-4 border-t border-gray-200 dark:border-zinc-700 space-y-4">
                            <Label className="text-sm font-semibold">방어 자산 정보</Label>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label className="text-sm">방어 자산 수</Label>
                                    <Input
                                        type="number"
                                        value={situation.defense_assets?.count || 5}
                                        onChange={(e) => updateSituation({
                                            defense_assets: {
                                                ...situation.defense_assets,
                                                count: parseInt(e.target.value) || 0
                                            }
                                        })}
                                        min={0}
                                        max={100}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-sm">평균 화력 지수</Label>
                                    <Input
                                        type="number"
                                        value={situation.defense_assets?.firepower || 75}
                                        onChange={(e) => updateSituation({
                                            defense_assets: {
                                                ...situation.defense_assets,
                                                firepower: parseInt(e.target.value) || 0
                                            }
                                        })}
                                        min={0}
                                        max={100}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* 실제 데이터 선택 - 접근방식에 따라 다른 목록 표시 */}
                {inputMode === 'real_data' && (
                    <div className="space-y-4 pt-2 border-t border-gray-200 dark:border-zinc-700">
                        <Label className="text-sm font-medium">실제 데이터에서 위협 선택</Label>
                        <div className="space-y-2">
                            {loadingThreats ? (
                                <div className="flex items-center justify-center p-4">
                                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                                    <span className="ml-2 text-sm text-gray-500">위협 목록 로딩 중...</span>
                                </div>
                            ) : (
                                <>
                                    <select
                                        value={situation.selected_threat_id || ''}
                                        onChange={async (e) => {
                                            const threatId = e.target.value;
                                            if (!threatId) return;

                                            // 목록에서 선택된 위협 찾기
                                            const selectedThreat = availableThreats.find(t => t.threat_id === threatId);
                                            if (selectedThreat) {
                                                // 위협 유형 결정
                                                const threatType = selectedThreat.threat_type_code || selectedThreat.threat_type_original || (selectedThreat as any).threat_type || '';

                                                // 위협 수준 파싱 (문자열 "HIGH", "MEDIUM", "LOW" 지원)
                                                let threatLevel: number = 0.7;
                                                if (selectedThreat.threat_level !== undefined && selectedThreat.threat_level !== null) {
                                                    const parsed = parseThreatLevel(selectedThreat.threat_level);
                                                    if (parsed) {
                                                        threatLevel = parsed.normalized;
                                                    }
                                                }

                                                // 위협 데이터를 상황 정보에 반영
                                                updateSituation({
                                                    // 상황 ID를 위협 ID로 업데이트 (위협 선택 시 상황 ID = 위협 ID)
                                                    situation_id: threatId,
                                                    위협ID: threatId,
                                                    threat_id: threatId,
                                                    selected_threat_id: threatId,
                                                    threat_type: threatType,
                                                    threat_type_code: selectedThreat.threat_type_code,
                                                    threat_level: threatLevel,
                                                    location: selectedThreat.location_cell_id || (selectedThreat as any).location,
                                                    axis_id: selectedThreat.related_axis_id || (selectedThreat as any).axis_id,
                                                    위협유형: threatType,
                                                    위협수준: String(Math.round(threatLevel * 100)),
                                                    발생장소: selectedThreat.location_cell_id || (selectedThreat as any).location,
                                                    관련축선ID: selectedThreat.related_axis_id || (selectedThreat as any).axis_id,
                                                    location_cell_id: selectedThreat.location_cell_id,
                                                    related_axis_id: selectedThreat.related_axis_id,
                                                    latitude: selectedThreat.latitude,
                                                    longitude: selectedThreat.longitude,
                                                    // 위협에 연결된 임무 ID 추가
                                                    mission_id: selectedThreat.related_mission_id || undefined,
                                                    임무ID: selectedThreat.related_mission_id || undefined,
                                                    related_mission_id: selectedThreat.related_mission_id,
                                                    ...selectedThreat
                                                });
                                            }
                                        }}
                                        className="w-full h-10 rounded-md border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    >
                                        <option value="">위협 선택...</option>
                                        {availableThreats.map((threat) => {
                                            // 위협 유형 결정 (우선순위: threat_type_code → threat_type_original → threat_type → '미지정')
                                            const threatTypeCode = threat.threat_type_code || threat.threat_type_original || (threat as any).threat_type || '미지정';

                                            // 위협 유형을 한글 레이블로 변환
                                            const threatTypeLabel = getThreatTypeLabel(threatTypeCode) || threatTypeCode;

                                            // 위협 수준 파싱 (문자열일 수 있음)
                                            let threatLevel: number = 0.7;
                                            if (threat.threat_level !== undefined && threat.threat_level !== null) {
                                                if (typeof threat.threat_level === 'string') {
                                                    // 문자열인 경우 파싱 (예: "0.7", "70", "70%")
                                                    const cleaned = threat.threat_level.replace('%', '').trim();
                                                    const parsed = parseFloat(cleaned);
                                                    if (!isNaN(parsed)) {
                                                        // 100보다 크면 백분율로 간주 (예: 70 -> 0.7)
                                                        threatLevel = parsed > 1 ? parsed / 100 : parsed;
                                                    }
                                                } else {
                                                    threatLevel = typeof threat.threat_level === 'number' ? threat.threat_level : 0.7;
                                                }
                                            }

                                            const threatLevelPercent = Math.round(threatLevel * 100);

                                            return (
                                                <option key={threat.threat_id} value={threat.threat_id}>
                                                    {threat.threat_id} - {threatTypeLabel} ({threatLevelPercent}%)
                                                </option>
                                            );
                                        })}
                                    </select>
                                    {availableThreats.length === 0 && (
                                        <p className="text-xs text-yellow-600 dark:text-yellow-400">
                                            사용 가능한 위협 데이터가 없습니다. 수동 입력을 사용하세요.
                                        </p>
                                    )}
                                </>
                            )}
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                                데이터베이스에서 위협을 선택하면 자동으로 상황 정보가 채워집니다.
                            </p>
                        </div>
                    </div>
                )}

                {/* SITREP 텍스트 입력 */}
                {inputMode === 'sitrep' && (
                    <div className="space-y-2 pt-2 border-t border-gray-200 dark:border-zinc-700">
                        <Label className="text-sm">SITREP 텍스트 입력</Label>
                        <Textarea
                            value={situation.sitrep_text || ''}
                            onChange={(e) => updateSituation({ sitrep_text: e.target.value })}
                            placeholder="상황 보고서 텍스트를 입력하세요..."
                            rows={5}
                            className="font-mono text-sm"
                        />
                        <Button
                            onClick={async () => {
                                if (!situation.sitrep_text?.trim()) {
                                    alert('SITREP 텍스트를 입력해주세요.');
                                    return;
                                }
                                try {
                                    const response = await api.post('/threat/analyze', {
                                        sitrep_text: situation.sitrep_text
                                    });
                                    const threatData = response.data;
                                    
                                    // 🔥 FIX: 새로운 situation_id 생성 및 이전 데이터 명시적 초기화
                                    const newSituationId = `SITREP_${Date.now()}`;
                                    
                                    // 파싱된 위협 정보를 상황 정보에 반영 (이전 데이터 덮어쓰기)
                                    // 🔥 FIX: ...threatData를 먼저 spread하여 우리가 원하는 값이 덮어쓰이지 않도록 함
                                    updateSituation({
                                        // 백엔드 응답 먼저 spread (이후 값들로 덮어쓰기)
                                        ...threatData,
                                        
                                        // 새 ID 및 플래그 (덮어쓰기)
                                        situation_id: newSituationId,
                                        selected_threat_id: newSituationId, // 🔥 FIX: UI 표시용 ID도 업데이트
                                        is_sitrep: true,
                                        is_demo: false,
                                        is_manual: false,
                                        
                                        // 분석된 위협 정보 (명시적 설정)
                                        threat_id: newSituationId, // 🔥 항상 프론트엔드에서 생성한 ID 사용
                                        threat_type: threatData.threat_type_code || threatData.threat_type,
                                        threat_level: threatData.threat_level || 0.7,
                                        location: threatData.location_cell_id || threatData.location,
                                        axis_id: threatData.related_axis_id || threatData.axis_id,
                                        위협ID: newSituationId, // 🔥 항상 프론트엔드에서 생성한 ID 사용
                                        위협유형: threatData.threat_type_code || threatData.threat_type,
                                        위협수준: String(Math.round((threatData.threat_level || 0.7) * 100)),
                                        발생장소: threatData.location_cell_id || threatData.location,
                                        관련축선ID: threatData.related_axis_id || threatData.axis_id,
                                        
                                        // SITREP 텍스트를 description과 raw_report_text에 저장
                                        description: situation.sitrep_text,
                                        raw_report_text: situation.sitrep_text,
                                        
                                        // 좌표 정보 갱신 (API에서 제공하는 경우)
                                        latitude: threatData.latitude,
                                        longitude: threatData.longitude
                                    });

                                    // 위협 식별 콜백 호출 (selectedThreat에도 반영)
                                    // 🔥 FIX: 항상 newSituationId 사용
                                    if (onThreatIdentified) {
                                        onThreatIdentified({
                                            ...threatData,
                                            threat_id: newSituationId,
                                            situation_id: newSituationId,
                                            raw_report_text: situation.sitrep_text
                                        });
                                    }

                                    alert('SITREP 텍스트가 성공적으로 분석되었습니다.');
                                } catch (err: any) {
                                    console.error('SITREP 분석 오류:', err);
                                    alert(err.response?.data?.detail || 'SITREP 분석 중 오류가 발생했습니다.');
                                }
                            }}
                            className="w-full"
                            variant="default"
                        >
                            SITREP 분석 실행
                        </Button>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                            SITREP 텍스트를 입력하면 자동으로 파싱되어 상황 정보로 변환됩니다.
                        </p>
                    </div>
                )}

                {/* 시나리오 선택 */}
                {inputMode === 'scenario' && (
                    <div className="space-y-4 pt-2 border-t border-gray-200 dark:border-zinc-700">
                        <Label className="text-sm font-medium">데모 시나리오 선택</Label>
                        <ScenarioSelector
                            onScenarioSelect={(scenarioData) => {
                                // 데모 시나리오 선택 시 이전 위협 정보 명시적으로 제거
                                updateSituation({
                                    ...scenarioData,
                                    approach_mode: 'threat_centered',
                                    is_demo: true,
                                    // 이전 위협 및 위치 정보 명시적으로 제거
                                    selected_threat_id: undefined,
                                    위협ID: undefined,
                                    threat_id: undefined,
                                    related_mission_id: undefined,
                                    latitude: undefined,
                                    longitude: undefined,
                                    lat: undefined,
                                    lng: undefined,
                                    좌표정보: undefined,
                                    occurrence_time: undefined,
                                    time_str: undefined,
                                    // 🔥 FIX: 이전 위협의 raw_report_text가 남아있지 않도록 명시적 초기화
                                    raw_report_text: scenarioData.description || undefined,
                                    원시보고텍스트: undefined
                                });
                            }}
                        />
                    </div>
                )}
            </CardContent>
        </Card>
    );
};

// 데모 시나리오 데이터
const DEMO_SCENARIOS = [
    {
        id: "scenario_1",
        name: "시나리오 1: 적군 정찰기 침입",
        description: "적 정찰기가 경계 지역 침입 시 방책 추천",
        threat_type: "정찰",
        severity: 75,
        location: "경계지역",
        enemy_info: "적 정찰기 2대가 경계 지역 상공에서 정찰 활동 중",
        friendly_info: "1기갑여단이 경계 지역 근처에 배치되어 있음",
        expected_coa: "Moderate_Defense 또는 Main_Defense",
        mission_id: "MSN001", // 동부전선 방어작전
        mission_name: "동부전선 방어작전",
        key_points: [
            "정찰 활동은 공격 전 단계일 수 있음",
            "경계 지역은 중요 방어 지점",
            "기갑 부대의 기동력 활용 가능"
        ]
    },
    {
        id: "scenario_2",
        name: "시나리오 2: 적군 전차 부대 이동",
        description: "적 전차 부대가 전방기지로 이동 시 방책 추천",
        threat_type: "공격",
        severity: 90,
        location: "전방기지",
        enemy_info: "적 5전차 대대가 전방기지 방향으로 이동 중 (ThreatLevel: 92)",
        friendly_info: "2기갑여단이 전방기지에 배치되어 있음 (Firepower: 85)",
        expected_coa: "Main_Defense",
        mission_id: "MSN007", // 기갑돌파저지
        mission_name: "기갑돌파저지",
        key_points: [
            "높은 위협 수준 (90%)",
            "전차 부대는 공격력이 높음",
            "전방기지는 전략적 중요 지점"
        ]
    },
    {
        id: "scenario_3",
        name: "시나리오 3: 적군 정보수집 활동",
        description: "적군의 정보수집 활동 감지 시 방책 추천",
        threat_type: "정보수집",
        severity: 40,
        location: "후방기지",
        enemy_info: "적 정보수집 부대가 후방기지 근처에서 활동 중",
        friendly_info: "경계 부대가 후방기지 경계 임무 수행 중",
        expected_coa: "Minimal_Defense 또는 Moderate_Defense",
        mission_id: "MSN005", // 후방지역 방호
        mission_name: "후방지역 방호",
        key_points: [
            "낮은 위협 수준 (40%)",
            "정보수집은 직접 공격보다 위협도 낮음",
            "경계 강화로 대응 가능"
        ]
    },
    {
        id: "scenario_4",
        name: "시나리오 4: 적군 보급선 이동",
        description: "적 보급선 이동 감지 시 방책 추천",
        threat_type: "보급",
        severity: 60,
        location: "본부",
        enemy_info: "적 보급선이 본부 방향으로 이동 중",
        friendly_info: "본부 방어 부대가 배치되어 있음",
        expected_coa: "Moderate_Defense",
        mission_id: "MSN002", // 서부 기계화차단 (보급선 차단 성격)
        mission_name: "서부 기계화차단",
        key_points: [
            "보급선 이동은 공격 준비 신호일 수 있음",
            "본부는 중요 시설",
            "적절한 방어 조치 필요"
        ]
    }
];

// 시나리오 선택 컴포넌트
interface ScenarioSelectorProps {
    onScenarioSelect: (scenarioData: any) => void;
}

const ScenarioSelector: React.FC<ScenarioSelectorProps> = ({ onScenarioSelect }) => {
    const [selectedScenarioId, setSelectedScenarioId] = useState<string>('');

    // 모든 시나리오 사용 가능 (위협 중심 모드만 지원)
    const availableScenarios = DEMO_SCENARIOS;

    const selectedScenario = availableScenarios.find(s => s.id === selectedScenarioId);

    const handleScenarioChange = (scenarioId: string) => {
        setSelectedScenarioId(scenarioId);
        const scenario = availableScenarios.find(s => s.id === scenarioId);
        if (scenario) {
            // location을 기반으로 기본 축선 ID 매핑
            const locationToAxisMap: Record<string, string> = {
                '경계지역': 'AXIS01', // 동부 주공축선
                '전방기지': 'AXIS01', // 동부 주공축선
                '후방기지': 'AXIS02', // 서부 축선 (예시)
                '본부': 'AXIS01', // 동부 주공축선
                '중앙지역': 'AXIS01' // 기본값
            };

            const defaultAxisId = locationToAxisMap[scenario.location] || 'AXIS01';

            // 시나리오 데이터를 situation 정보로 변환
            const situationData = {
                situation_id: `SCENARIO_${scenario.id.toUpperCase()}_${Date.now()}`,
                threat_type: scenario.threat_type,
                threat_level: scenario.severity / 100.0,
                location: scenario.location,
                axis_id: defaultAxisId, // 기본 축선 ID 추가
                관련축선ID: defaultAxisId, // 한글 필드명도 추가
                위협유형: scenario.threat_type,
                위협수준: String(scenario.severity),
                발생장소: scenario.location,
                description: scenario.description,
                // 임무 정보 매핑 (FK)
                mission_id: (scenario as any).mission_id,
                임무ID: (scenario as any).mission_id,
                mission_name: (scenario as any).mission_name,
                // 추가 정보
                enemy_info: scenario.enemy_info,
                friendly_info: scenario.friendly_info,
                expected_coa: scenario.expected_coa,
                key_points: scenario.key_points,
                timestamp: new Date().toISOString()
            };
            onScenarioSelect(situationData);
        }
    };

    return (
        <div className="space-y-4">
            <select
                value={selectedScenarioId}
                onChange={(e) => handleScenarioChange(e.target.value)}
                className="w-full h-10 rounded-md border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
                <option value="">시나리오 선택...</option>
                {availableScenarios.map((scenario) => (
                    <option key={scenario.id} value={scenario.id}>
                        {scenario.name}
                    </option>
                ))}
            </select>

            {selectedScenario && (
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 space-y-3">
                    <div>
                        <h4 className="font-semibold text-sm mb-1 text-blue-900 dark:text-blue-100">
                            {selectedScenario.name}
                        </h4>
                        <p className="text-xs text-blue-700 dark:text-blue-300">
                            {selectedScenario.description}
                        </p>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-xs">
                        <div className="bg-white dark:bg-zinc-800 p-2 rounded">
                            <div className="text-gray-500 dark:text-gray-400">위협 유형</div>
                            <div className="font-bold text-gray-900 dark:text-white">{selectedScenario.threat_type}</div>
                        </div>
                        <div className="bg-white dark:bg-zinc-800 p-2 rounded">
                            <div className="text-gray-500 dark:text-gray-400">심각도</div>
                            <div className="font-bold text-gray-900 dark:text-white">{selectedScenario.severity}%</div>
                        </div>
                        <div className="bg-white dark:bg-zinc-800 p-2 rounded">
                            <div className="text-gray-500 dark:text-gray-400">발생 장소</div>
                            <div className="font-bold text-gray-900 dark:text-white">{selectedScenario.location}</div>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <div>
                            <div className="text-xs font-semibold text-blue-800 dark:text-blue-200 mb-1">적군 정보</div>
                            <div className="text-xs text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/30 p-2 rounded">
                                {selectedScenario.enemy_info}
                            </div>
                        </div>
                        <div>
                            <div className="text-xs font-semibold text-blue-800 dark:text-blue-200 mb-1">아군 정보</div>
                            <div className="text-xs text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/30 p-2 rounded">
                                {selectedScenario.friendly_info}
                            </div>
                        </div>
                        <div>
                            <div className="text-xs font-semibold text-blue-800 dark:text-blue-200 mb-1">예상 방책</div>
                            <div className="text-xs text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/30 p-2 rounded">
                                {selectedScenario.expected_coa}
                            </div>
                        </div>
                        <div>
                            <div className="text-xs font-semibold text-blue-800 dark:text-blue-200 mb-1">주요 포인트</div>
                            <ul className="text-xs text-blue-700 dark:text-blue-300 space-y-1 list-disc list-inside">
                                {selectedScenario.key_points.map((point, idx) => (
                                    <li key={idx}>{point}</li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
