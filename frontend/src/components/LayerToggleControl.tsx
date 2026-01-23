/**
 * 레이어 토글 컨트롤 컴포넌트
 * COP 시각화 레이어별 표시/숨김 제어
 */

import React from 'react';
import { Eye, EyeOff } from 'lucide-react';

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

interface LayerToggleControlProps {
    layers: LayerToggleState;
    onToggle: (layer: keyof LayerToggleState) => void;
}

export const LayerToggleControl: React.FC<LayerToggleControlProps> = ({ layers, onToggle }) => {
    const layerLabels: Array<{ key: keyof LayerToggleState; label: string; color: string }> = [
        { key: 'threats', label: '위협 마커', color: 'text-red-600' },
        { key: 'threatInfluence', label: '위협 영향 범위', color: 'text-orange-600' },
        { key: 'friendlyUnits', label: '아군 부대', color: 'text-blue-600' },
        { key: 'coaPaths', label: '방책 작전 경로', color: 'text-indigo-600' },
        { key: 'coaAreas', label: '방책 작전 영역', color: 'text-purple-600' },
        { key: 'axes', label: '축선', color: 'text-cyan-600' },
        { key: 'reasoningTrace', label: '추론 경로', color: 'text-pink-600' },
    ];

    return (
        <div className="absolute top-16 right-2 z-[10001] bg-white/95 dark:bg-zinc-900/95 backdrop-blur-sm rounded-lg border border-gray-300 dark:border-zinc-700 shadow-lg p-2 min-w-[180px]">
            <div className="text-xs font-bold mb-1 text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                레이어 제어
            </div>
            <div className="space-y-1">
                {layerLabels.map(({ key, label, color }) => (
                    <button
                        key={key}
                        onClick={() => onToggle(key)}
                        className={`w-full flex items-center justify-between px-2 py-1.5 rounded text-xs hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors ${
                            layers[key] ? 'text-gray-900 dark:text-white' : 'text-gray-400 dark:text-gray-500'
                        }`}
                    >
                        <span className={`flex items-center gap-1.5 ${layers[key] ? color : ''}`}>
                            {layers[key] ? (
                                <Eye className="w-3 h-3" />
                            ) : (
                                <EyeOff className="w-3 h-3" />
                            )}
                            {label}
                        </span>
                    </button>
                ))}
            </div>
        </div>
    );
};
