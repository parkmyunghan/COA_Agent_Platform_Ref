import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/card';

interface SchemaDetailsPanelProps {
    nodeId?: string | null;
}

export default function SchemaDetailsPanel({ nodeId }: SchemaDetailsPanelProps) {
    const [schema, setSchema] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [manualFilter, setManualFilter] = useState<string | null>(null);

    // Reset manual filter when nodeId changes
    useEffect(() => {
        setManualFilter(null);
    }, [nodeId]);

    useEffect(() => {
        const fetchSchema = async () => {
            try {
                const res = await fetch(`http://${window.location.hostname}:8000/api/v1/ontology/studio/schema`);
                const data = await res.json();
                setSchema(data);
            } catch (err) {
                console.error('Failed to fetch schema', err);
            } finally {
                setLoading(false);
            }
        };
        fetchSchema();
    }, []);

    if (loading) {
        return <div className="text-zinc-500 italic p-8 text-center animate-pulse">스키마 정보를 불러오고 있습니다...</div>;
    }

    if (!schema) {
        return <div className="text-red-500 p-8 text-center">스키마 정보를 불러오지 못했습니다.</div>;
    }

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Relation Mappings */}
            <div className="space-y-6">
                <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-black text-xs text-zinc-500 uppercase tracking-[0.2em]">데이터-온톨로지 매핑 (Mappings)</h3>
                    <div className="h-px flex-1 bg-zinc-800" />
                </div>
                <div className="grid grid-cols-1 gap-4">
                    {(() => {
                        // mappings is a List<Dict>, so we iterate it directly
                        const mappingList = Array.isArray(schema.mappings) ? schema.mappings : [];

                        // Use manual filter if selected, otherwise use nodeId
                        const effectiveFilter = manualFilter || nodeId;

                        const filteredMappings = mappingList.filter((m: any) => {
                            if (!effectiveFilter) return true;
                            // Check relevant fields for the filter
                            const checkStr = (val: any) => String(val || '').toLowerCase();
                            const filterLower = effectiveFilter.toLowerCase();

                            return checkStr(m.src_table).includes(filterLower) ||
                                checkStr(m.tgt_table).includes(filterLower) ||
                                checkStr(m.relation).includes(filterLower) ||
                                checkStr(effectiveFilter).includes(checkStr(m.src_table)) ||
                                checkStr(effectiveFilter).includes(checkStr(m.tgt_table));
                        });

                        // Header for manual filter state
                        const FilterHeader = manualFilter ? (
                            <div className="flex items-center justify-between bg-blue-900/20 border border-blue-800/50 p-2 rounded mb-2">
                                <span className="text-xs text-blue-200">
                                    Filtered by: <strong className="text-white">{manualFilter}</strong>
                                </span>
                                <button
                                    onClick={() => setManualFilter(null)}
                                    className="text-xs text-blue-400 hover:text-blue-300 underline"
                                >
                                    Clear Filter
                                </button>
                            </div>
                        ) : null;

                        if (filteredMappings.length === 0) {
                            return (
                                <div>
                                    {FilterHeader}
                                    <div className="text-zinc-500 italic text-sm p-4 border border-dashed border-zinc-800 rounded text-center">
                                        <p>No mappings found for "{effectiveFilter}"</p>
                                        <div className="mt-4 text-xs text-zinc-600">
                                            <p className="font-bold mb-2 text-zinc-500">Try selecting a related Schema Table:</p>
                                            <div className="flex flex-wrap justify-center gap-1.5">
                                                {Array.from(new Set(mappingList.map((m: any) => m.src_table))).slice(0, 30).map((k: any) => (
                                                    <button
                                                        key={k}
                                                        onClick={() => setManualFilter(k)}
                                                        className="bg-zinc-800 hover:bg-zinc-700 hover:text-white px-2 py-1 rounded text-zinc-400 transition-colors border border-zinc-700/50"
                                                    >
                                                        {k}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            );
                        }

                        return (
                            <div>
                                {FilterHeader}
                                {filteredMappings.map((mapping: any, idx: number) => (
                                    <Card key={idx} className="bg-zinc-900 border-zinc-800 overflow-hidden group hover:border-zinc-700 transition-all mb-4 last:mb-0">
                                        <CardHeader className="p-4 bg-zinc-950/50 border-b border-zinc-800">
                                            <CardTitle className="text-sm font-black text-zinc-200 font-mono">
                                                {mapping.src_table} → {mapping.relation} → {mapping.tgt_table}
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent className="p-4">
                                            <pre className="text-xs text-zinc-400 font-mono overflow-x-auto">
                                                {JSON.stringify(mapping, null, 2)}
                                            </pre>
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        );
                    })()}
                </div>
            </div>

            {/* Schema Registry */}
            <div className="space-y-6">
                <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-black text-xs text-zinc-500 uppercase tracking-[0.2em]">스키마 레지스트리 (Registry)</h3>
                    <div className="h-px flex-1 bg-zinc-800" />
                </div>
                <Card className="bg-zinc-900 border-zinc-800">
                    <CardContent className="p-0">
                        {(() => {
                            const entries = Object.entries(schema.registry || {});
                            const effectiveFilter = manualFilter || nodeId;

                            const filteredEntries = entries.filter(([label]) => {
                                if (!effectiveFilter) return true;
                                const l = label.toLowerCase();
                                const n = effectiveFilter.toLowerCase();
                                return l.includes(n) || n.includes(l);
                            });

                            if (filteredEntries.length === 0) {
                                return (
                                    <div className="text-zinc-500 italic text-sm p-4 text-center">
                                        <p>No registry items found for "{effectiveFilter}"</p>
                                        <div className="mt-4 text-xs text-zinc-600">
                                            <p className="font-bold mb-2 text-zinc-500">Try selecting a related Registry Class:</p>
                                            <div className="flex flex-wrap justify-center gap-1.5">
                                                {entries.map(([k]) => (
                                                    <button
                                                        key={k}
                                                        onClick={() => setManualFilter(k)}
                                                        className="bg-zinc-800 hover:bg-zinc-700 hover:text-white px-2 py-1 rounded text-zinc-400 transition-colors border border-zinc-700/50"
                                                    >
                                                        {k}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                );
                            }

                            return (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left text-sm">
                                        <thead className="text-[10px] text-zinc-500 uppercase tracking-widest bg-zinc-950">
                                            <tr>
                                                <th className="px-4 py-3 border-b border-zinc-800">Class Label</th>
                                                <th className="px-4 py-3 border-b border-zinc-800">URI Identifier</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-zinc-800">
                                            {filteredEntries.map(([label, uri]: [string, any]) => (
                                                <tr key={label} className="hover:bg-zinc-800/30 transition-colors">
                                                    <td className="px-4 py-3 font-bold text-zinc-300">{label}</td>
                                                    <td className="px-4 py-3 text-xs font-mono text-zinc-500">
                                                        {typeof uri === 'object' ? JSON.stringify(uri) : String(uri)}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            );
                        })()}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
