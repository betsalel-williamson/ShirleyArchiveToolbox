import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { describe, test, expect, beforeAll, afterEach, afterAll, vi, beforeEach } from 'vitest';
import ValidatePage from '../client/pages/ValidatePage';
import HomePage from '../client/pages/HomePage'; // For navigation testing
import type { ValidationData } from '../../types/types';

const MOCK_FILE_NAME = 'test-file.json';

const MOCK_INITIAL_DATA: ValidationData = {
  image_source: 'test-image.jpg',
  image_dimensions: { width: 1000, height: 800 },
  lines: [
    {
      words: [
        { id: 'w1', text: 'Hello', bounding_box: { x_min: 10, y_min: 10, x_max: 50, y_max: 30 } },
        { id: 'w2', text: 'World', bounding_box: { x_min: 60, y_min: 10, x_max: 110, y_max: 30 } },
      ],
    },
  ],
};

const MOCK_SOURCE_DATA: ValidationData = {
    ...MOCK_INITIAL_DATA,
    lines: [
        {
            words: [
                { id: 'w1', text: 'OriginalHello', bounding_box: { x_min: 10, y_min: 10, x_max: 50, y_max: 30 } },
                { id: 'w2', text: 'OriginalWorld', bounding_box: { x_min: 60, y_min: 10, x_max: 110, y_max: 30 } },
            ]
        }
    ]
};

const server = setupServer(
  http.get(`/api/files/${MOCK_FILE_NAME}`, () => {
    return HttpResponse.json(MOCK_INITIAL_DATA);
  }),
  http.patch(`/api/autosave/${MOCK_FILE_NAME}`, async () => {
    return HttpResponse.json({ status: 'ok' });
  }),
  http.patch(`/api/commit/${MOCK_FILE_NAME}`, async () => {
    return HttpResponse.json({ status: 'ok', nextFile: 'next-file.json' });
  }),
  http.get(`/api/source-data/${MOCK_FILE_NAME}`, () => {
    return HttpResponse.json(MOCK_SOURCE_DATA);
  })
);

// Mock react-router-dom's useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Wrapper component for routing context
const TestWrapper: React.FC = () => (
  <MemoryRouter initialEntries={[`/validate/${MOCK_FILE_NAME}`]}>
    <Routes>
      <Route path="/validate/:json_filename" element={<ValidatePage />} />
      <Route path="/" element={<HomePage />} />
      <Route path="/validate/next-file.json" element={<div>Next File Page</div>} />
    </Routes>
  </MemoryRouter>
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('ValidatePage', () => {
    beforeEach(() => {
        mockNavigate.mockClear();
        vi.spyOn(window, 'confirm').mockReturnValue(true);
        // JSDOM doesn't support layout, so we mock properties used for calculations
        Object.defineProperty(HTMLElement.prototype, 'clientWidth', { configurable: true, value: 500 });
        Object.defineProperty(HTMLElement.prototype, 'clientHeight', { configurable: true, value: 500 });
    });

    test('renders loading state and then loads data correctly', async () => {
        render(<TestWrapper />);
        expect(screen.getByText('Loading...')).toBeInTheDocument();

        await waitFor(() => {
            expect(screen.getByDisplayValue('Hello')).toBeInTheDocument();
            expect(screen.getByDisplayValue('World')).toBeInTheDocument();
        });
    });

    test('allows editing a word transcription and updates state', async () => {
        render(<TestWrapper />);
        await waitFor(() => expect(screen.getByDisplayValue('Hello')).toBeInTheDocument());

        const input = screen.getByDisplayValue('Hello') as HTMLInputElement;
        fireEvent.change(input, { target: { value: 'Changed' } });

        expect(input.value).toBe('Changed');
    });

    test('handles undo and redo functionality', async () => {
        render(<TestWrapper />);
        await waitFor(() => expect(screen.getByDisplayValue('Hello')).toBeInTheDocument());

        const undoButton = screen.getByRole('button', { name: /undo/i });
        const redoButton = screen.getByRole('button', { name: /redo/i });
        const input = screen.getByDisplayValue('Hello') as HTMLInputElement;

        expect(undoButton).toBeDisabled();

        fireEvent.change(input, { target: { value: 'Changed' } });
        expect(input.value).toBe('Changed');
        expect(undoButton).toBeEnabled();

        fireEvent.click(undoButton);
        expect(input.value).toBe('Hello');
        expect(undoButton).toBeDisabled();
        expect(redoButton).toBeEnabled();

        fireEvent.click(redoButton);
        expect(input.value).toBe('Changed');
    });

    test('triggers autosave after a debounced state change', async () => {
        vi.useFakeTimers();
        const fetchSpy = vi.spyOn(window, 'fetch');
        render(<TestWrapper />);
        await waitFor(() => expect(screen.getByDisplayValue('Hello')).toBeInTheDocument());

        fireEvent.change(screen.getByDisplayValue('Hello'), { target: { value: 'Changed' } });

        // Should not have saved yet
        expect(screen.queryByText('Saving...')).not.toBeInTheDocument();
        expect(fetchSpy).not.toHaveBeenCalledWith(expect.stringContaining('autosave'), expect.any(Object));

        // Advance timers past the debounce delay
        vi.advanceTimersByTime(1100);

        await waitFor(() => {
            expect(screen.getByText('Saving...')).toBeInTheDocument();
            expect(fetchSpy).toHaveBeenCalledWith(expect.stringContaining('autosave'), expect.any(Object));
        });

        await waitFor(() => {
            expect(screen.getByText('Draft Saved ✓')).toBeInTheDocument();
        });
        vi.useRealTimers();
    });

    test('commits changes and navigates to the next file', async () => {
        render(<TestWrapper />);
        await waitFor(() => expect(screen.getByDisplayValue('Hello')).toBeInTheDocument());

        const commitButton = screen.getByRole('button', { name: /commit & next/i });
        fireEvent.click(commitButton);

        await waitFor(() => {
            expect(mockNavigate).toHaveBeenCalledWith('/validate/next-file.json');
        });
    });

    test('reverts data to original source on confirmation', async () => {
        render(<TestWrapper />);
        await waitFor(() => expect(screen.getByDisplayValue('Hello')).toBeInTheDocument());

        fireEvent.change(screen.getByDisplayValue('Hello'), { target: { value: 'Changed' } });
        expect(screen.getByDisplayValue('Changed')).toBeInTheDocument();

        const revertButton = screen.getByRole('button', { name: /revert data/i });
        fireEvent.click(revertButton);

        await waitFor(() => {
            expect(screen.getByDisplayValue('OriginalHello')).toBeInTheDocument();
            expect(screen.getByDisplayValue('OriginalWorld')).toBeInTheDocument();
        });
    });
});
