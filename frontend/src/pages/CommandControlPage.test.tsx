
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import CommandControlPage from './CommandControlPage'
import * as SystemDataHook from '../hooks/useSystemData'

// Mock styles
vi.mock('../components/Layout', () => ({
    Layout: ({ children }: any) => <div data-testid="layout">{children}</div>
}))

// Mock child components
vi.mock('../components/TacticalMap', () => ({
    TacticalMap: () => <div data-testid="tactical-map">Map</div>
}))
vi.mock('../components/COAGenerator', () => ({
    COAGenerator: () => <div data-testid="coa-generator">COAGenerator</div>
}))
vi.mock('../components/ChatInterface', () => ({
    default: () => <div data-testid="chat-interface">Chat</div>
}))
vi.mock('../components/SettingsPanel', () => ({
    SettingsPanel: () => <div data-testid="settings-panel">Settings</div>
}))
vi.mock('../components/AgentSelector', () => ({
    AgentSelector: () => <div data-testid="agent-selector">AgentSelector</div>
}))
vi.mock('../components/SituationInputPanel', () => ({
    SituationInputPanel: () => <div data-testid="situation-input">SituationInput</div>
}))
vi.mock('../components/SituationSummaryPanel', () => ({
    SituationSummaryPanel: () => <div data-testid="situation-summary">SituationSummary</div>
}))
vi.mock('../components/AxisSummaryPanel', () => ({
    AxisSummaryPanel: () => <div data-testid="axis-summary">AxisSummary</div>
}))
vi.mock('../components/COAFloatingCards', () => ({
    COAFloatingCards: () => <div data-testid="coa-floating-cards">FloatingCards</div>
}))
vi.mock('../components/COAComparisonPanel', () => ({
    COAComparisonPanel: () => <div data-testid="coa-comparison">Comparison</div>
}))

// Mock fetch for KPI
global.fetch = vi.fn(() =>
    Promise.resolve({
        json: () => Promise.resolve({ kpi_data: 'some data' }),
        ok: true
    })
) as unknown as typeof fetch

describe('CommandControlPage', () => {
    const mockSystemData = {
        missions: [
            { mission_id: 'M001', name: 'Test Mission' }
        ],
        threats: [
            { threat_id: 'T001', threat_level: 'HIGH' }
        ],
        health: { status: 'ok' },
        loading: false,
        error: null,
        refetch: vi.fn(),
        friendlyUnits: [],
        axes: []
    }

    beforeEach(() => {
        vi.clearAllMocks()
        vi.spyOn(SystemDataHook, 'useSystemData').mockReturnValue(mockSystemData as any)
    })

    it('renders loading state', () => {
        vi.spyOn(SystemDataHook, 'useSystemData').mockReturnValue({
            ...mockSystemData,
            loading: true
        } as any)

        render(<CommandControlPage />)
        // The loading spinner in CommandControlPage doesn't have a specific testId but shares Layout
        expect(screen.getByTestId('layout')).toBeInTheDocument()
        // It basically renders nothing else from the main content if loading
        expect(screen.queryByTestId('tactical-map')).not.toBeInTheDocument()
    })

    it('renders main components when loaded', () => {
        render(<CommandControlPage />)

        expect(screen.getByTestId('tactical-map')).toBeInTheDocument()
        expect(screen.getByTestId('agent-selector')).toBeInTheDocument()
        expect(screen.getByTestId('settings-panel')).toBeInTheDocument()
        expect(screen.getByTestId('situation-input')).toBeInTheDocument()
        expect(screen.getByTestId('coa-generator')).toBeInTheDocument()
        expect(screen.getByTestId('chat-interface')).toBeInTheDocument()
    })

    it('displays active mission info', () => {
        // We mock the state where a mission is selected or passed via context
        // In the component, it might not auto-select initially unless logic dictates
        render(<CommandControlPage />)

        // Check for static elements or default state
        expect(screen.getByText('Active Mission')).toBeInTheDocument()
        // Since we didn't force selection state (internal state), it might show "선택된 임무 없음"
        expect(screen.getByText('선택된 임무 없음')).toBeInTheDocument()
    })

    it('fetches KPI stats on mount', async () => {
        render(<CommandControlPage />)
        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/api/v1/system/stats/kpi'))
        })
    })
})
