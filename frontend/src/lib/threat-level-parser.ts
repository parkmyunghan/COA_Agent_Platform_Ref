/**
 * 위협수준 파싱 유틸리티
 * 문자열(HIGH, MEDIUM, LOW) 및 숫자를 0-1 범위의 숫자로 정규화
 */

export interface ThreatLevelParseResult {
    normalized: number; // 0-1 범위
    percent: number; // 0-100 범위
    label: string; // "HIGH" | "MEDIUM" | "LOW"
    raw: string | number; // 원본 값
}

/**
 * 위협수준 문자열 매핑 테이블
 * 백엔드 SituationInfoConverter.THREAT_LEVEL_MAPPING과 동기화 필요
 * 
 * 참고: 백엔드 common/situation_converter.py의 THREAT_LEVEL_MAPPING과 일치해야 함
 */
const THREAT_LEVEL_MAPPING: Record<string, number> = {
    // 영어 (대소문자 무관) - 백엔드와 동일
    "critical": 0.95,
    "very high": 0.90,
    "veryhigh": 0.90,
    "high": 0.85,
    "medium": 0.60,
    "moderate": 0.60,
    "low": 0.30,
    "minimal": 0.15,
    // 한글 - 백엔드와 동일
    "위급": 0.95,
    "매우높음": 0.90,
    "높음": 0.85,
    "중간": 0.60,
    "보통": 0.60,
    "낮음": 0.30,
    "미미": 0.15,
    // 약어 - 백엔드와 동일
    "h": 0.85,
    "m": 0.60,
    "l": 0.30,
};

/**
 * 위협수준을 정규화된 숫자로 변환
 * 
 * @param rawValue 원본 값 (문자열 "HIGH", 숫자 0.5, 문자열 "50" 등)
 * @returns 정규화된 위협수준 정보
 */
export function parseThreatLevel(rawValue: any): ThreatLevelParseResult | null {
    if (rawValue === undefined || rawValue === null || rawValue === '') {
        return null;
    }

    const rawStr = String(rawValue).trim().toLowerCase();
    
    // 유효하지 않은 문자열 체크
    if (rawStr === 'nan' || rawStr === 'none' || rawStr === 'null' || 
        rawStr === 'inf' || rawStr === 'infinity' || rawStr === '') {
        return null;
    }

    try {
        let normalized: number;
        let label: string;

        // 1. 백엔드 변환 결과 처리 우선 (0-100 범위의 정수 문자열)
        // 백엔드에서 SituationInfoConverter.normalize_threat_level()을 사용하여
        // 변환된 경우 0-100 범위의 정수 문자열로 전달됨
        if (typeof rawValue === 'string') {
            // 순수 숫자 문자열인지 확인 (백엔드 변환 결과)
            const numericMatch = rawValue.match(/^\d+$/);
            if (numericMatch) {
                const numValue = parseInt(numericMatch[0], 10);
                if (!isNaN(numValue) && isFinite(numValue) && numValue >= 0 && numValue <= 100) {
                    normalized = numValue / 100;
                    label = getLabelFromNormalized(normalized);
                    return {
                        normalized,
                        percent: numValue,
                        label,
                        raw: rawValue
                    };
                }
            }
            
            // 2. 문자열 매핑 시도 (원본 문자열 "HIGH", "MEDIUM", "LOW" 등)
            const matched = Object.keys(THREAT_LEVEL_MAPPING).find(key => 
                rawStr.includes(key) || rawStr === key
            );
            
            if (matched) {
                normalized = THREAT_LEVEL_MAPPING[matched];
                label = getLabelFromNormalized(normalized);
                return {
                    normalized,
                    percent: Math.round(normalized * 100),
                    label,
                    raw: rawValue
                };
            }
        }

        // 3. 숫자로 변환 시도 (백엔드 변환 실패 또는 원본 숫자)
        let level: number;
        
        if (typeof rawValue === 'number') {
            if (isNaN(rawValue) || !isFinite(rawValue)) {
                return null;
            }
            level = rawValue;
        } else {
            // 문자열에서 숫자 추출 (예: "50.0", "50%", "50.0%" 등)
            const match = String(rawValue).match(/(\d+\.?\d*)/);
            if (match) {
                level = parseFloat(match[1]);
                if (isNaN(level) || !isFinite(level)) {
                    return null;
                }
            } else {
                return null;
            }
        }

        // 4. 범위 정규화
        if (level >= 0 && level <= 1) {
            // 이미 0-1 범위
            normalized = level;
        } else if (level >= 0 && level <= 100) {
            // 0-100 범위를 0-1로 정규화
            normalized = level / 100;
        } else {
            // 범위를 벗어남
            return null;
        }

        // 5. 레이블 결정
        label = getLabelFromNormalized(normalized);

        return {
            normalized,
            percent: Math.round(normalized * 100),
            label,
            raw: rawValue
        };
    } catch (e) {
        return null;
    }
}

/**
 * 정규화된 값(0-1)에서 레이블 결정
 */
function getLabelFromNormalized(normalized: number): string {
    if (normalized >= 0.85) {
        return "HIGH";
    } else if (normalized >= 0.60) {
        return "MEDIUM";
    } else {
        return "LOW";
    }
}

/**
 * 위협수준을 백분율 문자열로 변환 (표시용)
 */
export function formatThreatLevel(rawValue: any): string {
    const parsed = parseThreatLevel(rawValue);
    if (!parsed) {
        return '';
    }
    return `${parsed.percent}%`;
}

/**
 * 위협수준을 한글 텍스트로 변환 (표시용)
 */
export function formatThreatLevelText(rawValue: any): string {
    const parsed = parseThreatLevel(rawValue);
    if (!parsed) {
        return '미상';
    }
    
    const labelMap: Record<string, string> = {
        "HIGH": "높음",
        "MEDIUM": "중간",
        "LOW": "낮음"
    };
    
    return labelMap[parsed.label] || parsed.label;
}
