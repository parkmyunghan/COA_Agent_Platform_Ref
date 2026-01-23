import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Checkbox } from './ui/checkbox';
import { Label } from './ui/label';

interface ChainInfo {
    chains?: Array<{
        path: string[];
        predicates?: string[];
        score?: number;
    }>;
    summary?: {
        total_chains?: number;
        avg_depth?: number;
        avg_score?: number;
    };
    info?: string;
}

interface ChainVisualizerProps {
    chainInfo: ChainInfo;
    expanded?: boolean;
}

export const ChainVisualizer: React.FC<ChainVisualizerProps> = ({ chainInfo, expanded = false }) => {
    const [showRawPaths, setShowRawPaths] = useState(false);
    const [isExpanded, setIsExpanded] = useState(expanded);

    if (!chainInfo) {
        return null;
    }

    const chains = chainInfo.chains || [];
    const summary = chainInfo.summary || {};
    const totalChains = summary.total_chains || chains.length;

    if (chains.length === 0) {
        return (
            <Card className="border-gray-200 dark:border-zinc-700">
                <CardHeader>
                    <CardTitle className="text-sm font-semibold">🔗 전략 연결 체인 (연결 정보 없음)</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                        <p className="text-sm text-blue-700 dark:text-blue-300 mb-2">
                            <strong>⚠️ 전략 체인 미발견</strong>
                        </p>
                        <p className="text-xs text-blue-600 dark:text-blue-400 mb-2">
                            <strong>사유:</strong> {chainInfo.info || '해당 위협과 방책 간의 직접적인 온톨로지 연결(Graph Path)을 찾을 수 없습니다.'}
                        </p>
                        <p className="text-xs text-blue-600 dark:text-blue-400">
                            <strong>해설:</strong> 이 방책은 온톨로지 그래프상의 직접적인 인과관계(Chain)보다는, LLM의 추론이나 과거 통계적 패턴(전투 성공률 등)에 기반하여 추천되었습니다.
                        </p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    const getLabel = (uriOrStr: string): string => {
        if (!uriOrStr) return 'Unknown';
        if (uriOrStr.includes('#')) {
            return uriOrStr.split('#').pop() || uriOrStr;
        }
        if (uriOrStr.includes('/')) {
            return uriOrStr.split('/').pop() || uriOrStr;
        }
        return uriOrStr;
    };

    return (
        <Card className="border-gray-200 dark:border-zinc-700">
            <CardHeader>
                <CardTitle className="text-sm font-semibold">
                    🔗 전략 연결 체인 (Dynamic Chain of Strategy) - {totalChains} paths found
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Summary Metrics */}
                <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-3 bg-gray-50 dark:bg-zinc-800 rounded-lg">
                        <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Total Chains</div>
                        <div className="text-lg font-bold text-gray-900 dark:text-white">{totalChains}</div>
                    </div>
                    <div className="text-center p-3 bg-gray-50 dark:bg-zinc-800 rounded-lg">
                        <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Avg Depth</div>
                        <div className="text-lg font-bold text-gray-900 dark:text-white">{summary.avg_depth || 0}</div>
                    </div>
                    <div className="text-center p-3 bg-gray-50 dark:bg-zinc-800 rounded-lg">
                        <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Avg Score</div>
                        <div className="text-lg font-bold text-gray-900 dark:text-white">{(summary.avg_score || 0).toFixed(2)}</div>
                    </div>
                </div>

                {/* Chain Visualization */}
                <div className="space-y-3">
                    {chains.map((chain, chainIdx) => {
                        const path = chain.path || [];
                        if (path.length === 0) return null;

                        return (
                            <div key={chainIdx} className="p-3 bg-gray-50 dark:bg-zinc-800 rounded-lg border border-gray-200 dark:border-zinc-700">
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="text-xs font-semibold text-gray-500 dark:text-gray-400">Path {chainIdx + 1}</span>
                                    <span className="text-xs text-gray-400">Score: {(chain.score || 0).toFixed(2)}</span>
                                </div>
                                <div className="flex items-center gap-2 flex-wrap">
                                    {path.map((node, nodeIdx) => {
                                        const label = getLabel(node);
                                        const isStart = nodeIdx === 0;
                                        const isEnd = nodeIdx === path.length - 1;
                                        
                                        return (
                                            <React.Fragment key={nodeIdx}>
                                                <div className={`px-3 py-1 rounded text-xs font-medium ${
                                                    isStart 
                                                        ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-2 border-red-500'
                                                        : isEnd
                                                        ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border-2 border-blue-500'
                                                        : 'bg-gray-100 dark:bg-zinc-700 text-gray-700 dark:text-gray-300'
                                                }`}>
                                                    {label}
                                                </div>
                                                {nodeIdx < path.length - 1 && (
                                                    <span className="text-gray-400 dark:text-gray-600">→</span>
                                                )}
                                            </React.Fragment>
                                        );
                                    })}
                                </div>
                                {chain.predicates && chain.predicates.length > 0 && (
                                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                                        관계: {chain.predicates.map(p => getLabel(p)).join(' → ')}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Raw Paths Toggle */}
                <div className="flex items-center space-x-2 pt-2 border-t border-gray-200 dark:border-zinc-700">
                    <Checkbox
                        id="show-raw-paths"
                        checked={showRawPaths}
                        onCheckedChange={(checked) => setShowRawPaths(checked === true)}
                    />
                    <Label htmlFor="show-raw-paths" className="text-sm cursor-pointer">
                        Show Raw Paths
                    </Label>
                </div>

                {showRawPaths && (
                    <div className="space-y-2 p-3 bg-gray-50 dark:bg-zinc-800 rounded-lg">
                        {chains.map((chain, idx) => {
                            const pathLabels = (chain.path || []).map(p => getLabel(p));
                            return (
                                <div key={idx} className="text-xs text-gray-600 dark:text-gray-400 p-2 bg-white dark:bg-zinc-900 rounded border border-gray-200 dark:border-zinc-700">
                                    Path {idx + 1}: {pathLabels.join(' → ')} (Score: {(chain.score || 0).toFixed(2)})
                                </div>
                            );
                        })}
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
