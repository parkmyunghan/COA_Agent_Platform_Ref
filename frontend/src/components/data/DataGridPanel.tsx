// frontend/src/components/data/DataGridPanel.tsx
import React, { useState, useEffect } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { themeQuartz } from 'ag-grid-community';
import { Download, RefreshCw } from 'lucide-react';
import api from '../../lib/api';

interface TableInfo {
    name: string;
    display_name: string;
    row_count: number;
}

interface TableData {
    columns: string[];
    rows: Record<string, any>[];
    total_count: number;
}

export default function DataGridPanel() {
    const [tables, setTables] = useState<TableInfo[]>([]);
    const [selectedTable, setSelectedTable] = useState<string | null>(null);
    const [tableData, setTableData] = useState<TableData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [currentPage, setCurrentPage] = useState(1);
    const pageSize = 100;

    // Fetch table list on mount
    useEffect(() => {
        fetchTableList();
    }, []);

    // Fetch table data when selected table or page changes
    useEffect(() => {
        if (selectedTable) {
            fetchTableData(selectedTable, currentPage);
        }
    }, [selectedTable, currentPage]);

    const fetchTableList = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.get<{ tables: TableInfo[] }>('/data-management/tables');
            setTables(response.data.tables);
            if (response.data.tables.length > 0) {
                setSelectedTable(response.data.tables[0].name);
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || '테이블 목록 로딩 실패');
            console.error('Table list error:', err);
        } finally {
            setLoading(false);
        }
    };

    const fetchTableData = async (tableName: string, page: number) => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.get<TableData>(
                `/data-management/tables/${tableName}`,
                {
                    params: { page, page_size: pageSize }
                }
            );
            setTableData(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || '테이블 데이터 로딩 실패');
            console.error('Table data error:', err);
        } finally {
            setLoading(false);
        }
    };

    const downloadCSV = () => {
        if (!tableData || !tableData.rows.length) return;

        const csv = [
            tableData.columns.join(','),
            ...tableData.rows.map(row =>
                tableData.columns.map(col => {
                    const value = row[col];
                    // Escape commas and quotes
                    if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                        return `"${value.replace(/"/g, '""')}"`;
                    }
                    return value !== null && value !== undefined ? value : '';
                }).join(',')
            )
        ].join('\n');

        const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' }); // Add BOM for Excel
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${selectedTable || 'data'}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    // Prepare AG-Grid column definitions
    const columnDefs = tableData?.columns.map(col => ({
        field: col,
        headerName: col,
        sortable: true,
        filter: true,
        resizable: true,
        minWidth: 150
    })) || [];

    const totalPages = tableData ? Math.ceil(tableData.total_count / pageSize) : 0;

    return (
        <div className="flex flex-col h-full space-y-4">
            {/* Table Selection */}
            <div className="bg-zinc-900 p-4 rounded-lg border border-zinc-800 shrink-0">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                    <div className="md:col-span-2">
                        <label className="block text-sm font-medium text-zinc-300 mb-2">
                            데이터 테이블 선택
                        </label>
                        <select
                            value={selectedTable || ''}
                            onChange={(e) => {
                                setSelectedTable(e.target.value);
                                setCurrentPage(1);
                            }}
                            className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-zinc-100 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        >
                            {tables.map(table => (
                                <option key={table.name} value={table.name}>
                                    {table.display_name} ({table.row_count.toLocaleString()} rows)
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="flex gap-2">
                        <button
                            onClick={() => fetchTableData(selectedTable!, currentPage)}
                            disabled={loading || !selectedTable}
                            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-zinc-700 disabled:text-zinc-500 rounded text-sm font-medium transition-colors"
                        >
                            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                            새로고침
                        </button>
                        <button
                            onClick={downloadCSV}
                            disabled={!tableData || !tableData.rows.length}
                            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:text-zinc-500 rounded text-sm font-medium transition-colors"
                        >
                            <Download className="w-4 h-4" />
                            CSV
                        </button>
                    </div>
                </div>
            </div>

            {error && (
                <div className="bg-red-900/20 border border-red-800 text-red-400 p-4 rounded shrink-0">
                    <p className="font-semibold">오류:</p>
                    <p className="text-sm mt-1">{error}</p>
                </div>
            )}

            {/* Data Grid Container */}
            {tableData && (
                <div className="bg-zinc-900 p-4 rounded-lg border border-zinc-800 flex-1 flex flex-col min-h-0">
                    <div className="flex items-center justify-between mb-4 shrink-0">
                        <h3 className="text-sm font-semibold text-zinc-300">
                            {selectedTable} - {tableData.total_count.toLocaleString()} rows
                        </h3>

                        {/* Pagination Controls */}
                        <div className="flex items-center gap-4">
                            <span className="text-sm text-zinc-400">
                                Page {currentPage} of {totalPages}
                            </span>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                    disabled={currentPage === 1}
                                    className="px-3 py-1 bg-zinc-800 hover:bg-zinc-700 disabled:bg-zinc-800 disabled:text-zinc-600 rounded text-sm transition-colors"
                                >
                                    이전
                                </button>
                                <button
                                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                    disabled={currentPage === totalPages}
                                    className="px-3 py-1 bg-zinc-800 hover:bg-zinc-700 disabled:bg-zinc-800 disabled:text-zinc-600 rounded text-sm transition-colors"
                                >
                                    다음
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* AG-Grid (Fills container) */}
                    <div className="flex-1 min-h-0">
                        <AgGridReact
                            theme={themeQuartz.withParams({
                                accentColor: "#10b981",
                                backgroundColor: "#18181b",
                                borderColor: "#27272a",
                                borderRadius: 4,
                                headerBackgroundColor: "#27272a",
                                headerTextColor: "#d4d4d4",
                                textColor: "#e5e7eb",
                            })}
                            rowData={tableData.rows}
                            columnDefs={columnDefs}
                            defaultColDef={{
                                sortable: true,
                                filter: true,
                                resizable: true,
                            }}
                            domLayout="normal"
                        />
                    </div>

                    {/* Pagination Info */}
                    <div className="mt-4 text-sm text-zinc-400 text-center shrink-0">
                        Showing rows {(currentPage - 1) * pageSize + 1} - {Math.min(currentPage * pageSize, tableData.total_count)} of {tableData.total_count.toLocaleString()}
                    </div>
                </div>
            )}

            {loading && !tableData && (
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-12 text-center flex-1 flex items-center justify-center">
                    <div className="text-zinc-400">로딩 중...</div>
                </div>
            )}
        </div>
    );
}
