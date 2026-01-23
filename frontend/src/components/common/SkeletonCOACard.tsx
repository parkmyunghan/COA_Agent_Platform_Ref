import React from 'react';

export const SkeletonCOACard: React.FC = () => {
    return (
        <div className="p-4 border border-gray-200 dark:border-zinc-700 rounded-lg animate-pulse bg-white dark:bg-zinc-900">
            <div className="flex justify-between items-start mb-3">
                <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                        {/* Rank Badge Skeleton */}
                        <div className="h-4 w-12 bg-gray-200 dark:bg-zinc-700 rounded"></div>
                        {/* Title Skeleton */}
                        <div className="h-5 w-32 bg-gray-200 dark:bg-zinc-700 rounded"></div>
                        {/* Type Badge Skeleton */}
                        <div className="h-4 w-16 bg-gray-200 dark:bg-zinc-700 rounded"></div>
                    </div>
                    {/* Description Skeleton */}
                    <div className="space-y-2 mb-3">
                        <div className="h-3 w-full bg-gray-200 dark:bg-zinc-700 rounded"></div>
                        <div className="h-3 w-4/5 bg-gray-200 dark:bg-zinc-700 rounded"></div>
                    </div>

                    {/* Participating Units Skeleton */}
                    <div className="flex items-center gap-2 mb-2">
                        <div className="h-3 w-3 bg-zinc-300 dark:bg-zinc-600 rounded-full"></div>
                        <div className="h-3 w-48 bg-zinc-200 dark:bg-zinc-700 rounded"></div>
                    </div>

                    {/* Search Path Skeleton */}
                    <div className="h-6 w-full bg-gray-100 dark:bg-zinc-800 rounded mt-2"></div>
                </div>
            </div>
        </div>
    );
};
