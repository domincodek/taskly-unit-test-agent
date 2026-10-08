import { Text } from '../../../design-system'

export function TaskProgress({ complete }: { complete: boolean }) {
  return (
    <Text muted>
      {complete ? 'All tasks are complete.' : 'Some tasks are still open.'}
    </Text>
  )
}
