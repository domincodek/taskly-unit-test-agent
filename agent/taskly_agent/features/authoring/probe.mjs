import { readFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'

const modulePath = process.argv[2]
const payload = JSON.parse(readFileSync(process.argv[3], 'utf8'))
const loaded = await import(pathToFileURL(modulePath).href)
const results = []

for (const testCase of payload.cases) {
  const fn = loaded[testCase.function]
  if (typeof fn !== 'function') {
    results.push({ id: testCase.id, ok: false, error: 'TypeError', message: 'missing export' })
    continue
  }
  try {
    const value = await fn(...testCase.args)
    results.push({
      id: testCase.id,
      ok: true,
      value: value === undefined ? null : value,
      undefined: value === undefined,
    })
  } catch (error) {
    results.push({
      id: testCase.id,
      ok: false,
      error: error instanceof Error ? error.name : 'Error',
      message: error instanceof Error ? error.message : String(error),
    })
  }
}

process.stdout.write(JSON.stringify(results))
