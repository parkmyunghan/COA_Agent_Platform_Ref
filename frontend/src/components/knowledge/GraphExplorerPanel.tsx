// frontend/src/components/knowledge/GraphExplorerPanel.tsx
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Filter, Maximize2, Minimize2, MousePointer2, AlertTriangle, Shield, Users, Flag, Box, Map as MapIcon, HelpCircle, Brain } from 'lucide-react';
import ForceGraph2D from 'react-force-graph-2d';
import api from '../../lib/api';
import { Card } from '../ui/card';

interface GraphNode {
    id: string;
    label: string;
    group: string;
    x?: number;
    y?: number;
    val?: number; // importance/size
}

interface GraphLink {
    source: string | GraphNode;
    target: string | GraphNode;
    relation: string;
}

interface GraphData {
    nodes: GraphNode[];
    links: GraphLink[];
}

// Visual Configuration
interface NodeStyle {
    color: string;
    icon: string; // unicode character or text
    iconColor: string;
    label: string; // User friendly label for legend
}

const SCHEMA_TERM_HELP = {
    'subClassOf': '개념의 상속 구조를 나타냅니다. 하위 클래스는 상위 클래스의 모든 속성을 물려받습니다. (예: 주력부대는 부대의 하나)',
    'domain': '해당 속성(관계)이 정의되는 출발지 클래스입니다.',
    'range': '해당 속성이 가리키는 도착지 클래스 또는 데이터 타입입니다.'
};

const MODE_DESCRIPTIONS = {
    'instances': {
        title: 'A-Box (Assertion Box)',
        desc: '실재하는 구체적인 사실 정보들의 집합입니다.',
        detail: '온톨로지 설계도(T-Box)를 바탕으로 실제 전장 상황의 데이터(특정 부대, 지형, 기상 등)를 표현합니다. 객체지향의 "인스턴스"와 같은 개념입니다.'
    },
    'schema': {
        title: 'T-Box (Terminological Box)',
        desc: '온톨로지의 개념적 설계도 및 규칙 집합입니다.',
        detail: '클래스와 속성의 정의, 계층 구조(상속) 등을 나타냅니다. 실제 데이터가 채워지기 전의 "틀"이며, 프로그래밍의 "클래스 정의"와 같은 개념입니다.'
    }
};

const NODE_STYLES: Record<string, NodeStyle> = {
    // Standard Types
    'COA': { color: '#3b82f6', icon: '🛡️', iconColor: '#fff', label: '방책 (COA)' },
    'Threat': { color: '#ef4444', icon: '⚠️', iconColor: '#fff', label: '위협 (Threat)' },
    'Mission': { color: '#8b5cf6', icon: '🚩', iconColor: '#fff', label: '임무 (Mission)' },
    'Resource': { color: '#f59e0b', icon: '📦', iconColor: '#fff', label: '자원 (Resource)' },
    'Axis': { color: '#10b981', icon: '↔️', iconColor: '#fff', label: '축선 (Axis)' },
    'Unit': { color: '#06b6d4', icon: '👥', iconColor: '#fff', label: '부대 (Unit)' },
    'Terrain': { color: '#78716c', icon: '⛰️', iconColor: '#fff', label: '지형 (Terrain)' },
    'Unknown': { color: '#6b7280', icon: '❓', iconColor: '#fff', label: '기타' },

    // COA Detailed Types
    'DefenseCOA': { color: '#3b82f6', icon: '🛡️', iconColor: '#fff', label: '방어방책' },
    'OffensiveCOA': { color: '#2563eb', icon: '⚔️', iconColor: '#fff', label: '공격방책' },
    'CounterAttackCOA': { color: '#1d4ed8', icon: '🔄', iconColor: '#fff', label: '반격방책' },
    'PreemptiveCOA': { color: '#1e40af', icon: '⚡', iconColor: '#fff', label: '선제타격' },
    'DeterrenceCOA': { color: '#1e3a8a', icon: '🛑', iconColor: '#fff', label: '억제방책' },
    'ManeuverCOA': { color: '#3b82f6', icon: '🚜', iconColor: '#fff', label: '기동방책' },
    'InformationOpsCOA': { color: '#60a5fa', icon: '📡', iconColor: '#fff', label: '정보작전' },

    // Korean Mappings (Table Names)
    '위협상황': { color: '#ef4444', icon: '⚠️', iconColor: '#fff', label: '위협상황' },
    '임무정보': { color: '#8b5cf6', icon: '🚩', iconColor: '#fff', label: '임무정보' },
    '임무별_자원할당': { color: '#a78bfa', icon: '📋', iconColor: '#fff', label: '자원할당' },
    '가용자원': { color: '#f59e0b', icon: '📦', iconColor: '#fff', label: '가용자원' },
    '아군가용자산': { color: '#fbbf24', icon: '🚜', iconColor: '#fff', label: '아군자산' },
    '전장축선': { color: '#10b981', icon: '↔️', iconColor: '#fff', label: '전장축선' },
    '아군부대현황': { color: '#06b6d4', icon: '👨‍✈️', iconColor: '#fff', label: '아군부대' },
    '적군부대현황': { color: '#dc2626', icon: '👿', iconColor: '#fff', label: '적군부대' },
    '지형셀': { color: '#78716c', icon: '⛰️', iconColor: '#fff', label: '지형셀' },
    '기상상황': { color: '#0ea5e9', icon: '☁️', iconColor: '#fff', label: '기상상황' },
    '제약조건': { color: '#f97316', icon: '🚫', iconColor: '#fff', label: '제약조건' },
    '민간인지역': { color: '#14b8a6', icon: '🏘️', iconColor: '#fff', label: '민간지역' },
    '평가기준_가중치': { color: '#6366f1', icon: '⚖️', iconColor: '#fff', label: '평가기준' },
    '위협유형_마스터': { color: '#991b1b', icon: '📖', iconColor: '#fff', label: '위협마스터' },
    '시나리오모음': { color: '#d946ef', icon: '🎬', iconColor: '#fff', label: '시나리오' },
    '방책유형_위협유형_관련성': { color: '#4f46e5', icon: '🔗', iconColor: '#fff', label: '위협관련성' },

    // Ontology Technical Types
    // Ontology Technical Types
    'Class': { color: '#d97706', icon: '🏷️', iconColor: '#fff', label: '클래스' }, // Amber-600
    'Property': { color: '#475569', icon: '⚙️', iconColor: '#fff', label: '속성' }, // Slate-600 (Generic)
    'ObjectProperty': { color: '#2563eb', icon: '🔗', iconColor: '#fff', label: '객체속성' }, // Blue-600
    'DatatypeProperty': { color: '#059669', icon: '🔢', iconColor: '#fff', label: '데이터속성' }, // Emerald-600
    'Axiom': { color: '#9ca3af', icon: '📜', iconColor: '#fff', label: '공리' },
    'Environment': { color: '#10b981', icon: '🌍', iconColor: '#fff', label: '환경' },
    'Constraint': { color: '#f97316', icon: '🚫', iconColor: '#fff', label: '제약조건' },
    'OntologyCOAType': { color: '#3b82f6', icon: '🏷️', iconColor: '#fff', label: '방책유형' }
};

const TECHNICAL_GROUPS = ['Axiom', 'Class', 'Property', 'ObjectProperty', 'DatatypeProperty', 'Environment', 'Datatype', 'AnnotationProperty'];

// 시나리오 기반 탐색 정의
interface ExploreScenario {
    id: string;
    name: string;
    icon: string;
    description: string;
    nodeTypes: string[];  // 표시할 노드 그룹
    relationTypes?: string[];  // 표시할 관계 유형 (optional)
}

const EXPLORE_SCENARIOS: ExploreScenario[] = [
    {
        id: 'axis-units',
        name: '축선별 부대',
        icon: '🗺️',
        description: '축선과 배치된 부대 관계',
        nodeTypes: ['전장축선', 'Axis', '아군부대현황', '적군부대현황', 'Unit', '임무정보', 'Mission', '위협상황', 'Threat'],
        relationTypes: ['has전장축선', 'hasMission', 'has임무정보', 'has적군부대현황']
    },
    {
        id: 'threat-coa',
        name: '위협-방책',
        icon: '⚔️',
        description: '위협상황과 대응 방책',
        nodeTypes: ['위협상황', 'Threat', 'COA', 'COA_Library', 'DefenseCOA', 'OffensiveCOA', 'CounterAttackCOA', 'ManeuverCOA', 'PreemptiveCOA', 'DeterrenceCOA', 'InformationOpsCOA', '위협유형_마스터'],
        relationTypes: ['respondsTo', 'hasRelatedCOA', '위협유형코드']
    },
    {
        id: 'mission-resource',
        name: '임무-자원',
        icon: '📋',
        description: '임무와 할당된 자원/부대',
        nodeTypes: ['임무정보', 'Mission', '아군가용자산', 'Resource', '가용자원', '임무별_자원할당'],
        relationTypes: ['requiresResource', 'has전장축선', 'assignedToMission', 'referencesAsset']
    },
    {
        id: 'unit-terrain',
        name: '부대-지형',
        icon: '⛰️',
        description: '부대 위치와 지형 정보',
        nodeTypes: ['아군부대현황', '적군부대현황', '아군가용자산', 'Unit', '지형셀', 'Terrain'],
        relationTypes: ['locatedIn']
    },
    {
        id: 'all-relations',
        name: '전체 보기',
        icon: '🕸️',
        description: '모든 노드와 관계 표시',
        nodeTypes: [], // 빈 배열 = 모든 노드
    }
];

// 관계 유형별 스타일
const RELATION_STYLES: Record<string, { color: string; label: string }> = {
    'has전장축선': { color: '#10b981', label: '축선 배치' },
    'locatedIn': { color: '#06b6d4', label: '위치' },
    'respondsTo': { color: '#ef4444', label: '대응' },
    'hasRelatedCOA': { color: '#3b82f6', label: '관련 방책' },
    'requiresResource': { color: '#f59e0b', label: '필요 자원' },
    'hasConstraint': { color: '#f97316', label: '제약조건' },
    'compatibleWith': { color: '#22c55e', label: '호환' },
    'has지형셀': { color: '#78716c', label: '지형셀' },
    'appliesTo': { color: '#8b5cf6', label: '적용 대상' },
    'assignedToMission': { color: '#84cc16', label: '미션 할당' },
    'hasMission': { color: '#0891b2', label: '수행 임무' },
    'has위협상황': { color: '#dc2626', label: '발생 위협' },
    'has적군부대현황': { color: '#4338ca', label: '적군 부대' },
    'referencesAsset': { color: '#ea580c', label: '자원 참조' },
    'relatedTo': { color: '#64748b', label: '관련 정보' },
    'hasType': { color: '#9d174d', label: '유형' },
    'has임무정보': { color: '#0369a1', label: '임무 정보' },
    '위협유형코드': { color: '#b91c1c', label: '위협 유형' },
    '위협유형': { color: '#b91c1c', label: '위협 유형' },
    '단계정보': { color: '#fbbf24', label: '단계 정보' },
    '설명': { color: '#94a3b8', label: '상세 설명' },
    '적대응전술': { color: '#991b1b', label: '적 대응 전술' },
    '적용조건': { color: '#0ea5e9', label: '적용 조건' },
    '필요자원': { color: '#f59e0b', label: '필요 자원' },
    '환경호환성': { color: '#22c55e', label: '호환 환경' },
    '환경비호환성': { color: '#b91c1c', label: '비호환 환경' },
    '연계방책': { color: '#6366f1', label: '연계 방책' },
    '자원우선순위': { color: '#f59e0b', label: '자원 우선순위' },
    '워게임_모의_분석_승률': { color: '#10b981', label: '모의 승률' },
    '전장환경_최적조건': { color: '#22c55e', label: '최적 환경' },
    '전장환경_제약': { color: '#f97316', label: '환경 제약' },
    '주노력여부': { color: '#ef4444', label: '주노력 여부' },
    '키워드': { color: '#64748b', label: '키워드' },
    '위협수준': { color: '#ef4444', label: '위협 수준' },
    '위협심도': { color: '#7f1d1d', label: '위협 심도' },
    '위협카테고리': { color: '#991b1b', label: '위협 범주' },
    '임무역할': { color: '#0369a1', label: '임무 역할' },
    '고유명칭': { color: '#312e81', label: '고유 명칭' },
    '상급부대': { color: '#1e40af', label: '상급 부대' },
    '병종': { color: '#1e293b', label: '병종' },
    '제대': { color: '#334155', label: '제대' },
    '가용상태': { color: '#22c55e', label: '가용 상태' },
    'incompatibleWith': { color: '#7c2d12', label: '비호환 환경' },
    'isVirtualEntity': { color: '#71717a', label: '가상 엔티티' },
    'virtualEntitySource': { color: '#71717a', label: '가상 소스' },
    '포함됨In': { color: '#06b6d4', label: '하위 포함' },
    '배치된부대': { color: '#10b981', label: '배치 부대' },
    '소속축선': { color: '#78716c', label: '소속 축선' },
    '할당부대': { color: '#0891b2', label: '할당 부대' },
    '인접함': { color: '#d946ef', label: '인접' },
    '협력관계': { color: '#fb7185', label: '협력' },
    '축선연결': { color: '#f43f5e', label: '축선 연결' },
    '작전가능지역': { color: '#a855f7', label: '작전 가능 구역' },
    '위협영향지역': { color: '#ec4899', label: '위협 영향 구역' },
    '임무축선': { color: '#6366f1', label: '임무 축선' },
    '시나리오적군': { color: '#f43f5e', label: '시나리오 적군' },
    'sameAs': { color: '#4a044e', label: '동일 객체' },
    'subPropertyOf': { color: '#312e81', label: '상위 속성' },
    'equivalentClass': { color: '#1e1b4b', label: '동일 클래스' },
    'subClassOf': { color: '#94a3b8', label: '하위 클래스' },
    'domain': { color: '#6366f1', label: '도메인' },
    'range': { color: '#f43f5e', label: '레인지' },
    'default': { color: '#3f3f46', label: '기타 관계' }
};

export default function GraphExplorerPanel() {
    const navigate = useNavigate();
    const [mode, setMode] = useState('instances'); // instances | schema
    const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
    const [filteredData, setFilteredData] = useState<GraphData>({ nodes: [], links: [] });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isFullScreen, setIsFullScreen] = useState(false);

    // State for detailed node info
    const [nodeDetails, setNodeDetails] = useState<any>(null);
    const [detailsLoading, setDetailsLoading] = useState(false);

    // Filters
    const [availableGroups, setAvailableGroups] = useState<string[]>([]);
    const [selectedGroups, setSelectedGroups] = useState<string[]>([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
    const [focusNodeId, setFocusNodeId] = useState<string | null>(null);

    // 시나리오 & 관계 필터
    const [activeScenario, setActiveScenario] = useState<ExploreScenario | null>(null);
    const [selectedRelations, setSelectedRelations] = useState<string[]>([]);
    const [availableRelations, setAvailableRelations] = useState<string[]>([]);
    const [showHelp, setShowHelp] = useState(false);
    const [showModeInfo, setShowModeInfo] = useState(false);

    // D3 Force 최적화: 클러스터 간 거리 조절
    useEffect(() => {
        if (!graphRef.current) return;

        const fg = graphRef.current;

        // 척력 조절: 섬(클러스터) 간 반발력을 줄여 더 잘 모이게 함
        const chargeStrength = mode === 'schema' ? -100 : -150;
        fg.d3Force('charge').strength(chargeStrength);

        // 연결 거리 조절
        const linkDist = mode === 'schema' ? 40 : 50;
        fg.d3Force('link').distance(linkDist);

        // 중심력 강화: 끊어진 조각들을 중앙으로 더 부드럽게 당김
        fg.d3Force('center').strength(0.8);

        // 레이아웃 재가동
        fg.d3ReheatSimulation();
    }, [mode, filteredData]);

    // 시작점 선택 (드롭다운)
    const [selectedCategory, setSelectedCategory] = useState<string>('');
    const [categoryNodes, setCategoryNodes] = useState<GraphNode[]>([]);
    const [selectedStartNode, setSelectedStartNode] = useState<string>('');

    // OWL 추론 포함 옵션
    const [includeInferred, setIncludeInferred] = useState(false);

    const graphRef = useRef<any>();
    const containerRef = useRef<HTMLDivElement>(null);
    const [containerSize, setContainerSize] = useState({ width: 800, height: 600 });

    // 컨테이너 크기 추적 (ResizeObserver)
    useEffect(() => {
        if (!containerRef.current) return;

        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                const { width, height } = entry.contentRect;
                if (width > 0 && height > 0) {
                    setContainerSize({ width, height });
                }
            }
        });

        resizeObserver.observe(containerRef.current);

        return () => resizeObserver.disconnect();
    }, []);

    // Fetch graph data
    useEffect(() => {
        fetchGraphData();
    }, [mode, includeInferred]);

    const fetchGraphData = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.get<GraphData>('/ontology/graph', {
                params: {
                    mode,
                    include_inferred: includeInferred
                }
            });

            // Process data to ensure distinct IDs and basic sanitization
            const nodes = response.data.nodes.map(n => ({
                ...n,
                val: 1 // Default size, can be calculated based on degree later
            }));

            setGraphData({ nodes, links: response.data.links });

            // Extract unique groups
            const groups = Array.from(new Set(nodes.map(n => n.group)));
            setAvailableGroups(groups);

            // Extract unique relation types
            const relations = Array.from(new Set(response.data.links.map(l => l.relation).filter(r => r)));
            setAvailableRelations(relations);
            setSelectedRelations(relations); // 기본: 모든 관계 선택

            // Hide technical/metadata groups by default to provide a cleaner view
            // But show them in Schema mode as that's the point of schema view
            const technicalGroups = ['Axiom', 'Class', 'Property', 'ObjectProperty', 'DatatypeProperty', 'Environment', 'Datatype', 'AnnotationProperty'];
            let initialVisibleGroups;

            if (mode === 'schema') {
                initialVisibleGroups = groups;
            } else {
                initialVisibleGroups = groups.filter(g => !technicalGroups.includes(g));
            }

            setSelectedGroups(initialVisibleGroups);

            // 초기 화면: 연결이 많은 허브 노드만 표시 (Top 30)
            const nodeDegree = new Map<string, number>();
            response.data.links.forEach(l => {
                const sId = typeof l.source === 'string' ? l.source : l.source;
                const tId = typeof l.target === 'string' ? l.target : l.target;
                nodeDegree.set(sId as string, (nodeDegree.get(sId as string) || 0) + 1);
                nodeDegree.set(tId as string, (nodeDegree.get(tId as string) || 0) + 1);
            });

            // 허브 노드 ID 추출 (연결 수 기준 상위 30개)
            const hubNodeIds = Array.from(nodeDegree.entries())
                .sort((a, b) => b[1] - a[1])
                .slice(0, 30)
                .map(([id]) => id);

            // 초기에는 허브 노드의 그룹만 선택
            const hubGroups = new Set(nodes.filter(n => hubNodeIds.includes(n.id)).map(n => n.group));
            const initialHubGroups = Array.from(hubGroups).filter(g => !technicalGroups.includes(g));

            if (initialHubGroups.length > 0) {
                setSelectedGroups(initialHubGroups);
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || '그래프 데이터 로딩 실패');
            console.error('Graph data error:', err);
        } finally {
            setLoading(false);
        }
    };

    // Initialize/Update Simulation Forces
    useEffect(() => {
        if (!graphRef.current) return;

        // Apply stronger repulsion to prevent label overlap
        graphRef.current.d3Force('charge').strength(-300);
        graphRef.current.d3Force('link').distance(80);

        // Re-heat simulation if data changed
        graphRef.current.d3ReheatSimulation();
    }, [filteredData]);

    // Apply filters
    useEffect(() => {
        if (!graphData.nodes.length) return;

        let nodes = [...graphData.nodes];
        let links = [...graphData.links];

        // 1. Filter by Groups
        const validGroupSet = new Set(selectedGroups);
        const validNodeIds = new Set<string>();

        nodes = nodes.filter(n => {
            const isValid = validGroupSet.has(n.group);
            if (isValid) validNodeIds.add(n.id);
            return isValid;
        });

        // 2. Filter by Focus Mode (Explore Connections)
        if (focusNodeId) {
            const connectedIds = new Set<string>();
            connectedIds.add(focusNodeId);

            graphData.links.forEach((l: any) => {
                const sId = typeof l.source === 'object' ? l.source.id : l.source;
                const tId = typeof l.target === 'object' ? l.target.id : l.target;
                if (sId === focusNodeId) connectedIds.add(tId);
                if (tId === focusNodeId) connectedIds.add(sId);
            });

            nodes = nodes.filter(n => connectedIds.has(n.id));

            // Re-calculate valid IDs for links
            validNodeIds.clear();
            nodes.forEach(n => validNodeIds.add(n.id));
        }

        // 3. Filter by Search Term
        if (searchTerm) {
            const lowerTerm = searchTerm.toLowerCase();
            nodes = nodes.filter(n =>
                n.label.toLowerCase().includes(lowerTerm) || n.id.toLowerCase().includes(lowerTerm)
            );

            validNodeIds.clear();
            nodes.forEach(n => validNodeIds.add(n.id));
        }

        // 4. Filter Links by node validity AND relation type
        links = links.filter(l => {
            const sourceId = typeof l.source === 'object' ? (l.source as GraphNode).id : l.source;
            const targetId = typeof l.target === 'object' ? (l.target as GraphNode).id : l.target;
            const isNodeValid = validNodeIds.has(sourceId as string) && validNodeIds.has(targetId as string);

            // 관계 유형 필터 적용
            const isRelationValid = selectedRelations.length === 0 ||
                selectedRelations.includes(l.relation) ||
                selectedRelations.length === availableRelations.length; // 전체 선택 시

            return isNodeValid && isRelationValid;
        });

        setFilteredData({ nodes, links });
    }, [graphData, selectedGroups, searchTerm, focusNodeId, selectedRelations, availableRelations]);

    const handleExploreConnections = useCallback(() => {
        if (!selectedNode) return;

        const nodeToFocus = selectedNode;

        // 모달 닫기
        setSelectedNode(null);

        // 검색어 초기화
        setSearchTerm('');

        // 포커스 모드 활성화 - 해당 노드와 연결된 노드만 표시
        setFocusNodeId(nodeToFocus.id);

        // 해당 노드가 속한 그룹이 선택되어 있는지 확인하고 추가
        if (!selectedGroups.includes(nodeToFocus.group)) {
            setSelectedGroups([...selectedGroups, nodeToFocus.group]);
        }

        // 카메라 이동 및 줌
        if (graphRef.current) {
            setTimeout(() => {
                const x = nodeToFocus.x || 0;
                const y = nodeToFocus.y || 0;
                graphRef.current.centerAt(x, y, 800);
                graphRef.current.zoom(1.5, 800);
            }, 100);
        }
    }, [selectedNode, selectedGroups]);

    const handleNavigateToStudio = useCallback(() => {
        if (selectedNode) {
            // Encode the ID properly
            navigate(`/ontology-studio?nodeId=${encodeURIComponent(selectedNode.id)}`);
        } else {
            navigate('/ontology-studio');
        }
    }, [selectedNode, navigate]);

    const toggleGroup = (group: string) => {
        if (selectedGroups.includes(group)) {
            setSelectedGroups(selectedGroups.filter(g => g !== group));
        } else {
            setSelectedGroups([...selectedGroups, group]);
        }
    };

    // 시나리오 활성화
    const activateScenario = useCallback((scenario: ExploreScenario) => {
        setActiveScenario(scenario);
        setFocusNodeId(null);
        setSearchTerm('');
        setSelectedStartNode('');

        if (scenario.nodeTypes.length === 0) {
            // 전체 보기
            const nonTechnicalGroups = availableGroups.filter(g => !TECHNICAL_GROUPS.includes(g));
            setSelectedGroups(nonTechnicalGroups);
            setSelectedRelations(availableRelations);
        } else {
            // 특정 시나리오
            setSelectedGroups(scenario.nodeTypes);
            if (scenario.relationTypes) {
                setSelectedRelations(scenario.relationTypes);
            } else {
                setSelectedRelations(availableRelations);
            }
        }

        // 그래프 리셋
        if (graphRef.current) {
            graphRef.current.zoomToFit(400, 50);
        }
    }, [availableGroups, availableRelations]);

    // 관계 유형 토글
    const toggleRelation = (relation: string) => {
        if (selectedRelations.includes(relation)) {
            setSelectedRelations(selectedRelations.filter(r => r !== relation));
        } else {
            setSelectedRelations([...selectedRelations, relation]);
        }
    };

    // 카테고리 변경 시 해당 노드 목록 업데이트
    useEffect(() => {
        if (selectedCategory && graphData.nodes.length > 0) {
            const nodesInCategory = graphData.nodes.filter(n => n.group === selectedCategory);
            setCategoryNodes(nodesInCategory);
            setSelectedStartNode('');
        } else {
            setCategoryNodes([]);
        }
    }, [selectedCategory, graphData.nodes]);

    // 시작점 선택 시 자동 포커스
    const handleStartNodeSelect = useCallback((nodeId: string) => {
        setSelectedStartNode(nodeId);
        if (nodeId) {
            setFocusNodeId(nodeId);
            const node = graphData.nodes.find(n => n.id === nodeId);
            if (node && graphRef.current) {
                setTimeout(() => {
                    graphRef.current.centerAt(node.x || 0, node.y || 0, 1000);
                    graphRef.current.zoom(2.5, 1000);
                }, 100);
            }
        }
    }, [graphData.nodes]);

    // 검색 시 자동 포커스 (Enter 키)
    const handleSearchKeyDown = useCallback((e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && searchTerm) {
            const matchingNode = graphData.nodes.find(n =>
                n.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
                n.id.toLowerCase().includes(searchTerm.toLowerCase())
            );
            if (matchingNode) {
                setFocusNodeId(matchingNode.id);
                setSelectedNode(matchingNode);
                if (graphRef.current) {
                    graphRef.current.centerAt(matchingNode.x || 0, matchingNode.y || 0, 1000);
                    graphRef.current.zoom(2.5, 1000);
                }
            }
        }
    }, [searchTerm, graphData.nodes]);

    const handleNodeClick = useCallback(async (node: any) => {
        setSelectedNode(node);
        setNodeDetails(null);
        setDetailsLoading(true);

        // Focus camera on node - 부드럽게 이동만 (줌 유지)
        if (graphRef.current) {
            graphRef.current.centerAt(node.x, node.y, 500);
        }

        try {
            const response = await api.get(`/ontology/node/${encodeURIComponent(node.id)}`);
            setNodeDetails(response.data);
        } catch (err) {
            console.error("Failed to fetch node details", err);
        } finally {
            setDetailsLoading(false);
        }
    }, []);

    const toggleFullScreen = () => {
        setIsFullScreen(!isFullScreen);
    };

    // Custom Node Rendering
    const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const style = NODE_STYLES[node.group] || NODE_STYLES['Unknown'];
        const label = node.label;
        const fontSize = 12 / globalScale; // Scaled font size

        // 1. Draw Outer Circle (Background)
        const r = 5;
        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
        ctx.fillStyle = style.color;
        ctx.fill();

        // 2. Draw Icon (Emoji)
        const iconSize = r * 1.2;
        ctx.font = `${iconSize}px Sans-Serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = style.iconColor;
        ctx.fillText(style.icon, node.x, node.y + (iconSize * 0.1)); // visual adjustment

        // 3. Draw Label (Show when zoomed in or hovered)
        if (globalScale > 0.8) {
            // Invert the scaling logic: We want text to be roughly constant size on SCREEN 
            // but grow slightly and become more detailed as we zoom in.
            const baseFontSize = 14;
            const fontSize = baseFontSize / Math.pow(globalScale, 0.8);
            ctx.font = `${fontSize}px Sans-Serif`;

            // Maximum width in canvas units - should stay generous as we zoom in
            const maxWidth = 120 / Math.pow(globalScale, 0.8);

            const words = label.split(/(\s+|_|-)/);
            let lines: string[] = [];
            let currentLine = "";

            words.forEach(word => {
                const testLine = currentLine + word;
                if (ctx.measureText(testLine).width > maxWidth && currentLine !== "") {
                    lines.push(currentLine);
                    currentLine = word;
                } else {
                    currentLine = testLine;
                }
            });
            lines.push(currentLine);

            const displayLines = lines.slice(0, 3);
            if (lines.length > 3) {
                displayLines[2] = displayLines[2].substring(0, Math.max(0, displayLines[2].length - 3)) + "...";
            }

            const lineHeight = fontSize * 1.2;
            const blockHeight = displayLines.length * lineHeight;
            const blockWidth = Math.max(...displayLines.map(l => ctx.measureText(l).width));

            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';

            // Draw Single Background Card for the whole block
            const pad = 4 / globalScale;
            ctx.fillStyle = 'rgba(9, 9, 11, 0.85)'; // zinc-950 equivalent
            ctx.strokeStyle = 'rgba(63, 63, 70, 0.5)'; // zinc-700 equivalent
            ctx.lineWidth = 1 / globalScale;

            const rectX = node.x - blockWidth / 2 - pad;
            const rectY = node.y + r + 4;
            const rectW = blockWidth + pad * 2;
            const rectH = blockHeight + pad * 2;

            // Rounded rectangle
            const radius = 2 / globalScale;
            ctx.beginPath();
            ctx.moveTo(rectX + radius, rectY);
            ctx.lineTo(rectX + rectW - radius, rectY);
            ctx.quadraticCurveTo(rectX + rectW, rectY, rectX + rectW, rectY + radius);
            ctx.lineTo(rectX + rectW, rectY + rectH - radius);
            ctx.quadraticCurveTo(rectX + rectW, rectY + rectH, rectX + rectW - radius, rectY + rectH);
            ctx.lineTo(rectX + radius, rectY + rectH);
            ctx.quadraticCurveTo(rectX, rectY + rectH, rectX, rectY + rectH - radius);
            ctx.lineTo(rectX, rectY + radius);
            ctx.quadraticCurveTo(rectX, rectY, rectX + radius, rectY);
            ctx.closePath();
            ctx.fill();
            ctx.stroke();

            // Draw Text
            ctx.fillStyle = '#fff';
            displayLines.forEach((line, i) => {
                ctx.fillText(line, node.x, rectY + pad + (i * lineHeight));
            });
        }
    }, []);

    return (
        <div className={`flex flex-col h-full ${isFullScreen ? 'fixed inset-0 z-50 bg-zinc-950 p-4' : ''}`}>

            {/* 상단 컨트롤 영역 - 스크롤 없이 고정 */}
            <div className="shrink-0 space-y-3 mb-3">

                {/* 시나리오 기반 빠른 탐색 */}
                <div className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 p-4 rounded-xl border border-blue-800/30">
                    <div className="flex items-center gap-3 mb-3">
                        <span className="text-sm font-semibold text-zinc-300">🎯 빠른 탐색</span>
                        <span className="text-xs text-zinc-500">시나리오를 선택하여 관련 노드만 탐색하세요</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {EXPLORE_SCENARIOS.map((scenario) => (
                            <button
                                key={scenario.id}
                                onClick={() => activateScenario(scenario)}
                                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeScenario?.id === scenario.id
                                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/25'
                                    : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700 border border-zinc-700'
                                    }`}
                                title={scenario.description}
                            >
                                <span>{scenario.icon}</span>
                                <span>{scenario.name}</span>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Header / Controls */}
                <div className={`bg-zinc-900 p-4 rounded-xl border border-zinc-800 shadow-sm ${isFullScreen ? 'mb-4' : ''}`}>
                    <div className="flex flex-col md:flex-row gap-4 items-end md:items-center justify-between">

                        {/* Left: Mode & Search */}
                        <div className="flex flex-1 gap-4 w-full md:w-auto">
                            <div className="w-36 relative">
                                <div className="flex items-center gap-1.5 mb-1">
                                    <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider block">모드 (Mode)</label>
                                    <button
                                        onClick={() => setShowModeInfo(!showModeInfo)}
                                        className="text-zinc-500 hover:text-blue-400 transition-colors"
                                        title="개념 설명 보기"
                                    >
                                        <HelpCircle className="w-3 h-3" />
                                    </button>
                                </div>
                                <select
                                    value={mode}
                                    onChange={(e) => setMode(e.target.value)}
                                    className="w-full bg-zinc-800 text-zinc-200 text-sm border border-zinc-700 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500/50 outline-none transition-all"
                                >
                                    <option value="instances">인스턴스 (Data)</option>
                                    <option value="schema">스키마 (Structure)</option>
                                </select>

                                {/* 모드 개념 설명 팝오버 */}
                                {showModeInfo && (
                                    <div className="absolute top-14 left-0 w-64 z-50 bg-zinc-900 border border-zinc-700 rounded-xl p-3 shadow-2xl animate-in fade-in slide-in-from-top-2 duration-200">
                                        <div className="text-blue-400 text-xs font-bold mb-1 flex items-center gap-1">
                                            <Brain className="w-3 h-3" />
                                            {MODE_DESCRIPTIONS[mode as keyof typeof MODE_DESCRIPTIONS].title}
                                        </div>
                                        <div className="text-zinc-200 text-[11px] font-medium mb-1">
                                            {MODE_DESCRIPTIONS[mode as keyof typeof MODE_DESCRIPTIONS].desc}
                                        </div>
                                        <div className="text-zinc-400 text-[10px] leading-relaxed border-t border-zinc-800 pt-1.5 mt-1.5">
                                            {MODE_DESCRIPTIONS[mode as keyof typeof MODE_DESCRIPTIONS].detail}
                                        </div>
                                        <button
                                            onClick={() => setShowModeInfo(false)}
                                            className="w-full mt-2 py-1 text-[10px] text-zinc-500 hover:text-zinc-300 bg-zinc-800 hover:bg-zinc-750 rounded transition-colors"
                                        >
                                            닫기
                                        </button>
                                    </div>
                                )}
                            </div>

                            {/* OWL 추론 포함 옵션 */}
                            <div className="flex items-end pb-0.5">
                                <label className="flex items-center gap-2 px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg hover:bg-zinc-750 cursor-pointer transition-colors group">
                                    <input
                                        type="checkbox"
                                        checked={includeInferred}
                                        onChange={(e) => setIncludeInferred(e.target.checked)}
                                        className="w-4 h-4 rounded border-zinc-600 bg-zinc-800 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-zinc-900"
                                    />
                                    <div className="flex items-center gap-1.5">
                                        <Brain className={`w-3.5 h-3.5 ${includeInferred ? 'text-indigo-400' : 'text-zinc-500 group-hover:text-zinc-400'}`} />
                                        <span className={`text-xs font-medium ${includeInferred ? 'text-indigo-300' : 'text-zinc-500 group-hover:text-zinc-400'}`}>
                                            OWL 추론 포함
                                        </span>
                                    </div>
                                </label>
                            </div>

                            {/* 시작점 선택 드롭다운 */}
                            <div className="w-36">
                                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1 block">카테고리</label>
                                <select
                                    value={selectedCategory}
                                    onChange={(e) => setSelectedCategory(e.target.value)}
                                    className="w-full bg-zinc-800 text-zinc-200 text-sm border border-zinc-700 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500/50 outline-none transition-all"
                                >
                                    <option value="">선택...</option>
                                    {availableGroups.filter(g => mode === 'schema' ? true : !TECHNICAL_GROUPS.includes(g)).map(group => (
                                        <option key={group} value={group}>{NODE_STYLES[group]?.label || group}</option>
                                    ))}
                                </select>
                            </div>

                            {selectedCategory && categoryNodes.length > 0 && (
                                <div className="w-48">
                                    <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1 block">시작점</label>
                                    <select
                                        value={selectedStartNode}
                                        onChange={(e) => handleStartNodeSelect(e.target.value)}
                                        className="w-full bg-zinc-800 text-zinc-200 text-sm border border-zinc-700 rounded-lg px-3 py-2 focus:ring-2 focus:ring-green-500/50 outline-none transition-all"
                                    >
                                        <option value="">노드 선택...</option>
                                        {categoryNodes.slice(0, 50).map(node => (
                                            <option key={node.id} value={node.id}>{node.label}</option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            <div className="flex-1 relative">
                                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1 block">검색 (Enter로 포커스)</label>
                                <Search className="absolute left-3 top-8 w-4 h-4 text-zinc-500" />
                                <input
                                    type="text"
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    onKeyDown={handleSearchKeyDown}
                                    placeholder="노드 검색 후 Enter..."
                                    className="w-full pl-9 pr-4 py-2 bg-zinc-800 text-zinc-200 text-sm border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500/50 outline-none transition-all"
                                />
                            </div>
                            {focusNodeId && (
                                <div className="self-end pb-0.5">
                                    <div className="flex items-center gap-2 bg-blue-500/10 border border-blue-500/30 px-3 py-2 rounded-lg animate-in fade-in slide-in-from-left-2">
                                        <span className="text-xs text-blue-400 font-medium flex items-center gap-1">
                                            <Shield className="w-3 h-3" />
                                            포커스
                                        </span>
                                        <button
                                            onClick={() => setFocusNodeId(null)}
                                            className="p-1 hover:bg-blue-500/20 rounded-md transition-colors"
                                            title="전체 그래프 보기"
                                        >
                                            <Minimize2 className="w-3 h-3 text-blue-400" />
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Right: Legend & Actions */}
                        <div className="flex items-center gap-3">
                            <div className="flex items-center gap-2 mr-4 bg-zinc-800/50 p-2 rounded-lg border border-zinc-800/50">
                                {/* Mini Legend (Summary) */}
                                {Object.entries(NODE_STYLES).slice(0, 8).map(([key, style]) => (
                                    <div key={key} className="flex items-center gap-1" title={style.label}>
                                        <span style={{ color: style.color }} className="text-sm">{style.icon}</span>
                                    </div>
                                ))}
                                <span className="text-[10px] text-zinc-500 cursor-default" title="Filter tags below show full list">Legend</span>
                            </div>

                            <button
                                onClick={toggleFullScreen}
                                className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white transition-colors"
                                title={isFullScreen ? "Exit Full Screen" : "Full Screen"}
                            >
                                {isFullScreen ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
                            </button>
                        </div>
                    </div>

                    {/* Filter Tags (Legend Interactivity) */}
                    <div className="mt-4 flex flex-wrap gap-2 pt-3 border-t border-zinc-800/50">
                        <span className="text-xs text-zinc-500 mr-2 self-center">노드:</span>
                        {availableGroups.filter(g => mode === 'schema' ? true : !TECHNICAL_GROUPS.includes(g)).map(group => {
                            const style = NODE_STYLES[group] || NODE_STYLES['Unknown'];
                            const isSelected = selectedGroups.includes(group);
                            return (
                                <button
                                    key={group}
                                    onClick={() => toggleGroup(group)}
                                    className={`
                                    flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all
                                    ${isSelected
                                            ? `bg-zinc-800 border-zinc-700 text-zinc-200 hover:bg-zinc-700`
                                            : `bg-transparent border-zinc-800 text-zinc-600 hover:text-zinc-400 opacity-60`}
                                `}
                                >
                                    <span style={{ color: isSelected ? style.color : undefined }}>{style.icon}</span>
                                    {NODE_STYLES[group]?.label || group}
                                </button>
                            );
                        })}
                    </div>

                    {/* 관계 유형 필터 */}
                    {availableRelations.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2 pt-3 border-t border-zinc-800/50">
                            <span className="text-xs text-zinc-500 mr-2 self-center">관계:</span>
                            {availableRelations.slice(0, 15).map(relation => {
                                const style = RELATION_STYLES[relation] || RELATION_STYLES['default'];
                                const isSelected = selectedRelations.includes(relation);
                                return (
                                    <button
                                        key={relation}
                                        onClick={() => toggleRelation(relation)}
                                        className={`
                                        flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all
                                        ${isSelected
                                                ? `bg-zinc-800 border-zinc-700 text-zinc-200 hover:bg-zinc-700`
                                                : `bg-transparent border-zinc-800 text-zinc-600 hover:text-zinc-400 opacity-60`}
                                    `}
                                        style={{ borderColor: isSelected ? style.color : undefined }}
                                    >
                                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: isSelected ? style.color : '#52525b' }} />
                                        {style.label || relation}
                                    </button>
                                );
                            })}
                        </div>
                    )}
                </div>

            </div>{/* 상단 컨트롤 영역 끝 */}

            {/* Main Content Area - 남은 공간 모두 사용 */}
            <div className="flex-1 flex gap-4 relative" style={{ minHeight: '500px' }}>
                {/* Graph Canvas - 항상 전체 너비 사용 */}
                <div
                    ref={containerRef}
                    className="rounded-xl border border-zinc-800 bg-zinc-950 relative w-full"
                    style={{ minWidth: 0, height: '100%' }}
                >
                    {loading && (
                        <div className="absolute inset-0 z-10 flex items-center justify-center bg-zinc-950/80 backdrop-blur-sm">
                            <div className="flex flex-col items-center gap-3">
                                <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
                                <span className="text-sm text-zinc-400 animate-pulse">Loading Graph Data...</span>
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="absolute inset-0 z-10 flex items-center justify-center bg-zinc-950/90">
                            <div className="text-red-400 bg-red-950/30 px-6 py-4 rounded-xl border border-red-900/50 max-w-md text-center">
                                <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-80" />
                                <p className="font-medium">Failed to load graph</p>
                                <p className="text-sm mt-1 opacity-80">{error}</p>
                            </div>
                        </div>
                    )}

                    <ForceGraph2D
                        ref={graphRef}
                        width={containerSize.width}
                        height={containerSize.height}
                        graphData={filteredData}
                        nodeLabel="label"
                        nodeColor={node => (NODE_STYLES[node.group] || NODE_STYLES['Unknown']).color}
                        nodeCanvasObject={nodeCanvasObject}
                        linkDirectionalParticles={filteredData.links.length < 500 ? 2 : 0} // Optimize for large graphs
                        linkDirectionalParticleWidth={2}
                        linkColor={(link: any) => {
                            const style = RELATION_STYLES[link.relation] || RELATION_STYLES['default'];
                            return style.color;
                        }}
                        linkWidth={(link: any) => {
                            // 주요 관계는 더 두껍게
                            const importantRelations = ['has전장축선', 'locatedIn', 'respondsTo'];
                            return importantRelations.includes(link.relation) ? 2 : 1;
                        }}
                        linkLabel={(link: any) => {
                            const style = RELATION_STYLES[link.relation] || RELATION_STYLES['default'];
                            return style.label || link.relation;
                        }}
                        backgroundColor="#09090b" // zinc-950
                        onNodeClick={handleNodeClick}
                        cooldownTicks={100}
                        d3AlphaDecay={0.02}
                        d3VelocityDecay={0.3}
                        onEngineStop={() => {
                            // 시뮬레이션 종료 시점에 최종 위치 조정 (필요 시)
                        }}
                    />

                    {/* 도움말 아이콘 (Schema 모드 전용) */}
                    {mode === 'schema' && (
                        <div className="absolute top-4 right-4 flex flex-col items-end gap-2">
                            <button
                                onClick={() => setShowHelp(!showHelp)}
                                className={`p-2 rounded-full transition-all duration-300 ${showHelp ? 'bg-blue-600 text-white shadow-lg' : 'bg-zinc-900/80 text-zinc-400 hover:text-zinc-200 border border-zinc-700'
                                    }`}
                                title="온톨로지 용어 안내"
                            >
                                <HelpCircle className="w-5 h-5" />
                            </button>

                            {showHelp && (
                                <div className="w-64 bg-zinc-900/95 backdrop-blur border border-zinc-700 rounded-xl p-4 shadow-2xl animate-in fade-in slide-in-from-top-2 duration-300 text-xs text-zinc-300 space-y-4">
                                    <div className="flex items-center gap-2 border-b border-zinc-800 pb-2 mb-2 text-zinc-100 font-semibold">
                                        <Brain className="w-4 h-4 text-blue-400" />
                                        <span>Schema 가이드</span>
                                    </div>
                                    <div>
                                        <div className="text-blue-400 font-medium mb-1">하위 클래스 (subClassOf)</div>
                                        <p className="leading-relaxed opacity-80">{SCHEMA_TERM_HELP.subClassOf}</p>
                                    </div>
                                    <div>
                                        <div className="text-indigo-400 font-medium mb-1">도메인 (domain)</div>
                                        <p className="leading-relaxed opacity-80">{SCHEMA_TERM_HELP.domain}</p>
                                    </div>
                                    <div>
                                        <div className="text-rose-400 font-medium mb-1">레인지 (range)</div>
                                        <p className="leading-relaxed opacity-80">{SCHEMA_TERM_HELP.range}</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Overlay Stats */}
                    <div className="absolute bottom-4 right-4 bg-zinc-900/80 backdrop-blur border border-zinc-800 px-3 py-1.5 rounded-lg text-xs text-zinc-500">
                        {activeScenario && (
                            <>
                                <span className="text-blue-400 font-medium">{activeScenario.icon} {activeScenario.name}</span>
                                <span className="mx-2">·</span>
                            </>
                        )}
                        <span className="text-zinc-300 font-mono">{filteredData.nodes.length}</span> nodes
                        <span className="mx-2">·</span>
                        <span className="text-zinc-300 font-mono">{filteredData.links.length}</span> edges
                    </div>

                    {/* 관계 범례 (활성 시나리오가 있을 때) */}
                    {activeScenario && activeScenario.relationTypes && (
                        <div className="absolute bottom-4 left-4 bg-zinc-900/80 backdrop-blur border border-zinc-800 px-3 py-2 rounded-lg">
                            <div className="text-xs text-zinc-500 mb-1">관계 범례</div>
                            <div className="flex flex-col gap-1">
                                {activeScenario.relationTypes.map(rel => {
                                    const style = RELATION_STYLES[rel] || RELATION_STYLES['default'];
                                    return (
                                        <div key={rel} className="flex items-center gap-2 text-xs">
                                            <div className="w-4 h-0.5 rounded" style={{ backgroundColor: style.color }} />
                                            <span className="text-zinc-300">{style.label}</span>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>


                {/* Node Details Modal - 노드 선택 시 팝업으로 표시 */}
                {selectedNode && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => setSelectedNode(null)}>
                        {/* 배경 오버레이 */}
                        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm"></div>

                        {/* 모달 내용 */}
                        <div
                            className="relative w-96 max-h-[80vh] bg-zinc-900 border border-zinc-700 rounded-2xl flex flex-col shadow-2xl overflow-hidden"
                            onClick={(e) => e.stopPropagation()}
                        >
                            {/* Header */}
                            <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-gradient-to-r from-blue-900/30 to-purple-900/30 shrink-0">
                                <h3 className="font-semibold text-zinc-200 flex items-center gap-2">
                                    <Search className="w-4 h-4 text-blue-500" />
                                    엔티티 정보
                                </h3>
                                <button
                                    onClick={() => setSelectedNode(null)}
                                    className="p-1 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white transition-colors"
                                    title="닫기"
                                >
                                    <Minimize2 className="w-5 h-5" />
                                </button>
                            </div>

                            {/* Scrollable Content */}
                            <div className="flex-1 overflow-y-auto p-4 space-y-6">
                                {selectedNode && (
                                    <>
                                        {/* Header Info */}
                                        <div className="flex items-start gap-3">
                                            <div
                                                className="w-12 h-12 rounded-lg flex items-center justify-center text-2xl shadow-inner bg-zinc-950 border border-zinc-800 shrink-0"
                                                style={{ borderColor: (NODE_STYLES[selectedNode.group] || NODE_STYLES['Unknown']).color }}
                                            >
                                                {(NODE_STYLES[selectedNode.group] || NODE_STYLES['Unknown']).icon}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <h4 className="font-bold text-lg text-zinc-100 leading-tight break-words">{selectedNode.label}</h4>
                                                <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full mt-1 bg-zinc-800 text-zinc-400 border border-zinc-700">
                                                    {(NODE_STYLES[selectedNode.group] || NODE_STYLES['Unknown']).label}
                                                </span>
                                            </div>
                                        </div>

                                        {/* Properties Grid */}
                                        <div className="space-y-3">
                                            <h5 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">세부 속성 (Properties)</h5>
                                            <div className="grid grid-cols-1 gap-2 text-sm">
                                                <div className="bg-zinc-950/50 p-2 rounded border border-zinc-800/50 flex flex-col">
                                                    <span className="text-[10px] text-zinc-500">ID</span>
                                                    <span className="text-zinc-300 font-mono text-xs break-all">{selectedNode.id}</span>
                                                </div>

                                                <div className="bg-zinc-950/50 p-2 rounded border border-zinc-800/50 flex justify-between">
                                                    <span className="text-zinc-500 text-xs text-[10px] uppercase">연결 수</span>
                                                    <span className="text-zinc-300">
                                                        {filteredData.links.filter(l =>
                                                            (typeof l.source === 'object' ? l.source.id : l.source) === selectedNode.id ||
                                                            (typeof l.target === 'object' ? l.target.id : l.target) === selectedNode.id
                                                        ).length}
                                                    </span>
                                                </div>

                                                {detailsLoading ? (
                                                    <div className="py-4 flex flex-col items-center gap-2">
                                                        <div className="w-4 h-4 border-2 border-zinc-700 border-t-blue-500 rounded-full animate-spin" />
                                                        <span className="text-[10px] text-zinc-600">속성 로드 중...</span>
                                                    </div>
                                                ) : nodeDetails?.properties ? (
                                                    nodeDetails.properties
                                                        .filter((p: any) => !['label', 'type', 'isVirtualEntity', 'virtualEntitySource'].includes(p.predicate_label))
                                                        .map((prop: any, i: number) => (
                                                            <div key={i} className="bg-zinc-900/30 p-2 rounded border border-zinc-800/30 flex flex-col">
                                                                <span className="text-[10px] text-zinc-500 mb-0.5">{prop.predicate_label}</span>
                                                                <span className={`text-zinc-300 break-words ${prop.is_uri ? 'text-blue-400/80 cursor-help' : ''}`} title={prop.predicate}>
                                                                    {prop.value}
                                                                </span>
                                                            </div>
                                                        ))
                                                ) : null}
                                            </div>
                                        </div>
                                    </>
                                )}
                            </div>

                            {/* Footer Actions (Fixed) */}
                            <div className="p-4 border-t border-zinc-800 bg-zinc-900 shrink-0 space-y-2">
                                <button
                                    onClick={handleExploreConnections}
                                    className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-bold transition-all shadow-lg shadow-blue-900/20 flex items-center justify-center gap-2"
                                >
                                    <Search className="w-4 h-4" />
                                    연결망 탐색 (Focus)
                                </button>
                                <button
                                    onClick={handleNavigateToStudio}
                                    className="w-full py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg text-sm font-medium transition-colors border border-zinc-700 flex items-center justify-center gap-2"
                                >
                                    <Maximize2 className="w-4 h-4" />
                                    스튜디오에서 편집
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
