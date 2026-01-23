import React, { useState } from 'react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import api from '../lib/api';
import type { COASummary } from '../types/schema';
import { Download, FileText, Loader2 } from 'lucide-react';

interface ReportGeneratorProps {
    agentName?: string;
    summary?: string;
    citations?: string[];
    threatSummary?: any;
    coaRecommendations?: COASummary[];
    situationInfo?: any;
}

export const ReportGenerator: React.FC<ReportGeneratorProps> = ({
    agentName = 'COA Recommendation Agent',
    summary,
    citations = [],
    threatSummary,
    coaRecommendations = [],
    situationInfo
}) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    const handleGenerateReport = async (format: 'pdf' | 'docx' | 'txt') => {
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            const reportData = {
                agent_name: agentName,
                summary: summary || '방책 추천 요약 정보 없음',
                citations: citations,
                threat_info: threatSummary || situationInfo || {},
                coa_recommendations: coaRecommendations,
                format: format
            };

            const response = await api.post('/report/generate', reportData, {
                responseType: 'blob'
            });

            // 파일 다운로드
            const blob = new Blob([response.data]);
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
            link.download = `COA_Report_${timestamp}.${format}`;
            
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);

            setSuccess(`${format.toUpperCase()} 보고서가 생성되었습니다.`);
            setTimeout(() => setSuccess(null), 5000);
        } catch (err: any) {
            console.error('Report generation error:', err);
            setError(err.response?.data?.detail || '보고서 생성 중 오류가 발생했습니다.');
            setTimeout(() => setError(null), 5000);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="border-gray-200 dark:border-zinc-700">
            <CardHeader>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                    보고서 생성
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {error && (
                    <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                        <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
                    </div>
                )}

                {success && (
                    <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                        <p className="text-sm text-green-700 dark:text-green-300">{success}</p>
                    </div>
                )}

                <div className="space-y-2">
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                        방책 추천 결과를 PDF, Word, 또는 텍스트 형식으로 다운로드할 수 있습니다.
                    </p>
                    
                    <div className="grid grid-cols-3 gap-2">
                        <Button
                            onClick={() => handleGenerateReport('pdf')}
                            disabled={loading}
                            variant="outline"
                            size="sm"
                            className="flex items-center gap-2"
                        >
                            {loading ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <Download className="w-4 h-4" />
                            )}
                            PDF
                        </Button>
                        <Button
                            onClick={() => handleGenerateReport('docx')}
                            disabled={loading}
                            variant="outline"
                            size="sm"
                            className="flex items-center gap-2"
                        >
                            {loading ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <Download className="w-4 h-4" />
                            )}
                            Word
                        </Button>
                        <Button
                            onClick={() => handleGenerateReport('txt')}
                            disabled={loading}
                            variant="outline"
                            size="sm"
                            className="flex items-center gap-2"
                        >
                            {loading ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <Download className="w-4 h-4" />
                            )}
                            TXT
                        </Button>
                    </div>
                </div>

                {/* 보고서 내용 미리보기 */}
                {(summary || citations.length > 0 || coaRecommendations.length > 0) && (
                    <div className="mt-4 p-3 bg-gray-50 dark:bg-zinc-800 rounded-lg border border-gray-200 dark:border-zinc-700">
                        <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                            보고서 포함 내용:
                        </p>
                        <ul className="text-xs text-gray-600 dark:text-gray-400 space-y-1 list-disc list-inside">
                            {summary && <li>요약 정보</li>}
                            {citations.length > 0 && <li>참고 자료 ({citations.length}개)</li>}
                            {coaRecommendations.length > 0 && (
                                <li>추천 방책 ({coaRecommendations.length}개)</li>
                            )}
                            {threatSummary && <li>위협 상황 정보</li>}
                        </ul>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
