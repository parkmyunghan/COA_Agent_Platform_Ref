import React from 'react';
import { Target, Brain, Shield, Award, TrendingUp, FileText, BarChart3, MapPin, AlertTriangle, Info } from 'lucide-react';
import type { COASummary } from '../types/schema';
import { ReasoningExplanationPanel } from './ReasoningExplanationPanel';
import { DoctrineReferencePanel } from './DoctrineReferencePanel';

interface COADetailPanelProps {
    coa: COASummary | null;
    onCompare?: () => void;
}

export const COADetailPanel: React.FC<COADetailPanelProps> = ({ coa, onCompare }) => {
    if (!coa) {
        return (
            <div className="p-6 text-center text-gray-400 dark:text-gray-500">
                <p className="text-sm">지도에서 방책을 선택하면 상세 정보가 표시됩니다.</p>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-zinc-800 rounded-lg border border-gray-200 dark:border-zinc-700 overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-gray-200 dark:border-zinc-700 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-zinc-900 dark:to-zinc-800">
                <div className="flex items-center justify-between">
                    <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                            <span className="inline-block px-2 py-0.5 rounded text-xs font-bold bg-blue-600 text-white">
                                Rank {coa.rank}
                            </span>
                            <h3 className="text-lg font-bold text-gray-900 dark:text-white">{coa.coa_name}</h3>
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-normal break-keep">
                            {coa.description || '방책 설명 없음'}
                        </p>
                    </div>
                    {onCompare && (
                        <button
                            onClick={onCompare}
                            className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors ml-4"
                        >
                            <BarChart3 className="w-4 h-4" />
                            비교
                        </button>
                    )}
                </div>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4 max-h-[500px] overflow-y-auto">
                {/* Score Summary */}
                <section>
                    <div className="flex items-center gap-2 mb-3">
                        <Target className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                        <h4 className="font-bold text-sm text-gray-900 dark:text-white">종합 점수</h4>
                    </div>
                    <div className="mb-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded border-l-2 border-blue-500">
                        <p className="text-[10px] text-gray-700 dark:text-gray-300 leading-tight">
                            <strong>NATO AJP-5:</strong> 적합성/타당성/수용성은 총합점수와 별개의 평가 기준입니다.
                        </p>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div className="p-2 bg-indigo-50 dark:bg-indigo-900/20 rounded border border-indigo-200 dark:border-indigo-800" title="COAScorer breakdown의 가중합으로 계산된 종합 점수">
                            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">총점</div>
                            <div className="text-lg font-bold text-indigo-600 dark:text-indigo-400">
                                {coa.total_score !== undefined ? (coa.total_score * 100).toFixed(1) : 'N/A'}%
                            </div>
                        </div>
                        <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800" title="COA가 임무를 달성하고 계획 지침을 준수하는지 평가 (NATO AJP-5)">
                            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">적합성</div>
                            <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
                                {coa.suitability_score !== undefined ? (coa.suitability_score * 100).toFixed(1) : 'N/A'}%
                            </div>
                        </div>
                        <div className="p-2 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-800" title="시간, 공간, 자원이 가용하고 작전 환경에 적합한지 평가 (NATO AJP-5)">
                            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">타당성</div>
                            <div className="text-lg font-bold text-green-600 dark:text-green-400">
                                {coa.feasibility_score !== undefined ? (coa.feasibility_score * 100).toFixed(1) : 'N/A'}%
                            </div>
                        </div>
                        <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded border border-purple-200 dark:border-purple-800" title="예상 성과가 예상 비용(전력, 자원, 사상자, 위험 등)을 정당화하는지 평가 (NATO AJP-5)">
                            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">수용성</div>
                            <div className="text-lg font-bold text-purple-600 dark:text-purple-400">
                                {coa.acceptability_score !== undefined ? (coa.acceptability_score * 100).toFixed(1) : 'N/A'}%
                            </div>
                        </div>
                    </div>
                </section>

                {/* METT-C 점수 */}
                {coa.mett_c_scores && (
                    <section>
                        <div className="flex items-center gap-2 mb-2">
                            <MapPin className="w-4 h-4 text-orange-600 dark:text-orange-400" />
                            <h4 className="font-bold text-sm text-gray-900 dark:text-white">METT-C 종합 평가</h4>
                        </div>
                        <div className="mb-2 p-2 bg-orange-50 dark:bg-orange-900/20 rounded border-l-2 border-orange-500">
                            <p className="text-[10px] text-gray-700 dark:text-gray-300 leading-tight">
                                <strong>METT-C:</strong> Mission, Enemy, Terrain, Troops, Civilian, Time 평가 체계
                            </p>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                            <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800" title="임무 부합성 (가중치: 20%)">
                                <div className="text-[10px] text-gray-500 dark:text-gray-400 mb-1">🎯 임무</div>
                                <div className="text-sm font-bold text-blue-600 dark:text-blue-400">
                                    {coa.mett_c_scores.mission_score !== undefined ? coa.mett_c_scores.mission_score.toFixed(3) : 'N/A'}
                                </div>
                            </div>
                            <div className="p-2 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800" title="적군 대응 능력 (가중치: 20%)">
                                <div className="text-[10px] text-gray-500 dark:text-gray-400 mb-1">⚠️ 적군</div>
                                <div className="text-sm font-bold text-red-600 dark:text-red-400">
                                    {coa.mett_c_scores.enemy_score !== undefined ? coa.mett_c_scores.enemy_score.toFixed(3) : 'N/A'}
                                </div>
                            </div>
                            <div className="p-2 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-800" title="지형 적합성 (가중치: 15%)">
                                <div className="text-[10px] text-gray-500 dark:text-gray-400 mb-1">🌍 지형</div>
                                <div className="text-sm font-bold text-green-600 dark:text-green-400">
                                    {coa.mett_c_scores.terrain_score !== undefined ? coa.mett_c_scores.terrain_score.toFixed(3) : 'N/A'}
                                </div>
                            </div>
                            <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded border border-purple-200 dark:border-purple-800" title="부대 능력 (가중치: 15%)">
                                <div className="text-[10px] text-gray-500 dark:text-gray-400 mb-1">👥 부대</div>
                                <div className="text-sm font-bold text-purple-600 dark:text-purple-400">
                                    {coa.mett_c_scores.troops_score !== undefined ? coa.mett_c_scores.troops_score.toFixed(3) : 'N/A'}
                                </div>
                            </div>
                            <div className={`p-2 rounded border ${(coa.mett_c_scores.civilian_score !== undefined && coa.mett_c_scores.civilian_score < 0.3)
                                    ? 'bg-red-100 dark:bg-red-900/40 border-red-500 dark:border-red-600'
                                    : 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
                                }`} title="민간인 보호 (가중치: 15%)">
                                <div className="text-[10px] text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
                                    🏘️ 민간인
                                    {(coa.mett_c_scores.civilian_score !== undefined && coa.mett_c_scores.civilian_score < 0.3) && (
                                        <AlertTriangle className="w-3 h-3 text-red-600 dark:text-red-400" />
                                    )}
                                </div>
                                <div className="text-sm font-bold text-yellow-600 dark:text-yellow-400">
                                    {coa.mett_c_scores.civilian_score !== undefined ? coa.mett_c_scores.civilian_score.toFixed(3) : 'N/A'}
                                </div>
                            </div>
                            <div className={`p-2 rounded border ${(coa.mett_c_scores.time_score !== undefined && (coa.mett_c_scores.time_score === 0.0 || coa.mett_c_scores.time_score < 0.5))
                                    ? 'bg-red-100 dark:bg-red-900/40 border-red-500 dark:border-red-600'
                                    : 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800'
                                }`} title="시간 제약 준수 (가중치: 15%)">
                                <div className="text-[10px] text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
                                    ⏰ 시간
                                    {(coa.mett_c_scores.time_score !== undefined && (coa.mett_c_scores.time_score === 0.0 || coa.mett_c_scores.time_score < 0.5)) && (
                                        <AlertTriangle className="w-3 h-3 text-red-600 dark:text-red-400" />
                                    )}
                                </div>
                                <div className="text-sm font-bold text-indigo-600 dark:text-indigo-400">
                                    {coa.mett_c_scores.time_score !== undefined ? coa.mett_c_scores.time_score.toFixed(3) : 'N/A'}
                                </div>
                            </div>
                        </div>
                        {coa.mett_c_scores.total_score !== undefined && (
                            <div className="mt-2 p-2 bg-orange-100 dark:bg-orange-900/30 rounded border border-orange-300 dark:border-orange-700">
                                <div className="flex items-center justify-between">
                                    <span className="text-[10px] font-semibold text-gray-700 dark:text-gray-300">METT-C 종합</span>
                                    <span className="text-sm font-bold text-orange-600 dark:text-orange-400">
                                        {coa.mett_c_scores.total_score.toFixed(3)}
                                    </span>
                                </div>
                            </div>
                        )}
                    </section>
                )}

                {/* 선정 사유 */}
                {coa.reasoning?.justification && (
                    <section>
                        <div className="flex items-center gap-2 mb-2">
                            <Shield className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                            <h4 className="font-bold text-sm text-gray-900 dark:text-white">방책 선정 사유</h4>
                        </div>
                        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border-l-4 border-blue-500">
                            <p className="text-xs text-gray-700 dark:text-gray-300">
                                {coa.reasoning.justification}
                            </p>
                        </div>
                    </section>
                )}

                {/* 추론 근거 */}
                {coa.reasoning && (
                    <section>
                        <div className="flex items-center gap-2 mb-2">
                            <Brain className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                            <h4 className="font-bold text-sm text-gray-900 dark:text-white">추론 근거</h4>
                        </div>
                        <ReasoningExplanationPanel
                            recommendation={coa}
                            approachMode="threat_centered"
                        />
                    </section>
                )}

                {/* 교범 참조 */}
                {coa.doctrine_references && coa.doctrine_references.length > 0 && (
                    <section>
                        <div className="flex items-center gap-2 mb-2">
                            <FileText className="w-4 h-4 text-green-600 dark:text-green-400" />
                            <h4 className="font-bold text-sm text-gray-900 dark:text-white">교범 참조</h4>
                        </div>
                        <DoctrineReferencePanel
                            references={coa.doctrine_references}
                        />
                    </section>
                )}

                {/* 점수 세부 분석 */}
                {coa.score_breakdown && (
                    <section>
                        <div className="flex items-center gap-2 mb-2">
                            <TrendingUp className="w-4 h-4 text-orange-600 dark:text-orange-400" />
                            <h4 className="font-bold text-sm text-gray-900 dark:text-white">점수 세부 분석</h4>
                        </div>
                        <div className="space-y-2">
                            {coa.combat_power_score !== undefined && (
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-gray-600 dark:text-gray-400">전투력</span>
                                    <span className="font-semibold text-blue-600">
                                        {(coa.combat_power_score * 100).toFixed(1)}%
                                    </span>
                                </div>
                            )}
                            {coa.mobility_score !== undefined && (
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-gray-600 dark:text-gray-400">기동성</span>
                                    <span className="font-semibold text-green-600">
                                        {(coa.mobility_score * 100).toFixed(1)}%
                                    </span>
                                </div>
                            )}
                            {coa.constraint_score !== undefined && (
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-gray-600 dark:text-gray-400">제약조건</span>
                                    <span className="font-semibold text-yellow-600">
                                        {(coa.constraint_score * 100).toFixed(1)}%
                                    </span>
                                </div>
                            )}
                            {coa.threat_response_score !== undefined && (
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-gray-600 dark:text-gray-400">위협대응</span>
                                    <span className="font-semibold text-red-600">
                                        {(coa.threat_response_score * 100).toFixed(1)}%
                                    </span>
                                </div>
                            )}
                        </div>
                    </section>
                )}
            </div>
        </div>
    );
};
