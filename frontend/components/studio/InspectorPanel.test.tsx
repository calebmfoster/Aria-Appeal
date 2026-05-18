import '@testing-library/jest-dom'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import InspectorPanel from './InspectorPanel'
import { useStudioStore } from '@/store/studioStore'

// Mock the store
jest.mock('@/store/studioStore')

describe('InspectorPanel', () => {
    const mockUpdateSegment = jest.fn()
    const mockSetAudioUrl = jest.fn()

    beforeEach(() => {
        // Reset mocks
        jest.clearAllMocks();

        // Default store state
        (useStudioStore as unknown as jest.Mock).mockReturnValue({
            activeSegmentId: '1',
            script: [
                { id: '1', text: 'Hello world', start_ms: 0, end_ms: 1000, emotion: 'Happy' }
            ],
            audioUrl: '/test.wav',
            updateSegment: mockUpdateSegment,
            setAudioUrl: mockSetAudioUrl
        })
    })

    it('renders segment details when a segment is selected', () => {
        render(<InspectorPanel />)

        expect(screen.getByText('Inspector')).toBeInTheDocument()
        expect(screen.getByDisplayValue('Hello world')).toBeInTheDocument()
        expect(screen.getByDisplayValue('Happy')).toBeInTheDocument()
    })

    it('calls updateSegment when text is changed', () => {
        render(<InspectorPanel />)

        const textInput = screen.getByDisplayValue('Hello world')
        fireEvent.change(textInput, { target: { value: 'Hello universe' } })

        expect(mockUpdateSegment).toHaveBeenCalledWith('1', { text: 'Hello universe' })
    })

    it('shows empty state when no segment is selected', () => {
        (useStudioStore as unknown as jest.Mock).mockReturnValue({
            activeSegmentId: null,
            script: [],
            audioUrl: null
        })

        render(<InspectorPanel />)
        expect(screen.getByText('Select a segment to edit')).toBeInTheDocument()
    })

    it('calls regenerate API when button is clicked', async () => {
        global.fetch = jest.fn().mockResolvedValue({
            ok: true,
            json: async () => ({ task_id: 'task-123' })
        })

        render(<InspectorPanel />)

        const button = screen.getByText('Regenerate Segment')
        fireEvent.click(button)

        expect(global.fetch).toHaveBeenCalledWith(
            expect.stringContaining('/api/v1/regenerate-segment'),
            expect.anything()
        )
    })
})
