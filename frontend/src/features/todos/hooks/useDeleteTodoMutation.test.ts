import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { expect, it, vi } from 'vitest'

import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useDeleteTodoMutation } from './useDeleteTodoMutation'

const agentTestOwner = 'taskly-unit-test-agent'

vi.mock('../api/todos', () => ({ todosApi: { remove: vi.fn() } }))

it('removes the deleted task from the current list', async () => {
  const other = { ...todoFixture, id: 8 }
  vi.mocked(todosApi.remove).mockResolvedValue(undefined)
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  })
  client.setQueryData(todoKeys.list, [todoFixture, other])
  const { result } = renderHook(() => useDeleteTodoMutation(), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children),
  })
  act(() => result.current.mutate(todoFixture.id))
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(todosApi.remove).toHaveBeenCalledWith(todoFixture.id)
  expect(client.getQueryData(todoKeys.list)).toEqual([other])
})
