import { QueryClient } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'

import { AppProviders } from './AppProviders'

const agentTestOwner = 'taskly-unit-test-agent'

it('renders children inside the application providers', () => {
  const client = new QueryClient()
  render(
    <AppProviders client={client}>
      <p>Ready</p>
    </AppProviders>,
  )
  expect(screen.getByText('Ready')).toBeVisible()
})
