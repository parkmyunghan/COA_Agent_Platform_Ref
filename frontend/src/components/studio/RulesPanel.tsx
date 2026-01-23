import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { 
    BookOpen, Play, CheckCircle2, AlertTriangle, Filter, 
    ChevronDown, ChevronUp, ArrowRight, Zap, Shield, 
    Crosshair, Settings, RotateCcw, Eye
} from 'lucide-react';

interface RuleCategory {
    name: string;
    description: string;
    icon: string;
}

interface Rule {
    id: string;
    name: string;
    description: string;
    category: string;
    priority: string;
    enabled: boolean;
    condition_sparql?: string;
    conclusion_template?: string;
}

interface RuleResult {
    name: string;
    description: string;
    category: string;
    priority: string;
    inferred_count: number;
    inferred_triples: Array<{
        subject: string;
        predicate: string;
        object: string;
    }>;
}

interface ExecutionResult {
    total_rules_executed: number;
    total_inferred: number;
    rules_by_category: Record<string, number>;
    inferred_by_category: Record<string, number>;
    rule_results: Record<string, RuleResult>;
    applied_to_graph: boolean;
    applied_count: number;
}

export default function RulesPanel() {
    const [rules, setRules] = useState<Rule[]>([]);
    const [categories, setCategories] = useState<Record<string, RuleCategory>>({});
    const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
    const [selectedPriority, setSelectedPriority] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null);
    const [expandedRules, setExpandedRules] = useState<Set<string>>(new Set());
    const [applyToGraph, setApplyToGraph] = useState(false);
    const [selectedRuleDetail, setSelectedRuleDetail] = useState<Rule | null>(null);

    useEffect(() => {
        fetchRules();
    }, []);

    const fetchRules = async () => {
        try {
            const res = await fetch(`http://${window.location.hostname}:8000/api/v1/ontology/studio/rules`);
            const data = await res.json();
            setRules(data.rules || []);
            setCategories(data.categories || {});
        } catch (err) {
            console.error('Failed to fetch rules', err);
        }
    };

    const fetchRuleDetail = async (ruleId: string) => {
        try {
            const res = await fetch(`http://${window.location.hostname}:8000/api/v1/ontology/studio/rules/${ruleId}`);
            const data = await res.json();
            setSelectedRuleDetail(data);
        } catch (err) {
            console.error('Failed to fetch rule detail', err);
        }
    };

    const executeRules = async () => {
        setLoading(true);
        setExecutionResult(null);
        
        try {
            const res = await fetch(`http://${window.location.hostname}:8000/api/v1/ontology/studio/rules/execute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    categories: selectedCategories.length > 0 ? selectedCategories : null,
                    priority_filter: selectedPriority,
                    apply_to_graph: applyToGraph
                })
            });
            const data = await res.json();
            setExecutionResult(data);
        } catch (err) {
            console.error('Rules execution failed', err);
        } finally {
            setLoading(false);
        }
    };

    const toggleCategory = (category: string) => {
        setSelectedCategories(prev => 
            prev.includes(category) 
                ? prev.filter(c => c !== category)
                : [...prev, category]
        );
    };

    const toggleRuleExpand = (ruleId: string) => {
        setExpandedRules(prev => {
            const newSet = new Set(prev);
            if (newSet.has(ruleId)) {
                newSet.delete(ruleId);
            } else {
                newSet.add(ruleId);
            }
            return newSet;
        });
    };

    const getCategoryIcon = (category: string) => {
        switch (category) {
            case 'tactical': return <Crosshair className="w-4 h-4" />;
            case 'threat': return <AlertTriangle className="w-4 h-4" />;
            case 'resource': return <Settings className="w-4 h-4" />;
            case 'coa': return <BookOpen className="w-4 h-4" />;
            default: return <Zap className="w-4 h-4" />;
        }
    };

    const getCategoryColor = (category: string) => {
        switch (category) {
            case 'tactical': return 'bg-red-500/20 text-red-300 border-red-500/30';
            case 'threat': return 'bg-orange-500/20 text-orange-300 border-orange-500/30';
            case 'resource': return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
            case 'coa': return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
            default: return 'bg-zinc-500/20 text-zinc-300 border-zinc-500/30';
        }
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'HIGH': return 'bg-red-500/20 text-red-300';
            case 'MEDIUM': return 'bg-yellow-500/20 text-yellow-300';
            case 'LOW': return 'bg-green-500/20 text-green-300';
            default: return 'bg-zinc-500/20 text-zinc-300';
        }
    };

    return (
        <div className="space-y-6">
            {/* 상단 설명 */}
            <Card className="bg-gradient-to-r from-purple-950/30 to-indigo-950/20 border-purple-900/30">
                <CardContent className="pt-6">
                    <div className="flex gap-4">
                        <div className="p-3 bg-purple-500/10 rounded-xl h-fit">
                            <BookOpen className="w-6 h-6 text-purple-400" />
                        </div>
                        <div className="space-y-2 flex-1">
                            <h3 className="text-lg font-bold text-purple-100 flex items-center gap-2">
                                SWRL 스타일 도메인 추론 규칙
                            </h3>
                            <p className="text-sm text-purple-300/80 leading-relaxed">
                                전술 도메인에 특화된 추론 규칙을 실행합니다. 
                                <strong>교전 대상</strong>, <strong>위협 노출</strong>, <strong>화력 지원 범위</strong>, 
                                <strong>협력 관계</strong>, <strong>기동 제한</strong> 등의 관계를 자동으로 추론합니다.
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* 필터 및 실행 설정 */}
            <Card className="bg-zinc-900 border-zinc-800">
                <CardHeader>
                    <CardTitle className="text-zinc-100 flex items-center gap-2">
                        <Filter className="w-5 h-5 text-purple-400" />
                        규칙 필터 및 실행 설정
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* 카테고리 선택 */}
                    <div className="space-y-2">
                        <label className="text-xs text-zinc-400 font-bold uppercase">카테고리 선택</label>
                        <div className="flex flex-wrap gap-2">
                            {Object.entries(categories).map(([key, cat]) => (
                                <button
                                    key={key}
                                    onClick={() => toggleCategory(key)}
                                    className={`px-3 py-1.5 rounded-lg text-sm font-bold transition-all flex items-center gap-2 border ${
                                        selectedCategories.includes(key)
                                            ? getCategoryColor(key)
                                            : 'bg-zinc-800 text-zinc-400 border-zinc-700 hover:border-zinc-600'
                                    }`}
                                >
                                    {getCategoryIcon(key)}
                                    {cat.name}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* 우선순위 필터 */}
                    <div className="space-y-2">
                        <label className="text-xs text-zinc-400 font-bold uppercase">우선순위 필터</label>
                        <div className="flex gap-2">
                            {['HIGH', 'MEDIUM', 'LOW'].map(priority => (
                                <button
                                    key={priority}
                                    onClick={() => setSelectedPriority(selectedPriority === priority ? null : priority)}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                                        selectedPriority === priority
                                            ? getPriorityColor(priority)
                                            : 'bg-zinc-800 text-zinc-500 hover:text-zinc-300'
                                    }`}
                                >
                                    {priority}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* 그래프 적용 옵션 */}
                    <div className="flex items-center gap-3 p-3 bg-zinc-950 rounded-lg">
                        <input
                            type="checkbox"
                            id="applyToGraph"
                            checked={applyToGraph}
                            onChange={(e) => setApplyToGraph(e.target.checked)}
                            className="w-4 h-4 rounded border-zinc-600 bg-zinc-800 text-purple-500 focus:ring-purple-500"
                        />
                        <label htmlFor="applyToGraph" className="text-sm text-zinc-300">
                            추론 결과를 온톨로지 그래프에 적용
                            <span className="text-xs text-zinc-500 ml-2">(영구 저장됨)</span>
                        </label>
                    </div>

                    {/* 실행 버튼 */}
                    <Button
                        onClick={executeRules}
                        disabled={loading}
                        className="w-full bg-purple-600 hover:bg-purple-700 text-white font-black py-6 transition-all shadow-lg shadow-purple-500/10"
                    >
                        {loading ? (
                            <span className="flex items-center gap-2">
                                <RotateCcw className="w-4 h-4 animate-spin" />
                                규칙 실행 중...
                            </span>
                        ) : (
                            <span className="flex items-center gap-2">
                                <Play className="w-4 h-4" />
                                도메인 추론 규칙 실행
                            </span>
                        )}
                    </Button>
                </CardContent>
            </Card>

            {/* 실행 결과 */}
            {executionResult && (
                <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-500">
                    {/* 결과 요약 */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 text-center">
                            <div className="text-2xl font-black text-purple-400">{executionResult.total_rules_executed}</div>
                            <div className="text-[10px] text-zinc-500 uppercase font-bold">실행된 규칙</div>
                        </div>
                        <div className="bg-zinc-900/50 border border-purple-900/30 rounded-lg p-3 text-center">
                            <div className="text-2xl font-black text-indigo-400">{executionResult.total_inferred}</div>
                            <div className="text-[10px] text-zinc-500 uppercase font-bold">추론된 관계</div>
                        </div>
                        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 text-center">
                            <div className="text-2xl font-black text-green-400">
                                {executionResult.applied_to_graph ? executionResult.applied_count : '-'}
                            </div>
                            <div className="text-[10px] text-zinc-500 uppercase font-bold">그래프 적용</div>
                        </div>
                        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 text-center">
                            <div className="text-2xl font-black text-zinc-300">
                                {Object.keys(executionResult.rule_results).length}
                            </div>
                            <div className="text-[10px] text-zinc-500 uppercase font-bold">활성 규칙</div>
                        </div>
                    </div>

                    {/* 카테고리별 결과 */}
                    <Card className="bg-zinc-900 border-zinc-800">
                        <CardHeader>
                            <CardTitle className="text-xs text-zinc-400 uppercase tracking-widest font-black">
                                카테고리별 추론 결과
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                {Object.entries(executionResult.inferred_by_category).map(([cat, count]) => (
                                    <div key={cat} className={`p-3 rounded-lg border ${getCategoryColor(cat)}`}>
                                        <div className="flex items-center gap-2 mb-1">
                                            {getCategoryIcon(cat)}
                                            <span className="text-xs font-bold">{categories[cat]?.name || cat}</span>
                                        </div>
                                        <div className="text-xl font-black">{count}개</div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                    {/* 규칙별 상세 결과 */}
                    <Card className="bg-zinc-900 border-zinc-800">
                        <CardHeader>
                            <CardTitle className="text-xs text-zinc-400 uppercase tracking-widest font-black flex items-center gap-2">
                                <Zap className="w-4 h-4 text-purple-400" />
                                규칙별 추론 결과
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2 max-h-[500px] overflow-y-auto">
                            {Object.entries(executionResult.rule_results).map(([ruleId, result]) => (
                                <div 
                                    key={ruleId} 
                                    className="bg-zinc-950 border border-zinc-800 rounded-lg overflow-hidden"
                                >
                                    <button
                                        onClick={() => toggleRuleExpand(ruleId)}
                                        className="w-full p-3 flex items-center justify-between hover:bg-zinc-800/50 transition-colors"
                                    >
                                        <div className="flex items-center gap-3">
                                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${getCategoryColor(result.category)}`}>
                                                {result.category}
                                            </span>
                                            <span className="text-sm font-bold text-zinc-100">{result.name}</span>
                                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${getPriorityColor(result.priority)}`}>
                                                {result.priority}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-bold text-purple-400">
                                                {result.inferred_count}개 추론
                                            </span>
                                            {expandedRules.has(ruleId) ? (
                                                <ChevronUp className="w-4 h-4 text-zinc-500" />
                                            ) : (
                                                <ChevronDown className="w-4 h-4 text-zinc-500" />
                                            )}
                                        </div>
                                    </button>
                                    
                                    {expandedRules.has(ruleId) && (
                                        <div className="border-t border-zinc-800 p-3 space-y-3">
                                            <p className="text-xs text-zinc-400">{result.description}</p>
                                            
                                            {result.inferred_triples.length > 0 && (
                                                <div className="space-y-2">
                                                    <div className="text-[10px] text-zinc-500 font-bold uppercase">
                                                        추론된 트리플 (최대 10개)
                                                    </div>
                                                    {result.inferred_triples.map((triple, i) => (
                                                        <div 
                                                            key={i} 
                                                            className="flex items-center gap-2 text-xs bg-zinc-900 p-2 rounded font-mono"
                                                        >
                                                            <span className="text-blue-400 truncate max-w-[150px]">
                                                                {triple.subject.split('#').pop()}
                                                            </span>
                                                            <ArrowRight className="w-3 h-3 text-zinc-600 shrink-0" />
                                                            <span className="text-purple-400 shrink-0">
                                                                {triple.predicate.split('#').pop()}
                                                            </span>
                                                            <ArrowRight className="w-3 h-3 text-zinc-600 shrink-0" />
                                                            <span className="text-green-400 truncate max-w-[150px]">
                                                                {triple.object.split('#').pop()}
                                                            </span>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                            
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => fetchRuleDetail(ruleId)}
                                                className="text-xs text-purple-400 hover:text-purple-300"
                                            >
                                                <Eye className="w-3 h-3 mr-1" />
                                                SPARQL 조건 보기
                                            </Button>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* 규칙 상세 정보 모달 */}
            {selectedRuleDetail && (
                <div 
                    className="fixed inset-0 bg-black/70 flex items-center justify-center z-50"
                    onClick={() => setSelectedRuleDetail(null)}
                >
                    <div 
                        className="bg-zinc-900 border border-zinc-700 rounded-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="p-6 space-y-4">
                            <div className="flex items-center justify-between">
                                <h3 className="text-lg font-bold text-zinc-100">{selectedRuleDetail.name}</h3>
                                <button 
                                    onClick={() => setSelectedRuleDetail(null)}
                                    className="text-zinc-500 hover:text-zinc-300"
                                >
                                    ✕
                                </button>
                            </div>
                            
                            <div className="flex gap-2">
                                <span className={`px-2 py-1 rounded text-xs font-bold ${getCategoryColor(selectedRuleDetail.category)}`}>
                                    {selectedRuleDetail.category}
                                </span>
                                <span className={`px-2 py-1 rounded text-xs font-bold ${getPriorityColor(selectedRuleDetail.priority)}`}>
                                    {selectedRuleDetail.priority}
                                </span>
                            </div>
                            
                            <p className="text-sm text-zinc-400">{selectedRuleDetail.description}</p>
                            
                            <div className="space-y-2">
                                <div className="text-xs text-zinc-500 font-bold uppercase">조건 (SPARQL WHERE)</div>
                                <pre className="bg-zinc-950 p-4 rounded-lg text-xs text-purple-300 overflow-x-auto font-mono">
                                    {selectedRuleDetail.condition_sparql}
                                </pre>
                            </div>
                            
                            <div className="space-y-2">
                                <div className="text-xs text-zinc-500 font-bold uppercase">결론 (추론 트리플)</div>
                                <div className="bg-zinc-950 p-4 rounded-lg text-sm text-green-300 font-mono">
                                    {selectedRuleDetail.conclusion_template}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* 등록된 규칙 목록 */}
            <Card className="bg-zinc-900 border-zinc-800">
                <CardHeader>
                    <CardTitle className="text-xs text-zinc-400 uppercase tracking-widest font-black flex items-center gap-2">
                        <Shield className="w-4 h-4 text-zinc-500" />
                        등록된 도메인 규칙 ({rules.length}개)
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-[300px] overflow-y-auto">
                        {rules.map(rule => (
                            <div 
                                key={rule.id}
                                className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg hover:border-zinc-700 transition-colors cursor-pointer"
                                onClick={() => fetchRuleDetail(rule.id)}
                            >
                                <div className="flex items-center gap-2 mb-1">
                                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${getCategoryColor(rule.category)}`}>
                                        {rule.category}
                                    </span>
                                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${getPriorityColor(rule.priority)}`}>
                                        {rule.priority}
                                    </span>
                                </div>
                                <div className="text-sm font-bold text-zinc-200">{rule.name}</div>
                                <div className="text-[11px] text-zinc-500 mt-1 line-clamp-2">{rule.description}</div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
