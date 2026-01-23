import React, { useState, useEffect } from 'react';
import { X, CheckCircle2 } from 'lucide-react';

interface ProgressStatusProps {
    label: string;
    progress: number; // 0-100
    logs: string[];
    state: 'running' | 'complete' | 'error';
    onCancel?: () => void;
}

export const ProgressStatus: React.FC<ProgressStatusProps> = ({
    label,
    progress,
    logs,
    state,
    onCancel
}) => {
    // 2단계: 진척율 팝업 개선 - 완료 후 3초간 표시
    const [showComplete, setShowComplete] = useState(false);

    useEffect(() => {
        if (state === 'complete' && progress === 100) {
            setShowComplete(true);
            const timer = setTimeout(() => {
                setShowComplete(false);
            }, 3000); // 3초 후 사라짐
            return () => clearTimeout(timer);
        } else {
            setShowComplete(false);
        }
    }, [state, progress]);

    // 완료 상태이고 showComplete가 false면 숨김
    if (state === 'complete' && progress === 100 && !showComplete) {
        return null;
    }
    
    // 에러 상태는 사용자가 확인할 수 있도록 표시

    const getStateColor = () => {
        switch (state) {
            case 'running':
                return 'border-blue-500 bg-blue-50 dark:bg-blue-900/20';
            case 'complete':
                return 'border-green-500 bg-green-50 dark:bg-green-900/20';
            case 'error':
                return 'border-red-500 bg-red-50 dark:bg-red-900/20';
            default:
                return 'border-gray-500 bg-gray-50 dark:bg-gray-900/20';
        }
    };

    return (
        <div className={`fixed top-4 left-1/2 transform -translate-x-1/2 z-[100] 
                        bg-white dark:bg-zinc-900 rounded-lg shadow-xl border-2 
                        ${getStateColor()} p-4 min-w-[400px] max-w-[600px]`}
             style={{ pointerEvents: 'auto' }}>
            <div className="flex items-center justify-between mb-2">
                <h3 className="font-bold text-sm text-gray-900 dark:text-white">{label}</h3>
                <div className="flex items-center gap-2">
                    {state === 'running' && onCancel && (
                        <button
                            onClick={onCancel}
                            className="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
                        >
                            취소
                        </button>
                    )}
                    {state === 'complete' && (
                        <span className="flex items-center gap-1 text-green-600 dark:text-green-400 text-xs">
                            <CheckCircle2 className="w-4 h-4 animate-in fade-in zoom-in duration-300" />
                            완료
                        </span>
                    )}
                    {state === 'error' && (
                        <span className="text-red-600 dark:text-red-400 text-xs">✗ 오류</span>
                    )}
                </div>
            </div>
            
            {/* Progress Bar */}
            <div className="w-full h-2 bg-gray-200 dark:bg-zinc-800 rounded-full mb-2 overflow-hidden">
                <div 
                    className={`h-full rounded-full transition-all duration-300 ${
                        state === 'error' 
                            ? 'bg-red-500' 
                            : state === 'complete'
                            ? 'bg-green-500'
                            : 'bg-blue-600'
                    }`}
                    style={{ width: `${Math.min(progress, 100)}%` }}
                />
            </div>
            
            <div className="flex justify-between items-center text-xs text-gray-500 dark:text-gray-400 mb-2">
                <span>{progress}%</span>
                {state === 'running' && (
                    <span className="animate-pulse">처리 중...</span>
                )}
            </div>
            
            {/* Logs */}
            {logs.length > 0 && (
                <div className="max-h-32 overflow-y-auto text-xs text-gray-600 dark:text-gray-400 
                              bg-gray-50 dark:bg-zinc-800 rounded p-2 border border-gray-200 dark:border-zinc-700">
                    {logs.map((log, idx) => (
                        <div key={idx} className="py-0.5 font-mono">{log}</div>
                    ))}
                </div>
            )}
        </div>
    );
};
