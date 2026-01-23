// frontend/src/pages/DataManagementPage.tsx
import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import DataGridPanel from '../components/data/DataGridPanel';
import DataQualityPanel from '../components/data/DataQualityPanel';

import { Layout } from '../components/Layout';

export default function DataManagementPage() {
    return (
        <Layout>
            <div className="h-full flex flex-col">
                {/* Information Header */}
                <div className="mb-6 p-4 bg-emerald-50/50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-900/30 rounded-xl">
                    <p className="text-sm text-emerald-700 dark:text-emerald-300 font-medium">
                        🛠️ 엑셀 및 다양한 소스 데이터를 플랫폼에 주입하고 품질을 검증할 수 있는 관리 영역입니다.
                    </p>
                </div>

                {/* Tabs */}
                <Tabs defaultValue="grid" className="flex-1 flex flex-col min-h-0">
                    <TabsList className="grid w-full grid-cols-2 bg-zinc-100 dark:bg-zinc-900 p-1 rounded-xl h-auto">
                        <TabsTrigger
                            value="grid"
                            className="py-2.5 data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-800 data-[state=active]:text-emerald-600 dark:data-[state=active]:text-emerald-400 data-[state=active]:shadow-sm rounded-lg font-bold transition-all"
                        >
                            📊 데이터 그리드
                        </TabsTrigger>
                        <TabsTrigger
                            value="quality"
                            className="py-2.5 data-[state=active]:bg-white dark:data-[state=active]:bg-zinc-800 data-[state=active]:text-emerald-600 dark:data-[state=active]:text-emerald-400 data-[state=active]:shadow-sm rounded-lg font-bold transition-all"
                        >
                            ✅ 품질 검증
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="grid" className="mt-6 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar">
                        <DataGridPanel />
                    </TabsContent>

                    <TabsContent value="quality" className="mt-6 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar">
                        <DataQualityPanel />
                    </TabsContent>
                </Tabs>
            </div>
        </Layout>
    );
}
