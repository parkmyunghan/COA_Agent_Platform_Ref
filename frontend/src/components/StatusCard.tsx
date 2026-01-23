import React from 'react';

interface StatusCardProps {
    title: string;
    value: string | number;
    icon?: React.ReactNode;
    trend?: 'up' | 'down' | 'neutral';
    trendValue?: string;
    description?: string;
    color?: 'blue' | 'red' | 'green' | 'yellow' | 'gray';
}

const colorStyles = {
    blue: 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300',
    red: 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300',
    green: 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300',
    yellow: 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-300',
    gray: 'bg-gray-50 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
};

export const StatusCard: React.FC<StatusCardProps> = ({
    title,
    value,
    icon,
    trend,
    trendValue,
    description,
    color = 'gray'
}) => {
    return (
        <div className="bg-white dark:bg-zinc-800 p-2.5 rounded-lg shadow-sm border border-gray-200 dark:border-zinc-700">
            <div className="flex justify-between items-center gap-2">
                <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-[10px] text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-0.5">{title}</h3>
                    <div className="text-lg font-bold text-gray-900 dark:text-white leading-tight">{value}</div>
                    {(trend || description) && (
                        <div className="flex items-center gap-1.5 mt-1">
                            {trend && (
                                <span className={`
                                    font-medium text-[10px]
                                    ${trend === 'up' ? 'text-green-600' : ''}
                                    ${trend === 'down' ? 'text-red-600' : ''}
                                    ${trend === 'neutral' ? 'text-gray-500' : ''}
                                `}>
                                    {trend === 'up' && '↑'}
                                    {trend === 'down' && '↓'}
                                    {trendValue}
                                </span>
                            )}
                            {description && (
                                <span className="text-[10px] text-gray-500 dark:text-gray-400 truncate">{description}</span>
                            )}
                        </div>
                    )}
                </div>
                {icon && (
                    <div className={`p-1.5 rounded-md flex-shrink-0 ${colorStyles[color]}`}>
                        <span className="text-sm">{icon}</span>
                    </div>
                )}
            </div>
        </div>
    );
};
