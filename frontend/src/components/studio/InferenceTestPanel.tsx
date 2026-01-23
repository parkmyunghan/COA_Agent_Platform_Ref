import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Combobox } from '../ui/combobox';
import { Info, Zap, Target, ArrowRight, Brain, Link2, RotateCcw, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import api from '../../lib/api';

interface InferenceStats {
    original_triples?: number;
    inferred_triples?: number;
    new_inferences?: number;
    elapsed_time_ms?: number;
    success?: boolean;
    error?: string;
    fallback?: boolean;
}

interface Relation {
    relation: string;
    target?: string;
    source?: string;
    type: string;
    reasoning?: string;
    depth?: number;
    path?: string[];
}

interface OWLInferenceResult {
    entity: string;
    entity_uri: string;
    direct_relations: Relation[];
    inferred_relations: Relation[];
    total_direct: number;
    total_inferred: number;
    confidence: number;
    stats: InferenceStats;
    reasoning_enabled: boolean;
}

export default function InferenceTestPanel() {
    const [entityId, setEntityId] = useState('');
    const [maxResults, setMaxResults] = useState(50);
    const [loading, setLoading] = useState(false);
    const [entities, setEntities] = useState<{ value: string; label: string }[]>([]);
    const [result, setResult] = useState<OWLInferenceResult | null>(null);
    const [inferenceMode, setInferenceMode] = useState<'owl' | 'keyword'>('owl');
    const [owlStats, setOwlStats] = useState<any>(null);
    const [applyToGraph, setApplyToGraph] = useState(false);

    useEffect(() => {
        fetchEntities();
        fetchOwlStats();
    }, []);

    const fetchEntities = async () => {
        try {
            const res = await api.get('/ontology/graph?mode=instances');
            const nodes = res.data.nodes || [];

            // 기술적 엔티티 필터링 (Axiom, Class, Property 등 제외)
            const excludedGroups = ['Axiom', 'Class', 'Property', 'Restriction', 'Ontology', 'NamedIndividual', 'Unknown'];

            const options = nodes
                .filter((node: any) => !excludedGroups.some(group => (node.group || '').includes(group)))
                .map((node: any) => {
                    // 엔티티 ID에서 괄호와 설명 제거 (예: 임무정보_MSN004(기만작전 실시) -> 임무정보_MSN004)
                    let entityId = node.id || '';
                    entityId = entityId.replace(/\([^)]*\)/g, '').trim();
                    
                    return {
                        value: entityId,
                        label: node.label || node.id
                    };
                });
            setEntities(options);
        } catch (err) {
            console.error('Failed to fetch entities', err);
        }
    };

    const fetchOwlStats = async () => {
        try {
            const res = await fetch(`http://${window.location.hostname}:8000/api/v1/ontology/studio/owl-inference/stats`);
            const data = await res.json();
            setOwlStats(data);
        } catch (err) {
            console.error('Failed to fetch OWL stats', err);
        }
    };

    const handleRunInference = async () => {
        if (!entityId) return;
        setLoading(true);
        setResult(null);
        
        try {
            // 엔티티 ID 정규화 (괄호와 설명 제거)
            let normalizedEntityId = entityId.replace(/\([^)]*\)/g, '').trim();
            
            const endpoint = inferenceMode === 'owl' 
                ? '/api/v1/ontology/studio/owl-inference'
                : '/api/v1/ontology/studio/inference';
            
            const body = inferenceMode === 'owl'
                ? { entity_id: normalizedEntityId, include_rdfs: true, max_results: maxResults, apply_to_graph: applyToGraph }
                : { entity_id: normalizedEntityId, max_depth: 2 };
            
            const res = await fetch(`http://${window.location.hostname}:8000${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            const data = await res.json();
            
            // 기존 API 응답을 OWL 형식으로 변환
            if (inferenceMode === 'keyword') {
                setResult({
                    entity: entityId,
                    entity_uri: `http://coa-agent-platform.org/ontology#${entityId}`,
                    direct_relations: data.direct_relations || [],
                    inferred_relations: data.indirect_relations || [],
                    total_direct: data.direct_relations?.length || 0,
                    total_inferred: data.indirect_relations?.length || 0,
                    confidence: data.confidence || 0,
                    stats: { success: true },
                    reasoning_enabled: false
                });
            } else {
                setResult(data);
            }
        } catch (err) {
            console.error('Inference failed', err);
        } finally {
            setLoading(false);
        }
    };

    const getRuleTypeBadge = (reasoning: string | undefined) => {
        if (!reasoning) return null;
        
        const ruleColors: Record<string, string> = {
            '역관계': 'bg-blue-500/20 text-blue-300 border-blue-500/30',
            '속성체인': 'bg-purple-500/20 text-purple-300 border-purple-500/30',
            '대칭관계': 'bg-green-500/20 text-green-300 border-green-500/30',
            '전이관계': 'bg-orange-500/20 text-orange-300 border-orange-500/30',
            '도메인추론': 'bg-pink-500/20 text-pink-300 border-pink-500/30',
        };
        
        for (const [key, color] of Object.entries(ruleColors)) {
            if (reasoning.includes(key)) {
                return (
                    <span className={`text-[9px] px-1.5 py-0.5 rounded border ${color} font-bold`}>
                        {key}
                    </span>
                );
            }
        }
        
        return (
            <span className="text-[9px] px-1.5 py-0.5 rounded border bg-zinc-500/20 text-zinc-400 border-zinc-500/30 font-bold">
                OWL-RL
            </span>
        );
    };

    return (
        <div className="space-y-6">
            {/* 상단 설명 카드 */}
            <Card className="bg-gradient-to-r from-indigo-950/30 to-purple-950/20 border-indigo-900/30">
                <CardContent className="pt-6">
                    <div className="flex gap-4">
                        <div className="p-3 bg-indigo-500/10 rounded-xl h-fit">
                            <Brain className="w-6 h-6 text-indigo-400" />
                        </div>
                        <div className="space-y-2 flex-1">
                            <h3 className="text-lg font-bold text-indigo-100 flex items-center gap-2">
                                OWL-RL 기반 지능형 추론 엔진
                                {owlStats?.owlrl_available && (
                                    <span className="text-[10px] px-2 py-0.5 bg-green-500/20 text-green-300 rounded-full font-medium">
                                        ✓ OWL-RL 활성화
                                    </span>
                                )}
                            </h3>
                            <p className="text-sm text-indigo-300/80 leading-relaxed">
                                W3C OWL 표준 규칙을 적용하여 <strong>논리적으로 숨겨진 관계</strong>를 자동 추론합니다.
                                전이적 관계(Transitive), 역관계(Inverse), 속성 체인(PropertyChain), 대칭 관계(Symmetric) 등의 규칙이 적용됩니다.
                            </p>
                            {owlStats?.supported_rules && owlStats.supported_rules.length > 0 && (
                                <div className="flex flex-wrap gap-1.5 pt-1">
                                    {owlStats.supported_rules.map((rule: string) => (
                                        <span key={rule} className="text-[10px] px-2 py-0.5 bg-indigo-500/10 text-indigo-300/70 rounded border border-indigo-500/20">
                                            {rule}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </CardContent>
            </Card>

            <Card className="bg-zinc-900 border-zinc-800">
                <CardHeader>
                    <CardTitle className="text-zinc-100 flex items-center gap-2">
                        🧠 관계 추론 실행 설정
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* 추론 모드 선택 */}
                    <div className="flex gap-2 p-1 bg-zinc-950 rounded-lg">
                        <button
                            onClick={() => setInferenceMode('owl')}
                            className={`flex-1 py-2 px-4 rounded-md text-sm font-bold transition-all flex items-center justify-center gap-2 ${
                                inferenceMode === 'owl' 
                                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' 
                                    : 'text-zinc-400 hover:text-zinc-200'
                            }`}
                        >
                            <Brain className="w-4 h-4" />
                            OWL-RL 추론
                        </button>
                        <button
                            onClick={() => setInferenceMode('keyword')}
                            className={`flex-1 py-2 px-4 rounded-md text-sm font-bold transition-all flex items-center justify-center gap-2 ${
                                inferenceMode === 'keyword' 
                                    ? 'bg-zinc-700 text-white shadow-lg' 
                                    : 'text-zinc-400 hover:text-zinc-200'
                            }`}
                        >
                            <Link2 className="w-4 h-4" />
                            키워드 유사도 추론
                        </button>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="entity-id" className="text-zinc-400 font-medium">분석 대상 엔티티 선택</Label>
                            <Combobox
                                options={entities}
                                value={entityId}
                                onValueChange={setEntityId}
                                placeholder="엔티티(위협, 부대 등)를 선택하세요..."
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="max-results" className="text-zinc-400 font-medium">
                                {inferenceMode === 'owl' ? '최대 결과 수' : '탐색 깊이 (Depth)'}
                            </Label>
                            <Input
                                id="max-results"
                                type="number"
                                min={inferenceMode === 'owl' ? 10 : 1}
                                max={inferenceMode === 'owl' ? 100 : 5}
                                value={maxResults}
                                onChange={(e) => setMaxResults(parseInt(e.target.value))}
                                className="bg-zinc-950 border-zinc-800 text-zinc-100 focus:ring-indigo-500"
                            />
                        </div>
                    </div>
                    
                    {/* 그래프 적용 옵션 (OWL 모드만) */}
                    {inferenceMode === 'owl' && (
                        <div className="flex items-center gap-3 p-3 bg-zinc-950 rounded-lg border border-zinc-800">
                            <input
                                type="checkbox"
                                id="applyToGraph"
                                checked={applyToGraph}
                                onChange={(e) => setApplyToGraph(e.target.checked)}
                                className="w-4 h-4 rounded border-zinc-600 bg-zinc-800 text-indigo-500 focus:ring-indigo-500"
                            />
                            <label htmlFor="applyToGraph" className="text-sm text-zinc-300 cursor-pointer">
                                추론 결과를 온톨로지 그래프에 영구 적용
                                <span className="text-xs text-zinc-500 ml-2">(추론된 관계가 그래프 탐색에 표시됨)</span>
                            </label>
                        </div>
                    )}
                    
                    <Button
                        onClick={handleRunInference}
                        disabled={loading || !entityId}
                        className={`w-full text-white font-black py-6 transition-all shadow-lg ${
                            inferenceMode === 'owl'
                                ? 'bg-indigo-600 hover:bg-indigo-700 shadow-indigo-500/10'
                                : 'bg-zinc-700 hover:bg-zinc-600 shadow-zinc-500/10'
                        }`}
                    >
                        {loading ? (
                            <span className="flex items-center gap-2">
                                <RotateCcw className="w-4 h-4 animate-spin" />
                                추론 처리 중...
                            </span>
                        ) : (
                            <span className="flex items-center gap-2">
                                {inferenceMode === 'owl' ? <Brain className="w-4 h-4" /> : <Link2 className="w-4 h-4" />}
                                {inferenceMode === 'owl' ? 'OWL-RL 추론 실행' : '키워드 기반 추론 실행'}
                            </span>
                        )}
                    </Button>
                </CardContent>
            </Card>

            {/* 추론 통계 */}
            {result?.stats && result.stats.success && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 animate-in fade-in duration-300">
                    <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 text-center">
                        <div className="text-2xl font-black text-blue-400">{result.total_direct}</div>
                        <div className="text-[10px] text-zinc-500 uppercase font-bold">직접 관계</div>
                    </div>
                    <div className="bg-zinc-900/50 border border-indigo-900/30 rounded-lg p-3 text-center">
                        <div className="text-2xl font-black text-indigo-400">{result.total_inferred}</div>
                        <div className="text-[10px] text-zinc-500 uppercase font-bold">추론된 관계</div>
                    </div>
                    <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 text-center">
                        <div className="text-2xl font-black text-green-400">{(result.confidence * 100).toFixed(0)}%</div>
                        <div className="text-[10px] text-zinc-500 uppercase font-bold">신뢰도</div>
                    </div>
                    {result.stats.elapsed_time_ms !== undefined && (
                        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 text-center">
                            <div className="text-2xl font-black text-zinc-300 flex items-center justify-center gap-1">
                                <Clock className="w-4 h-4" />
                                {result.stats.elapsed_time_ms}
                            </div>
                            <div className="text-[10px] text-zinc-500 uppercase font-bold">처리시간(ms)</div>
                        </div>
                    )}
                </div>
            )}

            {result && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in slide-in-from-top-2 duration-500">
                    {/* Direct Relations */}
                    <Card className="bg-zinc-900 border-zinc-800">
                        <CardHeader className="pb-2 border-b border-zinc-800/50 mb-4">
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-xs text-zinc-400 uppercase tracking-widest font-black flex items-center gap-2">
                                    <Target className="w-4 h-4 text-blue-400" />
                                    직접 관계 (Direct Facts)
                                </CardTitle>
                                <span className="text-[10px] bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded font-bold">
                                    {result.total_direct}개
                                </span>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2">
                                {result.direct_relations?.length > 0 ? (
                                    result.direct_relations.map((rel: Relation, i: number) => (
                                        <div key={i} className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg flex justify-between items-center group hover:border-blue-500/50 transition-all">
                                            <div className="flex flex-col gap-1">
                                                <span className="text-xs font-bold text-blue-400/90">{rel.relation}</span>
                                                {rel.source && (
                                                    <span className="text-[10px] text-zinc-500">← {rel.source}</span>
                                                )}
                                            </div>
                                            <span className="text-sm font-bold text-zinc-100">{rel.target || rel.source}</span>
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-zinc-500 text-xs italic p-10 text-center bg-zinc-950/50 rounded-lg flex flex-col items-center gap-2">
                                        <AlertCircle className="w-6 h-6 text-zinc-600" />
                                        직접적인 관계 데이터가 없습니다.
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Inferred Relations */}
                    <Card className={`bg-zinc-900 ${result.reasoning_enabled ? 'border-indigo-900/30 ring-1 ring-indigo-500/10' : 'border-zinc-700'}`}>
                        <CardHeader className="pb-2 border-b border-indigo-900/30 mb-4">
                            <div className="flex flex-row items-center justify-between">
                                <CardTitle className="text-xs text-indigo-300 uppercase tracking-widest font-black flex items-center gap-2">
                                    <Zap className="w-4 h-4 text-indigo-400" />
                                    추론된 관계 (Inferred)
                                </CardTitle>
                                <div className="flex items-center gap-2">
                                    {result.reasoning_enabled ? (
                                        <span className="text-[10px] font-bold bg-green-500/20 text-green-300 px-2 py-0.5 rounded flex items-center gap-1">
                                            <CheckCircle2 className="w-3 h-3" />
                                            OWL-RL
                                        </span>
                                    ) : (
                                        <span className="text-[10px] font-bold bg-zinc-500/20 text-zinc-400 px-2 py-0.5 rounded">
                                            Keyword
                                        </span>
                                    )}
                                    <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded font-bold">
                                        {result.total_inferred}개
                                    </span>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {result.reasoning_enabled && (
                                <div className="p-3 bg-indigo-500/5 border border-indigo-500/20 rounded-lg">
                                    <p className="text-[11px] text-indigo-300/80 leading-snug flex items-start gap-2">
                                        <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                                        아래 관계는 OWL-RL 표준 규칙(역관계, 속성체인, 전이성, 대칭성)을 통해 논리적으로 추론된 사실입니다.
                                    </p>
                                </div>
                            )}

                            <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
                                {result.inferred_relations?.length > 0 ? (
                                    result.inferred_relations.map((rel: Relation, i: number) => (
                                        <div key={i} className="p-4 bg-zinc-950 border border-indigo-900/30 rounded-lg flex flex-col gap-2 group hover:border-indigo-500/50 transition-all shadow-sm">
                                            <div className="flex justify-between items-center">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-xs font-black text-indigo-300 bg-indigo-500/20 px-2 py-1 rounded">{rel.relation}</span>
                                                    {getRuleTypeBadge(rel.reasoning)}
                                                </div>
                                                {rel.depth && (
                                                    <span className="text-[10px] text-zinc-500 font-mono font-bold">Step: {rel.depth}</span>
                                                )}
                                            </div>
                                            <span className="text-sm font-black text-white">{rel.target || rel.source}</span>
                                            {rel.reasoning && (
                                                <div className="text-[10px] text-indigo-400/60 italic">
                                                    {rel.reasoning}
                                                </div>
                                            )}
                                            {rel.path && Array.isArray(rel.path) && (
                                                <div className="flex items-center gap-1.5 pt-1 overflow-hidden">
                                                    <span className="text-[9px] text-zinc-600 font-black uppercase shrink-0">Path:</span>
                                                    <div className="text-[10px] text-indigo-400/70 truncate font-mono flex items-center gap-1">
                                                        {rel.path.map((p: string, pi: number) => (
                                                            <React.Fragment key={pi}>
                                                                <span className="hover:text-indigo-300 transition-colors">{p}</span>
                                                                {pi < rel.path!.length - 1 && <ArrowRight className="w-2.5 h-2.5" />}
                                                            </React.Fragment>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-zinc-500 text-xs italic p-10 text-center bg-zinc-950/50 rounded-lg flex flex-col items-center gap-2">
                                        <AlertCircle className="w-6 h-6 text-zinc-600" />
                                        추론된 암시적 관계가 발견되지 않았습니다.
                                        {!result.reasoning_enabled && (
                                            <span className="text-[10px] text-zinc-600">OWL-RL 모드로 전환하면 더 많은 관계를 발견할 수 있습니다.</span>
                                        )}
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* 추론 상세 통계 */}
            {result?.stats && result.reasoning_enabled && result.stats.new_inferences !== undefined && (
                <Card className="bg-zinc-900/50 border-zinc-800">
                    <CardContent className="py-4">
                        <div className="flex items-center justify-between text-xs text-zinc-500">
                            <span>
                                그래프 확장: {result.stats.original_triples?.toLocaleString()} → {result.stats.inferred_triples?.toLocaleString()} 트리플
                                <span className="text-indigo-400 ml-2">
                                    (+{result.stats.new_inferences?.toLocaleString()} 추론됨)
                                </span>
                            </span>
                            <span className="flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3 text-green-400" />
                                OWL-RL 추론 완료
                            </span>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
