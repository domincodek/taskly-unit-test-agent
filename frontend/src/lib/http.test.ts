import { afterEach, expect, it, vi } from 'vitest'

import { request } from './http'

const agentTestOwner = 'taskly-unit-test-agent'

afterEach(() => vi.unstubAllGlobals())

it('returns json from a successful response', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'ok' }),
    }),
  )
  await expect(request('/health')).resolves.toEqual({ status: 'ok' })
  expect(fetch).toHaveBeenCalledWith('/api/health', {
    headers: { 'Content-Type': 'application/json' },
  })
})

it('returns undefined when the server has no content', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: async () => {
        throw new Error('no body')
      },
    }),
  )
  await expect(request('/todos/1', { method: 'DELETE' })).resolves.toBeUndefined()
})

it('explains a validation error', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({}),
    }),
  )
  await expect(request('/todos', { method: 'POST' })).rejects.toThrow(
    'Check the task details: title up to 120 characters, description up to 2000 characters, and a valid due date.',
  )
})

it('uses a string error detail from the server', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Title is required.' }),
    }),
  )
  await expect(request('/todos')).rejects.toThrow('Title is required.')
})

it('falls back when the server sends an unexpected error', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => null,
    }),
  )
  await expect(request('/todos')).rejects.toThrow('The operation failed. Please try again.')
})

it('reports that the server is unreachable', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network')))
  await expect(request('/todos')).rejects.toThrow('Cannot connect to the server. Please try again.')
})

it('preserves an aborted request', async () => {
  const error = new DOMException('aborted', 'AbortError')
  const signal = AbortSignal.abort()
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(error))
  await expect(request('/todos', { signal })).rejects.toBe(error)
})
