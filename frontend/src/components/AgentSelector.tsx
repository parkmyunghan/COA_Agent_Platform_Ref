import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import api from '../lib/api';

interface Agent {
    name: string;
    description?: string;
    enabled?: boolean;
}

interface AgentSelectorProps {
    onAgentChange: (agentName: string | null) => void;
    selectedAgent?: string | null;
}

export const AgentSelector: React.FC<AgentSelectorProps> = ({ onAgentChange, selectedAgent }) => {
    const [agents, setAgents] = useState<Agent[]>([]);
    const [loading, setLoading] = useState(true);
    
    // React StrictMode 이중 렌더링 방지
    const hasFetchedRef = useRef(false);
    const isFetchingRef = useRef(false);

    useEffect(() => {
        // 이미 요청했거나 요청 중이면 중복 요청 방지
        if (hasFetchedRef.current || isFetchingRef.current) {
            return;
        }
        
        const fetchAgents = async () => {
            try {
                isFetchingRef.current = true;
                setLoading(true);
                // API에서 Agent 목록 가져오기
                const response = await api.get('/system/agents');
                const agentsList = response.data.agents || [];
                const enabledAgents = agentsList.filter((a: Agent) => a.enabled !== false);
                setAgents(enabledAgents);
                
                // 첫 번째 Agent 자동 선택
                if (enabledAgents.length > 0 && !selectedAgent) {
                    onAgentChange(enabledAgents[0].name);
                }
                hasFetchedRef.current = true;
            } catch (err: any) {
                console.error('Failed to fetch agents:', err);
                // 기본 Agent 목록 사용 (에러 메시지 없이 조용히 처리)
                const defaultAgents = [
                    { name: 'coa_recommendation_agent', description: 'COA 추천 Agent', enabled: true }
                ];
                setAgents(defaultAgents);
                
                // 기본 Agent 자동 선택
                if (!selectedAgent) {
                    onAgentChange(defaultAgents[0].name);
                }
                hasFetchedRef.current = true;
            } finally {
                setLoading(false);
                isFetchingRef.current = false;
            }
        };

        fetchAgents();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // 빈 의존성 배열로 마운트 시 한 번만 실행

    if (loading) {
        return (
            <Card className="border-gray-200 dark:border-zinc-700">
                <CardContent className="p-4">
                    <div className="flex items-center justify-center">
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                        <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">Agent 목록 로딩 중...</span>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="border-gray-200 dark:border-zinc-700">
            <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold">Agent 선택</CardTitle>
            </CardHeader>
            <CardContent>
                <select
                    value={selectedAgent || ''}
                    onChange={(e) => onAgentChange(e.target.value || null)}
                    className="w-full h-10 rounded-md border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                    <option value="">실행할 Agent 선택</option>
                    {agents.map((agent) => (
                        <option key={agent.name} value={agent.name}>
                            {agent.name}
                        </option>
                    ))}
                </select>
                
                {selectedAgent && (
                    <div className="mt-3 p-2 bg-gray-50 dark:bg-zinc-800 rounded text-xs text-gray-600 dark:text-gray-400">
                        {agents.find(a => a.name === selectedAgent)?.description || 'Agent 설명 없음'}
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
