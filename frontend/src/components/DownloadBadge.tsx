import { Badge } from '@mantine/core';

export function DownloadBadge({ status }: { status: string | null | undefined }) {
  if (!status) {
    return <Badge color="gray" variant="light" size="sm">pending</Badge>;
  }

  const colorMap: Record<string, string> = {
    completed: 'green',
    downloading: 'blue',
    queued: 'cyan',
    pending: 'gray',
    failed: 'red',
    not_found: 'orange',
    searching: 'violet',
  };

  return (
    <Badge color={colorMap[status] || 'gray'} variant="light" size="sm">
      {status}
    </Badge>
  );
}