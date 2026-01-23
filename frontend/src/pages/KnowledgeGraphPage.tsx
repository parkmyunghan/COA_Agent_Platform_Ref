// frontend/src/pages/KnowledgeGraphPage.tsx
import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import SPARQLQueryPanel from '../components/knowledge/SPARQLQueryPanel';
import GraphExplorerPanel from '../components/knowledge/GraphExplorerPanel';
import SchemaValidationPanel from '../components/knowledge/SchemaValidationPanel';

import { Layout } from '../components/Layout';

export default function KnowledgeGraphPage() {
    return (
        <Layout>
            <div className="h-full flex flex-col">
                {/* Information Header (optional context) */}
                <div className="mb-6 p-4 bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30 rounded-xl">
                    <p className="text-sm text-blue-700 dark:text-blue-300 font-medium">
                        💡 온톨로지 지식 베이스를 직접 조회하거나 그래프 구조를 시각적으로 탐색할 수 있습니다.
                    </p>
                </div>

                {/* Tabs */}
                <Tabs defaultValue="sparql" className="flex-1 flex flex-col min-h-0">
                    <TabsList className="grid w-full grid-cols-3 bg-zinc-100 dark:bg-zinc-900 p-1 rounded-xl h-auto">
                        <TabsTrigger
                            value="sparql"
                            className="py-2.5 data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-800 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 data-[state=active]:shadow-sm rounded-lg font-bold transition-all"
                        >
                            🔍 SPARQL 쿼리
                        </TabsTrigger>
                        <TabsTrigger
                            value="graph"
                            className="py-2.5 data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-800 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 data-[state=active]:shadow-sm rounded-lg font-bold transition-all"
                        >
                            🕸️ 그래프 탐색
                        </TabsTrigger>
                        <TabsTrigger
                            value="validation"
                            className="py-2.5 data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-800 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 data-[state=active]:shadow-sm rounded-lg font-bold transition-all"
                        >
                            📊 스키마 검증
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="sparql" className="mt-6 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar">
                        <SPARQLQueryPanel />
                    </TabsContent>

                    <TabsContent value="graph" className="mt-6 flex-1 min-h-0 overflow-hidden">
                        <GraphExplorerPanel />
                    </TabsContent>

                    <TabsContent value="validation" className="mt-6 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar">
                        <SchemaValidationPanel />
                    </TabsContent>
                </Tabs>
            </div>
        </Layout>
    );
}
