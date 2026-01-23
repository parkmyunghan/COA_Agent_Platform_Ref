import React, { useEffect, useState, useRef } from 'react';
import { X, Target, Brain, FileCheck, Shield, Award, TrendingUp, Info, MapPin, Clock, Users, AlertTriangle, GripVertical } from 'lucide-react';
import type { COASummary } from '../types/schema';
import { TaskActionList } from './analysis/TaskActionList';
import { ReasoningTraceView } from './analysis/ReasoningTraceView';
import { ReasoningExplanationPanel } from './ReasoningExplanationPanel';
import { ChainVisualizer } from './ChainVisualizer';
import { DoctrineReferencePanel } from './DoctrineReferencePanel';
import { COAExecutionPlanPanel } from './COAExecutionPlanPanel';
import { ReportGenerator } from './ReportGenerator';

interface COADetailModalProps {
    coa: COASummary | null;
    onClose: () => void;
    anchorElement?: HTMLElement | null; // 플로팅 카드 요소 (초기 위치 계산용)
    situationInfo?: any; // 상황 정보 (자원 가용성 등)
}

export const COADetailModal: React.FC<COADetailModalProps> = ({ coa, onClose, anchorElement, situationInfo }) => {
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
    const containerRef = useRef<HTMLDivElement>(null);
    
    // 초기 위치 계산
    useEffect(() => {
        if (!coa) return;
        
        const calculateInitialPosition = () => {
            const viewportWidth = window.innerWidth;
            const viewportHeight = window.innerHeight;
            const modalWidth = 896; // max-w-4xl = 56rem = 896px
            
            if (anchorElement) {
                // 플로팅 카드 우측에 배치
                const rect = anchorElement.getBoundingClientRect();
                const gap = 16;
                let left = rect.right + gap;
                
                // 화면 오른쪽을 벗어나면 플로팅 카드 왼쪽에 배치
                if (left + modalWidth > viewportWidth - 16) {
                    left = rect.left - modalWidth - gap;
                    if (left < 16) {
                        left = Math.max(16, (viewportWidth - modalWidth) / 2);
                    }
                }
                
                let top = rect.top;
                if (top < 16) top = 16;
                if (top + viewportHeight * 0.9 > viewportHeight - 16) {
                    top = Math.max(16, viewportHeight - viewportHeight * 0.9 - 16);
                }
                
                setPosition({ x: left, y: top });
            } else {
                // 중앙 배치
                setPosition({
                    x: (viewportWidth - modalWidth) / 2,
                    y: (viewportHeight - viewportHeight * 0.9) / 2
                });
            }
        };
        
        calculateInitialPosition();
        
        // 윈도우 리사이즈 시 위치 재계산
        const handleResize = () => {
            calculateInitialPosition();
        };
        
        window.addEventListener('resize', handleResize);
        return () => {
            window.removeEventListener('resize', handleResize);
        };
    }, [coa, anchorElement]);
    
    // 드래그 핸들러
    const handleHeaderMouseDown = (e: React.MouseEvent) => {
        // 버튼 클릭은 드래그 방지
        const target = e.target as HTMLElement;
        if (target.closest('button') || target.tagName === 'BUTTON' || target.closest('svg') || target.closest('path')) {
            return;
        }
        setIsDragging(true);
        setDragStart({
            x: e.clientX - position.x,
            y: e.clientY - position.y
        });
        e.preventDefault();
    };

    useEffect(() => {
        if (!isDragging) return;

        const handleMouseMove = (e: MouseEvent) => {
            setPosition({
                x: e.clientX - dragStart.x,
                y: e.clientY - dragStart.y
            });
        };

        const handleMouseUp = () => {
            setIsDragging(false);
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);

        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDragging, dragStart, position]);
    
    // ESC 키로 창 닫기
    useEffect(() => {
        if (!coa) return;
        
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                onClose();
            }
        };
        
        document.addEventListener('keydown', handleEscape);
        return () => {
            document.removeEventListener('keydown', handleEscape);
        };
    }, [coa, onClose]);
    
    if (!coa) return null;

    return (
        <div 
            className="fixed inset-0 bg-black/30 z-50 pointer-events-none"
            onClick={(e) => {
                // 배경 클릭 시 창 닫기
                if (e.target === e.currentTarget) {
                    onClose();
                }
            }}
        >
            <div 
                ref={containerRef}
                className="bg-white dark:bg-zinc-900 rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col border border-gray-200 dark:border-zinc-700 fixed pointer-events-auto"
                style={{
                    top: `${position.y}px`,
                    left: `${position.x}px`,
                    maxWidth: '896px',
                    maxHeight: '90vh',
                    cursor: isDragging ? 'grabbing' : 'default',
                    userSelect: 'none'
                }}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header - 드래그 핸들 */}
                <div 
                    className="p-6 border-b border-gray-200 dark:border-zinc-700 bg-gradient-to-r from-blue-600 to-indigo-600 cursor-move select-none"
                    onMouseDown={handleHeaderMouseDown}
                >
                    <div className="flex justify-between items-start">
                        <div className="flex items-center gap-2 flex-1">
                            <GripVertical className="w-4 h-4 text-white/60" />
                            <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                    <span className="inline-block px-3 py-1 rounded-full text-xs font-bold bg-white/20 text-white">
                                        Rank {coa.rank}
                                    </span>
                                    <h2 className="text-2xl font-bold text-white">{coa.coa_name}</h2>
                                </div>
                                <p className="text-blue-100 text-sm">{coa.description || '방책 설명 없음'}</p>
                            </div>
                        </div>
                        <button
                            onMouseDown={(e) => {
                                e.stopPropagation(); // 드래그 방지
                            }}
                            onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                console.log('X 버튼 클릭 - onClose 호출');
                                if (onClose && typeof onClose === 'function') {
                                    onClose();
                                } else {
                                    console.error('onClose가 함수가 아닙니다:', onClose);
                                }
                            }}
                            className="ml-4 text-white/80 hover:text-white transition-colors p-2 hover:bg-white/10 rounded-lg flex-shrink-0 z-50 relative"
                            type="button"
                            aria-label="닫기"
                        >
                            <X className="w-6 h-6" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {/* Score Summary */}
                    <section>
                        <div className="flex items-center gap-2 mb-4">
                            <Target className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                            <h3 className="text-lg font-bold text-gray-900 dark:text-white">종합 점수</h3>
                        </div>
                        <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border-l-4 border-blue-500">
                            <p className="text-xs text-gray-700 dark:text-gray-300">
                                <strong className="font-semibold">NATO 교범 AJP-5 기준:</strong> 적합성(Suitability), 타당성(Feasibility), 수용성(Acceptability)은 
                                COA 평가의 표준 프레임워크입니다. 이 세 항목은 총합점수와는 별개의 평가 기준이며, 
                                총합점수는 COAScorer breakdown의 가중합으로 계산됩니다.
                            </p>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <ScoreCard label="총점" value={coa.total_score !== undefined ? coa.total_score.toFixed(1) : 'N/A'} color="indigo" tooltip="COAScorer breakdown의 가중합으로 계산된 종합 점수" />
                            <ScoreCard label="적합성" value={coa.suitability_score?.toFixed(1) || 'N/A'} color="blue" tooltip="COA가 임무를 달성하고 계획 지침을 준수하는지 평가 (NATO AJP-5)" />
                            <ScoreCard label="타당성" value={coa.feasibility_score?.toFixed(1) || 'N/A'} color="green" tooltip="시간, 공간, 자원이 가용하고 작전 환경에 적합한지 평가 (NATO AJP-5)" />
                            <ScoreCard label="수용성" value={coa.acceptability_score?.toFixed(1) || 'N/A'} color="purple" tooltip="예상 성과가 예상 비용(전력, 자원, 사상자, 위험 등)을 정당화하는지 평가 (NATO AJP-5)" />
                        </div>
                    </section>

                    {/* METT-C 점수 */}
                    {coa.mett_c_scores && (
                        <section>
                            <div className="flex items-center gap-2 mb-4">
                                <MapPin className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                                <h3 className="text-lg font-bold text-gray-900 dark:text-white">METT-C 종합 평가</h3>
                            </div>
                            <div className="mb-3 p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg border-l-4 border-orange-500">
                                <p className="text-xs text-gray-700 dark:text-gray-300">
                                    <strong>METT-C 프레임워크:</strong> Mission(임무), Enemy(적군), Terrain(지형), Troops(부대), Civilian(민간인), Time(시간)을 평가하는 별도 평가 체계입니다.
                                    적합성/타당성/수용성과는 다른 관점에서 COA를 평가합니다.
                                </p>
                            </div>
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                                <METTCScoreCard 
                                    label="🎯 임무" 
                                    value={coa.mett_c_scores.mission_score} 
                                    color="blue"
                                    tooltip="임무 부합성 (가중치: 20%)"
                                />
                                <METTCScoreCard 
                                    label="⚠️ 적군" 
                                    value={coa.mett_c_scores.enemy_score} 
                                    color="red"
                                    tooltip="적군 대응 능력 (가중치: 20%)"
                                />
                                <METTCScoreCard 
                                    label="🌍 지형" 
                                    value={coa.mett_c_scores.terrain_score} 
                                    color="green"
                                    tooltip="지형 적합성 (가중치: 15%)"
                                />
                                <METTCScoreCard 
                                    label="👥 부대" 
                                    value={coa.mett_c_scores.troops_score} 
                                    color="purple"
                                    tooltip="부대 능력 (가중치: 15%)"
                                />
                                <METTCScoreCard 
                                    label="🏘️ 민간인" 
                                    value={coa.mett_c_scores.civilian_score} 
                                    color="yellow"
                                    tooltip="민간인 보호 (가중치: 15%)"
                                    isWarning={coa.mett_c_scores.civilian_score !== undefined && coa.mett_c_scores.civilian_score < 0.3}
                                />
                                <METTCScoreCard 
                                    label="⏰ 시간" 
                                    value={coa.mett_c_scores.time_score} 
                                    color="indigo"
                                    tooltip="시간 제약 준수 (가중치: 15%)"
                                    isWarning={coa.mett_c_scores.time_score !== undefined && (coa.mett_c_scores.time_score === 0.0 || coa.mett_c_scores.time_score < 0.5)}
                                />
                            </div>
                            {coa.mett_c_scores.total_score !== undefined && (
                                <div className="mt-4 p-4 bg-orange-100 dark:bg-orange-900/30 rounded-lg border border-orange-300 dark:border-orange-700">
                                    <div className="flex items-center justify-between">
                                        <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">METT-C 종합 점수</span>
                                        <span className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                                            {coa.mett_c_scores.total_score.toFixed(3)}
                                        </span>
                                    </div>
                                </div>
                            )}
                        </section>
                    )}

                    {/* 상황판단 */}
                    {coa.reasoning?.situation_assessment && (
                        <section>
                            <div className="flex items-center gap-2 mb-4">
                                <Target className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                                <h3 className="text-lg font-bold text-gray-900 dark:text-white">상황판단</h3>
                            </div>
                            <div className="p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border-l-4 border-indigo-500">
                                <p className="text-sm text-gray-700 dark:text-gray-300">
                                    {coa.reasoning.situation_assessment}
                                </p>
                            </div>
                        </section>
                    )}

                    {/* 선정 사유 */}
                    {coa.reasoning?.justification && (
                        <section>
                            <div className="flex items-center gap-2 mb-4">
                                <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                                <h3 className="text-lg font-bold text-gray-900 dark:text-white">방책 선정 사유</h3>
                            </div>
                            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border-l-4 border-blue-500">
                                <p className="text-sm text-gray-700 dark:text-gray-300">
                                    {coa.reasoning.justification}
                                </p>
                            </div>
                        </section>
                    )}

                    {/* 부대 운용 근거 */}
                    {coa.reasoning?.unit_rationale && (
                        <section>
                            <div className="flex items-center gap-2 mb-4">
                                <Info className="w-5 h-5 text-green-600 dark:text-green-400" />
                                <h3 className="text-lg font-bold text-gray-900 dark:text-white">부대 운용 근거</h3>
                            </div>
                            <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border-l-4 border-green-500">
                                <p className="text-sm text-gray-700 dark:text-gray-300">
                                    {coa.reasoning.unit_rationale}
                                </p>
                            </div>
                        </section>
                    )}

                    {/* 시스템 탐색 과정 */}
                    {coa.reasoning?.system_search_path && (
                        <section>
                            <div className="flex items-center gap-2 mb-4">
                                <TrendingUp className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                                <h3 className="text-lg font-bold text-gray-900 dark:text-white">시스템 탐색 과정</h3>
                            </div>
                            <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border-l-4 border-purple-500">
                                <p className="text-xs text-gray-600 dark:text-gray-400 italic">
                                    {coa.reasoning.system_search_path}
                                </p>
                            </div>
                        </section>
                    )}

                    {/* Reasoning Explanation */}
                    <section>
                        <ReasoningExplanationPanel 
                            recommendation={coa}
                            approachMode="threat_centered"
                        />
                    </section>

                    {/* Chain Visualizer */}
                    {(coa.chain_info || (coa as any).chain_info_details) && (
                        <section>
                            <div className="flex items-center gap-2 mb-4">
                                <Brain className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                                <h3 className="text-lg font-bold text-gray-900 dark:text-white">전략 연계</h3>
                            </div>
                            <ChainVisualizer chainInfo={(coa as any).chain_info_details || coa.chain_info} />
                        </section>
                    )}

                    {/* Doctrine References */}
                    <section>
                        <DoctrineReferencePanel recommendation={coa} />
                    </section>

                    {/* Execution Plan */}
                    <section>
                        <COAExecutionPlanPanel
                            recommendation={coa}
                            situationInfo={situationInfo}
                            approachMode="threat_centered"
                        />
                    </section>

                    {/* Report Generator */}
                    <section className="px-0">
                        <ReportGenerator
                            agentName="COA Recommendation Agent"
                            summary={coa.description}
                            coaRecommendations={[coa]}
                        />
                    </section>
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-gray-200 dark:border-zinc-700 bg-gray-50 dark:bg-zinc-800/50">
                    <div className="flex justify-end gap-3">
                        <button
                            onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                console.log('닫기 버튼 클릭 - onClose 호출');
                                if (onClose && typeof onClose === 'function') {
                                    onClose();
                                } else {
                                    console.error('onClose가 함수가 아닙니다:', onClose);
                                }
                            }}
                            type="button"
                            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-zinc-700 dark:hover:bg-zinc-600 text-gray-900 dark:text-white rounded-lg font-medium transition-colors z-50 relative"
                            aria-label="닫기"
                        >
                            닫기
                        </button>
                        <button
                            className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-lg font-medium transition-all"
                        >
                            방책 실행
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

// Helper component for score cards
const ScoreCard: React.FC<{ label: string; value: string; color: string; tooltip?: string }> = ({ label, value, color, tooltip }) => {
    const colorClasses: Record<string, string> = {
        indigo: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-700',
        blue: 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-700',
        green: 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 border-green-200 dark:border-green-700',
        purple: 'bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-700',
    };

    return (
        <div className={`p-4 rounded-lg border ${colorClasses[color] || colorClasses.indigo} relative group`} title={tooltip}>
            <div className="text-xs font-medium opacity-70 mb-1 flex items-center gap-1">
                {label}
                {tooltip && (
                    <Info className="w-3 h-3 opacity-50 group-hover:opacity-100 transition-opacity" />
                )}
            </div>
            <div className="text-2xl font-bold">{value}</div>
        </div>
    );
};

// Helper component for METT-C score cards
const METTCScoreCard: React.FC<{ 
    label: string; 
    value?: number; 
    color: string; 
    tooltip?: string;
    isWarning?: boolean;
}> = ({ label, value, color, tooltip, isWarning }) => {
    const colorClasses: Record<string, string> = {
        blue: 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-700',
        red: 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border-red-200 dark:border-red-700',
        green: 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 border-green-200 dark:border-green-700',
        purple: 'bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-700',
        yellow: 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300 border-yellow-200 dark:border-yellow-700',
        indigo: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-700',
    };

    const warningClass = isWarning ? 'border-red-500 dark:border-red-600 bg-red-100 dark:bg-red-900/40' : '';

    return (
        <div className={`p-3 rounded-lg border ${colorClasses[color] || colorClasses.blue} ${warningClass} relative group`} title={tooltip}>
            <div className="text-xs font-medium opacity-70 mb-1 flex items-center gap-1">
                {label}
                {isWarning && <AlertTriangle className="w-3 h-3 text-red-600 dark:text-red-400" />}
                {tooltip && (
                    <Info className="w-3 h-3 opacity-50 group-hover:opacity-100 transition-opacity" />
                )}
            </div>
            <div className="text-xl font-bold">
                {value !== undefined ? value.toFixed(3) : 'N/A'}
            </div>
        </div>
    );
};
