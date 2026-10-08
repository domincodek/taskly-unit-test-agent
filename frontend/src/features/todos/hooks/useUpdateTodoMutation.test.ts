import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { expect, it, vi } from 'vitest'

import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useUpdateTodoMutation } from './useUpdateTodoMutation'

const agentTestOwner = 'taskly-unit-test-agent'

vi.mock('../api/todos', () => ({ todosApi: { update: vi.fn() } }))

it('replaces the updated task in the current list', async () => {
  const saved = { ...todoFixture, title: 'Updated' }
  vi.mocked(todosApi.update).mockResolvedValue(saved)
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  })
  client.setQueryData(todoKeys.list, [todoFixture])
  const { result } = renderHook(() => useUpdateTodoMutation(), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children),
  })
  act(() => result.current.mutate({ id: todoFixture.id, input: { title: 'Updated' } }))
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(todosApi.update).toHaveBeenCalledWith(todoFixture.id, { title: 'Updated' })
  expect(client.getQueryData(todoKeys.list)).toEqual([saved])
})
