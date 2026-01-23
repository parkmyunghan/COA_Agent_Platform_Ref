// frontend/src/components/knowledge/SPARQLQueryPanel.tsx
import React, { useState } from 'react';
import { Play, Download, Sparkles, ChevronDown, ChevronUp, Loader2, Copy, Check } from 'lucide-react';
import { AgGridReact } from 'ag-grid-react';
import { themeQuartz } from 'ag-grid-community';
import Editor from '@monaco-editor/react';
import api from '../../lib/api';

interface QueryResult {
    results: Record<string, any>[];
    count: number;
}

interface NLToSPARQLResponse {
    sparql: string;
    question: string;
    success: boolean;
    error?: string;
}

// 카테고리별 예시 질문
const SAMPLE_QUESTIONS: Record<string, string[]> = {
    "방책": [
        "모든 방책 목록을 보여줘",
        "공격용 방책에는 어떤 것들이 있어?",
        "방어 작전에 적합한 방책을 찾아줘",
        "반격 방책 목록을 알려줘"
    ],
    "아군": [
        "현재 가용한 아군 부대 목록",
        "아군 자산 정보를 보여줘",
        "기갑 부대는 어디에 배치되어 있어?",
        "포병 부대 목록과 위치를 알려줘"
    ],
    "적군": [
        "식별된 적 부대 현황",
        "적 기갑 부대 정보를 보여줘",
        "위협 수준이 높은 적 부대 목록",
        "동부 축선에 배치된 적 부대"
    ],
    "축선": [
        "모든 작전 축선 목록",
        "동부 주공축선 정보를 알려줘",
        "축선에 배치된 아군 부대",
        "조공 축선 목록"
    ],
    "위협": [
        "현재 위협 상황 목록",
        "위협 수준이 높은 상황 목록",
        "전면전 위협 목록",
        "공중 위협 관련 상황을 보여줘"
    ],
    "임무": [
        "모든 임무 목록을 보여줘",
        "방어 임무 현황을 알려줘",
        "공격 임무 목록",
        "임무와 관련된 축선 정보"
    ],
    "지형": [
        "지형셀 목록을 보여줘",
        "산악 지형에 해당하는 지역",
        "하천 지형 목록",
        "요충지인 지형 목록"
    ]
};

export default function SPARQLQueryPanel() {
    // 기본 상태
    const [query, setQuery] = useState(`PREFIX def: <http://coa-agent-platform.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?class WHERE { 
  ?class a owl:Class 
} LIMIT 50`);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [results, setResults] = useState<QueryResult | null>(null);

    // AI 도우미 상태
    const [naturalQuery, setNaturalQuery] = useState('');
    const [isConverting, setIsConverting] = useState(false);
    const [isAIHelperOpen, setIsAIHelperOpen] = useState(true);
    const [activeCategory, setActiveCategory] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);
    const [conversionSuccess, setConversionSuccess] = useState(false);
    const [previousQuery, setPreviousQuery] = useState('');
    const [lastExecutedInfo, setLastExecutedInfo] = useState<{ question?: string; query: string } | null>(null);

    // 자연어 → SPARQL 변환
    const convertToSPARQL = async () => {
        if (!naturalQuery.trim()) return;
        
        setIsConverting(true);
        setError(null);
        setConversionSuccess(false);
        setPreviousQuery(query); // 변환 전 쿼리 저장
        
        try {
            const response = await api.post<NLToSPARQLResponse>('/ontology/nl-to-sparql', {
                question: naturalQuery
            });
            
            if (response.data.success) {
                setQuery(response.data.sparql);
                setConversionSuccess(true);
                // 3초 후 성공 표시 제거
                setTimeout(() => setConversionSuccess(false), 3000);
            } else {
                setError(response.data.error || 'SPARQL 변환 실패');
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'SPARQL 변환 실패');
            console.error('NL to SPARQL error:', err);
        } finally {
            setIsConverting(false);
        }
    };

    // SPARQL 쿼리 실행
    const executeQuery = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.post<QueryResult>('/ontology/sparql', {
                query: query
            });
            setResults(response.data);
            // 실행 정보 저장 (자연어 질문이 있으면 함께 저장)
            setLastExecutedInfo({
                question: naturalQuery.trim() || undefined,
                query: query
            });
        } catch (err: any) {
            setError(err.response?.data?.detail || 'SPARQL 쿼리 실행 실패');
            console.error('SPARQL query error:', err);
        } finally {
            setLoading(false);
        }
    };

    // 예시 질문 선택
    const selectQuestion = (question: string) => {
        setNaturalQuery(question);
    };

    // 쿼리 복사
    const copyQuery = () => {
        navigator.clipboard.writeText(query);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    // URI 패턴 확인 함수
    const isUriValue = (value: any): boolean => {
        if (typeof value !== 'string') return false;
        return value.startsWith('http://') || value.startsWith('https://');
    };

    // AG-Grid 컬럼 정의 (순번 컬럼 포함, URI 필드 표시)
    const columnDefs = results && results.results.length > 0
        ? [
            {
                headerName: '#',
                valueGetter: (params: any) => params.node?.rowIndex != null ? params.node.rowIndex + 1 : '',
                width: 60,
                minWidth: 60,
                maxWidth: 80,
                sortable: false,
                filter: false,
                resizable: false,
                pinned: 'left' as const,
                cellStyle: { 
                    color: '#71717a', 
                    fontWeight: '500',
                    textAlign: 'center'
                }
            },
            ...Object.keys(results.results[0]).map(key => {
                // 첫 번째 유효한 값으로 URI 여부 판단
                const sampleValue = results.results.find(row => row[key] != null)?.[key];
                const isUri = isUriValue(sampleValue);
                
                return {
                    field: key,
                    headerName: isUri ? `${key} (URI)` : key,
                    minWidth: 150,
                    tooltipField: key,  // 마우스 오버 시 전체 내용 표시
                    sortable: true,
                    filter: true,
                    resizable: true,
                    // URI 필드는 약간 다른 스타일 적용
                    cellStyle: isUri ? { color: '#a78bfa', fontSize: '12px' } : undefined
                };
            })
        ]
        : [];

    return (
        <div className="space-y-4">
            {/* AI 쿼리 도우미 */}
            <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 p-4 rounded-xl border border-purple-700/50">
                <div 
                    className="flex items-center justify-between cursor-pointer"
                    onClick={() => setIsAIHelperOpen(!isAIHelperOpen)}
                >
                    <div className="flex items-center gap-2">
                        <Sparkles className="w-5 h-5 text-purple-400" />
                        <h3 className="text-sm font-bold text-purple-300">AI 쿼리 도우미</h3>
                        <span className="text-xs text-purple-400/70">자연어로 질문하면 SPARQL로 변환해 드립니다</span>
                    </div>
                    {isAIHelperOpen ? (
                        <ChevronUp className="w-5 h-5 text-purple-400" />
                    ) : (
                        <ChevronDown className="w-5 h-5 text-purple-400" />
                    )}
                </div>

                {isAIHelperOpen && (
                    <div className="mt-4 space-y-4">
                        {/* 자연어 입력 */}
                        <div className="flex gap-2">
                            <textarea
                                value={naturalQuery}
                                onChange={(e) => setNaturalQuery(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        convertToSPARQL();
                                    }
                                }}
                                placeholder="예: 공격용 방책 목록을 보여줘"
                                className="flex-1 h-16 bg-zinc-900/50 border border-purple-700/30 rounded-lg p-3 text-sm text-zinc-200 placeholder-zinc-500 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none resize-none"
                            />
                            <button
                                onClick={convertToSPARQL}
                                disabled={isConverting || !naturalQuery.trim()}
                                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-zinc-700 disabled:text-zinc-500 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 h-16"
                            >
                                {isConverting ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        <span>변환 중...</span>
                                    </>
                                ) : (
                                    <>
                                        <Sparkles className="w-4 h-4" />
                                        <span>SPARQL 변환</span>
                                    </>
                                )}
                            </button>
                        </div>

                        {/* 카테고리별 예시 질문 */}
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <span className="text-xs text-purple-400">💡 예시 질문:</span>
                                <div className="flex flex-wrap gap-1">
                                    {Object.keys(SAMPLE_QUESTIONS).map((category) => (
                                        <button
                                            key={category}
                                            onClick={() => setActiveCategory(activeCategory === category ? null : category)}
                                            className={`px-2 py-1 text-xs rounded-md transition-colors ${
                                                activeCategory === category
                                                    ? 'bg-purple-600 text-white'
                                                    : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-300'
                                            }`}
                                        >
                                            {category}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* 선택된 카테고리의 질문 표시 */}
                            {activeCategory && (
                                <div className="flex flex-wrap gap-2 mt-2 p-3 bg-zinc-900/50 rounded-lg border border-zinc-800">
                                    {SAMPLE_QUESTIONS[activeCategory].map((question, idx) => (
                                        <button
                                            key={idx}
                                            onClick={() => selectQuestion(question)}
                                            className="px-3 py-1.5 bg-zinc-800 hover:bg-purple-700/50 border border-zinc-700 hover:border-purple-600 rounded-lg text-xs text-zinc-300 hover:text-white transition-all"
                                        >
                                            {question}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* SPARQL 쿼리 에디터 */}
            <div className={`bg-zinc-900 p-4 rounded-lg border transition-colors duration-300 ${
                conversionSuccess 
                    ? 'border-green-500 shadow-lg shadow-green-500/20' 
                    : isConverting 
                        ? 'border-purple-500' 
                        : 'border-zinc-800'
            }`}>
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                        <h3 className="text-sm font-semibold text-zinc-300">📝 SPARQL 쿼리</h3>
                        {/* 변환 상태 표시 */}
                        {isConverting && (
                            <div className="flex items-center gap-2 px-3 py-1 bg-purple-600/20 border border-purple-500/50 rounded-full animate-pulse">
                                <Loader2 className="w-3.5 h-3.5 text-purple-400 animate-spin" />
                                <span className="text-xs text-purple-300 font-medium">AI가 SPARQL로 변환 중...</span>
                            </div>
                        )}
                        {conversionSuccess && !isConverting && (
                            <div className="flex items-center gap-2 px-3 py-1 bg-green-600/20 border border-green-500/50 rounded-full">
                                <Check className="w-3.5 h-3.5 text-green-400" />
                                <span className="text-xs text-green-300 font-medium">변환 완료!</span>
                            </div>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={copyQuery}
                            className="flex items-center gap-1 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded text-xs transition-colors"
                            title="쿼리 복사"
                        >
                            {copied ? (
                                <>
                                    <Check className="w-3.5 h-3.5 text-green-400" />
                                    <span className="text-green-400">복사됨</span>
                                </>
                            ) : (
                                <>
                                    <Copy className="w-3.5 h-3.5" />
                                    <span>복사</span>
                                </>
                            )}
                        </button>
                        <button
                            onClick={executeQuery}
                            disabled={loading || isConverting}
                            className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:text-zinc-500 rounded text-sm font-medium transition-colors"
                        >
                            {loading ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <Play className="w-4 h-4" />
                            )}
                            {loading ? '실행 중...' : '실행'}
                        </button>
                    </div>
                </div>

                {/* 에디터 영역 (변환 중 오버레이 포함) */}
                <div className="relative h-56 border border-zinc-700 rounded overflow-hidden">
                    <Editor
                        height="100%"
                        defaultLanguage="sparql"
                        theme="vs-dark"
                        value={query}
                        onChange={(value) => setQuery(value || '')}
                        options={{
                            minimap: { enabled: false },
                            fontSize: 13,
                            scrollBeyondLastLine: false,
                            automaticLayout: true,
                            padding: { top: 10, bottom: 10 },
                            lineNumbers: 'on',
                            wordWrap: 'on',
                            readOnly: isConverting // 변환 중에는 읽기 전용
                        }}
                    />
                    
                    {/* 변환 중 오버레이 */}
                    {isConverting && (
                        <div className="absolute inset-0 bg-zinc-900/70 backdrop-blur-sm flex flex-col items-center justify-center z-10">
                            <div className="flex flex-col items-center gap-3 p-6 bg-zinc-800/90 rounded-xl border border-purple-500/50 shadow-xl">
                                <Sparkles className="w-8 h-8 text-purple-400 animate-pulse" />
                                <div className="text-center">
                                    <p className="text-purple-300 font-medium">AI가 SPARQL 쿼리를 생성하고 있습니다</p>
                                    <p className="text-xs text-zinc-400 mt-1">잠시만 기다려 주세요...</p>
                                </div>
                                <div className="flex gap-1 mt-2">
                                    <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                    <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                    <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* 에러 메시지 */}
            {error && (
                <div className="bg-red-900/20 border border-red-800 text-red-400 p-4 rounded-lg">
                    <p className="font-semibold">⚠️ 오류:</p>
                    <p className="text-sm mt-1">{error}</p>
                </div>
            )}

            {/* 결과 */}
            {results && (
                <div className="bg-zinc-900 p-4 rounded-lg border border-zinc-800">
                    {/* 쿼리 실행 정보 */}
                    {lastExecutedInfo && (
                        <div className="mb-3 p-3 bg-zinc-800/50 rounded-lg border border-zinc-700">
                            {lastExecutedInfo.question ? (
                                <div className="flex items-start gap-2">
                                    <Sparkles className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
                                    <div>
                                        <span className="text-xs text-zinc-500">자연어 질문:</span>
                                        <p className="text-sm text-purple-300 font-medium">"{lastExecutedInfo.question}"</p>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex items-start gap-2">
                                    <Play className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                                    <div>
                                        <span className="text-xs text-zinc-500">실행된 쿼리:</span>
                                        <p className="text-sm text-zinc-300 font-mono truncate max-w-full">
                                            {lastExecutedInfo.query.split('\n').find(line => line.trim().toUpperCase().startsWith('SELECT')) || lastExecutedInfo.query.split('\n')[0]}
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                    
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-sm font-semibold text-zinc-300">
                            📊 결과 ({results.count}개)
                        </h3>
                        {results.results.length > 0 && (
                            <button
                                onClick={() => {
                                    // Download as CSV
                                    const csv = [
                                        Object.keys(results.results[0]).join(','),
                                        ...results.results.map(row =>
                                            Object.values(row).map(v => typeof v === 'string' && v.includes(',') ? `"${v}"` : v).join(',')
                                        )
                                    ].join('\n');
                                    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
                                    const url = URL.createObjectURL(blob);
                                    const a = document.createElement('a');
                                    a.href = url;
                                    a.download = 'sparql_results.csv';
                                    a.click();
                                    URL.revokeObjectURL(url);
                                }}
                                className="flex items-center gap-2 px-3 py-1 bg-zinc-800 hover:bg-zinc-700 rounded text-sm transition-colors"
                            >
                                <Download className="w-4 h-4" />
                                CSV 다운로드
                            </button>
                        )}
                    </div>

                    {results.results.length > 0 ? (
                        <div style={{ height: 400, width: '100%', overflowX: 'auto' }}>
                            <AgGridReact
                                theme={themeQuartz.withParams({
                                    accentColor: "#3b82f6",
                                    backgroundColor: "#18181b",
                                    borderColor: "#27272a",
                                    borderRadius: 4,
                                    headerBackgroundColor: "#27272a",
                                    headerTextColor: "#d4d4d4",
                                    textColor: "#e5e7eb",
                                })}
                                rowData={results.results}
                                columnDefs={columnDefs}
                                defaultColDef={{
                                    minWidth: 150,
                                    sortable: true,
                                    filter: true,
                                    resizable: true,
                                    wrapHeaderText: true,
                                    autoHeaderHeight: true
                                }}
                                pagination={false}
                                suppressPaginationPanel={true}
                                domLayout="normal"
                                tooltipShowDelay={300}
                                enableCellTextSelection={true}
                            />
                        </div>
                    ) : (
                        <div className="text-center py-8 text-zinc-500">
                            <p>결과가 없습니다</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
