import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import HomePage from '../pages/HomePage';
import { describe, test, expect, beforeAll, afterEach, afterAll } from 'vitest';

const server = setupServer(
  rest.get('/api/files', (req, res, ctx) => {
    return res(ctx.json([
      { filename: 'test1.json', status: 'validated' },
      { filename: 'test2.json', status: 'in_progress' },
    ]));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('HomePage', () => {
  test('renders file list from API', async () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    );

    expect(screen.getByText(/loading files/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('test1.json')).toBeInTheDocument();
      expect(screen.getByText('Validated ✓')).toBeInTheDocument();
      expect(screen.getByText('test2.json')).toBeInTheDocument();
      expect(screen.getByText('In Progress...')).toBeInTheDocument();
    });
  });
});
