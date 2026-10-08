import { describe, expect, it, vi } from 'vitest'
import type { Todo } from '../types'
import { todoFixture } from '../../../test/todoFixture'
import { formatDate, isOverdue, selectTodos, validateTodo } from './todos'

const base: Todo = {
  id: 1,
  title: 'Sprint plan',
  description: '',
  priority: 'medium',
  completed: false,
  due_date: null,
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
}

describe('selectTodos', () => {
  it('combines status with a case-insensitive search in the description', () => {
    const matching = { ...base, description: 'Discuss the API' }
    const todos = [
      matching,
      { ...matching, id: 2, completed: true },
      { ...base, id: 3 },
    ]
    expect(selectTodos(todos, 'active', ' api ', 'newest')).toEqual([matching])
  })

  it('sorts by priority without changing the source array', () => {
    const high: Todo = { ...base, id: 2, priority: 'high' }
    const todos = [base, high]
    expect(selectTodos(todos, 'all', '', 'priority')).toEqual([high, base])
    expect(todos).toEqual([base, high])
  })
})

it('marks an open task overdue only before the local day', () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date(2026, 9, 8, 15, 0, 0))
  try {
    const open = { ...todoFixture, due_date: '2026-10-07', completed: false }
    expect(isOverdue(open)).toBe(true)
    expect(isOverdue({ ...open, due_date: '2026-10-08' })).toBe(false)
    expect(isOverdue({ ...open, due_date: null })).toBe(false)
    expect(isOverdue({ ...open, completed: true })).toBe(false)
  } finally {
    vi.useRealTimers()
  }
})

it('characterizes validateTodo for case 0', () => {
  expect(validateTodo({ title: 'task', description: 'task', priority: 'low', due_date: null, completed: false })).toEqual({})
})

it('characterizes validateTodo for case 1', () => {
  expect(validateTodo({ title: '', description: 'task', priority: 'low', due_date: null, completed: false })).toEqual({ title: 'Enter a task title.' })
})

it('characterizes validateTodo for case 2', () => {
  expect(validateTodo({ title: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', description: 'task', priority: 'low', due_date: null, completed: false })).toEqual({ title: 'The title must be at most 120 characters.' })
})

it('characterizes validateTodo for case 3', () => {
  expect(validateTodo({ title: 'task', description: '', priority: 'low', due_date: null, completed: false })).toEqual({})
})

it('characterizes formatDate for case 0', () => {
  expect(formatDate('2026-10-08')).toEqual('8 Oct 2026')
})

it('rejects an oversized description and an impossible due date', () => {
  expect(
    validateTodo({
      title: 'task',
      description: 'x'.repeat(2001),
      priority: 'medium',
      due_date: '2026-02-31',
      completed: false,
    }),
  ).toEqual({
    description: 'The description must be at most 2000 characters.',
    due_date: 'Enter a valid date.',
  })
})

it('sorts tasks with a due date ahead of tasks without one', () => {
  const later = { ...base, id: 2, due_date: '2026-10-20' }
  const sooner = { ...base, id: 3, due_date: '2026-10-03' }
  expect(selectTodos([later, base, sooner], 'all', '', 'due')).toEqual([
    sooner,
    later,
    base,
  ])
})
