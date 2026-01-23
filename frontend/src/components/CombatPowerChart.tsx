import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface CombatPowerChartProps {
    data?: {
        name: string;
        friendly: number;
        enemy: number;
    }[];
}

const DEFAULT_DATA = [
    { name: 'Axis 1', friendly: 4000, enemy: 2400 },
    { name: 'Axis 2', friendly: 3000, enemy: 1398 },
    { name: 'Axis 3', friendly: 2000, enemy: 9800 },
];

export const CombatPowerChart: React.FC<CombatPowerChartProps> = ({ data = DEFAULT_DATA }) => {
    return (
        <div className="h-full w-full min-h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart
                    data={data}
                    margin={{
                        top: 20,
                        right: 30,
                        left: 20,
                        bottom: 5,
                    }}
                >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                    <XAxis dataKey="name" stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip
                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                        cursor={{ fill: 'rgba(0, 0, 0, 0.05)' }}
                    />
                    <Legend wrapperStyle={{ paddingTop: '10px' }} />
                    <Bar dataKey="friendly" name="아군 전투력" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={20} />
                    <Bar dataKey="enemy" name="적군 전투력" fill="#ef4444" radius={[4, 4, 0, 0]} barSize={20} />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
};
