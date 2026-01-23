import React from 'react';
import { ChevronRight, Lightbulb, Search, AlertTriangle, ShieldCheck } from 'lucide-react';

interface ReasoningTraceViewProps {
    traces: string[] | any[];
}

export const ReasoningTraceView: React.FC<ReasoningTraceViewProps> = ({ traces }) => {
    if (!traces || traces.length === 0) {
        return (
            <div className="text-center py-8 text-zinc-500 italic bg-zinc-50 dark:bg-zinc-800/50 rounded-lg border border-dashed border-zinc-300 dark:border-zinc-700">
                추론 근거 데이터가 없습니다.
            </div>
        );
    }

    const getIcon = (text: string) => {
        const lowerText = text.toLowerCase();
        if (lowerText.includes('search') || lowerText.includes('조회') || lowerText.includes('발견')) {
            return <Search className="w-4 h-4 text-amber-500" />;
        }
        if (lowerText.includes('risk') || lowerText.includes('위협') || lowerText.includes('경고')) {
            return <AlertTriangle className="w-4 h-4 text-red-500" />;
        }
        if (lowerText.includes('check') || lowerText.includes('확인') || lowerText.includes('안전')) {
            return <ShieldCheck className="w-4 h-4 text-emerald-500" />;
        }
        return <Lightbulb className="w-4 h-4 text-blue-500" />;
    };

    return (
        <div className="space-y-4">
            <div className="relative pl-8 space-y-6">
                {/* Timeline Line */}
                <div className="absolute left-[15px] top-2 bottom-2 w-0.5 bg-zinc-200 dark:bg-zinc-700" />

                {traces.map((trace, idx) => {
                    const traceText = typeof trace === 'string' ? trace : JSON.stringify(trace);

                    return (
                        <div key={idx} className="relative group">
                            {/* Dot/Icon */}
                            <div className="absolute -left-[25px] top-1 w-6 h-6 rounded-full bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-700 flex items-center justify-center group-hover:border-blue-500 transition-colors z-10 shadow-sm">
                                <div className="w-2 h-2 rounded-full bg-zinc-300 dark:bg-zinc-600 group-hover:bg-blue-500 transition-colors" />
                            </div>

                            <div className="bg-white dark:bg-zinc-800/60 p-4 rounded-xl border border-zinc-100 dark:border-zinc-700 hover:border-blue-200 dark:hover:border-blue-900/50 hover:bg-blue-50/10 transition-all shadow-sm">
                                <div className="flex items-start gap-3">
                                    <div className="mt-1 flex-shrink-0">
                                        {getIcon(traceText)}
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-[11px] font-bold text-zinc-400 uppercase tracking-widest mb-1 flex items-center gap-1">
                                            Step {String(idx + 1).padStart(2, '0')}
                                            <ChevronRight className="w-3 h-3" />
                                        </div>
                                        <div className="text-sm text-zinc-700 dark:text-zinc-200 leading-relaxed font-medium">
                                            {traceText}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            <div className="mt-6 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-emerald-500 text-white flex items-center justify-center flex-shrink-0">
                    <ShieldCheck className="w-5 h-5" />
                </div>
                <div className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
                    최종 분석 결론: 위협 대응 효율성 및 작전 지속 가능성이 가장 높은 방책으로 평가됨
                </div>
            </div>
        </div>
    );
};
