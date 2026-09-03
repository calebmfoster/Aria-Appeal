import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import VideoPreview from './VideoPreview'
import { useStudioStore } from '@/store/studioStore'

jest.mock('@/store/studioStore')

const mockAssemble = jest.fn()
const mockSetActiveClip = jest.fn()

function clip(order: number, over: Record<string, unknown> = {}) {
    return {
        id: `c${order}`,
        project_id: 'p1',
        segment_id: `s${order}`,
        sequence_order: order,
        source_type: 'asset',
        status: 'ready',
        prompt: `shot ${order}`,
        video_url: `/static/video/assets/c${order}.mp4`,
        duration_ms: 2000,
        timeline_start_ms: order * 2000,
        timeline_end_ms: (order + 1) * 2000,
        ...over,
    }
}

function mockStore(overrides: Record<string, unknown> = {}) {
    (useStudioStore as unknown as jest.Mock).mockReturnValue({
        videoClips: [clip(1), clip(0), clip(2)],
        script: [
            { id: 's0', text: 'first', start_ms: 0, end_ms: 2000 },
            { id: 's1', text: 'second', start_ms: 2000, end_ms: 4000 },
            { id: 's2', text: 'third', start_ms: 4000, end_ms: 6000 },
        ],
        activeSegmentId: null,
        activeClipId: null,
        setActiveClip: mockSetActiveClip,
        setActiveSegment: jest.fn(),
        ...overrides,
    })
}

describe('VideoPreview', () => {
    beforeEach(() => {
        jest.clearAllMocks()
        window.HTMLMediaElement.prototype.play = jest.fn().mockResolvedValue(undefined)
        window.HTMLMediaElement.prototype.pause = jest.fn()
        window.HTMLMediaElement.prototype.load = jest.fn()
    })

    it('shows the empty state with an assemble button before the first assembly', () => {
        mockStore()

        render(<VideoPreview exportState={{ status: 'idle', url: null, error: null }} onAssemble={mockAssemble} />)

        expect(screen.getByRole('button', { name: /assemble video/i })).toBeInTheDocument()
        expect(screen.queryByTestId('animatic-player')).not.toBeInTheDocument()
    })

    it('triggers assembly from the empty state', () => {
        mockStore()

        render(<VideoPreview exportState={{ status: 'idle', url: null, error: null }} onAssemble={mockAssemble} />)
        fireEvent.click(screen.getByRole('button', { name: /assemble video/i }))

        expect(mockAssemble).toHaveBeenCalled()
    })

    it('renders the player once an animatic url exists', () => {
        mockStore()

        render(<VideoPreview exportState={{ status: 'ready', url: '/static/video/a.mp4', error: null }} onAssemble={mockAssemble} />)

        expect(screen.getByTestId('animatic-player')).toBeInTheDocument()
    })

    it('orders the clip strip by sequence_order regardless of array order', () => {
        mockStore()

        render(<VideoPreview exportState={{ status: 'ready', url: '/static/video/a.mp4', error: null }} onAssemble={mockAssemble} />)

        const ids = screen.getAllByTestId('clip-strip-item').map(el => el.getAttribute('data-clip-id'))
        expect(ids).toEqual(['c0', 'c1', 'c2'])
    })

    it('shows the assembly error and keeps the previous animatic playable', () => {
        mockStore()

        render(<VideoPreview
            exportState={{ status: 'failed', url: '/static/video/old.mp4', error: 'Clips not ready: scene 3.' }}
            onAssemble={mockAssemble}
        />)

        expect(screen.getByText(/clips not ready: scene 3/i)).toBeInTheDocument()
        expect(screen.getByTestId('animatic-player')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    })

    it('shows a running indicator while assembling', () => {
        mockStore()

        render(<VideoPreview exportState={{ status: 'running', url: null, error: null }} onAssemble={mockAssemble} />)

        expect(screen.getByText(/assembling/i)).toBeInTheDocument()
    })

    it('pauses the player on unmount', () => {
        mockStore()
        const pause = jest.fn()
        window.HTMLMediaElement.prototype.pause = pause

        const { unmount } = render(
            <VideoPreview exportState={{ status: 'ready', url: '/static/video/a.mp4', error: null }} onAssemble={mockAssemble} />
        )
        unmount()

        expect(pause).toHaveBeenCalled()
    })
})
