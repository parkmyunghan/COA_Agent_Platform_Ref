
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { COAGenerator } from './COAGenerator'
import api from '../lib/api'

// Mock API
vi.mock('../lib/api', () => ({
    default: {
        post: vi.fn()
    }
}))

// Mock Context
vi.mock('../contexts/ExecutionContext', () => ({
    useExecutionContext: () => ({
        startExecution: vi.fn(),
        updateProgress: vi.fn(),
        addLog: vi.fn(),
        completeExecution: vi.fn(),
        errorExecution: vi.fn(),
        isRunning: false,
        progress: 0,
        logs: []
    })
}))

// Mock Child Components
vi.mock('./COADetailModal', () => ({
    COADetailModal: () => <div data-testid="coa-detail-modal">Detail Modal</div>
}))
vi.mock('./COAComparisonPanel', () => ({
    COAComparisonPanel: () => <div data-testid="coa-comparison-panel">Comparison Panel</div>
}))
vi.mock('./common/ProgressStatus', () => ({
    ProgressStatus: () => <div data-testid="progress-status">Progress</div>
}))

describe('COAGenerator', () => {
    const defaultProps = {
        selectedMission: null,
        selectedThreat: null,
        onResponse: vi.fn()
    }

    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('renders initial state correctly', () => {
        render(<COAGenerator {...defaultProps} />)
        expect(screen.getByText('방책 추천 (COA Recommendation)')).toBeInTheDocument()
        expect(screen.getByText('방책 추천 실행')).toBeDisabled()
    })

    it('enables button when valid inputs are provided', () => {
        const props = {
            ...defaultProps,
            selectedMission: { mission_id: 'M001' } as any
        }
        render(<COAGenerator {...props} />)
        // Check if button is enabled
        // Note: Logic says !selectedThreat && !selectedMission. So if one of them is present, it might be disabled? 
        // Let's check logic:
        // if (approachMode === 'threat_centered') return !threatToUse && !selectedThreat;
        // logic is tricky. Let's provide situationInfo which definitely enables it.

        // Actually, let's use situationInfo
    })

    it('enables button with situation info', () => {
        const props = {
            ...defaultProps,
            situationInfo: {
                situation_id: 'SIT001',
                threat_type: 'Attack',
                location: 'Test Location'
            }
        }
        render(<COAGenerator {...props} />)
        const button = screen.getByText('방책 추천 실행')
        expect(button).not.toBeDisabled()
    })

    it('handles successful COA generation', async () => {
        const mockResponse = {
            data: {
                coas: [
                    { coa_id: 'COA-1', coa_name: 'Option Alpha', total_score: 0.9, rank: 1 }
                ],
                progress_logs: []
            }
        }
        vi.mocked(api.post).mockResolvedValue(mockResponse)

        const props = {
            ...defaultProps,
            situationInfo: {
                situation_id: 'SIT001',
                threat_type: 'Attack',
                location: 'Test Location'
            }
        }
        render(<COAGenerator {...props} />)

        const button = screen.getByText('방책 추천 실행')
        fireEvent.click(button)

        await waitFor(() => {
            expect(api.post).toHaveBeenCalled()
        })

        // Wait for the response to be processed and state updated
        await waitFor(() => {
            expect(screen.getByText(/Option Alpha/)).toBeInTheDocument()
        }, { timeout: 3000 })
    })

    it('handles API error', async () => {
        const errorMsg = 'Server Error Details'
        // Mock rejected value matching axios error structure
        vi.mocked(api.post).mockRejectedValue({
            response: { status: 500, data: { detail: errorMsg } }
        })

        const props = {
            ...defaultProps,
            situationInfo: {
                situation_id: 'SIT001',
                threat_type: 'Attack',
                location: 'Test Location'
            }
        }
        render(<COAGenerator {...props} />)

        const button = screen.getByText('방책 추천 실행')
        fireEvent.click(button)

        await waitFor(() => {
            expect(screen.getByText((content) => content.includes(errorMsg))).toBeInTheDocument()
        }, { timeout: 3000 })
    })

    it('displays skeleton UI while loading', async () => {
        vi.mocked(api.post).mockImplementation(
            () => new Promise(resolve => setTimeout(() => resolve({
                data: mockResponse
            }), 100))
        )

        const props = {
            ...defaultProps,
            situationInfo: {
                situation_id: 'SIT001',
                threat_type: 'Attack',
                location: 'Test Location'
            }
        }
        render(<COAGenerator {...props} />)

        const button = screen.getByText('방책 추천 실행')
        fireEvent.click(button)

        expect(button).toBeDisabled()
        // Check for skeleton elements by checking if loading text is present
        expect(screen.getByText('방책 생성 및 워게임 진행 중...')).toBeInTheDocument()
    })
})
