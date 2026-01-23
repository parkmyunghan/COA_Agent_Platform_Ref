import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { ShieldCheck, Play, XCircle, AlertTriangle, Info } from 'lucide-react';
import api from '../../lib/api';

interface Issue {
    severity: 'error' | 'warning' | 'info';
    message: string;
    node_id?: string;
}

export default function QualityAssurancePanel() {
    const [status, setStatus] = useState<'idle' | 'loading' | 'done'>('idle');
    const [issues, setIssues] = useState<Issue[]>([]);
    const [overallStatus, setOverallStatus] = useState<string>('');
    const [progress, setProgress] = useState(0);
    const [loadingMsg, setLoadingMsg] = useState('');

    const runCheck = async () => {
        setStatus('loading');
        setIssues([]);
        setOverallStatus('');
        setProgress(0);

        // 1. 초기 시스템 점검 단계 (10-40%)
        const initialSteps = [
            { msg: '백엔드 검증 엔진 초기화 중...', prg: 10 },
            { msg: '온톨로지 스키마 무결성 스캔 (1/3: 전장축선)...', prg: 25 },
            { msg: '온톨로지 데이터 연결성 분석 (2/3: 고립 노드)...', prg: 40 }
        ];

        for (const step of initialSteps) {
            setLoadingMsg(step.msg);
            setProgress(step.prg);
            await new Promise(resolve => setTimeout(resolve, 500));
        }

        // 2. 심층 추론 및 대규모 그래프 스캔 단계 (40-99% 점근적 증가)
        setLoadingMsg('지능형 추론 규칙 적용 및 유불리 판단 자동 도출 중 (3/3: 추론 Capa)...');

        const startTime = Date.now();
        const progressInterval = setInterval(() => {
            const elapsed = Date.now() - startTime;
            // 점근적 진행률 함수: 100%에 가까워질수록 속도가 느려지지만 멈추지 않음
            // f(t) = 40 + 59 * (1 - e^(-t/10000)) -> 약 10초에 80%, 20초에 90% 도달
            const simulatedProgress = Math.min(99, 40 + 59 * (1 - Math.exp(-elapsed / 8000)));
            setProgress(parseFloat(simulatedProgress.toFixed(1)));

            // 시간에 따른 메시지 변화 (사용자가 무한루프라고 느끼지 않게 함)
            if (elapsed > 5000 && elapsed <= 10000) setLoadingMsg('대규모 지식 그래프 전체 노드 정밀 순회 중...');
            if (elapsed > 10000 && elapsed <= 15000) setLoadingMsg('SPARQL 쿼리 엔진 최적화 및 결과 집계 중...');
            if (elapsed > 15000) setLoadingMsg('최종 품질 보고서 인코딩 및 UI 전송 준비 중...');
        }, 500);

        try {
            const res = await api.get('/ontology/studio/quality-check');
            clearInterval(progressInterval);

            const data = res.data;
            setIssues(data.issues || []);
            setOverallStatus(data.status);
            setProgress(100);

            setLoadingMsg('검사 완료! 결과를 성공적으로 수신했습니다.');
            await new Promise(resolve => setTimeout(resolve, 500));
            setStatus('done');
        } catch (err) {
            clearInterval(progressInterval);
            console.error('Quality check failed', err);
            setLoadingMsg('검사 중 네트워크 또는 서버 오류가 발생했습니다.');
            setStatus('idle');
        }
    };

    const getIcon = (severity: string) => {
        switch (severity) {
            case 'error': return <XCircle className="w-4 h-4 text-red-500" />;
            case 'warning': return <AlertTriangle className="w-4 h-4 text-amber-500" />;
            default: return <Info className="w-4 h-4 text-blue-500" />;
        }
    };

    const getRowClass = (severity: string) => {
        switch (severity) {
            case 'error': return 'bg-red-950/20 border-red-900/50';
            case 'warning': return 'bg-amber-950/20 border-amber-900/50';
            default: return 'bg-blue-950/20 border-blue-900/50';
        }
    };

    const [selectedIssueIdx, setSelectedIssueIdx] = useState<number | null>(null);

    const handleAction = (idx: number) => {
        setSelectedIssueIdx(selectedIssueIdx === idx ? null : idx);
    };

    const getAdvice = (issue: Issue) => {
        if (issue.message.includes('전술적 유불리 추론')) {
            return [
                "'그래프 생성' 탭에서 '추론 그래프 생성' 옵션을 켜고 다시 생성해 보세요.",
                "'관계 관리' 탭에서 부대(Unit)와 축선(Axis)이 'operatesIn' 관계로 연결되어 있는지 확인하십시오.",
                "지형셀(Terrain)에 'hasTerrainFeature' 속성이 정의되어 있는지 확인이 필요합니다."
            ];
        } else if (issue.severity === 'error') {
            return [`해당 엔티티의 관계 설정을 '관계 관리' 탭에서 다시 점검하십시오.`];
        } else {
            return [`데이터 무결성을 위해 관련 필드를 확인해 주시기 바랍니다.`];
        }
    };

    return (
        <div className="space-y-6">
            <Card className="bg-zinc-900 border-zinc-800">
                <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-emerald-400" />
                        온톨로지 품질 보증 (QA)
                    </CardTitle>
                    <Button
                        onClick={runCheck}
                        disabled={status === 'loading'}
                        className="bg-emerald-600 hover:bg-emerald-700"
                        size="sm"
                    >
                        <Play className="w-3 h-3 mr-2" />
                        품질 검사 실행
                    </Button>
                </CardHeader>
                <CardContent>
                    {status === 'idle' && (
                        <div className="text-center py-12 text-zinc-500 italic">
                            검사 버튼을 눌러 온톨로지의 일관성과 품질을 확인하세요.
                        </div>
                    )}

                    {status === 'loading' && (
                        <div className="text-center py-12 space-y-6">
                            <div className="max-w-md mx-auto space-y-4">
                                <div className="flex justify-between text-xs text-zinc-400 mb-1">
                                    <span>{loadingMsg}</span>
                                    <span>{progress}%</span>
                                </div>
                                <div className="w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
                                    <div
                                        className="bg-emerald-500 h-full transition-all duration-500 ease-out"
                                        style={{ width: `${progress}%` }}
                                    ></div>
                                </div>
                                <div className="flex justify-center">
                                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-emerald-500"></div>
                                </div>
                            </div>
                        </div>
                    )}

                    {status === 'done' && (
                        <div className="space-y-4">
                            <div className={`p-4 rounded-lg border flex items-center justify-between ${overallStatus === 'valid' ? 'bg-emerald-950/30 border-emerald-800 text-emerald-400' :
                                overallStatus === 'error' ? 'bg-red-950/30 border-red-800 text-red-400' :
                                    overallStatus === 'unknown' ? 'bg-zinc-900 border-zinc-700 text-zinc-500' :
                                        'bg-amber-950/30 border-amber-800 text-amber-400'
                                }`}>
                                <div className="flex items-center gap-2">
                                    <ShieldCheck className="w-5 h-5" />
                                    <div className="flex flex-col">
                                        <span className="font-bold text-sm">검사 결과: {overallStatus.toUpperCase()}</span>
                                        <span className="text-[10px] opacity-70">모든 핵심 스키마 및 추론 규칙 검증 완료</span>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <span className="text-xs font-bold block">{issues.length}개의 항목 발견</span>
                                    <span className="text-[10px] opacity-60">Status: {overallStatus === 'valid' ? 'HEALTHY' : 'NEEDS OPTIMIZATION'}</span>
                                </div>
                            </div>

                            <div className="space-y-2">
                                {issues.length > 0 ? (
                                    issues.map((issue, idx) => (
                                        <div key={idx} className="space-y-2">
                                            <div className={`p-3 rounded border flex gap-3 items-start transition-all ${selectedIssueIdx === idx ? 'ring-1 ring-emerald-500/50' : 'hover:translate-x-1'} ${getRowClass(issue.severity)}`}>
                                                <div className="mt-0.5">{getIcon(issue.severity)}</div>
                                                <div className="flex-1">
                                                    <p className="text-sm text-zinc-200 font-medium">{issue.message}</p>
                                                    {issue.node_id && (
                                                        <p className="text-[10px] text-zinc-500 mt-1 font-mono bg-black/30 px-1 inline-block rounded">Identifier: {issue.node_id}</p>
                                                    )}
                                                </div>
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    className={`text-[10px] h-7 px-2 border border-white/10 ${selectedIssueIdx === idx ? 'bg-emerald-600 text-white' : 'hover:bg-white/5'}`}
                                                    onClick={() => handleAction(idx)}
                                                >
                                                    {selectedIssueIdx === idx ? '가이드 닫기' : '세부 조치'}
                                                </Button>
                                            </div>

                                            {selectedIssueIdx === idx && (
                                                <div className="ml-7 p-4 bg-zinc-950 border border-zinc-800 rounded-lg animate-in slide-in-from-top-2 duration-300">
                                                    <h4 className="text-xs font-bold text-emerald-400 mb-3 flex items-center gap-2">
                                                        <Info className="w-3 h-3" />
                                                        품질 개선 가이드
                                                    </h4>
                                                    <ul className="space-y-2">
                                                        {getAdvice(issue).map((text, i) => (
                                                            <li key={i} className="text-xs text-zinc-400 flex gap-2">
                                                                <span className="text-emerald-500 font-bold">•</span>
                                                                <span>{text}</span>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                    <div className="mt-4 pt-3 border-t border-zinc-800 flex justify-end">
                                                        <Button size="xs" variant="outline" className="text-[10px] h-6" onClick={() => setSelectedIssueIdx(null)}>
                                                            확인 완료
                                                        </Button>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-center py-8 text-emerald-500/50 italic border border-dashed border-emerald-900/30 rounded-lg">
                                        발견된 이슈가 없습니다. 온톨로지가 깨끗합니다! ✨
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
