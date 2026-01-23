// frontend/src/hooks/useCodeLabels.ts
import { useState, useEffect } from 'react';

export interface CodeLabelMappings {
    threat_types: Record<string, string>;
    axes: Record<string, string>;
    threat_ids: Record<string, string>;
}

export interface CodeLabelHelper {
    getThreatTypeLabel: (code: string) => string;
    getAxisLabel: (code: string) => string;
    getThreatIdLabel: (id: string) => string;
    formatWithCode: (label: string, code: string) => string;
    mappings: CodeLabelMappings | null;
    isLoading: boolean;
}

/**
 * 코드-한글 라벨 매핑 데이터를 로드하고 변환 함수를 제공하는 커스텀 훅
 */
export function useCodeLabels(): CodeLabelHelper {
    const [mappings, setMappings] = useState<CodeLabelMappings | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchMappings = async () => {
            try {
                const response = await fetch(`http://${window.location.hostname}:8000/api/v1/system/code-mappings`);
                if (response.ok) {
                    const data = await response.json();
                    setMappings(data);
                    console.log('[useCodeLabels] 코드 매핑 로드 완료:', {
                        threat_types: Object.keys(data.threat_types || {}).length,
                        axes: Object.keys(data.axes || {}).length,
                        threat_ids: Object.keys(data.threat_ids || {}).length
                    });
                } else {
                    console.error('[useCodeLabels] 코드 매핑 로드 실패:', response.status);
                    // 빈 매핑으로 fallback
                    setMappings({ threat_types: {}, axes: {}, threat_ids: {} });
                }
            } catch (error) {
                console.error('[useCodeLabels] 코드 매핑 로드 에러:', error);
                // 빈 매핑으로 fallback
                setMappings({ threat_types: {}, axes: {}, threat_ids: {} });
            } finally {
                setIsLoading(false);
            }
        };

        fetchMappings();
    }, []);

    const getThreatTypeLabel = (code: string): string => {
        if (!code || !mappings) return '미상';
        const codeStr = String(code).trim();

        // 이미 한글인 경우 그대로 반환
        if (Object.values(mappings.threat_types).includes(codeStr)) {
            return codeStr;
        }

        // 코드를 한글로 변환
        return mappings.threat_types[codeStr] || codeStr;
    };

    const getAxisLabel = (code: string): string => {
        if (!code || !mappings) return '';
        const codeStr = String(code).trim();

        // 이미 한글인 경우 그대로 반환
        if (Object.values(mappings.axes).includes(codeStr)) {
            return codeStr;
        }

        // 코드를 한글로 변환
        return mappings.axes[codeStr] || codeStr;
    };

    const getThreatIdLabel = (id: string): string => {
        if (!id || !mappings) return '';
        const idStr = String(id).trim();
        return mappings.threat_ids[idStr] || '';
    };

    const formatWithCode = (label: string, code: string): string => {
        if (!code || code.trim() === '') {
            return label || '미상';
        }

        if (!label || label === code) {
            return code;
        }

        return `${label} (${code})`;
    };

    return {
        getThreatTypeLabel,
        getAxisLabel,
        getThreatIdLabel,
        formatWithCode,
        mappings,
        isLoading
    };
}
