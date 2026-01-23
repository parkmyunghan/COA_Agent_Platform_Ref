import React, { useState } from 'react';
import { X, BarChart3, TrendingUp, Shield, AlertTriangle, Eye } from 'lucide-react';
import type { COASummary } from '../types/schema';

interface COAComparisonPanelProps {
    coas: COASummary[];
    onClose: () => void;
    onViewDetail?: (coa: COASummary) => void; // 상세 보기 콜백 추가
}

export const COAComparisonPanel: React.FC<COAComparisonPanelProps> = ({ coas, onClose, onViewDetail }) => {
    const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['total_score', 'combat_power_score', 'mobility_score', 'constraint_score', 'threat_response_score']);

    if (!coas || coas.length === 0) {
        return null;
    }

    // 비교표 항목 정의
    // 주의: 이 항목들은 COAEvaluator의 점수 필드명과 일치해야 함
    // 실제 점수 계산: COAScorer breakdown (threat, resources, assets, environment) → COAEvaluator 필드명으로 매핑
    const metrics = [
        { key: 'total_score', label: '총점', color: 'indigo', description: '종합 평가 점수' },
        { key: 'combat_power_score', label: '전투력', color: 'blue', description: '전투력 우세도 (COAScorer: assets)' },
        { key: 'mobility_score', label: '기동성', color: 'green', description: '기동 가능성 (COAScorer: resources)' },
        { key: 'constraint_score', label: '제약조건', color: 'yellow', description: '제약조건 준수도 (COAScorer: environment)' },
        { key: 'threat_response_score', label: '위협대응', color: 'red', description: '위협 대응도 (COAScorer: threat)' },
        { key: 'risk_score', label: '위험도', color: 'orange', description: '예상 손실/위험도' }
    ];

    const getScore = (coa: COASummary, key: string): number => {
        switch (key) {
            case 'total_score':
                return coa.total_score || 0;
            case 'combat_power_score':
                return coa.combat_power_score || 0;
            case 'mobility_score':
                return coa.mobility_score || 0;
            case 'constraint_score':
                return coa.constraint_score || 0;
            case 'threat_response_score':
                return coa.threat_response_score || 0;
            case 'risk_score':
                return coa.risk_score || 0;
            default:
                return 0;
        }
    };

    const getMaxScore = (key: string): number => {
        return Math.max(...coas.map(coa => getScore(coa, key)), 0.1);
    };

    const handleViewDetail = (coa: COASummary) => {
        if (onViewDetail) {
            onViewDetail(coa);
            onClose(); // 비교 패널 닫기
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-zinc-900 rounded-xl shadow-2xl max-w-7xl w-full max-h-[90vh] overflow-hidden flex flex-col border border-gray-200 dark:border-zinc-700">
                {/* Header */}
                <div className="p-6 border-b border-gray-200 dark:border-zinc-700 bg-gradient-to-r from-indigo-600 to-purple-600">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-3">
                            <BarChart3 className="w-6 h-6 text-white" />
                            <h2 className="text-2xl font-bold text-white">방책 비교 분석</h2>
                            <span className="text-blue-100 text-sm">({coas.length}개 방책)</span>
                        </div>
                        <button
                            onClick={onClose}
                            className="text-white/80 hover:text-white transition-colors p-2 hover:bg-white/10 rounded-lg"
                        >
                            <X className="w-6 h-6" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {/* 메트릭 선택 */}
                    <div className="bg-gray-50 dark:bg-zinc-800 rounded-lg p-4 border border-gray-200 dark:border-zinc-700">
                        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">비교할 지표 선택</h3>
                        <div className="flex flex-wrap gap-2">
                            {metrics.map(metric => (
                                <label
                                    key={metric.key}
                                    className="flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-zinc-800 transition-colors"
                                >
                                    <input
                                        type="checkbox"
                                        checked={selectedMetrics.includes(metric.key)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setSelectedMetrics([...selectedMetrics, metric.key]);
                                            } else {
                                                setSelectedMetrics(selectedMetrics.filter(m => m !== metric.key));
                                            }
                                        }}
                                        className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
                                    />
                                    <span className="text-sm text-gray-700 dark:text-gray-300">{metric.label}</span>
                                </label>
                            ))}
                        </div>
                    </div>

                    {/* 비교 테이블 */}
                    <div className="overflow-x-auto">
                        <table className="w-full border-collapse">
                            <thead>
                                <tr className="bg-gray-100 dark:bg-zinc-800 border-b-2 border-gray-300 dark:border-zinc-700">
                                    <th className="p-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-300 sticky left-0 bg-gray-100 dark:bg-zinc-800 z-10">
                                        방책
                                    </th>
                                    {coas.map((coa, idx) => (
                                        <th
                                            key={coa.coa_id}
                                            className="p-3 text-center text-sm font-semibold text-gray-700 dark:text-gray-300 min-w-[200px]"
                                        >
                                            <div className="flex flex-col items-center gap-2">
                                                <div className="flex flex-col items-center gap-1">
                                                    <span className="inline-block px-2 py-0.5 rounded text-xs font-black bg-indigo-600 text-white">
                                                        Rank {coa.rank}
                                                    </span>
                                                    <span className="font-bold">{coa.coa_name}</span>
                                                </div>
                                                {onViewDetail && (
                                                    <button
                                                        onClick={() => handleViewDetail(coa)}
                                                        className="flex items-center gap-1 px-2 py-1 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                                                        title="상세 정보 보기"
                                                    >
                                                        <Eye className="w-3 h-3" />
                                                        상세 보기
                                                    </button>
                                                )}
                                            </div>
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {/* 점수 비교 행들 */}
                                {selectedMetrics.map(metricKey => {
                                    const metric = metrics.find(m => m.key === metricKey);
                                    if (!metric) return null;

                                    const maxScore = getMaxScore(metricKey);

                                    return (
                                        <tr key={metricKey} className="border-b border-gray-200 dark:border-zinc-700 hover:bg-gray-50 dark:hover:bg-zinc-800/50">
                                            <td className="p-3 text-sm font-medium text-gray-700 dark:text-gray-300 sticky left-0 bg-white dark:bg-zinc-900 z-10">
                                                <div className="flex items-center gap-2">
                                                    <TrendingUp className="w-4 h-4 text-gray-500" />
                                                    {metric.label}
                                                </div>
                                            </td>
                                            {coas.map(coa => {
                                                const score = getScore(coa, metricKey);
                                                const safeScore = score !== undefined && score !== null ? score : 0;
                                                const percentage = maxScore > 0 ? (safeScore / maxScore) * 100 : 0;

                                                return (
                                                    <td key={coa.coa_id} className="p-3 text-center">
                                                        <div className="space-y-2">
                                                            <div className="text-lg font-bold text-gray-900 dark:text-white">
                                                                {safeScore !== undefined && safeScore !== null ? (safeScore * 100).toFixed(1) : 'N/A'}%
                                                            </div>
                                                            <div className="w-full h-3 bg-gray-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                                                                <div
                                                                    className={`h-full bg-gradient-to-r ${
                                                                        metric.color === 'indigo' ? 'from-indigo-500 to-indigo-600' :
                                                                        metric.color === 'blue' ? 'from-blue-500 to-blue-600' :
                                                                        metric.color === 'green' ? 'from-green-500 to-green-600' :
                                                                        metric.color === 'yellow' ? 'from-yellow-500 to-yellow-600' :
                                                                        metric.color === 'red' ? 'from-red-500 to-red-600' :
                                                                        'from-orange-500 to-orange-600'
                                                                    } transition-all duration-500`}
                                                                    style={{ width: `${percentage}%` }}
                                                                />
                                                            </div>
                                                        </div>
                                                    </td>
                                                );
                                            })}
                                        </tr>
                                    );
                                })}

                                {/* 설명 비교 */}
                                <tr className="border-b-2 border-gray-300 dark:border-zinc-700">
                                    <td className="p-3 text-sm font-medium text-gray-700 dark:text-gray-300 sticky left-0 bg-gray-50 dark:bg-zinc-800 z-10">
                                        <div className="flex items-center gap-2">
                                            <Shield className="w-4 h-4 text-gray-500" />
                                            설명
                                        </div>
                                    </td>
                                    {coas.map(coa => (
                                        <td key={coa.coa_id} className="p-3 text-sm text-gray-600 dark:text-gray-400">
                                            <p className="line-clamp-3">{coa.description || '설명 없음'}</p>
                                        </td>
                                    ))}
                                </tr>

                                {/* 참여 부대 비교 */}
                                <tr className="border-b border-gray-200 dark:border-zinc-700">
                                    <td className="p-3 text-sm font-medium text-gray-700 dark:text-gray-300 sticky left-0 bg-white dark:bg-zinc-900 z-10">
                                        참여 부대
                                    </td>
                                    {coas.map(coa => {
                                        const units = (coa as any).participating_units;
                                        const unitsText = Array.isArray(units) ? units.join(', ') : units || '정보 없음';
                                        return (
                                            <td key={coa.coa_id} className="p-3 text-sm text-gray-600 dark:text-gray-400">
                                                {unitsText}
                                            </td>
                                        );
                                    })}
                                </tr>

                                {/* 위험 요소 비교 */}
                                {coas.some(coa => coa.risk_score !== undefined) && (
                                    <tr className="border-b border-gray-200 dark:border-zinc-700 bg-red-50/30 dark:bg-red-900/10">
                                        <td className="p-3 text-sm font-medium text-gray-700 dark:text-gray-300 sticky left-0 bg-red-50/30 dark:bg-red-900/10 z-10">
                                            <div className="flex items-center gap-2">
                                                <AlertTriangle className="w-4 h-4 text-red-500" />
                                                위험도
                                            </div>
                                        </td>
                                        {coas.map(coa => {
                                            const riskScore = coa.risk_score !== undefined && coa.risk_score !== null ? coa.risk_score : 0;
                                            return (
                                                <td key={coa.coa_id} className="p-3 text-center">
                                                    <div className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${
                                                        riskScore > 0.7 ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                                                        riskScore > 0.4 ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                                                        'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                                    }`}>
                                                        {(riskScore * 100).toFixed(0)}%
                                                    </div>
                                                </td>
                                            );
                                        })}
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-gray-200 dark:border-zinc-700 bg-gray-50 dark:bg-zinc-800/50">
                    <div className="flex justify-end gap-3">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-zinc-700 dark:hover:bg-zinc-600 text-gray-900 dark:text-white rounded-lg font-medium transition-colors"
                        >
                            닫기
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
