import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { expect, it, vi } from 'vitest'

import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useCreateTodoMutation } from './useCreateTodoMutation'

const agentTestOwner = 'taskly-unit-test-agent'

vi.mock('../api/todos', () => ({ todosApi: { create: vi.fn() } }))

it('stores the created task ahead of the current list', async () => {
  const saved = { ...todoFixture, id: 9, title: 'Created' }
  vi.mocked(todosApi.create).mockResolvedValue(saved)
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  })
  client.setQueryData(todoKeys.list, [todoFixture])
  const { result } = renderHook(() => useCreateTodoMutation(), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children),
  })
  act(() => result.current.mutate(todoFixture))
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(todosApi.create).toHaveBeenCalledWith(todoFixture)
  expect(client.getQueryData(todoKeys.list)).toEqual([saved, todoFixture])
})
