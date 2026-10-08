import { render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'

import { TaskProgress } from './TaskProgress'

const agentTestOwner = 'taskly-unit-test-agent'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))

it('shows the alternate copy', () => {
  render(<TaskProgress complete={false} />)
  expect(screen.getAllByText('Some tasks are still open.').length).toBeGreaterThan(0)
})

it('shows the matching copy', () => {
  render(<TaskProgress complete />)
  expect(screen.getByText('All tasks are complete.')).toBeVisible()
})
