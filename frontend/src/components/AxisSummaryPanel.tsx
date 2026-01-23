// frontend/src/components/AxisSummaryPanel.tsx
import React from 'react';
import { ShieldAlert, TrendingUp, Boxes, Zap } from 'lucide-react';

interface AxisState {
    axis_id: string;
    axis_name: string;
    threat_level: string;
    friendly_combat_power: number;
    enemy_combat_power: number;
    combat_power_ratio: number;
    mobility_grade: number | null;
    constraint_count: number;
}

interface AxisSummaryPanelProps {
    axisStates: AxisState[];
}

export const AxisSummaryPanel: React.FC<AxisSummaryPanelProps> = ({ axisStates }) => {
    if (!axisStates || axisStates.length === 0) {
        return (
            <div className="p-4 text-center bg-gray-50 dark:bg-zinc-900/30 rounded-lg border-2 border-dashed border-gray-200 dark:border-zinc-800">
                <div className="text-gray-400 text-xs">축선 분석 데이터가 아직 생성되지 않았습니다.</div>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            {axisStates.map((axis) => {
                const ratio = axis.combat_power_ratio !== undefined && axis.combat_power_ratio !== null ? axis.combat_power_ratio : 0;
                const ratioColor = ratio > 1 ? 'text-blue-600 dark:text-blue-400' : 'text-red-600 dark:text-red-400';
                const friendlyPower = axis.friendly_combat_power !== undefined && axis.friendly_combat_power !== null ? axis.friendly_combat_power : 0;
                const enemyPower = axis.enemy_combat_power !== undefined && axis.enemy_combat_power !== null ? axis.enemy_combat_power : 0;

                return (
                    <div key={axis.axis_id} className="bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-lg p-2.5 shadow-sm hover:border-indigo-500/50 transition-all">
                        <div className="flex justify-between items-start mb-2">
                            <div>
                                <h4 className="font-bold text-sm text-gray-900 dark:text-white flex items-center gap-1.5">
                                    <Zap className="w-3 h-3 text-yellow-500" />
                                    {axis.axis_name}
                                </h4>
                                <span className="text-[9px] text-gray-500 font-mono">{axis.axis_id}</span>
                            </div>
                            <div className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${axis.threat_level === 'High' ? 'bg-red-100 text-red-700' :
                                    axis.threat_level === 'Medium' ? 'bg-orange-100 text-orange-700' :
                                        'bg-green-100 text-green-700'
                                }`}>
                                {axis.threat_level}
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between items-end">
                                <span className="text-[10px] text-gray-500 dark:text-gray-400 flex items-center gap-1">
                                    <TrendingUp className="w-2.5 h-2.5" /> 전투력 비율
                                </span>
                                <span className={`text-base font-black ${ratioColor}`}>
                                    {ratio !== undefined && ratio !== null ? ratio.toFixed(2) : 'N/A'}:1
                                </span>
                            </div>

                            <div className="w-full h-1 bg-gray-100 dark:bg-zinc-700 rounded-full overflow-hidden flex">
                                {(() => {
                                    const total = friendlyPower + enemyPower;
                                    const friendlyPercent = total > 0 ? (friendlyPower / total) * 100 : 0;
                                    const enemyPercent = total > 0 ? (enemyPower / total) * 100 : 0;
                                    return (
                                        <>
                                            <div
                                                className="h-full bg-blue-500"
                                                style={{ width: `${friendlyPercent}%` }}
                                            />
                                            <div
                                                className="h-full bg-red-500"
                                                style={{ width: `${enemyPercent}%` }}
                                            />
                                        </>
                                    );
                                })()}
                            </div>

                            <div className="grid grid-cols-2 gap-1.5 mt-1.5">
                                <div className="p-1.5 bg-gray-50 dark:bg-zinc-900/50 rounded-md">
                                    <div className="text-[9px] text-gray-400 uppercase">아군</div>
                                    <div className="text-xs font-bold text-blue-600">{friendlyPower !== undefined && friendlyPower !== null ? friendlyPower.toFixed(1) : 'N/A'}</div>
                                </div>
                                <div className="p-1.5 bg-gray-50 dark:bg-zinc-900/50 rounded-md text-right">
                                    <div className="text-[9px] text-gray-400 uppercase">적군</div>
                                    <div className="text-xs font-bold text-red-600">{enemyPower !== undefined && enemyPower !== null ? enemyPower.toFixed(1) : 'N/A'}</div>
                                </div>
                            </div>

                            <div className="flex justify-between items-center pt-1.5 border-t border-gray-100 dark:border-zinc-700/50">
                                <div className="flex items-center gap-1 text-[10px] text-gray-500 dark:text-gray-400">
                                    <Boxes className="w-2.5 h-2.5" /> 제약: <span className="font-bold text-gray-700 dark:text-zinc-300">{axis.constraint_count}</span>
                                </div>
                                <div className="text-[10px] text-gray-500 dark:text-gray-400">
                                    기동성: <span className="font-bold text-indigo-500">{axis.mobility_grade || 'N/A'}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
};
