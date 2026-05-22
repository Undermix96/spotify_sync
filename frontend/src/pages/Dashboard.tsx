import { useState, useEffect } from 'react';
import { Container, Title, Button, Group, SimpleGrid, Text, Paper, Loader } from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { PlaylistCard } from '../components/PlaylistCard';
import { AddPlaylistModal } from '../components/AddPlaylistModal';
import { usePlaylists } from '../hooks/usePlaylists';
import { statsApi, Stats } from '../api/settings';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export default function Dashboard() {
  const { playlists, loading, add, remove, sync } = usePlaylists();
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    statsApi.get().then(setStats).catch(() => {});
  }, [playlists]);

  return (
    <Container fluid>
      <Group justify="space-between" mb="lg">
        <Title order={3}>Dashboard</Title>
        <Button
          leftSection={<IconPlus size={18} />}
          onClick={() => setAddModalOpen(true)}
        >
          Add Playlist
        </Button>
      </Group>

      {stats && (
        <SimpleGrid cols={{ base: 2, sm: 4 }} mb="lg">
          <Paper withBorder p="md" radius="md">
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Playlists</Text>
            <Text size="xl" fw={700}>{stats.total_playlists}</Text>
          </Paper>
          <Paper withBorder p="md" radius="md">
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Spotify Tracks</Text>
            <Text size="xl" fw={700}>{stats.total_tracks_spotify}</Text>
          </Paper>
          <Paper withBorder p="md" radius="md">
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Downloaded</Text>
            <Text size="xl" fw={700}>{stats.total_tracks_downloaded}</Text>
          </Paper>
          <Paper withBorder p="md" radius="md">
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Active Downloads</Text>
            <Text size="xl" fw={700} c={stats.active_downloads > 0 ? 'blue' : undefined}>
              {stats.active_downloads}
            </Text>
          </Paper>
          <Paper withBorder p="md" radius="md">
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Local Tracks</Text>
            <Text size="xl" fw={700}>{stats.local_tracks}</Text>
          </Paper>
          <Paper withBorder p="md" radius="md">
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>Disk Usage</Text>
            <Text size="xl" fw={700}>{formatBytes(stats.disk_usage_bytes)}</Text>
          </Paper>
        </SimpleGrid>
      )}

      {loading ? (
        <Loader />
      ) : playlists.length === 0 ? (
        <Text c="dimmed" ta="center" py="xl">
          No playlists yet. Click "Add Playlist" to get started.
        </Text>
      ) : (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
          {playlists.map((pl) => (
            <PlaylistCard
              key={pl.id}
              playlist={pl}
              onSync={(id) => sync(id).catch(() => {})}
              onRemove={(id) => remove(id).catch(() => {})}
            />
          ))}
        </SimpleGrid>
      )}

      <AddPlaylistModal
        opened={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        onSubmit={async (url) => { await add(url); }}
      />
    </Container>
  );
}