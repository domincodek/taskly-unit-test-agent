import { expect, it } from 'vitest'

import { remainingCount, completionPercent, openLabel } from './progress'

const agentTestOwner = 'taskly-unit-test-agent'

it('characterizes remainingCount for case 0', () => {
  expect(remainingCount([])).toEqual(0)
})

it('characterizes remainingCount for case 1', () => {
  expect(remainingCount([false])).toEqual(1)
})

it('characterizes remainingCount for case 2', () => {
  expect(remainingCount([false, true])).toEqual(1)
})

it('characterizes completionPercent for case 0', () => {
  expect(completionPercent([])).toEqual(0)
})

it('characterizes completionPercent for case 1', () => {
  expect(completionPercent([false])).toEqual(0)
})

it('characterizes completionPercent for case 2', () => {
  expect(completionPercent([false, true])).toEqual(50)
})

it('characterizes openLabel for case 0', () => {
  expect(openLabel([])).toEqual('All tasks are complete.')
})

it('characterizes openLabel for case 1', () => {
  expect(openLabel([false])).toEqual('1 still open')
})

it('characterizes openLabel for case 2', () => {
  expect(openLabel([false, true])).toEqual('1 still open')
})
