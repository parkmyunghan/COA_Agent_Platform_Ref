import React, { useState } from 'react';
import api from '../lib/api';
import type { ThreatAnalyzeRequest, ThreatEventBase } from '../types/schema';

interface ThreatAnalysisPanelProps {
    onThreatIdentified?: (threat: ThreatEventBase) => void;
}

export const ThreatAnalysisPanel: React.FC<ThreatAnalysisPanelProps> = ({ onThreatIdentified }) => {
    const [sitrep, setSitrep] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<ThreatEventBase | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleAnalyze = async () => {
        if (!sitrep.trim()) return;

        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const payload: ThreatAnalyzeRequest = {
                sitrep_text: sitrep,
                // mission_id can be added here if we have context
            };

            const response = await api.post<ThreatEventBase>('/threat/analyze', payload);
            setResult(response.data);
            if (onThreatIdentified) {
                onThreatIdentified(response.data);
            }
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || '분석 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-white dark:bg-zinc-800 p-4 rounded-lg shadow-sm border border-gray-200 dark:border-zinc-700">
            <h3 className="font-semibold text-lg mb-4 dark:text-white">위협 식별 및 분석 (Threat Analysis)</h3>

            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        상황 보고 (SITREP) 입력
                    </label>
                    <textarea
                        className="w-full p-2 border border-gray-300 dark:border-zinc-600 rounded bg-white dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-blue-500 min-h-[100px] dark:text-white"
                        placeholder="예: 적 전차대대가 00지역에서 남하하는 징후 식별..."
                        value={sitrep}
                        onChange={(e) => setSitrep(e.target.value)}
                    />
                </div>

                <button
                    onClick={handleAnalyze}
                    disabled={loading || !sitrep.trim()}
                    className={`w-full py-2 px-4 rounded text-white font-medium transition-colors ${loading || !sitrep.trim()
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-blue-600 hover:bg-blue-700'
                        }`}
                >
                    {loading ? (
                        <span className="flex items-center justify-center gap-2">
                            <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
                            분석 중...
                        </span>
                    ) : (
                        '유사도 분석 및 식별 실행'
                    )}
                </button>

                {error && (
                    <div className="p-3 bg-red-50 text-red-700 text-sm rounded border border-red-200">
                        {error}
                    </div>
                )}

                {result && (
                    <div className="mt-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded">
                        <h4 className="font-bold text-green-800 dark:text-green-300 mb-2">분석 결과</h4>
                        <ul className="text-sm space-y-1 text-gray-700 dark:text-gray-300">
                            <li><span className="font-semibold">ID:</span> {result.threat_id}</li>
                            <li><span className="font-semibold">유형:</span> {result.threat_type_code} ({result.threat_type_original})</li>
                            <li><span className="font-semibold">신뢰도:</span> {result.confidence}%</li>
                            <li><span className="font-semibold">위치:</span> {result.location_cell_id}</li>
                            <li><span className="font-semibold">발생시간:</span> {result.occurrence_time}</li>
                        </ul>
                    </div>
                )}
            </div>
        </div>
    );
};
