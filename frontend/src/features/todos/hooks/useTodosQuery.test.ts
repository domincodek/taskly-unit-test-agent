import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { expect, it, vi } from 'vitest'

import { todoFixture } from '../../../test/todoFixture'
import { todosApi } from '../api/todos'
import { useTodosQuery } from './useTodosQuery'

const agentTestOwner = 'taskly-unit-test-agent'

vi.mock('../api/todos', () => ({ todosApi: { list: vi.fn() } }))

it('loads tasks through the task query', async () => {
  vi.mocked(todosApi.list).mockResolvedValue([todoFixture])
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const { result } = renderHook(() => useTodosQuery(), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children),
  })
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(result.current.data).toEqual([todoFixture])
  expect(todosApi.list).toHaveBeenCalledWith(expect.any(AbortSignal))
})
