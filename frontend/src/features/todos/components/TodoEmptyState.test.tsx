import userEvent from '@testing-library/user-event'

import { render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'

import { TodoEmptyState } from './TodoEmptyState'

const agentTestOwner = 'taskly-unit-test-agent'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))

it('shows the alternate copy', () => {
  render(<TodoEmptyState hasTodos={false} disabled={false} onCreate={vi.fn()} />)
  expect(screen.getAllByText('Add your first task').length).toBeGreaterThan(0)
  expect(screen.getAllByText('Write down what you need to do and get started.').length).toBeGreaterThan(0)
})

it('shows the matching copy', () => {
  render(<TodoEmptyState hasTodos disabled={false} onCreate={vi.fn()} />)
  expect(screen.getByText('No matching tasks')).toBeVisible()
  expect(screen.getByText('Change the status filter or search to find your tasks.')).toBeVisible()
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
})

it('forwards the requested action', async () => {
  const user = userEvent.setup()
  const onCreate = vi.fn()
  render(<TodoEmptyState hasTodos={false} disabled={false} onCreate={onCreate} />)
  await user.click(screen.getByRole('button'))
  expect(onCreate).toHaveBeenCalledTimes(1)
})

it('blocks the action while the view is disabled', () => {
  render(<TodoEmptyState hasTodos={false} disabled onCreate={vi.fn()} />)
  expect(screen.getByRole('button')).toBeDisabled()
})
