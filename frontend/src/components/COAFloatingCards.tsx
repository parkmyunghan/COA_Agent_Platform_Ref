import React, { useState, useRef, forwardRef, useImperativeHandle } from 'react';
import { X, BarChart3, Minimize2, Maximize2, GripVertical, FileSearch } from 'lucide-react';
import type { COASummary } from '../types/schema';
import { detectCOAType, extractKeyTactics, summarizeUnitDeployment } from '../lib/cop-visualization-utils';

interface COAFloatingCardsProps {
    coas: COASummary[];
    selectedCOA: COASummary | null;
    onCOASelect: (coa: COASummary) => void;
    onViewDetail?: (coa: COASummary) => void; // 상세 분석 버튼 클릭 시
    onCompare?: () => void;
}

export interface COAFloatingCardsRef {
    getContainerElement: () => HTMLDivElement | null;
}

export const COAFloatingCards = forwardRef<COAFloatingCardsRef, COAFloatingCardsProps>(({
    coas,
    selectedCOA,
    onCOASelect,
    onViewDetail,
    onCompare
}, ref) => {
    const [isMinimized, setIsMinimized] = useState(false);
    const [position, setPosition] = useState<{ x: number; y: number } | null>(null); // null로 초기화하여 위치 계산 전까지 숨김
    const [isDragging, setIsDragging] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
    const containerRef = useRef<HTMLDivElement>(null);

    // 외부에서 containerRef에 접근할 수 있도록 노출
    useImperativeHandle(ref, () => ({
        getContainerElement: () => containerRef.current
    }));

    // 정황보고 박스 위치 계산하여 초기 위치 설정
    React.useEffect(() => {
        // coas가 없으면 위치 계산하지 않음
        if (!coas || coas.length === 0) {
            return;
        }

        const calculateInitialPosition = () => {
            // 정황보고 박스 찾기 (situation-summary-box 클래스 사용)
            const situationBox = document.querySelector('.situation-summary-box') as HTMLElement;

            if (situationBox) {
                const rect = situationBox.getBoundingClientRect();
                // 정황보고 박스 아래 위치 (bottom + 여백)
                // 상황판단이 추가되어 박스 높이가 늘어났으므로 여백을 더 크게 설정
                const newY = rect.bottom + 20; // 20px 여백 (상황판단 추가로 박스 높이 증가 반영)
                const newX = rect.left; // 정황보고 박스와 같은 x 위치

                setPosition({ x: newX, y: newY });
            } else {
                // 정황보고 박스를 찾을 수 없으면 지도 컨테이너를 찾아서 그 위에 배치
                const mapContainer = document.querySelector('.leaflet-container') as HTMLElement;
                if (mapContainer) {
                    const mapRect = mapContainer.getBoundingClientRect();
                    // 지도 상단 좌측에 배치 (정황보고 박스가 있을 위치 고려)
                    // 상황판단 추가로 박스 높이가 늘어났으므로 더 아래로 배치
                    setPosition({ x: mapRect.left + 8, y: mapRect.top + 80 }); // top-2 (8px) + 정황보고+상황판단 높이 (약 70px) + 여백 (10px)
                } else {
                    // 지도도 찾을 수 없으면 화면 중앙 상단
                    setPosition({ x: window.innerWidth / 2 - 160, y: 50 }); // 카드 너비의 절반을 빼서 중앙 정렬
                }
            }
        };

        // 지도가 렌더링된 후 위치 계산 (여러 번 시도)
        // 즉시 한 번 실행하고, 추가로 지연 실행
        calculateInitialPosition();
        const timer1 = setTimeout(calculateInitialPosition, 50);
        const timer2 = setTimeout(calculateInitialPosition, 200);
        const timer3 = setTimeout(calculateInitialPosition, 500);

        return () => {
            clearTimeout(timer1);
            clearTimeout(timer2);
            clearTimeout(timer3);
        };
    }, [coas]); // coas가 변경될 때마다 재계산

    // 드래그 이벤트 처리
    React.useEffect(() => {
        if (!isDragging || position === null) return;

        const handleMouseMove = (e: MouseEvent) => {
            setPosition({
                x: e.clientX - dragStart.x,
                y: e.clientY - dragStart.y
            });
        };

        const handleMouseUp = () => {
            setIsDragging(false);
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);

        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDragging, dragStart, position]);

    const handleHeaderMouseDown = (e: React.MouseEvent) => {
        // 버튼 클릭은 드래그 방지
        if ((e.target as HTMLElement).closest('button')) {
            return;
        }
        if (position === null) return;
        setIsDragging(true);
        setDragStart({
            x: e.clientX - position.x,
            y: e.clientY - position.y
        });
        e.preventDefault();
    };

    // 조건부 렌더링: JSX에서 처리 (hooks 규칙 준수)
    // coas가 없거나 position이 계산되지 않았으면 렌더링하지 않음
    if (!coas || coas.length === 0 || position === null) {
        return null;
    }

    return (
        <div
            ref={containerRef}
            className={`fixed z-50 transition-all duration-300 ${isMinimized ? 'w-64' : 'w-80'
                }`}
            style={{
                left: `${position.x}px`,
                top: `${position.y}px`,
                cursor: isDragging ? 'grabbing' : 'default',
                userSelect: 'none',
                opacity: 1,
                pointerEvents: 'auto'
            }}
        >
            <div className="bg-white/95 dark:bg-zinc-900/95 backdrop-blur-sm rounded-xl shadow-2xl border-2 border-indigo-500/50 overflow-hidden">
                {/* Header - 드래그 핸들 */}
                <div
                    className="bg-gradient-to-r from-indigo-600 to-purple-600 p-2 flex items-center justify-between cursor-move select-none"
                    onMouseDown={handleHeaderMouseDown}
                >
                    <div className="flex items-center gap-2 flex-1">
                        <GripVertical className="w-4 h-4 text-white/60" />
                        <div className="flex-1">
                            <h3 className="text-white font-bold text-xs">
                                추천 방책 ({coas.length}개)
                            </h3>
                        </div>
                    </div>
                    <div className="flex items-center gap-1">
                        {onCompare && coas.length > 1 && (
                            <button
                                onClick={onCompare}
                                className="p-1.5 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                                title="비교 분석"
                            >
                                <BarChart3 className="w-4 h-4" />
                            </button>
                        )}
                        <button
                            onClick={() => setIsMinimized(!isMinimized)}
                            className="p-1.5 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                            title={isMinimized ? '확대' : '최소화'}
                        >
                            {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
                        </button>
                    </div>
                </div>

                {/* Content */}
                {!isMinimized && (
                    <div className="p-3 space-y-2 max-h-96 overflow-y-auto">
                        {coas.map((coa, idx) => {
                            const isSelected = selectedCOA?.coa_id === coa.coa_id;
                            const score = coa.total_score !== undefined ? (coa.total_score * 100).toFixed(1) : 'N/A';

                            return (
                                <div
                                    key={coa.coa_id}
                                    onClick={() => onCOASelect(coa)}
                                    className={`p-3 bg-white dark:bg-zinc-900 rounded-lg border-2 cursor-pointer transition-all transform hover:scale-[1.02] ${isSelected
                                        ? 'border-indigo-500 dark:border-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 shadow-md'
                                        : 'border-gray-200 dark:border-zinc-700 hover:border-indigo-300 dark:hover:border-indigo-600'
                                        }`}
                                >
                                    {/* Rank Badge & Score */}
                                    <div className="flex items-center justify-between mb-1.5">
                                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-black ${idx === 0
                                            ? 'bg-yellow-500 text-white'
                                            : idx === 1
                                                ? 'bg-gray-400 text-white'
                                                : 'bg-orange-600 text-white'
                                            }`}>
                                            {idx === 0 ? '🥇' : idx === 1 ? '🥈' : '🥉'} {coa.rank}
                                        </span>
                                        <span className="text-base font-black text-indigo-600 dark:text-indigo-400">
                                            {score}%
                                        </span>
                                    </div>

                                    {/* COA Type & Name */}
                                    <div className="flex items-center gap-1.5 mb-1">
                                        {(() => {
                                            const typeInfo = detectCOAType(coa.coa_name, coa.description);
                                            return (
                                                <>
                                                    <span className="text-base" title={typeInfo.label}>
                                                        {typeInfo.icon}
                                                    </span>
                                                    <h4 className="font-bold text-xs text-gray-900 dark:text-white flex-1 whitespace-normal break-keep">
                                                        {coa.coa_name}
                                                    </h4>
                                                </>
                                            );
                                        })()}
                                    </div>

                                    {/* Key Tactics */}
                                    <div className="mb-1.5 p-1.5 bg-indigo-50 dark:bg-indigo-900/20 rounded border border-indigo-200 dark:border-indigo-700">
                                        <p className="text-[10px] font-semibold text-indigo-700 dark:text-indigo-300 whitespace-normal break-keep">
                                            💡 {extractKeyTactics(coa)}
                                        </p>
                                    </div>

                                    {/* Unit Deployment */}
                                    <div className="mb-2">
                                        <p className="text-[10px] text-gray-600 dark:text-gray-400">
                                            📍 {summarizeUnitDeployment(coa)}
                                        </p>
                                    </div>

                                    {/* Quick Score Indicator */}
                                    <div className="flex items-center gap-2 mb-2">
                                        <div className="flex-1 h-1.5 bg-gray-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-indigo-500 rounded-full transition-all"
                                                style={{ width: `${(coa.total_score || 0) * 100}%` }}
                                            />
                                        </div>
                                        {isSelected && (
                                            <span className="text-[9px] text-indigo-600 dark:text-indigo-400 font-semibold">
                                                ✓
                                            </span>
                                        )}
                                    </div>

                                    {/* 상세 분석 버튼 */}
                                    {onViewDetail && (
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation(); // 카드 클릭 이벤트 방지
                                                onViewDetail(coa);
                                            }}
                                            className="w-full flex items-center justify-center gap-1.5 px-2 py-1.5 text-[10px] font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-md transition-colors"
                                            title="상세 분석 보기"
                                        >
                                            <FileSearch className="w-3 h-3" />
                                            상세 분석
                                        </button>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* Minimized View */}
                {isMinimized && (
                    <div className="p-2">
                        <div className="flex items-center justify-center gap-1">
                            {coas.map((coa, idx) => {
                                const isSelected = selectedCOA?.coa_id === coa.coa_id;
                                return (
                                    <div
                                        key={coa.coa_id}
                                        onClick={() => onCOASelect(coa)}
                                        className={`w-8 h-8 rounded border-2 cursor-pointer flex items-center justify-center text-xs font-bold ${isSelected
                                            ? 'border-indigo-500 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                                            : 'border-gray-300 dark:border-zinc-600 bg-gray-100 dark:bg-zinc-800 text-gray-600 dark:text-gray-400'
                                            }`}
                                    >
                                        {idx + 1}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
});
