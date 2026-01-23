
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import SPARQLQueryPanel from './SPARQLQueryPanel'
import api from '../../lib/api'

// Mock dependencies
vi.mock('../../lib/api', () => ({
    default: {
        post: vi.fn()
    }
}))

// Mock Monaco Editor component to avoid heavy loading
vi.mock('@monaco-editor/react', () => ({
    default: ({ value, onChange }: any) => (
        <textarea
            data-testid="monaco-editor-mock"
            value={value}
            onChange={e => onChange(e.target.value)}
        />
    )
}))

// Mock Ag-Grid to avoid layout issues in JSDOM
vi.mock('ag-grid-react', () => ({
    AgGridReact: ({ rowData }: any) => (
        <div data-testid="ag-grid-mock">
            {rowData.map((row: any, idx: number) => (
                <div key={idx} data-testid="grid-row">{JSON.stringify(row)}</div>
            ))}
        </div>
    )
}))

describe('SPARQLQueryPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('renders properly', () => {
        render(<SPARQLQueryPanel />)
        expect(screen.getByText('SPARQL 쿼리')).toBeInTheDocument()
        expect(screen.getByText('실행')).toBeInTheDocument()
        // Check if default query is loaded in editor mock
        const editor = screen.getByTestId('monaco-editor-mock') as HTMLTextAreaElement
        expect(editor.value).toContain('SELECT DISTINCT')
    })

    it('executes query when button clicked', async () => {
        const mockData = {
            data: {
                results: [{ s: 'http://example.org/a', p: 'type', o: 'Class' }],
                count: 1
            }
        }

        // Setup mock response
        vi.mocked(api.post).mockResolvedValue(mockData)

        render(<SPARQLQueryPanel />)

        const executeButton = screen.getByRole('button', { name: /실행/ })
        fireEvent.click(executeButton)

        // Loading state might be too fast to catch with resolved mock

        await waitFor(() => {
            expect(screen.getByText('결과 (1개)')).toBeInTheDocument()
        })

        // Check if table renders data
        expect(screen.getByTestId('ag-grid-mock')).toBeInTheDocument()
        expect(screen.getByText(/http:\/\/example.org\/a/)).toBeInTheDocument()
    })

    it('handles API errors', async () => {
        const errorMessage = 'SPARQL query failed: <lambda>() missing 1 argument'
        vi.mocked(api.post).mockRejectedValue({
            response: {
                data: {
                    detail: errorMessage
                }
            }
        })

        render(<SPARQLQueryPanel />)

        const executeButton = screen.getByText('실행')
        fireEvent.click(executeButton)

        await waitFor(() => {
            expect(screen.getByText(errorMessage)).toBeInTheDocument()
        })
    })
})

// Helper to find text that might be split
function buttonText(text: string) {
    return screen.getByText((content, element) => {
        return element?.textContent === text
    })
}
