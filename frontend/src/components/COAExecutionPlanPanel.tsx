import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import type { COASummary } from '../types/schema';

interface ExecutionStep {
    step: string;
    content: string;
    duration: string;
    responsible: string;
    priority: 'high' | 'medium' | 'low';
}

interface COAExecutionPlanPanelProps {
    recommendation: COASummary;
    situationInfo?: any;
    approachMode?: 'threat_centered' | 'mission_centered';
}

export const COAExecutionPlanPanel: React.FC<COAExecutionPlanPanelProps> = ({
    recommendation,
    situationInfo,
    approachMode = 'threat_centered'
}) => {
    if (!recommendation) {
        return (
            <div className="p-4 bg-gray-50 dark:bg-zinc-800 rounded-lg text-sm text-gray-500 dark:text-gray-400">
                추천된 방책이 없습니다.
            </div>
        );
    }

    const headerText = approachMode === 'mission_centered' ? '📋 임무 수행 계획' : '📋 방책 실행 계획';
    const executionSteps = generateExecutionSteps(recommendation, approachMode);
    const requiredResources = extractRequiredResources(recommendation, situationInfo);
    const riskAssessment = assessRisks(recommendation, approachMode);
    const timeEstimate = estimateExecutionTime(executionSteps);

    return (
        <div className="space-y-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{headerText}</h3>

            {/* 부대 운용 근거 */}
            {recommendation.reasoning?.unit_rationale && (
                <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                    <p className="text-sm text-blue-700 dark:text-blue-300">
                        <span className="font-semibold">🛡️ 부대 운용 근거:</span> {recommendation.reasoning.unit_rationale}
                    </p>
                </div>
            )}

            {/* 단계별 실행 계획 */}
            <Card className="border-gray-200 dark:border-zinc-700">
                <CardHeader>
                    <CardTitle className="text-sm font-semibold">
                        {approachMode === 'mission_centered' ? '📝 단계별 임무 수행 계획' : '📝 단계별 실행 계획'}
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {executionSteps.map((step, idx) => (
                        <div key={idx} className="border-l-4 border-blue-500 pl-4 py-2">
                            <div className="flex items-start justify-between mb-2">
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                        {step.priority === 'high' && <span className="text-red-500">🔴</span>}
                                        {step.priority === 'medium' && <span className="text-yellow-500">🟡</span>}
                                        {step.priority === 'low' && <span className="text-green-500">🟢</span>}
                                        <span className="font-semibold text-gray-900 dark:text-white">{step.step}</span>
                                    </div>
                                    <p className="text-sm text-gray-600 dark:text-gray-400">{step.content}</p>
                                </div>
                                <div className="ml-4 text-right">
                                    <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">
                                        소요시간
                                    </div>
                                    <div className="text-sm font-bold text-gray-900 dark:text-white">
                                        {step.duration}
                                    </div>
                                </div>
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400">
                                담당: {step.responsible}
                            </div>
                        </div>
                    ))}
                </CardContent>
            </Card>

            {/* 필요 자원 목록 */}
            <Card className="border-gray-200 dark:border-zinc-700">
                <CardHeader>
                    <CardTitle className="text-sm font-semibold">📦 필요 자원 목록</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-3">
                        {Object.entries(requiredResources).map(([type, info]: [string, any]) => (
                            <div key={type} className="flex justify-between items-center p-2 bg-gray-50 dark:bg-zinc-800 rounded">
                                <div className="flex-1">
                                    <div className="font-semibold text-sm text-gray-900 dark:text-white">{type}</div>
                                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                        필요량: {info.required} | 가용량: {info.available}
                                    </div>
                                </div>
                                <div className={`px-2 py-1 rounded text-xs font-semibold ${
                                    info.status === 'sufficient' 
                                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                        : info.status === 'partial'
                                        ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                                        : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                }`}>
                                    {info.status === 'sufficient' ? '충분' : info.status === 'partial' ? '부분' : '부족'}
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* 위험 요소 및 대응 방안 */}
            <Card className="border-gray-200 dark:border-zinc-700">
                <CardHeader>
                    <CardTitle className="text-sm font-semibold">⚠️ 위험 요소 및 대응 방안</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                    {riskAssessment.map((risk, idx) => (
                        <div key={idx} className={`p-3 rounded-lg border ${
                            risk.level === 'high'
                                ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                                : risk.level === 'medium'
                                ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
                                : 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                        }`}>
                            <div className="flex items-center gap-2 mb-2">
                                {risk.level === 'high' && <span className="text-red-500">🔴</span>}
                                {risk.level === 'medium' && <span className="text-yellow-500">🟡</span>}
                                {risk.level === 'low' && <span className="text-green-500">🟢</span>}
                                <span className="font-semibold text-sm text-gray-900 dark:text-white">
                                    {risk.element} (위험도: {risk.level === 'high' ? '높음' : risk.level === 'medium' ? '중간' : '낮음'})
                                </span>
                            </div>
                            <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                                <span className="font-semibold">설명:</span> {risk.description}
                            </p>
                            <p className="text-xs text-gray-600 dark:text-gray-400">
                                <span className="font-semibold">대응 방안:</span> {risk.response}
                            </p>
                        </div>
                    ))}
                </CardContent>
            </Card>

            {/* 예상 소요 시간 */}
            <Card className="border-gray-200 dark:border-zinc-700">
                <CardHeader>
                    <CardTitle className="text-sm font-semibold">⏱️ 예상 소요 시간</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-3 gap-4">
                        <div className="text-center">
                            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">총 소요 시간</div>
                            <div className="text-lg font-bold text-gray-900 dark:text-white">{timeEstimate.total}</div>
                        </div>
                        <div className="text-center">
                            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">예상 시작</div>
                            <div className="text-sm font-semibold text-gray-900 dark:text-white">{timeEstimate.start}</div>
                        </div>
                        <div className="text-center">
                            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">예상 완료</div>
                            <div className="text-sm font-semibold text-gray-900 dark:text-white">{timeEstimate.end}</div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* 승인 워크플로우 */}
            <Card className="border-gray-200 dark:border-zinc-700">
                <CardHeader>
                    <CardTitle className="text-sm font-semibold">✅ 방책 승인</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                    <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                        <p className="text-xs text-blue-700 dark:text-blue-300">
                            💡 <span className="font-semibold">실전 적용 시:</span> 방책 승인 워크플로우가 여기에 표시됩니다.
                        </p>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                        <Button variant="outline" size="sm" className="text-xs">
                            📋 방책 검토 요청
                        </Button>
                        <Button size="sm" className="text-xs">
                            ✅ 방책 승인
                        </Button>
                        <Button variant="destructive" size="sm" className="text-xs">
                            ❌ 방책 반려
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

function generateExecutionSteps(
    recommendation: COASummary,
    approachMode: 'threat_centered' | 'mission_centered'
): ExecutionStep[] {
    const coaName = recommendation.coa_name || '';

    const baseSteps: ExecutionStep[] = [
        {
            step: '1. 초기 배치',
            content: approachMode === 'mission_centered'
                ? '임무 수행을 위한 초기 부대 및 자원 배치'
                : '방책 실행을 위한 초기 부대 및 자원 배치',
            duration: '30분',
            responsible: '작전 계획 담당',
            priority: 'high'
        },
        {
            step: '2. 자원 배치',
            content: '필요한 자원(인력, 장비, 보급품) 배치',
            duration: '1시간',
            responsible: '보급 담당',
            priority: 'high'
        },
        {
            step: '3. 통신망 구축',
            content: '작전 통신망 구축 및 연락 체계 확립',
            duration: '30분',
            responsible: '통신 담당',
            priority: 'medium'
        },
        {
            step: approachMode === 'mission_centered' ? '4. 작전 수행' : '4. 방책 실행',
            content: approachMode === 'mission_centered'
                ? `${coaName} 임무 수행`
                : `${coaName} 방책 본격 실행`,
            duration: '2시간',
            responsible: '작전 담당',
            priority: 'high'
        },
        {
            step: '5. 모니터링 및 조정',
            content: '실행 상황 모니터링 및 필요시 조정',
            duration: '지속',
            responsible: '지휘부',
            priority: 'medium'
        }
    ];

    // 공격 관련 방책인 경우 추가 단계
    if (coaName.includes('공격') || coaName.includes('공세')) {
        baseSteps.splice(3, 0, {
            step: '3-1. 공격 준비',
            content: '공격 작전 준비 및 최종 점검',
            duration: '1시간',
            responsible: '작전 담당',
            priority: 'high'
        });
    }

    return baseSteps;
}

function extractRequiredResources(recommendation: COASummary, situationInfo?: any): Record<string, any> {
    const resourceScore = recommendation.score_breakdown?.resources || 0;
    const resourceAvailability = situationInfo?.resource_availability || 0.7; // 기본값 70%
    
    // 온톨로지에서 추출한 실제 자원 데이터가 있으면 우선 사용
    if (recommendation.required_resources && recommendation.required_resources.length > 0) {
        const resources: Record<string, any> = {};
        
        // 자원을 유형별로 그룹화
        const resourcesByType: Record<string, any[]> = {};
        recommendation.required_resources.forEach((resource: any) => {
            const type = resource.type || '기타';
            if (!resourcesByType[type]) {
                resourcesByType[type] = [];
            }
            resourcesByType[type].push(resource);
        });
        
        // 각 유형별로 자원 정보 구성
        Object.entries(resourcesByType).forEach(([type, resourceList]) => {
            const resourceNames = resourceList
                .map((r: any) => r.name || r.resource_id || '알 수 없음')
                .join(', ');
            
            // 가용량은 상황 정보에서 가져오거나 시뮬레이션
            const requiredCount = resourceList.length;
            const availableCount = Math.round(requiredCount * resourceAvailability);
            
            // 충족도 계산
            let status: 'sufficient' | 'partial' | 'insufficient';
            if (availableCount >= requiredCount) {
                status = 'sufficient';
            } else if (availableCount >= requiredCount * 0.7) {
                status = 'partial';
            } else {
                status = 'insufficient';
            }
            
            resources[type] = {
                required: resourceNames || `${requiredCount}개 필요`,
                available: availableCount >= requiredCount 
                    ? `${availableCount}개 가용 (충분)`
                    : `${availableCount}개 가용 (부족)`,
                status: status
            };
        });
        
        // 자원이 있으면 반환
        if (Object.keys(resources).length > 0) {
            return resources;
        }
    }
    
    // 온톨로지 데이터가 없을 때만 시뮬레이션 데이터 사용
    return {
        인력: {
            required: '1개 대대',
            available: resourceAvailability >= 0.7 ? '1개 대대' : `${Math.round(resourceAvailability * 100)}% 가용`,
            status: resourceScore > 0.7 ? 'sufficient' : resourceScore < 0.5 ? 'insufficient' : 'partial'
        },
        장비: {
            required: '전차 10대, 장갑차 5대',
            available: resourceAvailability >= 0.8 ? '전차 12대, 장갑차 6대' : '전차 8대, 장갑차 4대',
            status: resourceAvailability >= 0.8 ? 'sufficient' : resourceAvailability >= 0.6 ? 'partial' : 'insufficient'
        },
        보급품: {
            required: '연료 1000L, 탄약 5000발',
            available: resourceAvailability >= 0.8 ? '연료 1200L, 탄약 6000발' : '연료 800L, 탄약 4000발',
            status: resourceAvailability >= 0.8 ? 'sufficient' : resourceAvailability >= 0.6 ? 'partial' : 'insufficient'
        },
        통신장비: {
            required: '무선기 10대',
            available: resourceAvailability >= 0.8 ? '무선기 15대' : '무선기 8대',
            status: resourceAvailability >= 0.8 ? 'sufficient' : resourceAvailability >= 0.6 ? 'partial' : 'insufficient'
        }
    };
}

function assessRisks(
    recommendation: COASummary,
    approachMode: 'threat_centered' | 'mission_centered'
): Array<{ element: string; level: 'high' | 'medium' | 'low'; description: string; response: string }> {
    if (approachMode === 'mission_centered') {
        return [
            {
                element: '임무 방해 요소',
                level: 'medium',
                description: '적군 또는 환경 요인에 의한 임무 달성 방해 가능성',
                response: '우발 계획 수립 및 실시간 모니터링'
            },
            {
                element: '기상 및 지형',
                level: 'low',
                description: '작전 지역의 지형지물 또는 기상 변화에 따른 제한',
                response: '상세 지형 분석 및 기상 정찰 강화'
            },
            {
                element: '자원 무결성',
                level: 'low',
                description: '임무 수행 중 자원의 소모 또는 손실',
                response: '예비대 편성 및 보급로 확보'
            }
        ];
    }

    return [
        {
            element: '적군 대응',
            level: 'medium',
            description: '적군의 대응 작전으로 인한 예상치 못한 상황 발생 가능',
            response: '실시간 정찰 및 상황 모니터링 강화'
        },
        {
            element: '기상 악화',
            level: 'low',
            description: '기상 조건 악화로 인한 작전 지연 가능',
            response: '기상 정보 지속 모니터링 및 대체 계획 수립'
        },
        {
            element: '자원 부족',
            level: 'low',
            description: '예상치 못한 자원 소모로 인한 부족 가능',
            response: '비상 자원 확보 및 우선순위 조정'
        }
    ];
}

function estimateExecutionTime(steps: ExecutionStep[]): { total: string; start: string; end: string } {
    let totalMinutes = 0;

    steps.forEach(step => {
        const duration = step.duration;
        if (duration.includes('시간')) {
            const hours = parseInt(duration.replace('시간', '').trim());
            totalMinutes += hours * 60;
        } else if (duration.includes('분')) {
            const minutes = parseInt(duration.replace('분', '').trim());
            totalMinutes += minutes;
        }
    });

    const now = new Date();
    const endTime = new Date(now.getTime() + totalMinutes * 60000);

    const formatTime = (date: Date) => {
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
    };

    return {
        total: `${Math.floor(totalMinutes / 60)}시간 ${totalMinutes % 60}분`,
        start: formatTime(now),
        end: formatTime(endTime)
    };
}
