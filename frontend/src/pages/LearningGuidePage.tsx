// frontend/src/pages/LearningGuidePage.tsx
import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Layout } from '../components/Layout';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { ChevronRight, FileText, Globe, BookOpen } from 'lucide-react';

export default function LearningGuidePage() {
    const [categories, setCategories] = useState<any>({});
    const [selectedDoc, setSelectedDoc] = useState<any>(null);
    const [content, setContent] = useState<string>('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchDocs();
    }, []);

    const fetchDocs = async () => {
        try {
            const res = await fetch('http://localhost:8000/api/v1/system/docs');
            const data = await res.json();
            setCategories(data.categories || {});
        } catch (err) {
            console.error('Failed to fetch docs', err);
        }
    };

    const handleSelectDoc = async (doc: any) => {
        setSelectedDoc(doc);
        setLoading(true);
        try {
            const res = await fetch(`http://${window.location.hostname}:8000/api/v1/system/docs/content?path=${doc.path}`);
            const data = await res.json();
            setContent(data.content || '');
        } catch (err) {
            console.error('Failed to fetch content', err);
            setContent('문서를 불러오는데 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Layout>
            <div className="flex h-full gap-6 overflow-hidden">
                {/* 좌측: 문서 내비게이션 */}
                <div className="w-80 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 flex flex-col overflow-y-auto rounded-2xl shadow-sm">
                    <div className="p-5 border-b border-gray-100 dark:border-zinc-800 bg-gray-50/50 dark:bg-zinc-900/50">
                        <h2 className="flex items-center gap-2 text-sm font-black text-gray-900 dark:text-zinc-100 uppercase tracking-widest">
                            <BookOpen className="w-4 h-4 text-indigo-500" />
                            Library Index
                        </h2>
                    </div>
                    <div className="flex-1 p-2 space-y-4">
                        {Object.keys(categories).sort().map((cat) => (
                            <div key={cat} className="space-y-1">
                                <h3 className="px-3 py-2 text-xs font-bold text-zinc-500 uppercase tracking-widest">{cat}</h3>
                                {categories[cat].map((doc: any) => (
                                    <button
                                        key={doc.path}
                                        onClick={() => handleSelectDoc(doc)}
                                        className={`w-full text-left px-3 py-2 rounded text-sm transition-all flex items-center justify-between group
                                            ${selectedDoc?.path === doc.path
                                                ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30'
                                                : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200'}`}
                                    >
                                        <div className="flex items-center gap-2 overflow-hidden">
                                            {doc.type === 'html' ? <Globe className="w-4 h-4 flex-shrink-0" /> : <FileText className="w-4 h-4 flex-shrink-0" />}
                                            <span className="truncate">{doc.name.replace('.md', '').replace('.html', '').replace(/_/g, ' ')}</span>
                                        </div>
                                        <ChevronRight className={`w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity ${selectedDoc?.path === doc.path ? 'opacity-100' : ''}`} />
                                    </button>
                                ))}
                            </div>
                        ))}
                    </div>
                </div>

                {/* 우측: 컨텐츠 뷰어 */}
                <div className="flex-1 flex flex-col bg-white dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-zinc-800 shadow-sm overflow-hidden">
                    {selectedDoc ? (
                        <div className="flex flex-col h-full">
                            <div className="p-4 border-b border-zinc-800 bg-zinc-900/50 flex justify-between items-center">
                                <h1 className="text-xl font-bold text-zinc-100 truncate flex items-center gap-3">
                                    <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-500 font-mono uppercase">{selectedDoc.type}</span>
                                    {selectedDoc.name}
                                </h1>
                                <Button
                                    variant="ghost"
                                    className="text-zinc-500 hover:text-zinc-300"
                                    onClick={() => setSelectedDoc(null)}
                                >
                                    닫기
                                </Button>
                            </div>

                            <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
                                {loading ? (
                                    <div className="flex items-center justify-center h-full">
                                        <div className="animate-pulse text-zinc-500 font-mono">Loading documentation...</div>
                                    </div>
                                ) : (
                                    selectedDoc.type === 'html' ? (
                                        <iframe
                                            srcDoc={content}
                                            className="w-full h-full border-0 bg-white rounded shadow-inner"
                                            title={selectedDoc.name}
                                        />
                                    ) : (
                                        <div className="prose prose-invert prose-zinc w-full">
                                            <ReactMarkdown
                                                components={{
                                                    h1: ({ node, ...props }) => <h1 className="text-4xl font-extrabold text-white mb-6 border-b border-zinc-800 pb-4" {...props} />,
                                                    h2: ({ node, ...props }) => <h2 className="text-2xl font-bold text-blue-400 mt-10 mb-4" {...props} />,
                                                    h3: ({ node, ...props }) => <h3 className="text-xl font-semibold text-zinc-200 mt-8 mb-3" {...props} />,
                                                    p: ({ node, ...props }) => <p className="text-zinc-400 leading-relaxed mb-4" {...props} />,
                                                    code: ({ node, className, children, ...props }) => (
                                                        <code className="bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-300 font-mono text-sm" {...props}>
                                                            {children}
                                                        </code>
                                                    ),
                                                    pre: ({ node, ...props }) => <pre className="bg-zinc-900 p-4 rounded-lg border border-zinc-800 overflow-x-auto my-6" {...props} />,
                                                    li: ({ node, ...props }) => <li className="text-zinc-400 mb-2" {...props} />,
                                                }}
                                            >
                                                {content}
                                            </ReactMarkdown>
                                        </div>
                                    )
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
                            <BookOpen className="w-24 h-24 text-zinc-800 animate-bounce" />
                            <div>
                                <h3 className="text-2xl font-bold text-zinc-400">문서를 선택해 주세요</h3>
                                <p className="text-zinc-600 mt-2">좌측 메뉴에서 시스템 소개 및 가이드 문서를 찾아 열람할 수 있습니다.</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <style>{`
                .custom-scrollbar::-webkit-scrollbar {
                    width: 8px;
                }
                .custom-scrollbar::-webkit-scrollbar-track {
                    background: transparent;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: #27272a;
                    border-radius: 4px;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover {
                    background: #3f3f46;
                }
                .prose pre code {
                    background: transparent !important;
                    padding: 0 !important;
                }
            `}</style>
        </Layout>
    );
}
