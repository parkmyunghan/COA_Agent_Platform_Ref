import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, Minimize2, FileText, ChevronRight, ChevronDown } from 'lucide-react';
import api from '../lib/api';
import type { ChatMessage, ChatResponse } from '../types/chat';
import type { COASummary, COAResponse } from '../types/schema';

interface ChatInterfaceProps {
    className?: string;
    coaRecommendations?: COASummary[];
    selectedCOA?: COASummary | null;
    situationInfo?: any;
    isOpen?: boolean;
    onOpenChange?: (isOpen: boolean) => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
    className,
    coaRecommendations = [],
    selectedCOA,
    situationInfo,
    isOpen: externalIsOpen,
    onOpenChange
}) => {
    const [internalIsOpen, setInternalIsOpen] = useState(false);
    const isOpen = externalIsOpen !== undefined ? externalIsOpen : internalIsOpen;
    const setIsOpen = onOpenChange || setInternalIsOpen;
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // COA 결과가 변경되면 자동으로 메시지 초기화 및 컨텍스트 메시지 추가
    useEffect(() => {
        // COA 추천 결과가 있을 때
        if (coaRecommendations.length > 0) {
            const contextMessage: ChatMessage = {
                role: 'assistant',
                content: `방책 추천이 완료되었습니다. 총 ${coaRecommendations.length}개의 방책이 추천되었습니다.\n\n추천된 방책:\n${coaRecommendations.map((coa, idx) => `${idx + 1}. ${coa.coa_name} (점수: ${coa.total_score !== undefined ? (coa.total_score * 100).toFixed(1) : 'N/A'}%)`).join('\n')}\n\n이 방책들에 대해 질문해주세요. 예: "첫 번째 방책의 위험 요소는 무엇인가요?"`,
                timestamp: new Date().toISOString()
            };
            // 새로운 방책 추천 시 이전 대화 초기화하고 새 컨텍스트 메시지 설정
            setMessages([contextMessage]);
        } else if (coaRecommendations.length === 0 && messages.length > 0) {
            // COA가 없어졌을 때 (새로운 위협 선택 등) 메시지 초기화
            setMessages([]);
        }
    }, [coaRecommendations.length, coaRecommendations[0]?.coa_id]); // COA 개수와 첫 번째 COA ID 변경 감지

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isOpen]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMessage: ChatMessage = {
            role: 'user',
            content: input,
            timestamp: new Date().toISOString()
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            // [DEBUG] 상황 정보 로깅
            console.log('[ChatInterface] Sending message with situationInfo:', situationInfo);

            // Retrieve Agent ID from Session/Context if implementing Agent Selection
            // For now, using default or none. 
            // In a real scenario, this would come from a Context Provider.

            // COA 컨텍스트 추가
            const contextData: any = {
                message: userMessage.content,
                history: messages,
                use_rag: true
            };

            // COA 추천 결과가 있으면 컨텍스트에 추가
            if (coaRecommendations.length > 0) {
                contextData.coa_context = {
                    recommendations: coaRecommendations.map(coa => ({
                        coa_id: coa.coa_id,
                        coa_name: coa.coa_name,
                        total_score: coa.total_score,
                        description: coa.description,
                        reasoning: coa.reasoning,
                        score_breakdown: coa.score_breakdown
                    })),
                    selected_coa: selectedCOA ? {
                        coa_id: selectedCOA.coa_id,
                        coa_name: selectedCOA.coa_name
                    } : null
                };
            }

            // 상황 정보 추가
            const situationId = situationInfo?.threat_id || situationInfo?.위협ID || situationInfo?.selected_threat_id;
            if (situationId) {
                contextData.situation_id = situationId;
            }
            if (situationInfo) {
                contextData.situation_info = situationInfo;
            }

            // [DEBUG] API 요청 페이로드 로깅
            console.log('[ChatInterface] API Request Payload:', JSON.stringify(contextData, null, 2));

            const response = await api.post<ChatResponse>('/chat/completions', contextData);

            const assistantMessage: ChatMessage = {
                role: 'assistant',
                content: response.data.response,
                citations: response.data.citations,
                timestamp: new Date().toISOString()
            };

            setMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            console.error('Chat error:', error);
            const errorMessage: ChatMessage = {
                role: 'assistant',
                content: '죄송합니다. 오류가 발생했습니다.',
                timestamp: new Date().toISOString()
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    if (!isOpen) {
        // 외부에서 제어하는 경우 우측 하단 버튼을 표시하지 않음
        if (onOpenChange) {
            return null;
        }

        return (
            <button
                onClick={() => setIsOpen(true)}
                className={`fixed bottom-20 right-6 p-4 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg transition-all z-[60] flex items-center gap-2 ${className}`}
            >
                <MessageSquare className="w-6 h-6" />
                <span className="font-semibold">작전 지휘관 채팅 (AI)</span>
            </button>
        );
    }

    return (
        <div className={`fixed bottom-20 right-6 w-96 h-[600px] bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl flex flex-col z-[60] ${className}`}>
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-zinc-700 bg-zinc-800/50 rounded-t-xl">
                <div className="flex items-center gap-2">
                    <MessageSquare className="w-5 h-5 text-blue-400" />
                    <h3 className="font-semibold text-white">작전 지휘관 채팅</h3>
                </div>
                <div className="flex items-center gap-2">
                    <button onClick={() => setIsOpen(false)} className="text-zinc-400 hover:text-white transition-colors">
                        <Minimize2 className="w-4 h-4" />
                    </button>
                    <button onClick={() => setMessages([])} className="text-xs text-zinc-400 hover:text-red-400 ml-2">
                        기록 삭제
                    </button>
                </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 && (
                    <div className="text-center text-zinc-500 mt-10">
                        <p>AI 작전 참모에게 질문하세요.</p>
                        <p className="text-sm mt-2">예: "현재 위협 상황을 요약해줘"</p>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                        <div
                            className={`max-w-[85%] p-3 rounded-lg ${msg.role === 'user'
                                ? 'bg-blue-600 text-white'
                                : 'bg-zinc-800 text-zinc-200 border border-zinc-700'
                                }`}
                        >
                            <div className="whitespace-pre-wrap text-sm">{msg.content}</div>
                        </div>

                        {/* Citations (Accordion) */}
                        {msg.citations && msg.citations.length > 0 && (
                            <div className="mt-2 w-[85%]">
                                <CitationAccordion citations={msg.citations} />
                            </div>
                        )}

                        <span className="text-xs text-zinc-500 mt-1">
                            {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''}
                        </span>
                    </div>
                ))}

                {isLoading && (
                    <div className="flex items-start">
                        <div className="bg-zinc-800 p-3 rounded-lg border border-zinc-700 flex gap-2 items-center">
                            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" />
                            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce delay-75" />
                            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce delay-150" />
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-zinc-700 bg-zinc-800/30 rounded-b-xl">
                <div className="flex gap-2">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyPress}
                        placeholder="질문을 입력하세요..."
                        className="flex-1 bg-zinc-950 border border-zinc-700 rounded-lg p-2 text-sm text-white focus:outline-none focus:border-blue-500 resize-none h-12" // Fixed height for simplicity
                    />
                    <button
                        onClick={handleSend}
                        disabled={isLoading || !input.trim()}
                        className="bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 text-white p-2 rounded-lg transition-colors flex items-center justify-center shrink-0 w-12"
                    >
                        <Send className="w-5 h-5" />
                    </button>
                </div>
            </div>
        </div>
    );
};

// Sub-component for Citations
const CitationAccordion: React.FC<{ citations: any[] }> = ({ citations }) => {
    const [isOpen, setIsOpen] = useState(false);

    if (!citations || citations.length === 0) return null;

    return (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-md overflow-hidden">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between p-2 text-xs text-zinc-400 hover:bg-zinc-800 transition-colors"
            >
                <div className="flex items-center gap-1">
                    <FileText className="w-3 h-3" />
                    <span>참고 문서 ({citations.length})</span>
                </div>
                {isOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            </button>

            {isOpen && (
                <div className="p-2 space-y-2 border-t border-zinc-800">
                    {citations.map((cit, idx) => (
                        <div key={idx} className="bg-zinc-950 p-2 rounded text-xs border border-zinc-800 text-zinc-300">
                            {/* Show Agent Result if available */}
                            {cit.metadata?.source === 'agent' ? (
                                <div>
                                    <span className="font-bold text-amber-500">[Agent Result]</span>
                                    <div className="mt-1 whitespace-pre-wrap max-h-32 overflow-y-auto custom-scrollbar">
                                        {cit.text}
                                    </div>
                                </div>
                            ) : (
                                <div>
                                    <span className="font-bold text-blue-400">[{cit.metadata?.doc_name || `Doc ${cit.doc_id}`}]</span>
                                    <p className="mt-1 line-clamp-3 hover:line-clamp-none cursor-pointer" title="Click to expand">
                                        {cit.text}
                                    </p>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ChatInterface;
