// frontend/src/components/studio/RelationshipManagerPanel.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { Search, Plus, Trash2, RefreshCw, Database, Link, Target } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Combobox } from '../ui/combobox';
import { AgGridReact } from 'ag-grid-react';
import { themeQuartz } from 'ag-grid-community';
import api from '../../lib/api';

interface Triple {
    subject: string;
    predicate: string;
    object_val: string;
}

export default function RelationshipManagerPanel() {
    const [triples, setTriples] = useState<Triple[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchSubject, setSearchSubject] = useState('');
    const [newTriple, setNewTriple] = useState({ subject: '', predicate: '', object_val: '' });
    const [isLiteral, setIsLiteral] = useState(false);

    // Suggestion lists
    const [entities, setEntities] = useState<{ value: string; label: string }[]>([]);
    const [predicates, setPredicates] = useState<{ value: string; label: string }[]>([]);

    const fetchRelations = useCallback(async (subject?: string) => {
        try {
            setLoading(true);
            const params = subject ? { subject } : {};
            const response = await api.get('/ontology/studio/relations', { params });
            // 백엔드가 리스트를 직접 반환하므로 response.data가 배열임
            setTriples(Array.isArray(response.data) ? response.data : []);
        } catch (err) {
            console.error('Failed to fetch relations', err);
            setTriples([]);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchSuggestions = useCallback(async () => {
        try {
            // 1. 엔티티(주체/대상) 조회
            const nodesRes = await api.get('/ontology/graph', { params: { mode: 'instances' } });
            if (nodesRes.data && nodesRes.data.nodes) {
                // 관계 설정이 불필요한 기술적 엔티티 필터링
                const excludedGroups = ['Axiom', 'Class', 'ObjectProperty', 'DatatypeProperty', 'OntologyCOAType', 'Restriction', 'Ontology', 'NamedIndividual', 'Unknown'];

                const nodeOptions = nodesRes.data.nodes
                    .filter((n: any) => !excludedGroups.some(group => (n.group || '').includes(group)))
                    .map((n: any) => ({
                        value: n.id,
                        label: n.label || n.id
                    }));
                setEntities(nodeOptions);
            }

            // 2. 스키마(Predicate) 조회
            const schemaRes = await api.get('/ontology/studio/schema');
            if (schemaRes.data && schemaRes.data.mappings) {
                const predOptions = Object.entries(schemaRes.data.mappings).map(([key, val]: [string, any]) => ({
                    value: key,
                    label: val.label || key
                }));

                // 공통적으로 사용되는 관계 추가 (없을 경우)
                const commonPreds = ['coa:recommendedCOA', 'coa:respondsTo', 'coa:locatedIn', 'coa:hasStatus', 'coa:belongsTo'];
                commonPreds.forEach(p => {
                    if (!predOptions.find(opt => opt.value === p)) {
                        predOptions.push({ value: p, label: p });
                    }
                });

                setPredicates(predOptions);
            }
        } catch (err) {
            console.error('Failed to fetch suggestions', err);
        }
    }, []);

    useEffect(() => {
        fetchRelations();
        fetchSuggestions();
    }, [fetchRelations, fetchSuggestions]);

    // 검색 주체 변경 시 자동 조회
    useEffect(() => {
        fetchRelations(searchSubject);
    }, [searchSubject, fetchRelations]);

    // Link 'newTriple.subject' selection to 'searchSubject'
    const handleNewSubjectChange = (val: string) => {
        setNewTriple(prev => ({ ...prev, subject: val }));
        setSearchSubject(val); // Sync to browser search
    };

    const handleAddRelation = async () => {
        if (!newTriple.subject || !newTriple.predicate || !newTriple.object_val) return;
        try {
            const res = await api.post('/ontology/studio/relations', {
                subject: newTriple.subject,
                predicate: newTriple.predicate,
                object_val: newTriple.object_val
            });
            if (res.status === 200) {
                // Keep S and P for multi-add convenience
                setNewTriple(prev => ({ ...prev, object_val: '' }));
                fetchRelations(newTriple.subject); // Refresh current filter context
            }
        } catch (err) {
            console.error('Failed to add relation', err);
        }
    };

    const handleDeleteRelation = async (triple: Triple) => {
        if (!window.confirm('정말 이 관계를 삭제하시겠습니까?')) return;
        try {
            console.log("Deleting triple:", triple);
            const res = await api.delete('/ontology/studio/relations', {
                params: {
                    subject: triple.subject,
                    predicate: triple.predicate,
                    object_val: triple.object_val
                }
            });
            if (res.status === 200) {
                fetchRelations(searchSubject); // Refresh with current context
            }
        } catch (err) {
            console.error('Failed to delete relation', err);
        }
    };

    const columnDefs = [
        {
            field: 'subject',
            headerName: 'Subject (주체)',
            flex: 2,
            sortable: true,
            filter: true,
            cellRenderer: (p: any) => {
                const val = String(p.value || "");
                const label = val.split('#').pop() || val.split('/').pop() || val;
                return <span className="text-blue-400 font-mono text-xs" title={val}>{label}</span>
            }
        },
        {
            field: 'predicate',
            headerName: 'Predicate (속성)',
            flex: 2,
            sortable: true,
            filter: true,
            cellRenderer: (p: any) => {
                const val = String(p.value || "");
                const label = val.split('#').pop() || val.split('/').pop() || val;
                return <span className="text-zinc-400 font-bold text-xs" title={val}>{label}</span>
            }
        },
        {
            field: 'object_val',
            headerName: 'Object (대상)',
            flex: 2,
            sortable: true,
            filter: true,
            cellRenderer: (p: any) => {
                const val = String(p.value || "");
                const label = val.split('#').pop() || val.split('/').pop() || val;
                return <span className="text-cyan-400 font-bold text-xs" title={val}>{label}</span>
            }
        },
        {
            headerName: '관리',
            width: 80,
            cellRenderer: (params: any) => (
                <button
                    onClick={() => handleDeleteRelation(params.data)}
                    className="p-1 text-red-400 hover:text-red-300 transition-colors"
                >
                    <Trash2 className="w-4 h-4" />
                </button>
            )
        }
    ];

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Left: Add Relation Form */}
                <Card className="bg-zinc-900 border-zinc-800 lg:col-span-1 border-l-4 border-l-blue-500">
                    <CardHeader>
                        <CardTitle className="text-sm font-black flex items-center gap-2 uppercase tracking-widest">
                            <Plus className="w-4 h-4 text-blue-400" />
                            새 관계 생성
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="space-y-2">
                            <Label className="text-[10px] text-zinc-500 font-black uppercase flex items-center gap-1.5">
                                <Database className="w-3 h-3" /> 주체 (Subject)
                            </Label>
                            <Combobox
                                options={entities}
                                value={newTriple.subject}
                                onValueChange={handleNewSubjectChange}
                                placeholder="주체 엔티티 선택..."
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-[10px] text-zinc-500 font-black uppercase flex items-center gap-1.5">
                                <Link className="w-3 h-3" /> 속성 (Predicate)
                            </Label>
                            <Combobox
                                options={predicates}
                                value={newTriple.predicate}
                                onValueChange={(val) => setNewTriple({ ...newTriple, predicate: val })}
                                placeholder="관계 속성 선택..."
                            />
                        </div>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <Label className="text-[10px] text-zinc-500 font-black uppercase flex items-center gap-1.5">
                                    <Target className="w-3 h-3" /> 대상 (Object)
                                </Label>
                                <div className="flex items-center gap-1.5 cursor-pointer" onClick={() => setIsLiteral(!isLiteral)}>
                                    <div className={`w-3 h-3 rounded-sm border ${isLiteral ? 'bg-blue-500 border-blue-500' : 'border-zinc-700'}`} />
                                    <span className="text-[9px] text-zinc-500 font-bold uppercase">Literal</span>
                                </div>
                            </div>
                            {isLiteral ? (
                                <Input
                                    value={newTriple.object_val}
                                    onChange={(e) => setNewTriple({ ...newTriple, object_val: e.target.value })}
                                    placeholder="직접 텍스트 입력..."
                                    className="bg-zinc-950 border-zinc-800"
                                />
                            ) : (
                                <Combobox
                                    options={entities}
                                    value={newTriple.object_val}
                                    onValueChange={(val) => setNewTriple({ ...newTriple, object_val: val })}
                                    placeholder="대상 엔티티 선택..."
                                />
                            )}
                        </div>
                        <Button
                            onClick={handleAddRelation}
                            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-black py-6 transition-all shadow-lg shadow-blue-500/10"
                            disabled={!newTriple.subject || !newTriple.predicate || !newTriple.object_val}
                        >
                            RDF 트리플 저장
                        </Button>
                        <div className="p-3 bg-zinc-950/50 border border-zinc-800/50 rounded-lg">
                            <p className="text-[10px] text-zinc-500 leading-relaxed italic">
                                * 엔티티 선택 시 오른쪽 탐색기 내용이 자동 필터링되어 중복 입력을 방지할 수 있습니다.
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* Right: Relation Browser */}
                <Card className="bg-zinc-900 border-zinc-800 lg:col-span-3">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b border-zinc-800/50 mb-2">
                        <CardTitle className="text-sm font-black flex items-center gap-2 uppercase tracking-widest">
                            <RefreshCw className={`w-4 h-4 text-zinc-400 ${loading ? 'animate-spin' : ''}`} />
                            지식 그래프 트리플 탐색기
                        </CardTitle>
                        <div className="flex items-center gap-2 w-1/2">
                            <Label className="text-[10px] text-zinc-500 font-black uppercase whitespace-nowrap">Filter S:</Label>
                            <Combobox
                                options={[{ value: '', label: '전체 (All Subjects)' }, ...entities]}
                                value={searchSubject}
                                onValueChange={setSearchSubject}
                                placeholder="Subject 필터링..."
                                className="w-full"
                            />
                            <Button size="sm" variant="ghost" onClick={() => fetchRelations(searchSubject)} disabled={loading}>
                                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                            </Button>
                        </div>
                    </CardHeader>
                    <CardContent className="p-0">
                        <div style={{ height: 600, width: '100%' }}>
                            <AgGridReact
                                theme={themeQuartz.withParams({
                                    accentColor: "#3b82f6",
                                    backgroundColor: "#18181b",
                                    borderColor: "#27272a",
                                    borderRadius: 4,
                                    headerBackgroundColor: "#27272a",
                                    headerTextColor: "#94a3b8",
                                    textColor: "#e2e8f0",
                                    rowHoverColor: "#27272a",
                                })}
                                rowData={triples}
                                columnDefs={columnDefs}
                                defaultColDef={{
                                    resizable: true,
                                    sortable: true,
                                    filter: true,
                                    headerClass: 'text-[10px] font-black uppercase tracking-tighter'
                                }}
                            />
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
