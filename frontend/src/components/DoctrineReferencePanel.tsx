import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import type { COASummary } from '../types/schema';

interface DoctrineReference {
    statement_id?: string;
    doctrine_id?: string;
    source?: string;
    excerpt?: string;
    relevance_score?: number;
    mett_c_elements?: string[];
    reference_type?: 'doctrine' | 'general';
}

interface DoctrineReferencePanelProps {
    recommendation?: COASummary;
    references?: Array<{
        statement_id?: string;
        doctrine_id?: string;
        source?: string;
        excerpt?: string;
        relevance_score?: number;
        mett_c_elements?: string[];
        reference_type?: 'doctrine' | 'general';
    }>;
    situationInfo?: any;
    mettCAnalysis?: any;
}

export const DoctrineReferencePanel: React.FC<DoctrineReferencePanelProps> = ({
    recommendation,
    references,
    situationInfo,
    mettCAnalysis
}) => {
    // references prop이 있으면 우선 사용, 없으면 recommendation에서 추출
    const doctrineRefs = references || recommendation?.doctrine_references || [];

    if (!doctrineRefs || doctrineRefs.length === 0) {
        return (
            <Card className="border-gray-200 dark:border-zinc-700">
                <CardHeader>
                    <CardTitle className="text-sm font-semibold">📚 적용된 참고 자료</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                        <p className="text-sm text-blue-700 dark:text-blue-300">
                            참고 자료 데이터가 비어 있습니다.
                        </p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    // 교리 문서와 일반 문서 구분
    const doctrineRefsList: DoctrineReference[] = [];
    const generalRefsList: DoctrineReference[] = [];

    doctrineRefs.forEach((ref: any) => {
        let refType = ref.reference_type;
        
        // reference_type이 없으면 자동 판단
        if (!refType) {
            if (ref.doctrine_id && ref.doctrine_id !== 'UNKNOWN') {
                refType = 'doctrine';
            } else if (String(ref.source || '').trim().toLowerCase() === 'doctrine') {
                refType = 'doctrine';
            } else {
                refType = 'general';
            }
        }

        if (refType === 'doctrine') {
            doctrineRefsList.push(ref);
        } else if (refType === 'general') {
            generalRefsList.push(ref);
        } else {
            // 판단 불가 시 교리 문서로 간주
            doctrineRefsList.push(ref);
        }
    });

    return (
        <Card className="border-gray-200 dark:border-zinc-700">
            <CardHeader>
                <CardTitle className="text-sm font-semibold">📚 적용된 참고 자료</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                    본 COA 추천은 다음 교리 문장 및 참고 자료를 근거로 합니다.
                </p>

                {/* 교리 문서 */}
                {doctrineRefsList.length > 0 && (
                    <div className="space-y-3">
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">📖 교리 문서</h4>
                        {doctrineRefsList.map((ref, idx) => (
                            <DoctrineReferenceCard
                                key={idx}
                                ref={ref}
                                isDoctrine={true}
                                defaultExpanded={idx === 0}
                            />
                        ))}
                    </div>
                )}

                {doctrineRefsList.length === 0 && (
                    <div className="p-3 bg-gray-50 dark:bg-zinc-800 rounded-lg">
                        <p className="text-xs text-gray-500 dark:text-gray-400">교리 문서 참조가 없습니다.</p>
                    </div>
                )}

                {/* 일반 참고 문서 */}
                {generalRefsList.length > 0 && (
                    <div className="space-y-3 pt-4 border-t border-gray-200 dark:border-zinc-700">
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">📄 일반 참고 문서</h4>
                        {generalRefsList.map((ref, idx) => (
                            <DoctrineReferenceCard
                                key={idx}
                                ref={ref}
                                isDoctrine={false}
                                defaultExpanded={idx === 0 && doctrineRefsList.length === 0}
                            />
                        ))}
                    </div>
                )}

                {generalRefsList.length === 0 && doctrineRefsList.length === 0 && (
                    <div className="p-3 bg-gray-50 dark:bg-zinc-800 rounded-lg">
                        <p className="text-xs text-gray-500 dark:text-gray-400">참고 자료가 없습니다. (일반/교리 데이터 부재)</p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};

// 교리 참조 카드 컴포넌트
const DoctrineReferenceCard: React.FC<{
    ref: DoctrineReference;
    isDoctrine: boolean;
    defaultExpanded: boolean;
}> = ({ ref, isDoctrine, defaultExpanded }) => {
    const [isOpen, setIsOpen] = useState(defaultExpanded);

    const statementId = ref.statement_id || 'Unknown';
    const excerpt = ref.excerpt || '';
    const relevanceScore = ref.relevance_score || 0;
    const mettCElements = ref.mett_c_elements || [];
    const doctrineId = ref.doctrine_id || 'Unknown';
    const source = ref.source || 'Unknown';

    const bgColor = isDoctrine 
        ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
        : 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800';
    
    const textColor = isDoctrine
        ? 'text-blue-700 dark:text-blue-300'
        : 'text-yellow-700 dark:text-yellow-300';
    
    const borderColor = isDoctrine
        ? 'border-blue-500'
        : 'border-yellow-500';

    return (
        <div className="border border-gray-200 dark:border-zinc-700 rounded-lg overflow-hidden">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full p-3 bg-gray-50 dark:bg-zinc-800 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-colors flex items-center justify-between"
            >
                <div className="flex-1 text-left">
                    <span className="font-semibold text-sm text-gray-900 dark:text-white">
                        {isDoctrine ? `[${statementId}]` : source}
                    </span>
                    <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                        (관련도: {relevanceScore.toFixed(2)})
                    </span>
                </div>
                <span className="text-gray-500 text-sm">{isOpen ? '▲' : '▼'}</span>
            </button>
            
            {isOpen && (
                <div className="p-4 space-y-3 border-t border-gray-200 dark:border-zinc-700">
                    {/* 교리/문서 문장 본문 */}
                    <div className={`p-3 ${bgColor} border-l-4 ${borderColor} rounded`}>
                        <p className={`text-sm italic ${textColor}`}>
                            "{excerpt}"
                        </p>
                    </div>

                    {/* 메타데이터 */}
                    <div className="grid grid-cols-2 gap-4 text-xs">
                        <div>
                            <span className="text-gray-500 dark:text-gray-400 font-semibold">
                                {isDoctrine ? '교리 ID:' : '문서 소스:'}
                            </span>
                            <span className="ml-2 text-gray-700 dark:text-gray-300">
                                {isDoctrine ? doctrineId : source}
                            </span>
                        </div>
                        {mettCElements.length > 0 && (
                            <div>
                                <span className="text-gray-500 dark:text-gray-400 font-semibold">
                                    관련 METT-C:
                                </span>
                                <span className="ml-2 text-gray-700 dark:text-gray-300">
                                    {mettCElements.join(', ')}
                                </span>
                            </div>
                        )}
                    </div>

                    {/* 관련도 진행 바 */}
                    <div className="space-y-1">
                        <div className="flex justify-between text-xs">
                            <span className="text-gray-500 dark:text-gray-400">관련도</span>
                            <span className="text-gray-700 dark:text-gray-300 font-semibold">
                                {(relevanceScore * 100).toFixed(1)}%
                            </span>
                        </div>
                        <div className="w-full bg-gray-200 dark:bg-zinc-700 rounded-full h-2">
                            <div
                                className={`h-2 rounded-full transition-all ${
                                    isDoctrine 
                                        ? 'bg-blue-500 dark:bg-blue-400'
                                        : 'bg-yellow-500 dark:bg-yellow-400'
                                }`}
                                style={{ width: `${relevanceScore * 100}%` }}
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
