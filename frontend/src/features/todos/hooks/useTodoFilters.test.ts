import { act, renderHook } from '@testing-library/react'
import { expect, it } from 'vitest'

import { todoFixture } from '../../../test/todoFixture'
import { useTodoFilters } from './useTodoFilters'

const agentTestOwner = 'taskly-unit-test-agent'

it('starts from the default view and applies the status filter', () => {
  const { result } = renderHook(() => useTodoFilters([todoFixture]))
  expect(result.current.filter).toBe('all')
  expect(result.current.search).toBe('')
  expect(result.current.sort).toBe('newest')
  expect(result.current.visible).toEqual([todoFixture])
  act(() => result.current.setFilter('completed'))
  expect(result.current.filter).toBe('completed')
  expect(result.current.visible).toEqual([])
  act(() => result.current.setSearch('missing-task'))
  expect(result.current.search).toBe('missing-task')
})
