
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { SituationInputPanel } from './SituationInputPanel'
import * as SystemDataHook from '../hooks/useSystemData'
import api from '../lib/api'

// Mock API
vi.mock('../lib/api', () => ({
    default: {
        post: vi.fn()
    }
}))

// Mock UI components that might be complex
vi.mock('./ui/slider', () => ({
    Slider: ({ onValueChange, value, ...props }: any) => (
        <input
            type="range"
            data-testid="slider-mock"
            value={value?.[0] ?? 50}
            onChange={e => onValueChange([parseInt(e.target.value)])}
            {...props}
        />
    )
}))

describe('SituationInputPanel', () => {
    const mockOnSituationChange = vi.fn()
    const mockOnThreatIdentified = vi.fn()
    const mockSystemData = {
        threats: [
            { threat_id: 'T001', threat_type: '공중침투', location: 'Section A' }
        ],
        loading: false
    }

    beforeEach(() => {
        vi.clearAllMocks()
        vi.spyOn(SystemDataHook, 'useSystemData').mockReturnValue(mockSystemData as any)
    })

    it('renders correctly with default manual mode', () => {
        render(<SituationInputPanel onSituationChange={mockOnSituationChange} />)

        expect(screen.getByText('📋 상황 정보 설정')).toBeInTheDocument()
        expect(screen.getByText('접근 방식 선택')).toBeInTheDocument()
        expect(screen.getByText('입력 방식')).toBeInTheDocument()
        // Manual mode defaults
        expect(screen.getByText('상황 ID')).toBeInTheDocument()
    })

    it('switches input modes', async () => {
        render(<SituationInputPanel onSituationChange={mockOnSituationChange} />);

        // Find select by current value "수동 입력"
        const select = screen.getByDisplayValue('수동 입력') as HTMLSelectElement;

        // Select Real Data mode
        fireEvent.change(select, { target: { value: 'real_data' } });
        await waitFor(() => {
            expect(screen.getByText(/실제 데이터에서 위협 선택/)).toBeInTheDocument();
        });

        // Re-find select by new value to ensure we have the correct element/state
        const selectAfter = screen.getByDisplayValue('실제 데이터에서 선택') as HTMLSelectElement;

        // Select SITREP mode
        fireEvent.change(selectAfter, { target: { value: 'sitrep' } });
        await waitFor(() => {
            expect(screen.getByText(/SITREP 텍스트 입력/)).toBeInTheDocument();
        });
    });

    it('updates situation data in manual mode', () => {
        render(<SituationInputPanel onSituationChange={mockOnSituationChange} />)

        const situationIdInput = screen.getByPlaceholderText('SIT_20240101_120000')
        fireEvent.change(situationIdInput, { target: { value: 'NEW_SIT_001' } })

        expect(mockOnSituationChange).toHaveBeenCalledWith(expect.objectContaining({
            situation_id: 'NEW_SIT_001'
        }))
    })

    it('handles SITREP text submission', async () => {
        const mockAnalysisResult = {
            threat_type: '침투',
            location: '강릉',
            threat_level: 0.8
        }
        vi.mocked(api.post).mockResolvedValue({ data: mockAnalysisResult })

        // Setup window.alert mock
        vi.spyOn(window, 'alert').mockImplementation(() => { })

        render(
            <SituationInputPanel
                onSituationChange={mockOnSituationChange}
                onThreatIdentified={mockOnThreatIdentified}
            />
        );

        // Switch to SITREP mode
        const select = screen.getByDisplayValue('수동 입력')
        fireEvent.change(select, { target: { value: 'sitrep' } })

        const textArea = screen.getByPlaceholderText('상황 보고서 텍스트를 입력하세요...')
        fireEvent.change(textArea, { target: { value: '적 특수부대 침투 징후 포착' } })

        const submitButton = screen.getByText('SITREP 분석 실행')
        fireEvent.click(submitButton)

        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith('/threat/analyze', {
                sitrep_text: '적 특수부대 침투 징후 포착'
            })
            expect(mockOnSituationChange).toHaveBeenCalledWith(expect.objectContaining({
                threat_type: '침투',
                location: '강릉'
            }))
            expect(mockOnThreatIdentified).toHaveBeenCalled()
        })
    })
})
