import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Layout } from '../components/Layout';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Upload, FileText, Database, Search, RefreshCw, X, CheckCircle, AlertCircle } from 'lucide-react';

interface DocumentInfo {
    filename: string;
    size_kb: number;
    modified_at: string;
    is_indexed: boolean;
}

export default function RAGManagementPage() {
    const [status, setStatus] = useState<any>(null);
    const [documents, setDocuments] = useState<DocumentInfo[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<any[]>([]);
    const [searching, setSearching] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [reindexing, setReindexing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchStatus();
        fetchDocuments();
    }, []);

    const fetchStatus = async () => {
        try {
            const res = await fetch(`http://${window.location.hostname}:8000/api/v1/rag/status`);
            const data = await res.json();
            setStatus(data);
        } catch (err) {
            console.error('Failed to fetch RAG status', err);
        }
    };

    const fetchDocuments = async () => {
        try {
            const res = await fetch(`http://${window.location.hostname}:8000/api/v1/rag/documents`);
            if (res.ok) {
                const data = await res.json();
                setDocuments(data);
            }
        } catch (err) {
            console.error('Failed to fetch documents', err);
        }
    };

    const handleSearch = async () => {
        if (!searchQuery) return;
        setSearching(true);
        setError(null);
        try {
            const res = await fetch(`http://${window.location.hostname}:8000/api/v1/rag/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: searchQuery, top_k: 5 })
            });
            const data = await res.json();
            if (res.ok) {
                setSearchResults(data);
            } else {
                setError(data.detail || '검색 실패');
            }
        } catch (err) {
            setError('RAG 검색 중 오류가 발생했습니다.');
        } finally {
            setSearching(false);
        }
    };

    const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        setUploading(true);
        setError(null);
        try {
            const res = await fetch(`http://${window.location.hostname}:8000/api/v1/rag/upload`, {
                method: 'POST',
                body: formData
            });
            if (res.ok) {
                await fetchDocuments();
                // Reset file input
                event.target.value = '';
            } else {
                const data = await res.json();
                setError(data.detail || '업로드 실패');
            }
        } catch (err) {
            setError('파일 업로드 중 오류가 발생했습니다.');
        } finally {
            setUploading(false);
        }
    };

    const handleReindex = async () => {
        if (!window.confirm('전체 인덱스를 재구성하시겠습니까? 문서 수에 따라 시간이 걸릴 수 있습니다.')) return;

        setReindexing(true);
        setError(null);
        try {
            const res = await fetch(`http://${window.location.hostname}:8000/api/v1/rag/reindex`, {
                method: 'POST'
            });
            const data = await res.json();
            if (res.ok) {
                await fetchStatus();
                await fetchDocuments();
                alert(`인덱스 재구축 완료: 총 ${data.total_chunks} 청크 생성`);
            } else {
                setError(data.detail || '인덱스 재구축 실패');
            }
        } catch (err) {
            setError('인덱싱 과정에서 오류가 발생했습니다.');
        } finally {
            setReindexing(false);
        }
    };

    return (
        <Layout>
            <div className="h-full flex flex-col">
                {/* Information Header */}
                <div className="mb-6 p-4 bg-cyan-50/50 dark:bg-cyan-900/10 border border-cyan-100 dark:border-cyan-900/30 rounded-xl">
                    <p className="text-sm text-cyan-700 dark:text-cyan-300 font-medium">
                        🔍 RAG(Retrieval-Augmented Generation) 지식 베이스를 관리하고 시맨틱 검색을 테스트할 수 있습니다.
                    </p>
                </div>

                {/* Status Dashboard Summary */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <Card className="bg-white dark:bg-zinc-900 border-gray-200 dark:border-zinc-800 shadow-sm">
                        <CardHeader className="pb-1 pt-3">
                            <CardTitle className="text-[10px] uppercase text-gray-400 font-black tracking-widest">엔진 상태</CardTitle>
                        </CardHeader>
                        <CardContent className="pb-3">
                            <div className={`text-sm font-black flex items-center gap-2 ${status?.is_available ? 'text-green-500' : 'text-red-500'}`}>
                                <div className={`w-2 h-2 rounded-full ${status?.is_available ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                                {status?.is_available ? 'OPERATIONAL' : 'OFFLINE'}
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="bg-white dark:bg-zinc-900 border-gray-200 dark:border-zinc-800 shadow-sm">
                        <CardHeader className="pb-1 pt-3">
                            <CardTitle className="text-[10px] uppercase text-gray-400 font-black tracking-widest">인덱싱 청크</CardTitle>
                        </CardHeader>
                        <CardContent className="pb-3">
                            <div className="text-lg font-black text-gray-900 dark:text-zinc-100">{status?.index_count?.toLocaleString() || 0} <span className="text-[10px] text-gray-400">units</span></div>
                        </CardContent>
                    </Card>
                    <Card className="bg-white dark:bg-zinc-900 border-gray-200 dark:border-zinc-800 shadow-sm">
                        <CardHeader className="pb-1 pt-3">
                            <CardTitle className="text-[10px] uppercase text-gray-400 font-black tracking-widest">소스 문서</CardTitle>
                        </CardHeader>
                        <CardContent className="pb-3">
                            <div className="text-lg font-black text-gray-900 dark:text-zinc-100">{status?.sources?.length || 0} <span className="text-[10px] text-gray-400">docs</span></div>
                        </CardContent>
                    </Card>
                </div>

                {error && (
                    <div className="mb-6 p-4 bg-red-900/20 border border-red-800 text-red-400 rounded-lg flex items-center gap-2">
                        <AlertCircle className="w-5 h-5 flex-shrink-0" />
                        <span className="text-sm font-medium">{error}</span>
                    </div>
                )}

                <Tabs defaultValue="search" className="flex-1 flex flex-col min-h-0">
                    <TabsList className="grid w-full grid-cols-2 bg-zinc-100 dark:bg-zinc-900 p-1 rounded-xl h-auto shrink-0">
                        <TabsTrigger value="search" className="py-2.5 data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-800 data-[state=active]:text-cyan-600 dark:data-[state=active]:text-cyan-400 rounded-lg font-bold transition-all flex items-center gap-2">
                            <Search className="w-4 h-4" /> 검색 테스트
                        </TabsTrigger>
                        <TabsTrigger value="documents" className="py-2.5 data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-800 data-[state=active]:text-cyan-600 dark:data-[state=active]:text-cyan-400 rounded-lg font-bold transition-all flex items-center gap-2">
                            <FileText className="w-4 h-4" /> 문서 관리
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="search" className="mt-6 flex-1 flex flex-col min-h-0 overflow-y-auto pr-2 space-y-4 custom-scrollbar">
                        <div className="flex gap-2 shrink-0">
                            <Input
                                placeholder="검색어를 입력하세요 (예: 보병부대 전술)"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="bg-zinc-950 border-zinc-800 text-zinc-100"
                                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                            />
                            <Button onClick={handleSearch} disabled={searching} className="bg-cyan-600 hover:bg-cyan-700">
                                {searching ? <RefreshCw className="w-4 h-4 animate-spin" /> : '검색'}
                            </Button>
                        </div>

                        <div className="space-y-4">
                            {searchResults.length === 0 && !searching && (
                                <div className="text-center py-20 bg-zinc-900/30 rounded-xl border border-dashed border-zinc-800 text-zinc-500">
                                    <Search className="w-12 h-12 mx-auto mb-4 opacity-20" />
                                    검색어를 입력하여 지식 베이스 검색 결과를 테스트하세요.
                                </div>
                            )}
                            {searchResults.map((res, i) => (
                                <Card key={i} className="bg-zinc-900 border-zinc-800 hover:border-cyan-900/50 transition-colors">
                                    <CardContent className="pt-4">
                                        <div className="flex justify-between items-start mb-2 text-[10px]">
                                            <div className="flex items-center gap-2">
                                                <span className="px-1.5 py-0.5 bg-cyan-900/30 text-cyan-400 rounded font-mono">Score: {res.score.toFixed(4)}</span>
                                                <span className="text-zinc-500">{res.metadata?.source || 'Unknown'}</span>
                                            </div>
                                            {res.metadata?.statement_id && (
                                                <span className="text-cyan-600 font-mono">{res.metadata.statement_id}</span>
                                            )}
                                        </div>
                                        <div className="text-zinc-300 text-sm leading-relaxed whitespace-pre-wrap">{res.text}</div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </TabsContent>

                    <TabsContent value="documents" className="mt-6 flex-1 flex flex-col min-h-0 overflow-y-auto pr-2 custom-scrollbar">
                        <div className="flex justify-between items-center mb-4 shrink-0">
                            <div className="flex gap-2">
                                <Button className="bg-cyan-600 hover:bg-cyan-700 relative overflow-hidden" disabled={uploading}>
                                    <input
                                        type="file"
                                        className="absolute inset-0 opacity-0 cursor-pointer"
                                        onChange={handleFileUpload}
                                        accept=".txt,.md,.pdf,.docx"
                                    />
                                    {uploading ? <RefreshCw className="w-4 h-4 animate-spin mr-2" /> : <Upload className="w-4 h-4 mr-2" />}
                                    문서 업로드
                                </Button>
                                <Button variant="outline" className="border-zinc-800 text-zinc-300 hover:bg-zinc-800" onClick={handleReindex} disabled={reindexing}>
                                    {reindexing ? <RefreshCw className="w-4 h-4 animate-spin mr-2" /> : <Database className="w-4 h-4 mr-2" />}
                                    인덱스 재구축
                                </Button>
                            </div>
                            <Button variant="ghost" className="text-zinc-500 hover:text-zinc-300" onClick={fetchStatus}>
                                <RefreshCw className="w-4 h-4" />
                            </Button>
                        </div>

                        <Card className="bg-zinc-900 border-zinc-800 flex-1 flex flex-col min-h-0">
                            <CardHeader className="py-4 border-b border-zinc-800 shrink-0">
                                <CardTitle className="text-sm font-bold flex items-center justify-between text-zinc-300">
                                    <span>업로드된 문서 목록</span>
                                    <span className="text-xs font-normal text-zinc-500">{documents.length} files</span>
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-0 overflow-auto">
                                {documents.length === 0 ? (
                                    <div className="text-center py-20 text-zinc-600">
                                        업로드된 문서가 없습니다.
                                    </div>
                                ) : (
                                    <div className="divide-y divide-zinc-800/50">
                                        {documents.map((doc, i) => (
                                            <div key={i} className="px-4 py-3 hover:bg-white/5 transition-colors flex items-center justify-between group">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded bg-zinc-950 flex items-center justify-center text-zinc-400 group-hover:text-cyan-500 transition-colors">
                                                        <FileText className="w-4 h-4" />
                                                    </div>
                                                    <div>
                                                        <div className="text-sm font-medium text-zinc-200">{doc.filename}</div>
                                                        <div className="text-[10px] text-zinc-500 flex items-center gap-2">
                                                            <span>{(doc.size_kb).toFixed(1)} KB</span>
                                                            <span>•</span>
                                                            <span>{doc.modified_at}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-4">
                                                    {doc.is_indexed ? (
                                                        <div className="flex items-center gap-1.5 text-xs text-green-500/80 bg-green-500/10 px-2 py-0.5 rounded-full border border-green-500/20">
                                                            <CheckCircle className="w-3 h-3" /> Indexed
                                                        </div>
                                                    ) : (
                                                        <div className="flex items-center gap-1.5 text-xs text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-full">
                                                            <RefreshCw className="w-3 h-3" /> Pending
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>
            </div>
        </Layout>
    );
}
