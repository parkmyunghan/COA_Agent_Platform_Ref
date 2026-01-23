import React, { createContext, useContext, useState, ReactNode } from 'react';

interface ExecutionContextValue {
    isRunning: boolean;
    progress: number;
    message: string;
    logs: string[];
    startExecution: () => void;
    updateProgress: (progress: number, message: string) => void;
    addLog: (log: string) => void;
    completeExecution: () => void;
    errorExecution: (error: string) => void;
    cancelExecution: () => void;
}

const ExecutionContext = createContext<ExecutionContextValue | null>(null);

export const useExecutionContext = () => {
    const context = useContext(ExecutionContext);
    if (!context) {
        throw new Error('useExecutionContext must be used within ExecutionProvider');
    }
    return context;
};

interface ExecutionProviderProps {
    children: ReactNode;
}

export const ExecutionProvider: React.FC<ExecutionProviderProps> = ({ children }) => {
    const [isRunning, setIsRunning] = useState(false);
    const [progress, setProgress] = useState(0);
    const [message, setMessage] = useState('');
    const [logs, setLogs] = useState<string[]>([]);
    
    const startExecution = () => {
        setIsRunning(true);
        setProgress(0);
        setMessage('방책 생성 시작...');
        setLogs([]);
    };
    
    const updateProgress = (newProgress: number, newMessage: string) => {
        setProgress(Math.min(Math.max(newProgress, 0), 100));
        setMessage(newMessage);
    };
    
    const addLog = (log: string) => {
        setLogs(prev => [...prev, `${new Date().toLocaleTimeString()}: ${log}`]);
    };
    
    const completeExecution = () => {
        setProgress(100);
        setMessage('방책 생성 완료');
        addLog('방책 생성이 성공적으로 완료되었습니다.');
        // 완료 후 약간의 지연을 두고 isRunning을 false로 설정
        setTimeout(() => {
            setIsRunning(false);
        }, 2000);
    };
    
    const errorExecution = (error: string) => {
        setMessage(`오류: ${error}`);
        addLog(`[ERROR] ${error}`);
        // 에러 상태는 사용자가 확인할 수 있도록 isRunning을 유지하지 않음
        // 하지만 progress는 유지하여 에러 메시지를 표시할 수 있도록 함
        setIsRunning(false);
    };
    
    const cancelExecution = () => {
        setIsRunning(false);
        setMessage('사용자에 의해 취소되었습니다.');
        addLog('[CANCELLED] 방책 생성이 취소되었습니다.');
    };
    
    return (
        <ExecutionContext.Provider value={{
            isRunning,
            progress,
            message,
            logs,
            startExecution,
            updateProgress,
            addLog,
            completeExecution,
            errorExecution,
            cancelExecution
        }}>
            {children}
        </ExecutionContext.Provider>
    );
};
