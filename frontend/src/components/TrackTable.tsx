import { Table, Text, Group } from '@mantine/core';
import { Track } from '../api/playlists';
import { DownloadBadge } from './DownloadBadge';

interface TrackTableProps {
  tracks: Track[];
}

function formatDuration(ms: number | null): string {
  if (!ms) return '--:--';
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}:${sec.toString().padStart(2, '0')}`;
}

export function TrackTable({ tracks }: TrackTableProps) {
  const rows = tracks.map((track) => (
    <Table.Tr key={track.id}>
      <Table.Td style={{ width: 40 }}>{track.position + 1}</Table.Td>
      <Table.Td>
        <Text size="sm" fw={500}>{track.title}</Text>
      </Table.Td>
      <Table.Td>
        <Text size="sm" c="dimmed">{track.artist}</Text>
      </Table.Td>
      <Table.Td>
        <Text size="sm" c="dimmed">{track.album || '-'}</Text>
      </Table.Td>
      <Table.Td style={{ width: 80 }}>
        <Text size="sm" c="dimmed">{formatDuration(track.duration_ms)}</Text>
      </Table.Td>
      <Table.Td style={{ width: 120 }}>
        <DownloadBadge status={track.download_status} />
      </Table.Td>
      <Table.Td style={{ width: 60 }}>
        {track.removed_from_spotify ? (
          <Text size="xs" c="red">Removed</Text>
        ) : null}
      </Table.Td>
    </Table.Tr>
  ));

  return (
    <Table>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>#</Table.Th>
          <Table.Th>Title</Table.Th>
          <Table.Th>Artist</Table.Th>
          <Table.Th>Album</Table.Th>
          <Table.Th>Duration</Table.Th>
          <Table.Th>Status</Table.Th>
          <Table.Th></Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>{rows}</Table.Tbody>
    </Table>
  );
}