export interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp?: string;
    citations?: Citation[];
}

export interface Citation {
    doc_id: number;
    text: string;
    score: number;
    index: number;
    metadata?: Record<string, any>;
}

export interface ChatRequest {
    message: string;
    history?: ChatMessage[];
    agent_id?: string;
    situation_id?: string;
    use_rag?: boolean;
    llm_model?: string;
}

export interface ChatResponse {
    response: string;
    citations?: Citation[];
    agent_result?: Record<string, any>;
}
