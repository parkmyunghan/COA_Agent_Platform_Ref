// frontend/src/components/knowledge/SchemaValidationPanel.tsx
import React, { useState, useEffect } from 'react';
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw } from 'lucide-react';
import api from '../../lib/api';

interface ValidationIssue {
    severity: 'error' | 'warning' | 'info';
    message: string;
    node_id?: string;
}

interface ValidationStatistics {
    total_nodes: number;
    total_edges: number;
    classes: number;
    individuals: number;
}

interface ValidationResponse {
    status: 'valid' | 'warning' | 'error';
    statistics: ValidationStatistics;
    issues: ValidationIssue[];
}

const SEVERITY_COLORS = {
    error: 'text-red-400 bg-red-900/20 border-red-800',
    warning: 'text-yellow-400 bg-yellow-900/20 border-yellow-800',
    info: 'text-blue-400 bg-blue-900/20 border-blue-800'
};

const SEVERITY_ICONS = {
    error: XCircle,
    warning: AlertTriangle,
    info: CheckCircle2
};

export default function SchemaValidationPanel() {
    const [validation, setValidation] = useState<ValidationResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        runValidation();
    }, []);

    const runValidation = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.get<ValidationResponse>('/ontology/validate');
            setValidation(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || '스키마 검증 실패');
            console.error('Validation error:', err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            {/* Header with Refresh Button */}
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-zinc-100">온톨로지 스키마 검증</h2>
                <button
                    onClick={runValidation}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:text-zinc-500 rounded text-sm font-medium transition-colors"
                >
                    <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    {loading ? '검증 중...' : '재검증'}
                </button>
            </div>

            {error && (
                <div className="bg-red-900/20 border border-red-800 text-red-400 p-4 rounded">
                    <p className="font-semibold">오류:</p>
                    <p className="text-sm mt-1">{error}</p>
                </div>
            )}

            {validation && (
                <>
                    {/* Overall Status */}
                    <div className={`p-6 rounded-lg border ${validation.status === 'valid'
                        ? 'bg-green-900/20 border-green-800'
                        : validation.status === 'warning'
                            ? 'bg-yellow-900/20 border-yellow-800'
                            : 'bg-red-900/20 border-red-800'
                        }`}>
                        <div className="flex items-center gap-3">
                            {validation.status === 'valid' ? (
                                <CheckCircle2 className="w-8 h-8 text-green-400" />
                            ) : validation.status === 'warning' ? (
                                <AlertTriangle className="w-8 h-8 text-yellow-400" />
                            ) : (
                                <XCircle className="w-8 h-8 text-red-400" />
                            )}
                            <div>
                                <h3 className={`text-xl font-semibold ${validation.status === 'valid'
                                    ? 'text-green-400'
                                    : validation.status === 'warning'
                                        ? 'text-yellow-400'
                                        : 'text-red-400'
                                    }`}>
                                    {validation.status === 'valid' && '검증 성공'}
                                    {validation.status === 'warning' && '경고 발견'}
                                    {validation.status === 'error' && '오류 발견'}
                                </h3>
                                <p className="text-sm text-zinc-400 mt-1">
                                    {validation.issues.length === 0
                                        ? '온톨로지에 문제가 없습니다.'
                                        : `총 ${validation.issues.length}개의 이슈가 발견되었습니다.`}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Statistics */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-zinc-900 p-4 rounded-lg border border-zinc-800">
                            <div className="text-2xl font-bold text-blue-400">
                                {validation.statistics.total_nodes.toLocaleString()}
                            </div>
                            <div className="text-sm text-zinc-400 mt-1">총 노드</div>
                        </div>

                        <div className="bg-zinc-900 p-4 rounded-lg border border-zinc-800">
                            <div className="text-2xl font-bold text-green-400">
                                {validation.statistics.total_edges.toLocaleString()}
                            </div>
                            <div className="text-sm text-zinc-400 mt-1">총 엣지</div>
                        </div>

                        <div className="bg-zinc-900 p-4 rounded-lg border border-zinc-800">
                            <div className="text-2xl font-bold text-purple-400">
                                {validation.statistics.classes.toLocaleString()}
                            </div>
                            <div className="text-sm text-zinc-400 mt-1">클래스</div>
                        </div>

                        <div className="bg-zinc-900 p-4 rounded-lg border border-zinc-800">
                            <div className="text-2xl font-bold text-cyan-400">
                                {validation.statistics.individuals.toLocaleString()}
                            </div>
                            <div className="text-sm text-zinc-400 mt-1">개체</div>
                        </div>
                    </div>

                    {/* Issues List */}
                    {validation.issues.length > 0 && (
                        <div className="bg-zinc-900 p-4 rounded-lg border border-zinc-800">
                            <h3 className="text-sm font-semibold text-zinc-300 mb-4">이슈 목록</h3>
                            <div className="space-y-2 max-h-96 overflow-y-auto">
                                {validation.issues.map((issue, idx) => {
                                    const Icon = SEVERITY_ICONS[issue.severity];
                                    return (
                                        <div
                                            key={idx}
                                            className={`p-3 rounded border ${SEVERITY_COLORS[issue.severity]}`}
                                        >
                                            <div className="flex items-start gap-3">
                                                <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
                                                <div className="flex-1">
                                                    <p className="text-sm">{issue.message}</p>
                                                    {issue.node_id && (
                                                        <p className="text-xs mt-1 opacity-70 font-mono">
                                                            Node: {issue.node_id}
                                                        </p>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
