// frontend/src/components/data/DataQualityPanel.tsx
import React, { useState, useEffect } from 'react';
import { RefreshCw, AlertCircle, CheckCircle2, Info } from 'lucide-react';
import api from '../../lib/api';

interface QualityIssue {
    severity: 'error' | 'warning' | 'info';
    type: string;
    field?: string;
    row_index?: number;
    message: string;
}

interface TableQuality {
    name: string;
    display_name: string;
    quality_score: number;
    issues: QualityIssue[];
}

interface DataQualityResponse {
    tables: TableQuality[];
}

const SEVERITY_COLORS = {
    error: 'text-red-400 bg-red-900/20 border-red-800',
    warning: 'text-yellow-400 bg-yellow-900/20 border-yellow-800',
    info: 'text-blue-400 bg-blue-900/20 border-blue-800'
};

const SEVERITY_ICONS = {
    error: AlertCircle,
    warning: AlertCircle,
    info: Info
};

export default function DataQualityPanel() {
    const [qualityData, setQualityData] = useState<DataQualityResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

    useEffect(() => {
        runQualityCheck();
    }, []);

    const runQualityCheck = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.get<DataQualityResponse>('/data-management/quality-check');
            setQualityData(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || '품질 검증 실패');
            console.error('Quality check error:', err);
        } finally {
            setLoading(false);
        }
    };

    const toggleTable = (tableName: string) => {
        const newExpanded = new Set(expandedTables);
        if (newExpanded.has(tableName)) {
            newExpanded.delete(tableName);
        } else {
            newExpanded.add(tableName);
        }
        setExpandedTables(newExpanded);
    };

    const getScoreColor = (score: number) => {
        if (score >= 90) return 'text-green-400';
        if (score >= 70) return 'text-yellow-400';
        return 'text-red-400';
    };

    const getScoreBgColor = (score: number) => {
        if (score >= 90) return 'bg-green-900/20 border-green-800';
        if (score >= 70) return 'bg-yellow-900/20 border-yellow-800';
        return 'bg-red-900/20 border-red-800';
    };

    const overallScore = qualityData
        ? qualityData.tables.reduce((sum, t) => sum + t.quality_score, 0) / qualityData.tables.length
        : 0;

    const totalIssues = qualityData
        ? qualityData.tables.reduce((sum, t) => sum + t.issues.length, 0)
        : 0;

    return (
        <div className="space-y-6 pb-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-zinc-100">데이터 품질 검증</h2>
                <button
                    onClick={runQualityCheck}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-zinc-700 disabled:text-zinc-500 rounded text-sm font-medium transition-colors"
                >
                    <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    {loading ? '검증 중...' : '재검증'}
                </button>
            </div>

            {
                error && (
                    <div className="bg-red-900/20 border border-red-800 text-red-400 p-4 rounded">
                        <p className="font-semibold">오류:</p>
                        <p className="text-sm mt-1">{error}</p>
                    </div>
                )
            }

            {
                qualityData && (
                    <>
                        {/* Overall Summary */}
                        <div className={`p-6 rounded-lg border ${getScoreBgColor(overallScore)}`}>
                            <div className="flex items-center justify-between">
                                <div>
                                    <h3 className="text-lg font-semibold text-zinc-100">전체 품질 점수</h3>
                                    <p className="text-sm text-zinc-400 mt-1">
                                        {qualityData.tables.length}개 테이블 분석 완료
                                    </p>
                                </div>
                                <div className="text-right">
                                    <div className={`text-4xl font-bold ${getScoreColor(overallScore)}`}>
                                        {overallScore.toFixed(1)}
                                    </div>
                                    <div className="text-sm text-zinc-400 mt-1">/ 100</div>
                                </div>
                            </div>

                            {totalIssues > 0 && (
                                <div className="mt-4 pt-4 border-t border-zinc-700">
                                    <p className="text-sm text-zinc-300">
                                        총 <span className="font-semibold text-yellow-400">{totalIssues}개</span>의 이슈가 발견되었습니다.
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* Tables List */}
                        <div className="space-y-4">
                            {qualityData.tables.map(table => (
                                <div
                                    key={table.name}
                                    className="bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden"
                                >
                                    {/* Table Header */}
                                    <button
                                        onClick={() => toggleTable(table.name)}
                                        className="w-full p-4 flex items-center justify-between hover:bg-zinc-800/50 transition-colors"
                                    >
                                        <div className="flex items-center gap-4">
                                            <CheckCircle2
                                                className={`w-6 h-6 ${getScoreColor(table.quality_score)}`}
                                            />
                                            <div className="text-left">
                                                <h3 className="text-sm font-semibold text-zinc-100">
                                                    {table.display_name}
                                                </h3>
                                                <p className="text-xs text-zinc-400 mt-0.5">
                                                    {table.issues.length === 0
                                                        ? '이슈 없음'
                                                        : `${table.issues.length}개 이슈 발견`}
                                                </p>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-4">
                                            <div className={`text-2xl font-bold ${getScoreColor(table.quality_score)}`}>
                                                {table.quality_score.toFixed(1)}
                                            </div>
                                            <svg
                                                className={`w-5 h-5 text-zinc-400 transition-transform ${expandedTables.has(table.name) ? 'rotate-180' : ''
                                                    }`}
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                            >
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                            </svg>
                                        </div>
                                    </button>

                                    {/* Issues List (Collapsible) */}
                                    {expandedTables.has(table.name) && table.issues.length > 0 && (
                                        <div className="border-t border-zinc-800 p-4">
                                            <h4 className="text-sm font-semibold text-zinc-300 mb-3">이슈 상세</h4>
                                            <div className="space-y-2">
                                                {table.issues.map((issue, idx) => {
                                                    const Icon = SEVERITY_ICONS[issue.severity];
                                                    return (
                                                        <div
                                                            key={idx}
                                                            className={`p-3 rounded border ${SEVERITY_COLORS[issue.severity]}`}
                                                        >
                                                            <div className="flex items-start gap-3">
                                                                <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
                                                                <div className="flex-1">
                                                                    <div className="flex items-center gap-2 mb-1">
                                                                        <span className="text-xs font-semibold uppercase">
                                                                            {issue.type.replace('_', ' ')}
                                                                        </span>
                                                                        {issue.field && (
                                                                            <span className="text-xs opacity-70">
                                                                                • Field: <code className="font-mono">{issue.field}</code>
                                                                            </span>
                                                                        )}
                                                                        {issue.row_index !== undefined && issue.row_index !== null && (
                                                                            <span className="text-xs opacity-70">
                                                                                • Row: {issue.row_index}
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                    <p className="text-sm">{issue.message}</p>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}

                                    {expandedTables.has(table.name) && table.issues.length === 0 && (
                                        <div className="border-t border-zinc-800 p-4">
                                            <div className="flex items-center gap-2 text-green-400">
                                                <CheckCircle2 className="w-5 h-5" />
                                                <p className="text-sm">이 테이블에는 품질 이슈가 없습니다.</p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </>
                )
            }

            {
                loading && !qualityData && (
                    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-12 text-center">
                        <div className="text-zinc-400">품질 검증 실행 중...</div>
                    </div>
                )
            }
        </div >
    );
}
