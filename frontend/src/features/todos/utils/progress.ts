export function remainingCount(completed: boolean[]): number {
  return completed.filter((item) => !item).length
}

export function completionPercent(completed: boolean[]): number {
  if (completed.length === 0) return 0
  const done = completed.filter(Boolean).length
  return Math.round((done * 100) / completed.length)
}
