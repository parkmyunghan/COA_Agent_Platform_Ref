import { Link, useLocation } from 'react-router-dom';
import { Home, LayoutGrid, Activity } from 'lucide-react';
import { useEffect, useRef, useMemo } from 'react';
import { useSystemData } from '../contexts/SystemDataContext';

interface HeaderProps {
    toggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = () => {
    const location = useLocation();
    const { health, refetch } = useSystemData();
    
    // refetch를 useRef로 안정적인 참조로 유지하여 useEffect가 불필요하게 재실행되지 않도록 함
    const refetchRef = useRef(refetch);
    
    // refetch가 변경될 때만 refetchRef 업데이트 (렌더링 중에 직접 할당하여 최신 참조 유지)
    // useEffect를 사용하지 않아서 불필요한 사이클 방지
    refetchRef.current = refetch;

    // Dashboard 페이지일 때 주기적으로 health 갱신 (30초마다)
    // location.pathname이 변경될 때만 interval 재생성
    // silent 모드로 호출하여 loading 상태 변경 없이 데이터만 갱신
    useEffect(() => {
        if (location.pathname === '/dashboard') {
            const interval = setInterval(() => {
                // silent 모드로 호출하여 불필요한 리렌더링 방지
                (refetchRef.current as any)(true); // useRef를 통해 최신 refetch 함수 호출
            }, 30000); // 30초마다 갱신
            return () => clearInterval(interval);
        }
    }, [location.pathname]); // refetch를 의존성 배열에서 완전히 제거

    // health 표시 부분을 useMemo로 메모이제이션하여 불필요한 리렌더링 방지
    const healthDisplay = useMemo(() => {
        if (location.pathname === '/dashboard' && health) {
            return (
                <span className="ml-2 px-1.5 py-0.5 rounded text-[9px] bg-green-500/10 text-green-600 dark:text-green-400">
                    {health.status === 'ok' ? '✓' : '⚠'} {(health as any).version || 'v1.0'}
                </span>
            );
        }
        return null;
    }, [location.pathname, health?.status, (health as any)?.version]);

    // Get page title based on path
    const getPageTitle = (path: string) => {
        switch (path) {
            case '/dashboard': return '지휘통제 및 작전분석';
            case '/knowledge-graph': return '지식 그래프 탐색';
            case '/data-management': return '데이터 관리 센터';
            case '/ontology-studio': return '온톨로지 스튜디오';
            case '/rag-management': return 'RAG 지식 인덱싱';
            case '/learning-guide': return '시스템 학습 가이드';
            default: return '플랫폼 대시보드';
        }
    };

    return (
        <header className="flex justify-between items-center h-16 bg-white dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 px-6 flex-shrink-0 z-50">
            <div className="flex items-center gap-6">
                <Link
                    to="/"
                    className="flex items-center gap-2 group p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-zinc-800 transition-all border border-transparent hover:border-gray-200 dark:hover:border-zinc-700"
                    title="포털 센터로 돌아가기"
                >
                    <div className="bg-indigo-600 text-white p-2 rounded-lg group-hover:scale-110 transition-transform shadow-lg shadow-indigo-500/20">
                        <Home className="w-5 h-5" />
                    </div>
                </Link>

                <div className="flex flex-col">
                    <h1 className="text-lg font-black text-gray-900 dark:text-white tracking-tight flex items-center gap-2">
                        {getPageTitle(location.pathname)}
                        <span className="text-[10px] font-bold text-indigo-500 bg-indigo-500/10 px-1.5 py-0.5 rounded leading-none">ALPHA</span>
                    </h1>
                    <div className="flex items-center gap-2 text-[10px] text-gray-400 font-bold uppercase tracking-widest">
                        <Activity className="w-3 h-3 text-green-500" /> System Online & Synced
                        {healthDisplay}
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-4">
                <Link
                    to="/"
                    className="flex items-center gap-2 px-4 py-2 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 rounded-xl text-xs font-black uppercase tracking-wider transition-all border border-zinc-200 dark:border-zinc-700"
                >
                    <LayoutGrid className="w-4 h-4" /> 포털 메뉴
                </Link>

                <div className="h-8 w-px bg-gray-200 dark:bg-zinc-800 mx-2" />

                <div className="flex items-center gap-3 bg-gray-50 dark:bg-zinc-800/50 p-1 pr-3 rounded-full border border-gray-200 dark:border-zinc-700">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-black text-xs shadow-inner">
                        AD
                    </div>
                    <span className="text-xs font-bold text-gray-600 dark:text-zinc-400">ADMIN</span>
                </div>
            </div>
        </header>
    );
};
