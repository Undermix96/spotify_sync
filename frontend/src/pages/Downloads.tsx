import { Container, Title, Table, Text, Group, Badge, Progress, ActionIcon, Tooltip, Loader } from '@mantine/core';
import { IconPlayerPlay, IconX } from '@tabler/icons-react';
import { useDownloads } from '../hooks/useDownloads';
import { StatusBadge } from '../components/StatusBadge';

export default function Downloads() {
  const { downloads, loading, retry, cancel } = useDownloads();

  if (loading) return <Container fluid><Loader /></Container>;

  return (
    <Container fluid>
      <Title order={3} mb="lg">Downloads</Title>

      {downloads.length === 0 ? (
        <Text c="dimmed" ta="center" py="xl">No download activity.</Text>
      ) : (
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Track</Table.Th>
              <Table.Th>Playlist</Table.Th>
              <Table.Th>Source</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Progress</Table.Th>
              <Table.Th>Retries</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {downloads.map((d) => (
              <Table.Tr key={d.id}>
                <Table.Td>
                  <Text size="sm" fw={500}>
                    {d.track_title || 'Unknown'}
                  </Text>
                  <Text size="xs" c="dimmed">{d.track_artist || ''}</Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c="dimmed">{d.playlist_name || '-'}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge variant="light" color={d.source === 'slskd' ? 'violet' : 'blue'} size="sm">
                    {d.source || '-'}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <StatusBadge status={d.status} />
                </Table.Td>
                <Table.Td style={{ minWidth: 120 }}>
                  {d.status === 'downloading' ? (
                    <Progress value={d.progress} size="sm" animated />
                  ) : d.status === 'completed' ? (
                    <Progress value={100} size="sm" color="green" />
                  ) : (
                    <Text size="sm" c="dimmed">-</Text>
                  )}
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c="dimmed">{d.retry_count}/{d.max_retries}</Text>
                </Table.Td>
                <Table.Td>
                  <Group gap={4}>
                    {d.status === 'failed' || d.status === 'not_found' ? (
                      <Tooltip label="Retry">
                        <ActionIcon variant="subtle" color="blue" onClick={() => retry(d.id)}>
                          <IconPlayerPlay size={16} />
                        </ActionIcon>
                      </Tooltip>
                    ) : null}
                    {(d.status === 'queued' || d.status === 'downloading' || d.status === 'pending') ? (
                      <Tooltip label="Cancel">
                        <ActionIcon variant="subtle" color="red" onClick={() => cancel(d.id)}>
                          <IconX size={16} />
                        </ActionIcon>
                      </Tooltip>
                    ) : null}
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Container>
  );
}