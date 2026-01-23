import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null
        };
    }

    static getDerivedStateFromError(error: Error): State {
        return {
            hasError: true,
            error,
            errorInfo: null
        };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('ErrorBoundary caught an error:', error, errorInfo);
        this.setState({
            error,
            errorInfo
        });
    }

    handleReset = () => {
        this.setState({
            hasError: false,
            error: null,
            errorInfo: null
        });
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-zinc-900 p-4">
                    <div className="max-w-2xl w-full bg-white dark:bg-zinc-800 rounded-lg shadow-lg border border-red-200 dark:border-red-800 p-6">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
                                <span className="text-2xl">⚠️</span>
                            </div>
                            <div>
                                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                                    오류가 발생했습니다
                                </h2>
                                <p className="text-sm text-gray-500 dark:text-gray-400">
                                    예상치 못한 오류가 발생했습니다.
                                </p>
                            </div>
                        </div>

                        {this.state.error && (
                            <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                                <p className="text-sm font-semibold text-red-800 dark:text-red-300 mb-2">
                                    오류 메시지:
                                </p>
                                <p className="text-sm text-red-700 dark:text-red-400 font-mono">
                                    {this.state.error.message || '알 수 없는 오류'}
                                </p>
                            </div>
                        )}

                        {this.state.errorInfo && (
                            <details className="mb-4">
                                <summary className="text-sm font-semibold text-gray-700 dark:text-gray-300 cursor-pointer mb-2">
                                    상세 정보 보기
                                </summary>
                                <pre className="text-xs text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-zinc-900 p-3 rounded overflow-auto max-h-64">
                                    {this.state.errorInfo.componentStack}
                                </pre>
                            </details>
                        )}

                        <div className="flex gap-3">
                            <button
                                onClick={this.handleReset}
                                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                            >
                                다시 시도
                            </button>
                            <button
                                onClick={() => window.location.reload()}
                                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-zinc-700 dark:hover:bg-zinc-600 text-gray-900 dark:text-white rounded-lg font-medium transition-colors"
                            >
                                페이지 새로고침
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
