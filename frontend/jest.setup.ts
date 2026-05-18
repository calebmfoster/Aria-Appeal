import '@testing-library/jest-dom'

// Mock ResizeObserver for wavesurfer.js
global.ResizeObserver = class ResizeObserver {
    observe() { }
    unobserve() { }
    disconnect() { }
}

// Mock fetch
global.fetch = jest.fn()
