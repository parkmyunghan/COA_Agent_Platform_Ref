import React, { createContext, useContext, useState, useEffect, useRef, useCallback, useMemo, ReactNode } from 'react';
import api from '../lib/api';
import type {
    MissionBase,
    ThreatEventBase,
    SystemHealthResponse,
    MissionListResponse,
    ThreatListResponse,
    FriendlyUnitListResponse,
    FriendlyUnit,
    AxisListResponse,
    AxisItem,
    TerrainCellListResponse,
    TerrainCellItem
} from '../types/schema';

interface SystemDataContextType {
    missions: MissionBase[];
    threats: ThreatEventBase[];
    friendlyUnits: FriendlyUnit[];
    axes: AxisItem[];
    terrainCells: TerrainCellItem[];
    health: SystemHealthResponse | null;
    loading: boolean;
    error: string | null;
    refetch: (silent?: boolean) => Promise<void>;
}

const SystemDataContext = createContext<SystemDataContextType | undefined>(undefined);

export const SystemDataProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [missions, setMissions] = useState<MissionBase[]>([]);
    const [threats, setThreats] = useState<ThreatEventBase[]>([]);
    const [friendlyUnits, setFriendlyUnits] = useState<FriendlyUnit[]>([]);
    const [axes, setAxes] = useState<AxisItem[]>([]);
    const [terrainCells, setTerrainCells] = useState<TerrainCellItem[]>([]);
    const [health, setHealth] = useState<SystemHealthResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // React StrictMode 이중 렌더링 방지
    const hasFetchedRef = useRef(false);
    const isFetchingRef = useRef(false);

    // 이전 health 값을 추적하여 실제 변경 시에만 업데이트
    const prevHealthRef = useRef<SystemHealthResponse | null>(null);

    // fetchData를 useCallback으로 메모이제이션하여 refetch가 안정적으로 유지되도록 함
    const fetchData = useCallback(async (silent: boolean = false) => {
        // 이미 요청 중이면 중복 요청 방지
        if (isFetchingRef.current) {
            return;
        }

        try {
            isFetchingRef.current = true;
            // silent 모드가 아니거나 초기 로딩이면 loading 상태 변경
            if (!silent || !hasFetchedRef.current) {
                setLoading(true);
            }

            const [missionsRes, threatsRes, healthRes, friendlyUnitsRes, axesRes, terrainCellsRes] = await Promise.all([
                api.get<MissionListResponse>('/data/missions'),
                api.get<ThreatListResponse>('/data/threats'),
                api.get<SystemHealthResponse>('/system/health'),
                api.get<FriendlyUnitListResponse>('/data/units/friendly'),
                api.get<AxisListResponse>('/data/axes'),
                api.get<TerrainCellListResponse>('/data/terrain')
            ]);

            // missions와 threats가 실제로 변경되었는지 확인 (간단한 길이와 ID 비교)
            setMissions((prevMissions) => {
                const newMissions = missionsRes.data.missions;
                if (prevMissions.length !== newMissions.length) {
                    return newMissions;
                }
                const changed = prevMissions.some((m, i) => m.mission_id !== newMissions[i]?.mission_id);
                return changed ? newMissions : prevMissions;
            });

            setThreats((prevThreats) => {
                const newThreats = threatsRes.data.threats;
                if (prevThreats.length !== newThreats.length) {
                    return newThreats;
                }
                const changed = prevThreats.some((t, i) => t.threat_id !== newThreats[i]?.threat_id);
                return changed ? newThreats : prevThreats;
            });

            // 아군 부대 및 축선 업데이트 (단순 교체)
            if (friendlyUnitsRes.data && friendlyUnitsRes.data.units) {
                setFriendlyUnits(friendlyUnitsRes.data.units);
            }
            if (axesRes.data && axesRes.data.axes) {
                setAxes(axesRes.data.axes);
            }
            if (terrainCellsRes.data && terrainCellsRes.data.cells) {
                setTerrainCells(terrainCellsRes.data.cells);
            }

            // health가 실제로 변경되었는지 확인하여 불필요한 상태 업데이트 방지
            const newHealth = healthRes.data;
            const prevHealth = prevHealthRef.current;
            const healthChanged = !prevHealth ||
                prevHealth.status !== newHealth.status ||
                (prevHealth as any).version !== (newHealth as any).version;

            if (healthChanged) {
                setHealth(newHealth);
                prevHealthRef.current = newHealth;
            }

            setError(null);
            hasFetchedRef.current = true;
        } catch (err: any) {
            setError('데이터를 불러오는데 실패했습니다.');
            console.error(err);
        } finally {
            if (!silent || !hasFetchedRef.current) {
                setLoading(false);
            }
            isFetchingRef.current = false;
        }
    }, []); // 의존성 배열이 비어있어서 한 번만 생성됨

    useEffect(() => {
        // React StrictMode 이중 렌더링 방지: 이미 요청했으면 스킵
        if (!hasFetchedRef.current && !isFetchingRef.current) {
            fetchData();
        }
    }, []);

    // value 객체를 useMemo로 메모이제이션하여 불필요한 리렌더링 방지
    // fetchData는 useCallback으로 메모이제이션되어 있어 안정적 (의존성 배열이 비어있음)
    // health 객체의 실제 내용이 변경되었는지 확인하여 불필요한 재생성 방지
    // healthKey를 사용하여 health 객체의 내용이 실제로 변경된 경우에만 value 재생성
    const healthKey = health ? `${health.status}-${(health as any).version || ''}` : 'null';

    const value: SystemDataContextType = useMemo(() => ({
        missions,
        threats,
        friendlyUnits,
        axes,
        terrainCells,
        health, // health 상태 직접 사용 (fetchData에서 이미 변경 감지하여 업데이트)
        loading,
        error,
        refetch: fetchData // fetchData는 useCallback으로 안정적이므로 직접 사용
    }), [missions, threats, friendlyUnits, axes, terrainCells, healthKey, loading, error, fetchData]); // health 대신 healthKey 사용

    return (
        <SystemDataContext.Provider value={value}>
            {children}
        </SystemDataContext.Provider>
    );
};

export const useSystemData = (): SystemDataContextType => {
    const context = useContext(SystemDataContext);
    if (context === undefined) {
        throw new Error('useSystemData must be used within a SystemDataProvider');
    }
    return context;
};
