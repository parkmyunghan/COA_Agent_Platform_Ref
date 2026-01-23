import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import type { COASummary } from '../types/schema';

interface ReasoningExplanationPanelProps {
    recommendation: COASummary;
    approachMode?: 'threat_centered' | 'mission_centered';
}

export const ReasoningExplanationPanel: React.FC<ReasoningExplanationPanelProps> = ({
    recommendation,
    approachMode = 'threat_centered'
}) => {
    if (!recommendation) {
        return (
            <div className="p-4 bg-gray-50 dark:bg-zinc-800 rounded-lg text-sm text-gray-500 dark:text-gray-400">
                추천 근거 데이터가 없습니다.
            </div>
        );
    }

    const scoreBreakdown = recommendation.score_breakdown || {};
    const reasoning = scoreBreakdown.reasoning || [];
    const reasoningTrace = recommendation.reasoning_trace || [];
    const hasReasoningData = reasoning.length > 0;

    const headerText = approachMode === 'mission_centered' 
        ? '🎯 임무수행 상세 분석'
        : '🔍 추천 근거 상세 분석';

    return (
        <Card className="border-gray-200 dark:border-zinc-700">
            <CardHeader>
                <CardTitle className="text-sm font-semibold">{headerText}</CardTitle>
            </CardHeader>
            <CardContent>
                <Tabs defaultValue={hasReasoningData ? "score" : "references"} className="w-full">
                    <TabsList className="grid w-full grid-cols-3">
                        {hasReasoningData && (
                            <>
                                <TabsTrigger value="score">📊 점수 요인 분석</TabsTrigger>
                                <TabsTrigger value="details">📝 상세 설명</TabsTrigger>
                            </>
                        )}
                        <TabsTrigger value="references">📚 참고 자료</TabsTrigger>
                        {reasoningTrace.length > 0 && (
                            <TabsTrigger value="ontology">🌱 온톨로지 추론</TabsTrigger>
                        )}
                    </TabsList>

                    {hasReasoningData && (
                        <>
                            <TabsContent value="score" className="mt-4">
                                <ScoreChart reasoning={reasoning} approachMode={approachMode} />
                            </TabsContent>
                            <TabsContent value="details" className="mt-4">
                                <DetailedExplanation reasoning={reasoning} approachMode={approachMode} />
                            </TabsContent>
                        </>
                    )}

                    <TabsContent value="references" className="mt-4">
                        <DoctrineReferences recommendation={recommendation} />
                    </TabsContent>

                    {reasoningTrace.length > 0 && (
                        <TabsContent value="ontology" className="mt-4">
                            <OntologyReasoning trace={reasoningTrace} />
                        </TabsContent>
                    )}
                </Tabs>
            </CardContent>
        </Card>
    );
};

// 점수 요인 분석 차트
const ScoreChart: React.FC<{ reasoning: any[]; approachMode: string }> = ({ reasoning, approachMode }) => {
    const labelMap = approachMode === 'mission_centered' ? {
        'threat': '임무 수행',
        'resources': '자원 효율',
        'assets': '자산 능력',
        'environment': '환경 적합',
        'historical': '과거 사례',
        'chain': '연계 작전'
    } : {
        'threat': '위협 대응',
        'resources': '자원 효율',
        'assets': '자산 능력',
        'environment': '환경 적합',
        'historical': '과거 사례',
        'chain': '연계 작전'
    };

    const factors = reasoning.map(item => {
        const factorKey = item.factor || 'Unknown';
        return labelMap[factorKey as keyof typeof labelMap] || factorKey;
    });
    const scores = reasoning.map(item => (item.score || 0) * 100);
    const weights = reasoning.map(item => (item.weight || 0) * 100);

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
                {reasoning.map((item, idx) => {
                    const factorKey = item.factor || 'Unknown';
                    const label = labelMap[factorKey as keyof typeof labelMap] || factorKey;
                    const score = (item.score || 0) * 100;
                    const weight = (item.weight || 0) * 100;
                    
                    return (
                        <div key={idx} className="p-3 bg-gray-50 dark:bg-zinc-800 rounded-lg">
                            <div className="flex justify-between items-center mb-2">
                                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
                                <span className="text-xs text-gray-500 dark:text-gray-400">가중치: {weight.toFixed(1)}%</span>
                            </div>
                            <div className="w-full bg-gray-200 dark:bg-zinc-700 rounded-full h-2 mb-1">
                                <div
                                    className="bg-blue-600 h-2 rounded-full transition-all"
                                    style={{ width: `${score}%` }}
                                />
                            </div>
                            <div className="text-xs text-gray-600 dark:text-gray-400">
                                점수: {score.toFixed(1)}% | 가중 점수: {((item.weighted_score || 0) * 100).toFixed(1)}%
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

// 상세 설명
const DetailedExplanation: React.FC<{ reasoning: any[]; approachMode: string }> = ({ reasoning, approachMode }) => {
    return (
        <div className="space-y-3">
            {reasoning.map((item, idx) => (
                <div key={idx} className="p-3 bg-gray-50 dark:bg-zinc-800 rounded-lg border-l-4 border-blue-500">
                    <div className="font-semibold text-sm text-gray-900 dark:text-white mb-1">
                        {item.factor || 'Unknown'}
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                        {item.reason || '상세 설명 없음'}
                    </div>
                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-500">
                        점수: {(item.score || 0).toFixed(3)} | 가중치: {(item.weight || 0).toFixed(3)} | 가중 점수: {(item.weighted_score || 0).toFixed(3)}
                    </div>
                </div>
            ))}
        </div>
    );
};

// 온톨로지 추론
const OntologyReasoning: React.FC<{ trace: string[] | any[] }> = ({ trace }) => {
    // trace가 비어있거나 null인 경우 처리
    if (!trace || trace.length === 0) {
        return (
            <div className="p-4 bg-gray-50 dark:bg-zinc-800 rounded-lg text-sm text-gray-500 dark:text-gray-400">
                온톨로지 추론 경로 데이터가 없습니다.
            </div>
        );
    }

    return (
        <div className="space-y-3">
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <p className="text-sm text-blue-700 dark:text-blue-300">
                    이 방책은 지식그래프(Ontology) 상의 관계와 개체 속성을 기반으로 자동 도출되었습니다.
                </p>
            </div>
            {trace.map((step, idx) => {
                // step이 객체인 경우 문자열로 변환
                let stepContent: string;
                if (typeof step === 'string') {
                    stepContent = step;
                } else if (typeof step === 'object' && step !== null) {
                    // 객체인 경우 from, to, type 등의 정보를 문자열로 변환
                    if (step.from && step.to && step.type) {
                        stepContent = `${step.from} → ${step.to} (${step.type})`;
                    } else if (step.description) {
                        stepContent = step.description;
                    } else if (step.reasoning) {
                        stepContent = step.reasoning;
                    } else if (step.step) {
                        stepContent = step.step;
                    } else {
                        stepContent = JSON.stringify(step);
                    }
                } else {
                    stepContent = String(step);
                }

                return (
                    <div key={idx} className="space-y-2">
                        <div className="font-semibold text-sm text-gray-900 dark:text-white">
                            Step {idx + 1}
                        </div>
                        <div className="p-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded text-sm text-green-700 dark:text-green-300">
                            {stepContent}
                        </div>
                        {idx < trace.length - 1 && (
                            <div className="text-center text-gray-400 dark:text-gray-600">↓</div>
                        )}
                    </div>
                );
            })}
        </div>
    );
};

// 교리 참조 (임시 - DoctrineReferencePanel에서 구현)
const DoctrineReferences: React.FC<{ recommendation: COASummary }> = ({ recommendation }) => {
    const doctrineRefs = recommendation.doctrine_references || [];
    
    if (!doctrineRefs || doctrineRefs.length === 0) {
        return (
            <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                <p className="text-sm text-yellow-700 dark:text-yellow-300">
                    ⚠️ 참고 자료를 불러올 수 없습니다. 데이터 연결 상태를 확인해주세요.
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {doctrineRefs.map((ref: any, idx: number) => (
                <div key={idx} className="p-3 bg-gray-50 dark:bg-zinc-800 rounded-lg">
                    <div className="font-semibold text-sm text-gray-900 dark:text-white mb-1">
                        {ref.title || ref.name || `참고 자료 ${idx + 1}`}
                    </div>
                    {ref.description && (
                        <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                            {ref.description}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};
