import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import StudioTabs from './StudioTabs'
import { useStudioStore } from '@/store/studioStore'

jest.mock('@/store/studioStore')

const mockSetActiveTab = jest.fn()

function mockStore(overrides: Record<string, unknown> = {}) {
    (useStudioStore as unknown as jest.Mock).mockReturnValue({
        medium: 'video',
        activeTab: 'audio',
        setActiveTab: mockSetActiveTab,
        ...overrides,
    })
}

describe('StudioTabs', () => {
    beforeEach(() => {
        jest.clearAllMocks()
    })

    it('renders nothing at all for an audio-only campaign', () => {
        mockStore({ medium: 'audio' })

        const { container } = render(<StudioTabs />)

        expect(container).toBeEmptyDOMElement()
        expect(screen.queryByRole('tab', { name: /video/i })).not.toBeInTheDocument()
    })

    it('renders both tabs for a video campaign', () => {
        mockStore()

        render(<StudioTabs />)

        expect(screen.getByRole('tab', { name: /audio/i })).toBeInTheDocument()
        expect(screen.getByRole('tab', { name: /video/i })).toBeInTheDocument()
    })

    it('marks the active tab as selected', () => {
        mockStore({ activeTab: 'video' })

        render(<StudioTabs />)

        expect(screen.getByRole('tab', { name: /video/i })).toHaveAttribute('aria-selected', 'true')
        expect(screen.getByRole('tab', { name: /audio/i })).toHaveAttribute('aria-selected', 'false')
    })

    it('switches tab on click', () => {
        mockStore()

        fireEvent.click(render(<StudioTabs />).getByRole('tab', { name: /video/i }))

        expect(mockSetActiveTab).toHaveBeenCalledWith('video')
    })
})
