/**
 * COP 시각화 유틸리티 함수
 * 설계 문서: docs/40_Refactoring/cop_visualization_design.md 기반
 */

import type { LatLngExpression } from 'leaflet';

// ============================================================================
// 위협 영향 범위 계산
// ============================================================================

export interface ThreatInfluenceArea {
    threat_id: string;
    center: LatLngExpression;
    radius: number; // km 단위
    threat_level: number; // 0.0 ~ 1.0
    threat_type: string;
    visualization: {
        color: string;
        opacity: number; // 0.1 ~ 0.3
        stroke: boolean;
        strokeColor: string;
        strokeWidth: number;
    };
}

/**
 * 위협 수준에 따른 색상 결정
 */
export function getThreatLevelColor(threatLevel: number): string {
    if (threatLevel >= 0.8) return '#ef4444'; // 빨간색
    if (threatLevel >= 0.6) return '#f97316'; // 주황색
    if (threatLevel >= 0.3) return '#eab308'; // 노란색
    return '#22c55e'; // 초록색
}

/**
 * 위협 수준에 따른 투명도 결정
 */
export function getThreatLevelOpacity(threatLevel: number): number {
    if (threatLevel >= 0.8) return 0.3;
    if (threatLevel >= 0.6) return 0.2;
    if (threatLevel >= 0.3) return 0.15;
    return 0.1;
}

/**
 * 위협 유형별 기본 반경 (km)
 */
const THREAT_TYPE_RADIUS: Record<string, number> = {
    '미사일': 10.0,
    'MISSILE': 10.0,
    '포병': 15.0,
    'ARTILLERY': 8.0,
    '기갑': 5.0,
    'ARMOR': 5.0,
    '보병': 3.0,
    'INFANTRY': 3.0,
    '공중': 15.0,
    'AIR': 15.0,
    '해상': 12.0,
    'NAVAL': 12.0,
    '공격': 5.0,
    '정찰': 4.0,
    '정보수집': 4.0,
    '보급': 2.0,
    '특수부대': 8.0,
    'UNKNOWN': 5.0,
};

/**
 * 위협 영향 범위 반경 계산
 * @param threatLevel 위협 수준 (0.0 ~ 1.0)
 * @param threatTypeCode 위협 유형 코드
 * @param detectionRange 감지 범위 (km, 선택적)
 * @returns 계산된 반경 (km)
 */
export function calculateThreatInfluenceRadius(
    threatLevel: number,
    threatTypeCode?: string,
    detectionRange?: number
): number {
    // 기본 반경
    const baseRadius = 5.0; // km

    // 위협 수준 가중치 (1.0 ~ 2.0)
    const levelMultiplier = 1.0 + threatLevel;

    // 위협 유형별 추가 반경
    let typeBonus = 0.0;
    if (threatTypeCode) {
        typeBonus = THREAT_TYPE_RADIUS[threatTypeCode] || 0.0;
    }

    // 감지 범위 반영 (있는 경우)
    if (detectionRange) {
        typeBonus = Math.max(typeBonus, detectionRange);
    }

    // 최종 반경 계산
    const radius = baseRadius * levelMultiplier + typeBonus;

    // 최대 50km로 제한
    return Math.min(radius, 50.0);
}

/**
 * 위협 영향 범위 생성
 */
export function createThreatInfluenceArea(
    threat_id: string,
    center: LatLngExpression,
    threat_level: number,
    threat_type_code?: string,
    detection_range?: number
): ThreatInfluenceArea {
    const radius = calculateThreatInfluenceRadius(threat_level, threat_type_code, detection_range);
    const color = getThreatLevelColor(threat_level);
    const opacity = getThreatLevelOpacity(threat_level);

    return {
        threat_id,
        center,
        radius,
        threat_level,
        threat_type: threat_type_code || 'UNKNOWN',
        visualization: {
            color,
            opacity,
            stroke: true,
            strokeColor: color,
            strokeWidth: 2,
        },
    };
}

// ============================================================================
// 방책별 색상 구분
// ============================================================================

/**
 * 방책 Rank에 따른 색상 결정
 */
export function getCOAColor(rank: number): string {
    switch (rank) {
        case 1:
            return '#3b82f6'; // 파란색
        case 2:
            return '#10b981'; // 초록색
        case 3:
            return '#8b5cf6'; // 보라색
        default:
            return '#6b7280'; // 회색
    }
}

/**
 * 선택된 방책 강조 색상
 */
export const SELECTED_COA_COLOR = '#ef4444'; // 빨간색

// ============================================================================
// MIL-STD-2525D 심볼 매핑
// ============================================================================

/**
 * 아군 부대 유형별 SIDC 매핑
 */
const FRIENDLY_UNIT_SIDC_MAPPING: Record<string, string> = {
    // 보병
    '보병': 'SFGPUCI----K---',
    'INFANTRY': 'SFGPUCI----K---',
    // 기갑
    '기갑': 'SFGPUCA----K---',
    'ARMOR': 'SFGPUCA----K---',
    '기계화': 'SFGPUCA----K---',
    'MECHANIZED': 'SFGPUCA----K---',
    // 포병
    '포병': 'SFGPUCF----K---',
    'ARTILLERY': 'SFGPUCF----K---',
    // 공군
    '공군': 'SFAPUCI----K---',
    'AIR': 'SFAPUCI----K---',
    // 미사일
    '미사일': 'SFGPUCM----K---',
    'MISSILE': 'SFGPUCM----K---',
    '유도탄': 'SFGPUCM----K---',
    // 기본값
    'default': 'SFGPUCI----K---',
};

/**
 * 위협 유형별 적군 SIDC 매핑
 */
const THREAT_TYPE_SIDC_MAPPING: Record<string, string> = {
    '미사일': 'SHGPUCM----K---',
    'MISSILE': 'SHGPUCM----K---',
    '포병': 'SHGPUCF----K---',
    'ARTILLERY': 'SHGPUCF----K---',
    '기갑': 'SHGPUCA----K---',
    'ARMOR': 'SHGPUCA----K---',
    '보병': 'SHGPUCI----K---',
    'INFANTRY': 'SHGPUCI----K---',
    '공중': 'SHAPUCI----K---',
    'AIR': 'SHAPUCI----K---',
    // 기본값
    'default': 'SHGPUCA----K---',
};

/**
 * 아군 부대 SIDC 결정
 */
export function determineFriendlySIDC(제대?: string, 병종?: string): string {
    // 제대 + 병종 조합으로 매핑 시도
    if (제대 && 병종) {
        const key = `${제대}_${병종}`;
        // 부분 매칭 시도
        for (const [pattern, sidc] of Object.entries(FRIENDLY_UNIT_SIDC_MAPPING)) {
            if (pattern !== 'default' && (제대.includes(pattern) || 병종.includes(pattern))) {
                return sidc;
            }
        }
    }

    // 병종만으로 매핑 시도
    if (병종) {
        const sidc = FRIENDLY_UNIT_SIDC_MAPPING[병종];
        if (sidc) return sidc;
    }

    // 기본값
    return FRIENDLY_UNIT_SIDC_MAPPING['default'];
}

/**
 * 위협 유형으로부터 적군 SIDC 결정
 */
export function determineThreatSIDC(threatTypeCode?: string): string {
    if (!threatTypeCode) {
        return THREAT_TYPE_SIDC_MAPPING['default'];
    }

    // 직접 매핑 확인
    const sidc = THREAT_TYPE_SIDC_MAPPING[threatTypeCode];
    if (sidc) return sidc;

    // 부분 매칭 시도
    for (const [pattern, sidc] of Object.entries(THREAT_TYPE_SIDC_MAPPING)) {
        if (pattern !== 'default' && threatTypeCode.includes(pattern)) {
            return sidc;
        }
    }

    return THREAT_TYPE_SIDC_MAPPING['default'];
}

/**
 * SIDC 코드를 사용자 친화적인 설명으로 변환
 * MIL-STD-2525D 표준 기반
 * 매핑 테이블을 역으로 사용하여 더 정확한 설명 제공
 */
export function decodeSIDC(sidc: string): string {
    if (!sidc || sidc.length < 10) return '알 수 없는 심볼';

    // 표준 식별 확인 (인덱스 1)
    const standardIdentity = sidc[1];
    let identity = '';
    if (standardIdentity === 'F') identity = '아군';
    else if (standardIdentity === 'H') identity = '적군';
    else if (standardIdentity === 'N') identity = '중립';
    else if (standardIdentity === 'U') identity = '미확인';
    else identity = '알 수 없음';

    // 전투 차원 확인 (인덱스 2)
    const battleDimension = sidc[2];
    let dimension = '';
    if (battleDimension === 'P' || battleDimension === 'A') dimension = '공중';
    else if (battleDimension === 'G') dimension = '지상';
    else if (battleDimension === 'S') dimension = '해상';
    else if (battleDimension === 'U') dimension = '지하';
    else dimension = '알 수 없음';

    // 먼저 매핑 테이블에서 직접 매칭 시도
    const allMappings = { ...THREAT_TYPE_SIDC_MAPPING, ...FRIENDLY_UNIT_SIDC_MAPPING };
    for (const [type, mappedSidc] of Object.entries(allMappings)) {
        // SIDC 코드의 앞 10자리만 비교 (나머지는 변수일 수 있음)
        if (mappedSidc && mappedSidc.substring(0, 10) === sidc.substring(0, 10)) {
            // '공중', 'AIR' 같은 키는 그대로 사용하지 않고 더 적절한 표현 사용
            let displayType = type;
            if (type === '공중' || type === 'AIR') {
                displayType = '항공기';
            } else if (type === '기갑' || type === 'ARMOR') {
                displayType = '기갑';
            } else if (type === '보병' || type === 'INFANTRY') {
                displayType = '보병';
            } else if (type === '포병' || type === 'ARTILLERY') {
                displayType = '포병';
            } else if (type === '미사일' || type === 'MISSILE') {
                displayType = '미사일';
            }

            return `${identity} ${dimension} ${displayType} 부대`;
        }
    }

    // 매핑 테이블에 없으면 Function ID 기반으로 유형 추론 (인덱스 4-7)
    const funcId = sidc.substring(4, 7);
    let subtype = '';
    if (funcId.includes('CA')) subtype = '기갑';
    else if (funcId.includes('CI')) subtype = '보병';
    else if (funcId.includes('CF')) subtype = '포병';
    else if (funcId.includes('CM')) subtype = '미사일';
    else if (funcId.includes('CR')) subtype = '정찰';
    else if (dimension === '공중') subtype = '항공기';
    else if (dimension === '지상') subtype = '전투';
    else subtype = '';

    if (subtype) {
        return `${identity} ${dimension} ${subtype} 부대`;
    } else {
        return `${identity} ${dimension} 부대`;
    }
}

// ============================================================================
// 좌표 해결 유틸리티
// ============================================================================

/**
 * 위치 이름을 좌표로 변환 (데모 시나리오용)
 */
const LOCATION_COORDINATES: Record<string, LatLngExpression> = {
    '경계지역': [37.95, 126.67], // 서부전선
    '전방기지': [38.25, 127.12], // 중부전선
    '후방기지': [38.61, 128.35], // 동부전선
    '본부': [37.5665, 126.9780], // 서울
    '중앙지역': [38.0, 127.0], // DMZ 중앙
};

/**
 * 위치 이름 또는 좌표 문자열을 좌표로 변환
 * 항상 새 배열을 반환하여 참조 독립성 보장 (Circle과 Marker의 position 동기화를 위함)
 */
export function resolveLocation(location: string | undefined | null): LatLngExpression | null {
    if (!location) return null;

    // 1. 위치 이름 매핑 확인
    const locationName = String(location).trim();
    if (LOCATION_COORDINATES[locationName]) {
        const coords = LOCATION_COORDINATES[locationName];
        // 항상 새 배열 반환 (참조 독립성 보장)
        // 이렇게 하면 Circle과 Marker가 동일한 값이지만 다른 참조를 사용하여
        // React 렌더링 최적화로 인한 참조 변경 문제를 방지
        return Array.isArray(coords)
            ? [coords[0] as number, coords[1] as number]
            : coords;
    }

    // 2. 좌표 문자열 파싱
    const parsed = parseCoordinates(locationName);
    if (parsed) {
        // 파싱된 값도 새 배열로 반환 (참조 독립성 보장)
        return [parsed[0] as number, parsed[1] as number];
    }

    return null;
}

/**
 * 좌표 문자열 파싱 ("경도,위도" 또는 "위도,경도" 형식)
 */
export function parseCoordinates(coordStr: string): LatLngExpression | null {
    if (!coordStr) return null;

    try {
        const parts = coordStr.split(',').map(s => s.trim());
        if (parts.length !== 2) return null;

        const [first, second] = parts.map(Number);
        if (isNaN(first) || isNaN(second)) return null;

        // 일반적으로 경도는 -180~180, 위도는 -90~90
        // 한국 지역 기준: 위도 33~43, 경도 124~132
        if (first >= 33 && first <= 43 && second >= 124 && second <= 132) {
            // 위도, 경도 순서
            return [first, second];
        } else if (first >= 124 && first <= 132 && second >= 33 && second <= 43) {
            // 경도, 위도 순서 -> 위도, 경도로 변환
            return [second, first];
        }

        // 기본적으로 첫 번째를 위도로 가정
        return [first, second];
    } catch {
        return null;
    }
}

// ============================================================================
// 축선 타입별 스타일
// ============================================================================

export interface AxisLineStyle {
    color: string;
    weight: number;
    opacity: number;
    dashArray?: string;
}

/**
 * 축선 타입별 스타일 결정
 */
export function getAxisLineStyle(axisType: 'PRIMARY' | 'SECONDARY' | 'SUPPORT'): AxisLineStyle {
    switch (axisType) {
        case 'PRIMARY':
            return {
                color: '#1e40af', // 진한 파란색
                weight: 3,
                opacity: 0.6,
            };
        case 'SECONDARY':
            return {
                color: '#3b82f6', // 파란색
                weight: 2,
                opacity: 0.6,
                dashArray: '10, 5',
            };
        case 'SUPPORT':
            return {
                color: '#93c5fd', // 연한 파란색
                weight: 1,
                opacity: 0.6,
                dashArray: '5, 5',
            };
        default:
            return {
                color: '#3b82f6',
                weight: 2,
                opacity: 0.6,
            };
    }
}

// ============================================================================
// 경로 타입별 스타일
// ============================================================================

export interface PathStyle {
    color: string;
    weight: number;
    opacity: number;
    dashArray?: string;
    arrow?: boolean;
}

/**
 * 경로 타입별 스타일 결정
 */
export function getPathStyle(
    pathType: 'MOVEMENT' | 'ATTACK' | 'DEFENSE' | 'SUPPORT',
    isSelected: boolean = false
): PathStyle {
    const baseWeight = isSelected ? 4 : 2;

    switch (pathType) {
        case 'MOVEMENT':
            return {
                color: '#3b82f6', // 파란색
                weight: baseWeight,
                opacity: 0.7,
            };
        case 'ATTACK':
            return {
                color: '#ef4444', // 빨간색
                weight: baseWeight,
                opacity: 0.7,
                arrow: true,
            };
        case 'DEFENSE':
            return {
                color: '#3b82f6', // 파란색
                weight: baseWeight + 1,
                opacity: 0.7,
                dashArray: '10, 5',
            };
        case 'SUPPORT':
            return {
                color: '#10b981', // 초록색
                weight: baseWeight,
                opacity: 0.7,
                dashArray: '5, 5',
            };
        default:
            return {
                color: '#6b7280',
                weight: baseWeight,
                opacity: 0.7,
            };
    }
}

/**
 * 두 지점 간의 방위각 계산 (0-360도)
 * 축선 화살표 등의 회전 각도 계산에 사용
 */
export function calculateBearing(start: LatLngExpression, end: LatLngExpression): number {
    // LatLngExpression 타입 처리 (배열 또는 객체)
    let startLat: number, startLng: number, endLat: number, endLng: number;

    if (Array.isArray(start)) {
        startLat = start[0];
        startLng = start[1];
    } else {
        startLat = (start as any).lat;
        startLng = (start as any).lng;
    }

    if (Array.isArray(end)) {
        endLat = end[0];
        endLng = end[1];
    } else {
        endLat = (end as any).lat;
        endLng = (end as any).lng;
    }

    const startLatRad = startLat * Math.PI / 180;
    const startLngRad = startLng * Math.PI / 180;
    const endLatRad = endLat * Math.PI / 180;
    const endLngRad = endLng * Math.PI / 180;

    const y = Math.sin(endLngRad - startLngRad) * Math.cos(endLatRad);
    const x = Math.cos(startLatRad) * Math.sin(endLatRad) -
        Math.sin(startLatRad) * Math.cos(endLatRad) * Math.cos(endLngRad - startLngRad);

    const bearing = Math.atan2(y, x) * 180 / Math.PI;
    return (bearing + 360) % 360;
}

// ============================================================================
// 방책(COA) 유형 및 전술 분석
// ============================================================================

export type COAType = 'DEFENSE' | 'OFFENSIVE' | 'COUNTER_ATTACK' | 'MANEUVER' | 'PREEMPTIVE' | 'COMBINED';

export interface COATypeInfo {
    type: COAType;
    icon: string;
    color: string;
    label: string;
}

/**
 * COA 유형 감지 (이름 및 설명 기반)
 */
export function detectCOAType(coaName: string, description?: string): COATypeInfo {
    const text = `${coaName} ${description || ''}`.toLowerCase();

    // 키워드 기반 유형 감지
    if (text.includes('방어') || text.includes('저지') || text.includes('차단') || text.includes('defense')) {
        return {
            type: 'DEFENSE',
            icon: '🛡️',
            color: '#3b82f6',
            label: '방어'
        };
    }

    if (text.includes('반격') || text.includes('역습') || text.includes('counter')) {
        return {
            type: 'COUNTER_ATTACK',
            icon: '🎯',
            color: '#f97316',
            label: '반격'
        };
    }

    if (text.includes('공격') || text.includes('타격') || text.includes('offensive') || text.includes('attack')) {
        return {
            type: 'OFFENSIVE',
            icon: '⚔️',
            color: '#ef4444',
            label: '공격'
        };
    }

    if (text.includes('기동') || text.includes('우회') || text.includes('침투') || text.includes('maneuver')) {
        return {
            type: 'MANEUVER',
            icon: '🚁',
            color: '#8b5cf6',
            label: '기동'
        };
    }

    if (text.includes('선제') || text.includes('preemptive')) {
        return {
            type: 'PREEMPTIVE',
            icon: '⚡',
            color: '#eab308',
            label: '선제'
        };
    }

    // 기본값: 복합
    return {
        type: 'COMBINED',
        icon: '🔄',
        color: '#6b7280',
        label: '복합'
    };
}

/**
 * COA에서 핵심 전술 추출 (간단 버전)
 */
export function extractKeyTactics(coa: any): string {
    // reasoning.key_tactics가 있으면 사용
    if (coa.reasoning?.key_tactics) {
        return coa.reasoning.key_tactics;
    }

    // description에서 핵심 문장 추출 (첫 문장)
    if (coa.description) {
        const firstSentence = coa.description.split('.')[0].trim();
        if (firstSentence.length > 0) {
            return firstSentence;
        }
    }

    // coa_name에서 추출
    if (coa.coa_name) {
        return coa.coa_name;
    }

    return '전술 정보 없음';
}

/**
 * COA 부대 배치 요약
 */
export function summarizeUnitDeployment(coa: any): string {
    const units = coa.participating_units || [];
    const unitCount = units.length;

    if (unitCount === 0) {
        return '배치 정보 없음';
    }

    // 주요 배치 축선 또는 위치 (첫 번째 부대 기준)
    const primaryLocation = units[0]?.deployment_location || units[0]?.axis_id || '전선';

    return `${unitCount}개 부대, ${primaryLocation} 배치`;
}
