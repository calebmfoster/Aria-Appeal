import { renderHook, act, waitFor } from '@testing-library/react'
import { useVideoExport } from './useVideoExport'

jest.mock('@/lib/api', () => ({
    apiFetch: jest.fn(),
}))

import { apiFetch } from '@/lib/api'

const mockApiFetch = apiFetch as jest.Mock

function ok(body: unknown) {
    return { ok: true, json: async () => body }
}

function fail(status: number, body: unknown) {
    return { ok: false, status, json: async () => body }
}

describe('useVideoExport', () => {
    beforeEach(() => {
        jest.clearAllMocks()
        jest.useFakeTimers()
    })

    afterEach(() => {
        jest.runOnlyPendingTimers()
        jest.useRealTimers()
    })

    it('reports ready and exposes the url when the first status read is already ready', async () => {
        mockApiFetch.mockResolvedValue(
            ok({ status: 'ready', video_master_url: '/static/video/a.mp4', error: null })
        )

        const { result } = renderHook(() => useVideoExport('p1', 'tok'))

        await act(async () => { await result.current.refresh() })

        expect(result.current.state.status).toBe('ready')
        expect(result.current.state.url).toBe('/static/video/a.mp4')
    })

    it('goes running on assemble, then ready once the poll flips', async () => {
        mockApiFetch
            .mockResolvedValueOnce(ok({ status: 'running', message: 'Assembly started.' }))
            .mockResolvedValueOnce(ok({ status: 'running', video_master_url: null, error: null }))
            .mockResolvedValueOnce(ok({ status: 'ready', video_master_url: '/static/video/a.mp4', error: null }))

        const { result } = renderHook(() => useVideoExport('p1', 'tok'))

        await act(async () => { await result.current.assemble() })
        expect(result.current.state.status).toBe('running')

        await act(async () => { jest.advanceTimersByTime(2000) })
        await act(async () => { jest.advanceTimersByTime(2000) })

        await waitFor(() => expect(result.current.state.status).toBe('ready'))
        expect(result.current.state.url).toBe('/static/video/a.mp4')
    })

    it('surfaces the endpoint error string when assembly is rejected', async () => {
        mockApiFetch.mockResolvedValueOnce(
            fail(400, { detail: 'Clips not ready: scene 3, 5.' })
        )

        const { result } = renderHook(() => useVideoExport('p1', 'tok'))

        await act(async () => { await result.current.assemble() })

        expect(result.current.state.status).toBe('failed')
        expect(result.current.state.error).toContain('scene 3, 5')
    })

    it('surfaces a failure reported by the poll', async () => {
        mockApiFetch
            .mockResolvedValueOnce(ok({ status: 'running' }))
            .mockResolvedValueOnce(ok({ status: 'failed', video_master_url: null, error: 'ffmpeg exploded' }))

        const { result } = renderHook(() => useVideoExport('p1', 'tok'))

        await act(async () => { await result.current.assemble() })
        await act(async () => { jest.advanceTimersByTime(2000) })

        await waitFor(() => expect(result.current.state.status).toBe('failed'))
        expect(result.current.state.error).toBe('ffmpeg exploded')
    })

    it('keeps the previous animatic url playable after a failed re-assembly', async () => {
        mockApiFetch
            .mockResolvedValueOnce(ok({ status: 'ready', video_master_url: '/static/video/old.mp4', error: null }))
            .mockResolvedValueOnce(fail(400, { detail: 'Clips not ready: scene 2.' }))

        const { result } = renderHook(() => useVideoExport('p1', 'tok'))

        await act(async () => { await result.current.refresh() })
        await act(async () => { await result.current.assemble() })

        expect(result.current.state.status).toBe('failed')
        expect(result.current.state.url).toBe('/static/video/old.mp4')
    })

    it('stops polling on unmount', async () => {
        mockApiFetch
            .mockResolvedValueOnce(ok({ status: 'running' }))
            .mockResolvedValue(ok({ status: 'running', video_master_url: null, error: null }))

        const { result, unmount } = renderHook(() => useVideoExport('p1', 'tok'))

        await act(async () => { await result.current.assemble() })
        const callsBefore = mockApiFetch.mock.calls.length

        unmount()
        await act(async () => { jest.advanceTimersByTime(10000) })

        expect(mockApiFetch.mock.calls.length).toBe(callsBefore)
    })

    it('does nothing without a token', async () => {
        const { result } = renderHook(() => useVideoExport('p1', undefined))

        await act(async () => { await result.current.assemble() })

        expect(mockApiFetch).not.toHaveBeenCalled()
    })
})
