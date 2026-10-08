import { useIsMutating } from '@tanstack/react-query'
import { renderHook } from '@testing-library/react'
import { expect, it, vi } from 'vitest'

import { todoKeys } from '../api/queryKeys'
import { useTodosBusy } from './useTodosBusy'

const agentTestOwner = 'taskly-unit-test-agent'

vi.mock('@tanstack/react-query', () => ({ useIsMutating: vi.fn() }))

it('is busy only while a task mutation is running', () => {
  vi.mocked(useIsMutating).mockReturnValue(0)
  expect(renderHook(() => useTodosBusy()).result.current).toBe(false)
  vi.mocked(useIsMutating).mockReturnValue(2)
  expect(renderHook(() => useTodosBusy()).result.current).toBe(true)
  expect(useIsMutating).toHaveBeenCalledWith({ mutationKey: todoKeys.all })
})
