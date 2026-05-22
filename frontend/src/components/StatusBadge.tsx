import { Badge } from '@mantine/core';

const statusColors: Record<string, string> = {
  synced: 'green',
  syncing: 'yellow',
  error: 'red',
  pending: 'gray',
  queued: 'blue',
  searching: 'violet',
  downloading: 'cyan',
  completed: 'green',
  failed: 'red',
  not_found: 'orange',
};

export function StatusBadge({ status }: { status: string | null | undefined }) {
  const color = statusColors[status ?? ''] || 'gray';
  return (
    <Badge color={color} variant="light" size="sm">
      {status ?? 'unknown'}
    </Badge>
  );
}