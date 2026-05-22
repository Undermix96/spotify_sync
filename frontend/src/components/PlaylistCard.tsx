import { Card, Group, Text, Progress, ActionIcon, Tooltip } from '@mantine/core';
import { IconRefresh, IconTrash, IconExternalLink } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { Playlist } from '../api/playlists';
import { StatusBadge } from './StatusBadge';

interface PlaylistCardProps {
  playlist: Playlist;
  onSync: (id: number) => void;
  onRemove: (id: number) => void;
}

export function PlaylistCard({ playlist, onSync, onRemove }: PlaylistCardProps) {
  const navigate = useNavigate();
  const percent = playlist.track_count > 0
    ? Math.round((playlist.downloaded_count / playlist.track_count) * 100)
    : 0;

  const lastSync = playlist.last_synced
    ? new Date(playlist.last_synced).toLocaleString()
    : 'Never';

  return (
    <Card
      padding="md"
      radius="md"
      style={{ cursor: 'pointer' }}
      onClick={() => navigate(`/playlist/${playlist.id}`)}
    >
      <Group justify="space-between" mb="xs">
        <Text fw={600} size="lg" lineClamp={1}>{playlist.name}</Text>
        <Group gap={4}>
          <Tooltip label="Sync now">
            <ActionIcon
              variant="subtle"
              color="blue"
              onClick={(e) => { e.stopPropagation(); onSync(playlist.id); }}
            >
              <IconRefresh size={16} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Remove">
            <ActionIcon
              variant="subtle"
              color="red"
              onClick={(e) => { e.stopPropagation(); onRemove(playlist.id); }}
            >
              <IconTrash size={16} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>

      <Group gap="xs" mb="xs">
        <Text size="sm" c="dimmed">{playlist.owner_name || 'unknown'}</Text>
        <StatusBadge status={playlist.last_synced ? 'synced' : 'pending'} />
      </Group>

      <Group gap="xs" mb={5}>
        <Text size="sm">{playlist.downloaded_count}/{playlist.track_count} tracks</Text>
      </Group>

      <Progress value={percent} color={percent === 100 ? 'green' : percent > 50 ? 'yellow' : 'blue'} size="sm" />

      <Text size="xs" c="dimmed" mt="xs">
        Last sync: {lastSync}
      </Text>
    </Card>
  );
}