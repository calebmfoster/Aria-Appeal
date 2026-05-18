import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import ScriptEditor from './ScriptEditor'
import { useStudioStore } from '@/store/studioStore'

jest.mock('@/store/studioStore')

describe('ScriptEditor', () => {
    const mockSetActiveSegment = jest.fn()

    beforeEach(() => {
        jest.clearAllMocks();
        (useStudioStore as unknown as jest.Mock).mockReturnValue({
            script: [
                { id: '1', text: 'First segment', start_ms: 0, end_ms: 1000 },
                { id: '2', text: 'Second segment', start_ms: 1000, end_ms: 2000 }
            ],
            activeSegmentId: null,
            currentTime: 0,
            setActiveSegment: mockSetActiveSegment
        })

        // Mock scrollIntoView
        window.HTMLElement.prototype.scrollIntoView = jest.fn()
    })

    it('renders all script segments', () => {
        render(<ScriptEditor />)

        expect(screen.getByText('First segment')).toBeInTheDocument()
        expect(screen.getByText('Second segment')).toBeInTheDocument()
    })

    it('sets active segment on click', () => {
        render(<ScriptEditor />)

        const segment = screen.getByText('First segment')
        fireEvent.click(segment)

        expect(mockSetActiveSegment).toHaveBeenCalledWith('1')
    })
})
