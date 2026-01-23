// frontend/src/pages/OntologyStudioPage.tsx
import React, { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Checkbox } from '../components/ui/checkbox';
import { Label } from '../components/ui/label';
import { Layout } from '../components/Layout';
import api from '../lib/api';
import InferenceTestPanel from '../components/studio/InferenceTestPanel';
import SchemaDetailsPanel from '../components/studio/SchemaDetailsPanel';
import RelationshipManagerPanel from '../components/studio/RelationshipManagerPanel';
import QualityAssurancePanel from '../components/studio/QualityAssurancePanel';
import RulesPanel from '../components/studio/RulesPanel';

import { useSearchParams } from 'react-router-dom';

export default function OntologyStudioPage() {
    const [searchParams] = useSearchParams();
    const nodeIdParam = searchParams.get('nodeId');

    // Default to 'schema' if nodeId is present, otherwise 'overview'
    const [activeTab, setActiveTab] = useState(nodeIdParam ? 'schema' : 'overview');

    const [stats, setStats] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [genOptions, setGenOptions] = useState({
        virtualEntities: true,
        reasonedGraph: false
    });
    const [genResult, setGenResult] = useState<any>(null);

    useEffect(() => {
        fetchStats();
    }, []);

    const fetchStats = async () => {
        try {
            const res = await api.get('/ontology/studio/stats');
            setStats(res.data);
        } catch (err) {
            console.error('Failed to fetch stats', err);
        }
    };

    const handleGenerate = async () => {
        setLoading(true);
        try {
            const res = await api.post('/ontology/studio/generate', {
                enable_virtual_entities: genOptions.virtualEntities,
                enable_reasoned_graph: genOptions.reasonedGraph
            });
            setGenResult(res.data);
            fetchStats();
        } catch (err) {
            console.error('Generation failed', err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Layout>
            <div className="h-full flex flex-col">
                {/* Information Header */}
                <div className="mb-6 p-4 bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30 rounded-xl">
                    <p className="text-sm text-blue-700 dark:text-blue-300 font-medium">
                        🛠️ 온톨로지 스키마를 정의하고 지식 그래프 자동 생성 및 추론 설정을 관리합니다.
                    </p>
                </div>

                <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
                    <TabsList className="grid w-full grid-cols-7 bg-zinc-100 dark:bg-zinc-900 p-1 rounded-xl h-auto">
                        <TabsTrigger value="overview" className="py-2.5 text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-800 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 rounded-lg font-bold transition-all text-xs">개요</TabsTrigger>
                        <TabsTrigger value="relations" className="py-2.5 text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-800 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 rounded-lg font-bold transition-all text-xs">관계 관리</TabsTrigger>
                        <TabsTrigger value="qa" className="py-2.5 text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-800 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 rounded-lg font-bold transition-all text-xs">품질 보증</TabsTrigger>
                        <TabsTrigger value="generation" className="py-2.5 text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-800 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 rounded-lg font-bold transition-all text-xs">그래프 생성</TabsTrigger>
                        <TabsTrigger value="inference" className="py-2.5 text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-800 data-[state=active]:text-indigo-600 dark:data-[state=active]:text-indigo-400 rounded-lg font-bold transition-all text-xs">OWL 추론</TabsTrigger>
                        <TabsTrigger value="rules" className="py-2.5 text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-800 data-[state=active]:text-purple-600 dark:data-[state=active]:text-purple-400 rounded-lg font-bold transition-all text-xs">도메인 규칙</TabsTrigger>
                        <TabsTrigger value="schema" className="py-2.5 text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-800 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 rounded-lg font-bold transition-all text-xs">스키마 상세</TabsTrigger>
                    </TabsList>

                    <TabsContent value="overview" className="mt-6 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <Card className="bg-zinc-900 border-zinc-800">
                                <CardHeader>
                                    <CardTitle className="text-sm text-zinc-400">총 Triples</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-4xl font-mono font-bold text-blue-400">
                                        {stats?.stats?.total_triples?.toLocaleString() || '-'}
                                    </div>
                                </CardContent>
                            </Card>
                            {/* More stat cards can be added here */}
                        </div>

                        {stats?.schema_summary && (
                            <Card className="mt-6 bg-zinc-900 border-zinc-800">
                                <CardHeader>
                                    <CardTitle>스키마 요약</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <pre className="text-xs text-zinc-300 whitespace-pre-wrap font-mono p-4 bg-black rounded border border-zinc-800">
                                        {stats.schema_summary}
                                    </pre>
                                </CardContent>
                            </Card>
                        )}
                    </TabsContent>

                    <TabsContent value="relations" className="mt-6 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar">
                        <RelationshipManagerPanel />
                    </TabsContent>

                    <TabsContent value="qa" className="mt-6 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar">
                        <QualityAssurancePanel />
                    </TabsContent>

                    <TabsContent value="generation" className="mt-6 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar">
                        <Card className="bg-zinc-900 border-zinc-800 max-w-2xl">
                            <CardHeader>
                                <CardTitle>온톨로지 그래프 생성</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                <div className="space-y-4">
                                    <div className="flex items-center space-x-2">
                                        <Checkbox
                                            id="virtual"
                                            checked={genOptions.virtualEntities}
                                            onCheckedChange={(checked) => setGenOptions({ ...genOptions, virtualEntities: !!checked })}
                                        />
                                        <Label htmlFor="virtual" className="text-zinc-300">가상 엔티티 생성 활성화</Label>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <Checkbox
                                            id="reasoned"
                                            checked={genOptions.reasonedGraph}
                                            onCheckedChange={(checked) => setGenOptions({ ...genOptions, reasonedGraph: !!checked })}
                                        />
                                        <Label htmlFor="reasoned" className="text-zinc-300">추론 그래프 생성 (시간 소요)</Label>
                                    </div>
                                </div>

                                <Button
                                    onClick={handleGenerate}
                                    className="w-full bg-blue-600 hover:bg-blue-700"
                                    disabled={loading}
                                >
                                    {loading ? '생성 중...' : '그래프 생성 실행'}
                                </Button>

                                {genResult && (
                                    <div className={`p-4 rounded border ${genResult.success ? 'bg-green-900/20 border-green-800 text-green-400' : 'bg-red-900/20 border-red-800 text-red-400'}`}>
                                        {genResult.message} (Triples: {genResult.triple_count})
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    <TabsContent value="inference" className="mt-6 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar">
                        <InferenceTestPanel />
                    </TabsContent>

                    <TabsContent value="rules" className="mt-6 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar">
                        <RulesPanel />
                    </TabsContent>

                    <TabsContent value="schema" className="mt-6 flex-1 min-h-0 overflow-y-auto custom-scrollbar">
                        {nodeIdParam && (
                            <div className="mb-4 p-3 bg-zinc-800/50 border border-zinc-700 rounded-lg flex items-center gap-2 text-sm text-zinc-300 shrink-0">
                                <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs font-mono">Incoming Selection</span>
                                <div>
                                    Focusing on <strong className="text-white">{nodeIdParam}</strong>.
                                </div>
                            </div>
                        )}
                        <SchemaDetailsPanel nodeId={nodeIdParam} />
                    </TabsContent>
                </Tabs>
            </div>
        </Layout>
    );
}
