import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorBoundary from '../app/error';

describe('Global ErrorBoundary Component', () => {
    it('renders the error boundary UI without crashing', () => {
        const mockError = new Error("Test crash");
        const mockReset = jest.fn();

        render(<ErrorBoundary error={mockError} reset={mockReset} />);

        // Check if the title is displayed
        expect(screen.getByText('Something went wrong!')).toBeInTheDocument();

        // Check if the message is displayed
        expect(screen.getByText(/An unexpected error occurred/i)).toBeInTheDocument();

        // Check if the Try Again button works
        const tryAgainButton = screen.getByRole('button', { name: /try again/i });
        expect(tryAgainButton).toBeInTheDocument();

        fireEvent.click(tryAgainButton);
        expect(mockReset).toHaveBeenCalledTimes(1);
    });
});
