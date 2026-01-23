// frontend/src/pages/LandingPage.tsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Target,
    Network,
    Database,
    Settings,
    BookOpen,
    Shield,
    Zap,
    ArrowRight
} from 'lucide-react';

interface PortalCardProps {
    title: string;
    description: string;
    icon: React.ReactNode;
    to: string;
    phase: string;
    color: string;
}

const PortalCard: React.FC<PortalCardProps> = ({ title, description, icon, to, phase, color }) => {
    const navigate = useNavigate();

    return (
        <div
            onClick={() => navigate(to)}
            className="group relative bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-2xl p-6 cursor-pointer overflow-hidden transition-all duration-500 hover:shadow-2xl hover:shadow-indigo-500/10 hover:-translate-y-2 hover:border-indigo-500/50"
        >
            {/* Background Gradient Effect */}
            <div className={`absolute -right-10 -top-10 w-40 h-40 rounded-full blur-3xl opacity-0 group-hover:opacity-20 transition-opacity duration-700 ${color}`} />

            <div className="relative z-10 flex flex-col h-full">
                <div className="flex justify-between items-start mb-6">
                    <div className="p-3 bg-gray-50 dark:bg-zinc-800 rounded-xl group-hover:bg-indigo-600 group-hover:text-white transition-colors duration-300">
                        {icon}
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 bg-zinc-100 dark:bg-zinc-800 dark:text-zinc-400 px-2 py-1 rounded-md">
                        {phase}
                    </span>
                </div>

                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2 group-hover:text-indigo-400 transition-colors">
                    {title}
                </h3>

                <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed mb-6 flex-1">
                    {description}
                </p>

                <div className="flex items-center text-xs font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider group-hover:translate-x-2 transition-transform">
                    이동하기 <ArrowRight className="ml-1 w-4 h-4" />
                </div>
            </div>
        </div>
    );
};

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-white dark:bg-zinc-950 flex flex-col">
            {/* Hero Section */}
            <header className="relative bg-zinc-900 overflow-hidden py-24 border-b border-zinc-800">
                <div className="absolute inset-0 overflow-hidden pointer-events-none">
                    <div className="absolute top-1/4 -left-1/4 w-1/2 h-1/2 bg-blue-600/20 rounded-full blur-[120px] animate-pulse" />
                    <div className="absolute bottom-1/4 -right-1/4 w-1/2 h-1/2 bg-indigo-600/20 rounded-full blur-[120px] animate-pulse delay-1000" />
                </div>

                <div className="w-full px-6 md:px-12 lg:px-24 relative z-10 text-center">
                    <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 px-3 py-1 rounded-full text-indigo-400 text-xs font-bold uppercase tracking-widest mb-8">
                        <Zap className="w-4 h-4" /> Defense Intelligent Agent Platform
                    </div>
                    <h1 className="text-5xl md:text-7xl lg:text-8xl font-black text-white mb-6 tracking-tight">
                        지휘결심 지원 <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-500">포털 대시보드</span>
                    </h1>
                    <p className="max-w-4xl mx-auto text-lg md:text-xl text-zinc-400 leading-relaxed italic">
                        "데이터에서 지식으로, 지식에서 작전적 결심으로 이어지는 차세대 지능형 국방 분석 체계"
                    </p>
                </div>
            </header>

            {/* Portal Grid */}
            <main className="flex-1 w-full px-6 md:px-12 lg:px-16 py-16">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6 gap-6 md:gap-8">
                    <PortalCard
                        title="지휘통제 및 방책분석"
                        description="실시간 작전 상황도(COP)를 기반으로 위협을 탐지하고 최적의 방책(COA)을 추천 및 분석합니다."
                        icon={<Target className="w-6 h-6" />}
                        to="/dashboard"
                        phase="Phase 2 & 4"
                        color="bg-red-500"
                    />
                    <PortalCard
                        title="지식 그래프 탐색"
                        description="온톨로지 기반의 지식 연결망을 탐색하고 복잡한 군사 지식을 시각적으로 분석합니다."
                        icon={<Network className="w-6 h-6" />}
                        to="/knowledge-graph"
                        phase="Phase 3"
                        color="bg-blue-500"
                    />
                    <PortalCard
                        title="데이터 관리 센터"
                        description="시스템의 기초가 되는 엑셀 및 다양한 데이터 소스를 업로드하고 정제 및 관리합니다."
                        icon={<Database className="w-6 h-6" />}
                        to="/data-management"
                        phase="Phase 1 & 3"
                        color="bg-green-500"
                    />
                    <PortalCard
                        title="온톨로지 스튜디오"
                        description="지식 베이스의 스키마를 정의하고, 도메인 지식을 구조화하여 인공지능의 추론 기반을 구축합니다."
                        icon={<Settings className="w-6 h-6" />}
                        to="/ontology-studio"
                        phase="Phase 4"
                        color="bg-purple-500"
                    />
                    <PortalCard
                        title="RAG 지식 인덱싱"
                        description="비정형 군사 교범 및 문서를 벡터화하여 LLM이 정확한 근거 기반 답변을 하도록 관리합니다."
                        icon={<BookOpen className="w-6 h-6" />}
                        to="/rag-management"
                        phase="Phase 4"
                        color="bg-yellow-500"
                    />
                    <PortalCard
                        title="시스템 학습 가이드"
                        description="플랫폼 사용법, 설계 원칙 및 국방 도메인 지식 체계에 대한 상세 문서를 열람합니다."
                        icon={<Shield className="w-6 h-6" />}
                        to="/learning-guide"
                        phase="Phase 5"
                        color="bg-zinc-500"
                    />
                </div>
            </main>

            {/* Footer */}
            <footer className="py-8 border-t border-gray-100 dark:border-zinc-900 text-center">
                <p className="text-zinc-500 text-xs font-mono uppercase tracking-widest">
                    &copy; 2026 NEXT GENERATION COA AGENT PLATFORM - ALL RIGHTS RESERVED
                </p>
            </footer>
        </div>
    );
}
