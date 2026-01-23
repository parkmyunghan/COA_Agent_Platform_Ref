/**
 * 개선된 지도 범례 컴포넌트
 * Palantir 스타일 군사 시각화 표준 참고
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

export interface LayerToggleState {
    threats: boolean;
    threatInfluence: boolean;
    friendlyUnits: boolean;
    coaPaths: boolean;
    coaAreas: boolean;
    axes: boolean;
    terrain: boolean;
    reasoningTrace: boolean;
}

interface MapLegendProps {
    layers: LayerToggleState;
    onToggle: (layer: keyof LayerToggleState) => void;
    // 선택적: 현재 표시 중인 마커 개수 등
    stats?: {
        threatCount?: number;
        friendlyUnitCount?: number;
        coaCount?: number;
        hasFriendlyUnits?: boolean;
        hasCOA?: boolean;
    };
}

interface LegendGroup {
    title: string;
    items: Array<{
        key: keyof LayerToggleState;
        label: string;
        icon: JSX.Element;
        description?: string;
    }>;
}

export const MapLegend: React.FC<MapLegendProps> = ({ layers, onToggle, stats }) => {
    const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
        new Set(['위협 요소', '아군 요소', '방책 요소', '지형 및 분석 요소'])
    );

    const toggleGroup = (groupTitle: string) => {
        setExpandedGroups(prev => {
            const newSet = new Set(prev);
            if (newSet.has(groupTitle)) {
                newSet.delete(groupTitle);
            } else {
                newSet.add(groupTitle);
            }
            return newSet;
        });
    };

    const legendGroups: LegendGroup[] = [
        {
            title: '위협 요소',
            items: [
                {
                    key: 'threats',
                    label: '위협 마커',
                    icon: (
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <circle cx="8" cy="8" r="5" fill="#ef4444" stroke="#991b1b" strokeWidth="1.5" />
                        </svg>
                    ),
                    description: '적 위협 위치 및 유형',
                },
                {
                    key: 'threatInfluence',
                    label: '위협 영향권',
                    icon: (
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <circle cx="8" cy="8" r="6" fill="none" stroke="#f97316" strokeWidth="1.5" strokeDasharray="2,2" opacity="0.6" />
                        </svg>
                    ),
                    description: '위협 영향 범위',
                },
            ],
        },
        {
            title: '아군 요소',
            items: [
                {
                    key: 'friendlyUnits',
                    label: '아군 부대',
                    icon: (
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <polygon points="8,2 14,14 8,11 2,14" fill="#3b82f6" stroke="#1e3a8a" strokeWidth="1.5" />
                        </svg>
                    ),
                    description: '아군 부대 배치',
                },
            ],
        },
        {
            title: '방책 요소',
            items: [
                {
                    key: 'coaPaths',
                    label: '작전 경로',
                    icon: (
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <path d="M2 8 L14 8" stroke="#3b82f6" strokeWidth="2" fill="none" />
                            <polygon points="14,8 11,6 11,10" fill="#3b82f6" />
                        </svg>
                    ),
                    description: '부대 이동 경로 및 방책-위협 관계',
                },
                {
                    key: 'coaAreas',
                    label: '작전 영역',
                    icon: (
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <rect x="3" y="3" width="10" height="10" fill="#8b5cf6" fillOpacity="0.2" stroke="#6d28d9" strokeWidth="1.5" />
                        </svg>
                    ),
                    description: '작전 수행 영역',
                },
            ],
        },
        {
            title: '지형 및 분석 요소',
            items: [
                {
                    key: 'axes',
                    label: '축선',
                    icon: (
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <path d="M2 8 L14 8" stroke="#1e40af" strokeWidth="2" strokeDasharray="4,2" fill="none" />
                            <polygon points="14,8 11,6 11,10" fill="#1e40af" />
                        </svg>
                    ),
                    description: '주요 접근로',
                },
                {
                    key: 'terrain',
                    label: '지형 분석',
                    icon: (
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <rect x="2" y="2" width="12" height="12" fill="#16a34a" fillOpacity="0.1" stroke="#16a34a" strokeWidth="1" strokeDasharray="2,2" />
                            <path d="M4 12 L7 8 L10 10 L13 5" stroke="#16a34a" strokeWidth="1.5" fill="none" />
                        </svg>
                    ),
                    description: '지형 및 장애물 분석',
                },
                {
                    key: 'reasoningTrace',
                    label: '추론 경로',
                    icon: (
                        <svg width="16" height="16" viewBox="0 0 16 16">
                            <path d="M2 8 L14 8" stroke="#8b5cf6" strokeWidth="1.5" strokeDasharray="2,3" fill="none" opacity="0.7" />
                        </svg>
                    ),
                    description: 'AI 분석 흐름',
                },
            ],
        },
    ];

    return (
        <div className="absolute top-16 right-2 z-[10001] bg-white/95 dark:bg-zinc-900/95 backdrop-blur-sm rounded-lg border border-gray-300 dark:border-zinc-700 shadow-xl max-w-[280px]">
            <div className="px-3 py-2 border-b border-gray-200 dark:border-zinc-700">
                <h3 className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    범례 (Legend)
                </h3>
            </div>
            <div className="max-h-[500px] overflow-y-auto p-2 space-y-1">
                {legendGroups.map((group) => {
                    const isExpanded = expandedGroups.has(group.title);
                    return (
                        <div key={group.title} className="border border-gray-200 dark:border-zinc-700 rounded-md overflow-hidden">
                            <button
                                onClick={() => toggleGroup(group.title)}
                                className="w-full flex items-center justify-between px-2 py-1.5 bg-gray-50 dark:bg-zinc-800 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-colors"
                            >
                                <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-1.5">
                                    {group.title}
                                    {group.title === '아군 요소' && stats?.hasFriendlyUnits && (
                                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                                    )}
                                    {group.title === '방책 요소' && stats?.hasCOA && (
                                        <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
                                    )}
                                </span>
                                {isExpanded ? (
                                    <ChevronDown className="w-3 h-3 text-gray-500" />
                                ) : (
                                    <ChevronRight className="w-3 h-3 text-gray-500" />
                                )}
                            </button>
                            {isExpanded && (
                                <div className="p-1 space-y-0.5 bg-white dark:bg-zinc-900">
                                    {group.items.map((item) => {
                                        const isActive = layers[item.key];
                                        return (
                                            <button
                                                key={item.key}
                                                onClick={() => onToggle(item.key)}
                                                className={`w-full flex items-start gap-2 px-2 py-1.5 rounded text-xs hover:bg-gray-50 dark:hover:bg-zinc-800 transition-colors ${isActive ? 'opacity-100' : 'opacity-40'
                                                    }`}
                                                title={item.description}
                                            >
                                                <div className="flex-shrink-0 mt-0.5">
                                                    {item.icon}
                                                </div>
                                                <div className="flex-1 text-left">
                                                    <div className={`font-medium ${isActive ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400'}`}>
                                                        {item.label}
                                                    </div>
                                                    {item.description && (
                                                        <div className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">
                                                            {item.description}
                                                        </div>
                                                    )}
                                                </div>
                                                <div className={`flex-shrink-0 w-3 h-3 rounded border-2 mt-0.5 ${isActive
                                                    ? 'bg-blue-500 border-blue-500'
                                                    : 'bg-white dark:bg-zinc-800 border-gray-300 dark:border-zinc-600'
                                                    }`}>
                                                    {isActive && (
                                                        <svg viewBox="0 0 12 12" fill="none" className="w-full h-full">
                                                            <path d="M2 6 L5 9 L10 3" stroke="white" strokeWidth="2" strokeLinecap="round" />
                                                        </svg>
                                                    )}
                                                </div>
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
            {stats && (
                <div className="px-3 py-2 border-t border-gray-200 dark:border-zinc-700 text-[10px] text-gray-500 dark:text-gray-400 space-y-0.5">
                    {stats.threatCount !== undefined && (
                        <div>위협: {stats.threatCount}개</div>
                    )}
                    {stats.friendlyUnitCount !== undefined && (
                        <div>아군 부대: {stats.friendlyUnitCount}개</div>
                    )}
                    {stats.coaCount !== undefined && (
                        <div>방책: {stats.coaCount}개</div>
                    )}
                </div>
            )}
        </div>
    );
};
