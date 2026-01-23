import React from 'react';
import { CheckCircle2, Circle, Clock, Users } from 'lucide-react';

interface Task {
    name: string;
    description?: string;
    status?: 'todo' | 'doing' | 'done';
}

interface Phase {
    name: string;
    description: string;
    tasks: string[];
}

interface TaskActionListProps {
    phases: Phase[];
}

export const TaskActionList: React.FC<TaskActionListProps> = ({ phases }) => {
    if (!phases || phases.length === 0) {
        return (
            <div className="text-center py-8 text-zinc-500 italic bg-zinc-50 dark:bg-zinc-800/50 rounded-lg border border-dashed border-zinc-300 dark:border-zinc-700">
                실행 계획 데이터가 없습니다.
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {phases.map((phase, phaseIdx) => (
                <div key={phaseIdx} className="relative">
                    {/* Vertical Line for Timeline */}
                    {phaseIdx < phases.length - 1 && (
                        <div className="absolute left-[19px] top-10 bottom-0 w-0.5 bg-zinc-200 dark:bg-zinc-700 -z-10" />
                    )}

                    <div className="flex gap-6">
                        {/* Phase Number/Icon */}
                        <div className="flex-shrink-0">
                            <div className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold shadow-lg shadow-blue-500/20">
                                {phaseIdx + 1}
                            </div>
                        </div>

                        {/* Phase Content */}
                        <div className="flex-1 pb-4">
                            <div className="bg-white dark:bg-zinc-800/80 rounded-xl border border-zinc-200 dark:border-zinc-700 overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                                <div className="p-4 bg-zinc-50 dark:bg-zinc-800 border-b border-zinc-200 dark:border-zinc-700">
                                    <h4 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                                        <Clock className="w-4 h-4 text-blue-500" />
                                        {phase.name}
                                    </h4>
                                    <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                                        {phase.description}
                                    </p>
                                </div>

                                <div className="p-4">
                                    <div className="space-y-3">
                                        {phase.tasks.map((task, taskIdx) => (
                                            <div
                                                key={taskIdx}
                                                className="flex items-start gap-3 p-3 rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-700/50 transition-colors group"
                                            >
                                                <div className="mt-0.5 text-zinc-400 group-hover:text-blue-500 transition-colors">
                                                    <Circle className="w-4 h-4" />
                                                </div>
                                                <div className="flex-1">
                                                    <div className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
                                                        {task}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="px-4 py-2 bg-zinc-50 dark:bg-zinc-800/50 border-t border-zinc-200 dark:border-zinc-700 flex justify-end">
                                    <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                                        <Users className="w-3 h-3" />
                                        Assignment Pending
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
};
