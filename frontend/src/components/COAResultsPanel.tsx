import React from 'react';
import { X, BarChart3, ChevronDown, ChevronUp } from 'lucide-react';
import type { COASummary } from '../types/schema';

interface COAResultsPanelProps {
    coas: COASummary[];
    selectedCOA: COASummary | null;
    onCOASelect: (coa: COASummary) => void;
    onClose?: () => void;
    onCompare?: () => void;
}

export const COAResultsPanel: React.FC<COAResultsPanelProps> = ({
    coas,
    selectedCOA,
    onCOASelect,
    onClose,
    onCompare
}) => {
    const [isMinimized, setIsMinimized] = React.useState(false);

    if (!coas || coas.length === 0) {
        return null;
    }

    return (
        <div className={`w-full transition-all duration-300 animate-in fade-in slide-in-from-top-4 ${
            isMinimized ? 'max-w-md mx-auto' : 'w-full'
        }`}>
            <div className="bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border-2 border-indigo-500/30 overflow-hidden">
                {/* Header */}
                <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-3 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                            <span className="text-white text-lg font-bold">🎯</span>
                        </div>
                        <div>
                            <h3 className="text-white font-bold text-sm">
                                추천 방책 결과 ({coas.length}개)
                            </h3>
                            <p className="text-blue-100 text-xs">
                                {selectedCOA ? `선택됨: ${selectedCOA.coa_name}` : '방책을 선택하세요'}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {onCompare && coas.length > 1 && (
                            <button
                                onClick={onCompare}
                                className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold bg-white/20 hover:bg-white/30 text-white rounded-lg transition-colors"
                            >
                                <BarChart3 className="w-4 h-4" />
                                비교
                            </button>
                        )}
                        <button
                            onClick={() => setIsMinimized(!isMinimized)}
                            className="p-1.5 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                        >
                            {isMinimized ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
                        </button>
                        {onClose && (
                            <button
                                onClick={onClose}
                                className="p-1.5 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        )}
                    </div>
                </div>

                {/* Content */}
                {!isMinimized && (
                    <div className="p-4 bg-gray-50 dark:bg-zinc-800/50">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            {coas.map((coa, idx) => {
                                const isSelected = selectedCOA?.coa_id === coa.coa_id;
                                const score = coa.total_score !== undefined ? (coa.total_score * 100).toFixed(1) : 'N/A';
                                
                                return (
                                    <div
                                        key={coa.coa_id}
                                        onClick={() => onCOASelect(coa)}
                                        className={`p-4 bg-white dark:bg-zinc-900 rounded-lg border-2 cursor-pointer transition-all transform hover:scale-[1.02] animate-in fade-in slide-in-from-bottom-4 ${
                                            isSelected
                                                ? 'border-indigo-500 dark:border-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 shadow-lg'
                                                : 'border-gray-200 dark:border-zinc-700 hover:border-indigo-300 dark:hover:border-indigo-600'
                                        }`}
                                        style={{ animationDelay: `${idx * 100}ms` }}
                                    >
                                        {/* Rank Badge */}
                                        <div className="flex items-center justify-between mb-2">
                                            <span className={`inline-block px-2 py-0.5 rounded text-xs font-black ${
                                                idx === 0 
                                                    ? 'bg-yellow-500 text-white' 
                                                    : idx === 1
                                                    ? 'bg-gray-400 text-white'
                                                    : 'bg-orange-600 text-white'
                                            }`}>
                                                {idx === 0 ? '🥇' : idx === 1 ? '🥈' : '🥉'} Rank {coa.rank}
                                            </span>
                                            <span className="text-lg font-black text-indigo-600 dark:text-indigo-400">
                                                {score}%
                                            </span>
                                        </div>

                                        {/* COA Name */}
                                        <h4 className="font-bold text-sm text-gray-900 dark:text-white mb-1 line-clamp-1">
                                            {coa.coa_name}
                                        </h4>

                                        {/* Description */}
                                        <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2 mb-3">
                                            {coa.description || '설명 없음'}
                                        </p>

                                        {/* Score Bars */}
                                        <div className="space-y-1.5">
                                            <div className="flex items-center justify-between text-[10px]">
                                                <span className="text-gray-500">전투력</span>
                                                <span className="font-semibold text-blue-600">
                                                    {coa.combat_power_score !== undefined ? (coa.combat_power_score * 100).toFixed(0) : 'N/A'}%
                                                </span>
                                            </div>
                                            <div className="w-full h-1.5 bg-gray-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-blue-500 rounded-full transition-all"
                                                    style={{ width: `${(coa.combat_power_score || 0) * 100}%` }}
                                                />
                                            </div>
                                        </div>

                                        {/* Click Indicator */}
                                        {isSelected && (
                                            <div className="mt-2 text-xs text-indigo-600 dark:text-indigo-400 font-semibold flex items-center gap-1">
                                                ✓ 선택됨
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
